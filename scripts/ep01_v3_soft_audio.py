"""EP01 V3 soft-audio rebuild (one-off; never edits the existing production chain).

Requires: Python 3.10+, numpy, scipy, FFmpeg/ffprobe on PATH.
Original film provides the untouched spoken track. The independent V2 music+FX
stem is spectrally separated to retain sustained music while reducing sharp
noisy/impact sounds. Real CC0 Foley is supplied via a small timestamp manifest.

Example:
  python -m pip install numpy scipy
  python scripts/ep01_v3_soft_audio.py ^
    --original "English_EP01_original_4K24.mp4" ^
    --stem "EP01_music_fx_stem.flac" ^
    --cues "EP01_v3_foley.json" ^
    --out "EP01_V3_soft_4K24.mp4"

This script cannot prove subjective sound quality. Listen to the encoded film.
"""
from __future__ import annotations

import argparse
from fractions import Fraction
import json
from pathlib import Path
import subprocess
import tempfile

import numpy as np
from scipy import ndimage, signal
from scipy.io import wavfile


def run(command: list[str], *, capture: bool = False) -> str:
    proc = subprocess.run(
        command,
        text=True,
        encoding="utf-8",
        errors="replace",
        stdout=subprocess.PIPE if capture else None,
        stderr=subprocess.PIPE if capture else None,
        check=False,
    )
    if proc.returncode:
        tail = (proc.stderr or "")[-3500:]
        raise RuntimeError(f"Command failed ({proc.returncode}): {' '.join(command[:8])}\n{tail}")
    return proc.stdout or ""


def probe(path: Path) -> dict:
    return json.loads(
        run(
            ["ffprobe", "-v", "error", "-show_entries",
             "format=duration:stream=index,codec_type,width,height,r_frame_rate,codec_name",
             "-of", "json", str(path)],
            capture=True,
        )
    )


def verify_original(path: Path) -> float:
    meta = probe(path)
    vs = next((s for s in meta["streams"] if s["codec_type"] == "video"), None)
    aud = next((s for s in meta["streams"] if s["codec_type"] == "audio"), None)
    if not vs or not aud:
        raise ValueError("Original MP4 must have both a video stream and the original narration audio.")
    fps = Fraction(vs.get("r_frame_rate", "0"))
    if (vs.get("width"), vs.get("height")) != (3840, 2160) or fps != 24:
        raise ValueError(f"Expected original 3840x2160/24; got {vs.get('width')}x{vs.get('height')}/{fps}.")
    return float(meta["format"]["duration"])


def clean_music_stem(stem: Path, destination: Path) -> dict:
    """Soft harmonic/percussive separation; suppress attacks, keep sustained music.

    Per channel: STFT -> horizontal/vertical median energy estimates ->
    conservative harmonic mask -> inverse STFT. Not a perfect stem separator;
    notably, a sustained electronic tone could remain.
    """
    decoded = destination.with_name("decoded_stem.wav")
    run(["ffmpeg", "-hide_banner", "-v", "error", "-y", "-i", str(stem),
         "-vn", "-ac", "2", "-ar", "32000", "-c:a", "pcm_f32le", str(decoded)])
    sr, samples = wavfile.read(decoded)
    if samples.ndim == 1:
        samples = np.column_stack((samples, samples))
    if sr != 32000 or samples.dtype != np.float32:
        raise ValueError("Unexpected FFmpeg stem decoding format.")
    cleaned = np.zeros_like(samples)
    for ch in range(2):
        f, t, spectrum = signal.stft(
            samples[:, ch], fs=sr, nperseg=2048, noverlap=1536,
            boundary="zeros", padded=True,
        )
        amplitude = np.abs(spectrum)
        harmonic = ndimage.median_filter(amplitude, size=(1, 31), mode="nearest")
        percussive = ndimage.median_filter(amplitude, size=(23, 1), mode="nearest")
        # Aggressively reject isolated vertical transients, including old zaps.
        h2 = harmonic ** 2
        mask = h2 / (h2 + 7.0 * percussive ** 2 + 1e-12)
        _, separated = signal.istft(
            spectrum * mask, fs=sr, nperseg=2048, noverlap=1536,
            input_onesided=True, boundary=True,
        )
        n = min(len(separated), len(samples))
        cleaned[:n, ch] = np.asarray(separated[:n], dtype=np.float32)
        del spectrum, amplitude, harmonic, percussive, h2, mask, separated
    wavfile.write(destination, sr, np.clip(cleaned, -0.99, 0.99))
    return {
        "sample_rate": sr,
        "channels": 2,
        "method": "STFT median harmonic mask + low-pass in mix",
        "note": "Not perceptually validated; the old FX cannot be guaranteed fully absent.",
    }


