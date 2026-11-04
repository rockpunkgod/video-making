"""EP01 V3 — natural/soft audio remaster; no recycled V2 synthetic-FX stem.

One-shot script on the isolated ep01-v3-soft-sound-20261103 branch.
- Original MP4 audio is the ONLY baseline soundtrack (voice + original music).
- Natural Kenney RPG Audio CC0 recordings replace V2 electronic FX.
- Cue timing is read from an explicit manifest, or conservatively inferred
  from scene changes for a DRAFT; inferred cue placement needs review.
- The original 4K/24fps video bitstream is copied without re-encoding.
- Does not overwrite the original, V2, or an existing output.
- A successful encoding is NOT a listening review or publication approval.

Requires: Python 3.10+, FFmpeg/ffprobe on PATH. No pip dependencies.
    python scripts/ep01_v3_soft_audio.py --original "英语有画说_EP01_首发候选_4K24.mp4" --out "EP01_V3_自然拟物_4K24.mp4"

To use an already-downloaded CC0 archive:
    ... --foley-zip "RPGsounds_Kenney.zip"

Optional explicit cue sheet:
    {"cues":[{"at":12.5,"material":"paper","gain_db":-27},
             {"at":32.0,"material":"tap","gain_db":-26}]}

Material names: paper, swish, tap, settle.
Sources: Kenney RPG Audio (CC0)
  https://kenney.nl/assets/rpg-audio
  https://opengameart.org/content/50-rpg-sound-effects
"""

from __future__ import annotations

import argparse
import hashlib
import json
from fractions import Fraction
from pathlib import Path
import re
import subprocess
import sys
import tempfile
from urllib.request import Request, urlopen
from zipfile import ZipFile, BadZipFile

PACK_URL = "https://opengameart.org/sites/default/files/RPGsounds_Kenney.zip"
PACK_CREDIT = "Kenney RPG Audio, CC0-1.0, https://kenney.nl/assets/rpg-audio"
MATERIALS = {
    "paper": ("bookFlip1.ogg", -27.5),
    "swish": ("cloth2.ogg", -29.0),
    "tap": ("bookPlace1.ogg", -26.5),
    "settle": ("bookClose.ogg", -29.0),
}
AUTO_SEQUENCE = ("paper", "swish", "tap", "paper", "settle")
TIME_RE = re.compile(r"pts_time:\s*([0-9]+(?:\.[0-9]+)?)")


def command(argv: list[str], *, timeout: int = 900) -> subprocess.CompletedProcess[str]:
    p = subprocess.run(argv, text=True, encoding="utf-8", errors="replace",
                       stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                       check=False, timeout=timeout)
    if p.returncode:
        raise RuntimeError(
            f"Command failed ({p.returncode}): {argv[:6]}\n"
            + (p.stderr or p.stdout)[-2500:]
        )
    return p


def inspect(path: Path) -> dict:
    return json.loads(command([
        "ffprobe", "-v", "error", "-show_entries",
        "format=duration:stream=codec_type,codec_name,width,height,r_frame_rate,nb_frames",
        "-of", "json", str(path),
    ]).stdout)


def video_spec(meta: dict) -> tuple[dict, dict, float]:
    video = next((s for s in meta["streams"] if s["codec_type"] == "video"), None)
    audio = next((s for s in meta["streams"] if s["codec_type"] == "audio"), None)
    if video is None or audio is None:
        raise RuntimeError("Original video must contain a video stream and baseline soundtrack.")
    fps = Fraction(video.get("r_frame_rate", "0"))
    if (video.get("width"), video.get("height")) != (3840, 2160) or fps != 24:
        raise RuntimeError("Expected 3840x2160, 24fps; actual: " + str(video))
    return video, audio, float(meta["format"]["duration"])


def suggest_times(original: Path, duration: float, threshold: float = 0.11) -> list[float]:
    """Approximate V3 draft cues from cut/motion changes; not hand-authored sync."""
    vf = f"fps=2,scale=320:-2,select='gt(scene,{threshold})',showinfo"
    p = command(["ffmpeg", "-hide_banner", "-nostdin", "-loglevel", "info",
                 "-i", str(original), "-an", "-sn", "-vf", vf,
                 "-f", "null", "-"], timeout=1200)
    detected: list[float] = []
    for line in p.stderr.splitlines():
        if "showinfo" not in line or "pts_time:" not in line:
            continue
        m = TIME_RE.search(line)
        if m:
            t = float(m.group(1))
            if 4.0 <= t <= duration - 4.0:
                detected.append(t)
    # Distinct and conservative: a small number of gentle physical cues.
    chosen: list[float] = []
    for t in sorted(set(detected)):
        if not chosen or t - chosen[-1] >= 8.0:
            chosen.append(t)
    if len(chosen) > 20:
        stride = len(chosen) / 20.0
        chosen = [chosen[int(k * stride)] for k in range(20)]
    return chosen


