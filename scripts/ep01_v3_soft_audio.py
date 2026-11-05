"""EP01 V3 — natural/soft audio remaster; no recycled V2 synthetic-FX stem.

One-shot script on the isolated ep01-v3-soft-sound-20261103 branch.
- An independent clean narration stem is mandatory for an OPUS-free candidate.
- V2 video is copied, V2 audio excluded; independently licensed music is optional.
- Kenney RPG Audio CC0 recordings replace old effects.
- Cue timing is read from an explicit manifest, or conservatively inferred
  from scene changes for a DRAFT; inferred cue placement needs review.
- The original 4K/24fps video bitstream is copied without re-encoding.
- Does not overwrite the original, V2, or an existing output.
- A successful encoding is NOT a listening review or publication approval.

Requires: Python 3.10+, FFmpeg/ffprobe on PATH. No pip dependencies.
    python scripts/ep01_v3_soft_audio.py --picture "V2.mp4" --clean-voice "voice_only.flac" --out "V3.mp4"

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
           cues: list[dict], output: Path, duration: float,
           *, music: Path | None = None) -> None:
    """Copy V2 picture; mix separate narration, optional new music and CC0 Foley.

    Input 0's audio is not mapped. The caller must ensure that input 1 is an
    independent, effect-free narration stem for a purported OPUS-free version.
    """
    inputs = ["-i", str(picture), "-i", str(original)]
    fx_start = 2
    if music is not None:
        inputs += ["-i", str(music)]
        fx_start = 3
    for cue in cues:
        inputs += ["-i", str(bank[cue["material"]])]

    filters = [
        f"[1:a:0]aresample=48000,aformat=channel_layouts=stereo,"
        f"asetpts=PTS-STARTPTS,apad,atrim=duration={duration:.6f},"
        "asetpts=N/SR/TB[vo]"
    ]
    labels = ["[vo]"]
    if music is not None:
        # Keep music separate and duck it beneath the full-length voice track.
        filters += [
            "[vo]asplit=2[voice][key]",
            f"[2:a:0]aresample=48000,aformat=channel_layouts=stereo,"
            f"asetpts=PTS-STARTPTS,highpass=f=65,lowpass=f=7500,"
            f"volume=-20dB,apad,atrim=duration={duration:.6f},"
            f"afade=t=in:st=0:d=1.8,"
            f"afade=t=out:st={max(0.0, duration - 2.5):.3f}:d=2.5[bed]",
            "[bed][key]sidechaincompress=threshold=0.04:ratio=4:"
            "attack=25:release=350[duck]"
        ]
        labels = ["[voice]", "[duck]"]

    for i, cue in enumerate(cues, fx_start):
        delay = round(cue["at"] * 1000)
        label = f"[fx{i}]"
        filters.append(
            f"[{i}:a:0]aresample=48000,aformat=channel_layouts=stereo,"
            f"highpass=f=75,lowpass=f=5300,volume={cue['gain_db']:.2f}dB,"
            f"afade=t=in:st=0:d=0.012,adelay={delay}|{delay}{label}"
        )
        labels.append(label)

    filters.append(
        "".join(labels)
        + f"amix=inputs={len(labels)}:duration=first:normalize=0:dropout_transition=0,"
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
    oa = next((s for s in original_meta["streams"] if s["codec_type"] == "audio"), None)
    if oa is None:
        raise RuntimeError("Narration stem has no audio stream.")
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
    p = argparse.ArgumentParser(description="EP01 V3: preserve V2 4K video; rebuild all audio")
    p.add_argument("--picture", required=True, type=Path, help="Existing V2 video; its audio is never mapped")
    p.add_argument("--clean-voice", type=Path,
                   help="Independent clean narration stem covering full timeline; for OPUS-free candidate")
    p.add_argument("--music", type=Path, help="Optional independently licensed new music, NOT older mixed bed")
    p.add_argument("--original", type=Path, help="Previous mixed MP4 for explicit UNSAFE preview only")
    p.add_argument("--draft-use-original-audio", action="store_true",
                   help="Preview only: older original mix could contain OPUS sound effects")
    p.add_argument("--out", required=True, type=Path)
    p.add_argument("--cues", type=Path, help="Reviewed cue timings; otherwise auto unreviewed draft")
    p.add_argument("--foley-zip", type=Path, help="Offline Kenney CC0 RPG audio pack")
    p.add_argument("--stem", type=Path, help="Deprecated/ignored; never reuse V2 mixed stem")
    args = p.parse_args()

    picture = args.picture.resolve()
    output = args.out.resolve()
    if not picture.is_file():
        p.error("V2 picture file not found: " + str(picture))
    if args.clean_voice is not None and args.draft_use_original_audio:
        p.error("Choose --clean-voice OR --draft-use-original-audio, not both.")
    if args.clean_voice is not None:
        soundtrack = args.clean_voice.resolve()
        soundtrack_policy = "INDEPENDENT_CLEAN_NARRATION_ASSERTED__LISTENING_REQUIRED"
        draft_audio = False
    elif args.draft_use_original_audio and args.original is not None:
        soundtrack = args.original.resolve()
        soundtrack_policy = "UNSAFE_MIXED_ORIGINAL__OLD_OPUS_EFFECTS_MAY_REMAIN"
        draft_audio = True
    else:
        p.error(
            "Cannot guarantee removal of OPUS effects from a mixed audio track. "
            "Supply --clean-voice FULL_LENGTH_CLEAN_VOICE.wav, or for a NON-PUBLISHABLE "
            "draft only, --draft-use-original-audio --original ORIGINAL.mp4."
        )
    if not soundtrack.is_file():
        p.error("Narration source not found: " + str(soundtrack))
    if soundtrack == picture:
        p.error("Narration cannot be the same file as the V2 picture.")
    if output.exists() or output in (picture, soundtrack):
        p.error("Output already exists or equals an input; no original media is overwritten.")
    music = args.music.resolve() if args.music else None
    if music is not None:
        if not music.is_file() or music in (picture, soundtrack, output):
            p.error("Music must be an existing independent file, not V2/narration/output.")
    if args.foley_zip and not args.foley_zip.is_file():
        p.error("--foley-zip does not point to a file.")
    if args.stem:
        print("SAFETY: ignored --stem; neither V2 nor older OPUS mixed stems are used.",
              file=sys.stderr)

    before = inspect(picture)
    _, _, duration = video_spec(before)
    source_meta = inspect(soundtrack)
    if not any(s["codec_type"] == "audio" for s in source_meta["streams"]):
        p.error("Narration source has no audio stream.")
    voice_duration = float(source_meta["format"]["duration"])
    if abs(voice_duration - duration) > 0.50:
        raise RuntimeError(
            f"Voice and V2 timeline differ: {voice_duration:.3f}s versus "
            f"{duration:.3f}s. Rebuild full-duration timeline-aligned voice."
        )
    cues, mode = cue_sheet(args.cues.resolve() if args.cues else None, picture, duration)
    if not cues:
        raise RuntimeError("No natural Foley cues. Supply --cues with true timestamps.")
    output.parent.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory(prefix="ep01-v3-natural-") as d:
        bank, provenance = prepare_foley(args.foley_zip, Path(d))
        render(picture, soundtrack, bank, cues, output, duration, music=music)

    validation = verify_output(before, source_meta, inspect(output), duration)
    status = ("DRAFT_OLD_OPUS_EFFECTS_MAY_REMAIN" if draft_audio
              else "ENCODED_CLEAN_SOURCE_UNLISTENED")
    receipt = {
        "status": status,
        "output": str(output),
        "picture_source": str(picture),
        "audio_source": str(soundtrack),
        "audio_source_policy": soundtrack_policy,
        "v2_audio": "EXCLUDED",
        "opus_sound_effects_absent_verified": False,
        "music_source": str(music) if music is not None else None,
        "music_rights_review": "REQUIRED" if music is not None else "NO_EXTERNAL_MUSIC",
        "foley_source": provenance,
        "cue_mode": mode,
        "cue_count": len(cues),
        "cues": cues,
        "validation": validation,
        "listening_and_sync_review": "REQUIRED: full real EP01 film, headphones and phone",
        "publication_approval": False,
    }
    report = output.with_suffix(".v3_receipt.json")
    report.write_text(json.dumps(receipt, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"output": str(output), "receipt": str(report),
                      "cue_mode": mode, "cue_count": len(cues), "status": status},
                     ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