def read_cues(manifest: Path | None, duration: float) -> list[dict]:
    if manifest is None:
        return []
    payload = json.loads(manifest.read_text(encoding="utf-8"))
    if not isinstance(payload.get("cues"), list):
        raise ValueError("Cue manifest requires a 'cues' array.")
    out = []
    for index, item in enumerate(payload["cues"]):
        path = (manifest.parent / str(item["file"])).resolve()
        when = float(item["at"])
        gain = float(item.get("gain_db", -19))
        if not path.is_file() or not (0 <= when < duration):
            raise ValueError(f"Missing FX or invalid time at cue {index + 1}: {path} / {when}")
        if item.get("license", "").upper() != "CC0" or not item.get("source"):
            raise ValueError(f"Cue {index + 1} must record verified CC0 license and source URL.")
        if not (-45 <= gain <= -8):
            raise ValueError(f"FX gain must be gentle (-45 to -8 dB): cue {index + 1}")
        out.append({**item, "file": str(path), "at": when, "gain_db": gain})
    if len(out) > 80:
        raise ValueError("Too many cues for one EP01 pass.")
    return out


def render(original: Path, clean_stem: Path, cues: list[dict], out: Path, duration: float) -> None:
    inputs = ["-i", str(original), "-i", str(clean_stem)]
    for cue in cues:
        inputs += ["-i", cue["file"]]

    fade_out = max(0.0, duration - 3.0)
    filters = [
        "[0:a:0]aresample=48000,aformat=channel_layouts=stereo,asplit=2[voice][key]",
        "[1:a:0]aresample=48000,aformat=channel_layouts=stereo,"
        f"highpass=f=100,lowpass=f=3900,volume=-9dB,"
        f"afade=t=in:st=0:d=2,afade=t=out:st={fade_out:.3f}:d=3[bed]",
        "[bed][key]sidechaincompress=threshold=0.035:ratio=5:"
        "attack=20:release=350[duck]",
    ]
    sources = ["[voice]", "[duck]"]
    for index, cue in enumerate(cues, start=2):
        delay = round(cue["at"] * 1000)
        label = f"[fx{index}]"
        filters.append(
            f"[{index}:a:0]aresample=48000,aformat=channel_layouts=stereo,"
            f"volume={cue['gain_db']:.2f}dB,adelay={delay}|{delay}{label}"
        )
        sources.append(label)
    filters.append(
        "".join(sources)
        + f"amix=inputs={len(sources)}:duration=first:normalize=0:dropout_transition=0,"
        "loudnorm=I=-14:TP=-1.5:LRA=9,alimiter=limit=0.90[mix]"
    )
    run([
        "ffmpeg", "-hide_banner", "-v", "warning", "-n",
        *inputs,
        "-filter_complex", ";".join(filters),
        "-map", "0:v:0", "-map", "[mix]",
        "-map_metadata", "0", "-map_chapters", "0",
        "-c:v", "copy", "-c:a", "aac", "-b:a", "320k",
        "-ar", "48000", "-ac", "2",
        "-movflags", "+faststart", "-shortest",
        str(out),
    ])


def main() -> None:
    parser = argparse.ArgumentParser(description="EP01 V3: re-mix gently, retain 4K stream.")
    parser.add_argument("--original", type=Path, required=True)
    parser.add_argument("--stem", type=Path, required=True)
    parser.add_argument("--cues", type=Path, help="JSON with verified natural CC0 Foley cues")
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()

    original, stem, out = args.original.resolve(), args.stem.resolve(), args.out.resolve()
    if not original.is_file() or not stem.is_file():
        parser.error("Original video and independent music/FX FLAC must both exist.")
    if out.exists() or out in (original, stem):
        parser.error("Output must be a NEW file; never overwrite original or V2.")
    out.parent.mkdir(parents=True, exist_ok=True)
    duration = verify_original(original)
    cues = read_cues(args.cues.resolve() if args.cues else None, duration)
    with tempfile.TemporaryDirectory(prefix="ep01-v3-") as scratch:
        cleaned = Path(scratch) / "music_harmonic.wav"
        method = clean_music_stem(stem, cleaned)
        render(original, cleaned, cues, out, duration)

    final = probe(out)
    video = next(s for s in final["streams"] if s["codec_type"] == "video")
    audio = next(s for s in final["streams"] if s["codec_type"] == "audio")
    output_duration = float(final["format"]["duration"])
    if (video["width"], video["height"]) != (3840, 2160):
        raise RuntimeError("Output failed 4K verification.")
    if abs(output_duration - duration) > 0.15:
        raise RuntimeError(f"Output duration drift: {duration:.3f}s -> {output_duration:.3f}s")
    receipt = {
        "status": "ENCODED_NOT_LISTENED",
        "original": str(original),
        "stem": str(stem),
        "output": str(out),
        "duration_seconds": output_duration,
        "video": "3840x2160 24fps original video stream copied, not re-encoded",
        "audio_codec": audio["codec_name"],
        "foley_count": len(cues),
        "foley": cues,
        "music_processing": method,
        "publication_approval": False,
    }
    report = out.with_suffix(".v3_receipt.json")
    report.write_text(json.dumps(receipt, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps({"output": str(out), "receipt": str(report), "foley_count": len(cues)},
                     ensure_ascii=False, indent=2))
    if not cues:
        print("WARNING: no Foley cue manifest; this is a cleaned-bed preview, not a complete V3 sound design.")
    print("NEXT: listen to beginning / attention hits / payoffs / ending before publication.")


if __name__ == "__main__":
    main()