def cue_sheet(path: Path | None, original: Path, duration: float) -> tuple[list[dict], str]:
    if path is None:
        times = suggest_times(original, duration)
        if not times:
            raise RuntimeError(
                "No detectable edit cues. Supply --cues with real timestamps; "
                "no arbitrary sound placement or old electronic FX will be inserted."
            )
        cues = [
            {"at": round(t, 3), "material": AUTO_SEQUENCE[i % len(AUTO_SEQUENCE)],
             "gain_db": MATERIALS[AUTO_SEQUENCE[i % len(AUTO_SEQUENCE)]][1],
             "placement": "automatic_scene_change_unreviewed"}
            for i, t in enumerate(times)
        ]
        return cues, "automatic_scene_change_unreviewed"

    data = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(data, dict) or not isinstance(data.get("cues"), list):
        raise ValueError('Cue sheet must be {"cues": [...]}')
    cues = []
    for i, raw in enumerate(data["cues"]):
        if not isinstance(raw, dict):
            raise ValueError(f"Cue {i + 1} is not an object.")
        if "file" in raw:
            raise ValueError("Legacy file-based FX are disabled to prevent reuse of V2 zaps.")
        mat = raw.get("material")
        if mat not in MATERIALS:
            raise ValueError(f"Cue {i + 1} has unknown material: {mat}")
        t = float(raw["at"])
        gain = float(raw.get("gain_db", MATERIALS[mat][1]))
        if not (0.0 <= t < duration - 0.3):
            raise ValueError(f"Cue {i + 1} is outside original timeline: {t}")
        if not (-45.0 <= gain <= -18.0):
            raise ValueError(f"Cue {i + 1} too loud for gentle mastering: {gain}")
        cues.append({"at": round(t, 3), "material": mat, "gain_db": gain,
                     "placement": "explicit_unlistened"})
    if len(cues) > 80:
        raise ValueError("More than 80 cues is not a gentle sound design.")
    return sorted(cues, key=lambda x: x["at"]), "explicit_unlistened"


def prepare_foley(zip_source: Path | None, folder: Path) -> tuple[dict[str, Path], dict]:
    if zip_source is not None:
        raw = zip_source.read_bytes()
        origin = str(zip_source.resolve())
    else:
        req = Request(PACK_URL, headers={"User-Agent": "EP01-natural-master/3.0"})
        try:
            with urlopen(req, timeout=45) as r:
                raw = r.read(5_000_001)
        except Exception as exc:
            raise RuntimeError(
                "Cannot download CC0 sample pack. Get RPGsounds_Kenney.zip from "
                "https://opengameart.org/content/50-rpg-sound-effects "
                "and pass --foley-zip PATH."
            ) from exc
        if len(raw) > 5_000_000:
            raise RuntimeError("Foley archive unexpectedly exceeds safety size limit.")
        origin = PACK_URL
    zip_path = folder / "kenney_rpg.zip"
    zip_path.write_bytes(raw)
    bank: dict[str, Path] = {}
    try:
        with ZipFile(zip_path) as z:
            names = z.namelist()
            for material, (filename, _) in MATERIALS.items():
                matches = [name for name in names
                           if name.replace("\\", "/").rsplit("/", 1)[-1].lower() == filename.lower()]
                if len(matches) != 1:
                    raise RuntimeError(f"Missing/ambiguous CC0 sound {filename}: {len(matches)} matches.")
                info = z.getinfo(matches[0])
                if info.file_size > 2_000_000:
                    raise RuntimeError(f"Suspicious sample size: {filename}")
                target = folder / filename
                target.write_bytes(z.read(info))
                bank[material] = target
    except BadZipFile as exc:
        raise RuntimeError("Downloaded file is not a valid Kenney audio ZIP.") from exc
    return bank, {
        "title": "Kenney RPG Audio",
        "license": "CC0-1.0",
        "source": origin,
        "upstream": PACK_CREDIT,
        "archive_sha256": hashlib.sha256(raw).hexdigest(),
        "used_files": {k: v.name for k, v in bank.items()},
    }


def render(picture: Path, original: Path, bank: dict[str, Path],
           cues: list[dict], output: Path, duration: float) -> None:
    """Use V2 picture unchanged and clean pre-V2 audio; discard ALL V2 audio."""
    inputs = ["-i", str(picture), "-i", str(original)]
    for cue in cues:
        inputs += ["-i", str(bank[cue["material"]])]

    source = (f"[1:a:0]aresample=48000,aformat=channel_layouts=stereo,apad,"
              f"atrim=duration={duration:.6f},asetpts=N/SR/TB[original]")
    filters = [source]
    labels = ["[original]"]
    for i, cue in enumerate(cues, 2):
        delay = round(cue["at"] * 1000)
        label = f"[fx{i}]"
        filters.append(
            f"[{i}:a:0]aresample=48000,aformat=channel_layouts=stereo,"
            f"highpass=f=75,lowpass=f=5300,volume={cue['gain_db']:.2f}dB,"
            f"afade=t=in:st=0:d=0.012,adelay={delay}|{delay}{label}"
        )
        labels.append(label)

    filters.append(
        "".join(labels) +
        f"amix=inputs={len(labels)}:duration=first:normalize=0:dropout_transition=0,"
        f"atrim=duration={duration:.6f},"
        "loudnorm=I=-14:TP=-1.5:LRA=9[mix]"
    )
    command([
        "ffmpeg", "-hide_banner", "-nostdin", "-y", "-v", "warning",
        *inputs,
        "-filter_complex", ";".join(filters),
        "-map", "0:v:0", "-map", "[mix]",
        "-map_metadata", "0", "-map_chapters", "0",
        "-c:v", "copy", "-c:a", "aac", "-b:a", "320k",
        "-ar", "48000", "-ac", "2",
        "-movflags", "+faststart",
        "-t", f"{duration:.6f}", str(output),
    ], timeout=1800)


def verify_output(picture_meta: dict, original_meta: dict, final: dict, duration: float) -> dict:
    ov, _, _ = video_spec(picture_meta)
    _, oa, _ = video_spec(original_meta)
    fv, fa, actual_duration = video_spec(final)
    if fv.get("codec_name") != ov.get("codec_name"):
        raise RuntimeError("Video codec changed unexpectedly.")
    if ov.get("nb_frames") and fv.get("nb_frames"):
        if ov["nb_frames"] != fv["nb_frames"]:
            raise RuntimeError("Frame count changed unexpectedly.")
    if abs(actual_duration - duration) > 0.15:
        raise RuntimeError(f"Duration drift: {duration:.3f}s -> {actual_duration:.3f}s")
    if fa.get("codec_name") != "aac":
        raise RuntimeError("Master does not have AAC audio.")
    return {
        "original_video_codec": ov["codec_name"],
        "new_video_codec": fv["codec_name"],
        "original_audio_codec": oa["codec_name"],
        "new_audio_codec": fa["codec_name"],
        "duration_before": duration,
        "duration_after": actual_duration,
        "video_stream_policy": "ffmpeg -c:v copy; video not recompressed",
    }


def main() -> None:
    p = argparse.ArgumentParser(description="EP01 V3 authentic Foley 4K sound rebuild")
    p.add_argument("--original", required=True, type=Path, help="Clean original MP4 for audio only")
    p.add_argument("--picture", type=Path, help="Existing V2 MP4, VIDEO ONLY; its audio is discarded")
    p.add_argument("--out", required=True, type=Path)
    p.add_argument("--cues", type=Path, help="Explicit cue timings; otherwise scene-change draft")
    p.add_argument("--foley-zip", type=Path, help="Offline Kenney CC0 RPG pack")
    p.add_argument("--stem", type=Path, help="Legacy flag; never used to avoid V2 zaps")
    args = p.parse_args()

    original = args.original.resolve()
    picture = args.picture.resolve() if args.picture else original
    output = args.out.resolve()
    if not original.is_file():
        p.error("Original MP4 not found.")
    if not picture.is_file():
        p.error("Picture MP4 not found.")
    if output.exists() or output in (original, picture):
        p.error("Output already exists or equals an input; no files will be overwritten.")
    if args.foley_zip and not args.foley_zip.is_file():
        p.error("--foley-zip file not found.")
    if args.stem:
        print("SAFETY: ignoring --stem. V2's processed music/FX track is NOT used.", file=sys.stderr)

    before = inspect(original)
    _, _, clean_audio_duration = video_spec(before)
    picture_before = inspect(picture)
    _, _, duration = video_spec(picture_before)
    if abs(clean_audio_duration - duration) > 0.50:
        raise RuntimeError(
            f"Original audio and V2 video timelines differ too much: "
            f"{clean_audio_duration:.3f}s vs {duration:.3f}s; cannot safely re-sync."
        )
    cues, mode = cue_sheet(args.cues.resolve() if args.cues else None, picture, duration)
    if not cues:
        raise RuntimeError("Empty cue sheet; V3 must contain natural Foley cues.")
    output.parent.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory(prefix="ep01-v3-natural-") as d:
        bank, provenance = prepare_foley(args.foley_zip, Path(d))
        render(picture, original, bank, cues, output, duration)

    validation = verify_output(picture_before, before, inspect(output), duration)
    receipt = {
        "status": "ENCODED_NOT_LISTENED_NOT_RELEASE_APPROVED",
        "output": str(output),
        "original": str(original),
        "picture_source": str(picture),
        "source_audio": "clean original MP4 only — V2 audio explicitly excluded",
        "foley_source": provenance,
        "cue_mode": mode,
        "cue_count": len(cues),
        "cues": cues,
        "validation": validation,
        "subjective_review": "REQUIRED: listen with headphones; approve any auto cues.",
        "visual_review": "REQUIRED: original encoded film still needs scene review.",
        "publication_approval": False,
    }
    report = output.with_suffix(".v3_receipt.json")
    report.write_text(json.dumps(receipt, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"output": str(output), "receipt": str(report),
                      "cue_mode": mode, "cue_count": len(cues),
                      "status": receipt["status"]}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
