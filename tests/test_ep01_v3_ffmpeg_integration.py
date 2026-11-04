"""Real FFmpeg smoke: V2 video packets stay, V2 audio is excluded.

Uses synthetic 2-second sources only, including newly sourced music with voice ducking. Does not imply that a user's actual 4K film
has been encoded or listened to. Set EP01_V3_INTEGRATION=1 to opt in.
"""
from __future__ import annotations

import math
import os
from pathlib import Path
import shutil
import struct
import subprocess
import tempfile
import unittest
import wave

from scripts import ep01_v3_soft_audio as v3


def ff(*args):
    p = subprocess.run(["ffmpeg", "-hide_banner", "-nostdin", "-y",
                        "-v", "error", *map(str, args)],
                       capture_output=True, text=True, timeout=180)
    if p.returncode:
        raise AssertionError("FFmpeg failed: " + (p.stderr or "")[-3000:])


def make_mp4(path, color, tone):
    ff("-f", "lavfi", "-i", f"color=c={color}:s=3840x2160:r=24:d=2",
       "-f", "lavfi", "-i", f"sine=frequency={tone}:sample_rate=48000:duration=2",
       "-map", "0:v", "-map", "1:a",
       "-c:v", "libx264", "-preset", "ultrafast", "-crf", "36",
       "-threads", "2", "-pix_fmt", "yuv420p",
       "-c:a", "aac", "-b:a", "128k", "-shortest", path)


def sample_rgb(path):
    p = subprocess.run(
        ["ffmpeg", "-v", "error", "-i", str(path),
         "-frames:v", "1", "-vf", "scale=1:1,format=rgb24",
         "-f", "rawvideo", "-pix_fmt", "rgb24", "-"],
        check=True, capture_output=True, timeout=60,
    )
    return p.stdout


def spectral_energy(pcm_path, frequency):
    with wave.open(str(pcm_path), "rb") as fh:
        rate = fh.getframerate()
        buf = fh.readframes(min(fh.getnframes(), int(0.8 * rate)))
    samples = struct.unpack("<" + "h" * (len(buf) // 2), buf)
    real = sum(v * math.cos(2 * math.pi * frequency * i / rate)
               for i, v in enumerate(samples))
    imag = sum(v * math.sin(2 * math.pi * frequency * i / rate)
               for i, v in enumerate(samples))
    return math.hypot(real, imag)


@unittest.skipUnless(
    os.environ.get("EP01_V3_INTEGRATION") == "1"
    and shutil.which("ffmpeg") and shutil.which("ffprobe"),
    "Integration smoke enabled only in dedicated FFmpeg workflow",
)
class V3FFmpegIntegration(unittest.TestCase):
    def test_replaces_v2_audio_but_preserves_v2_picture(self):
        with tempfile.TemporaryDirectory(prefix="v3-ci-") as d:
            root = Path(d)
            clean = root / "original.mp4"
            picture = root / "v2.mp4"
            effect = root / "soft.ogg"
            independent_music = root / "new_licensed_music.wav"
            output = root / "v3.mp4"
            wav = root / "audio.wav"
            make_mp4(clean, "black", 440)
            make_mp4(picture, "blue", 1000)
            ff("-f", "lavfi", "-i",
               "sine=frequency=160:sample_rate=48000:duration=0.15",
               "-c:a", "libvorbis", effect)
            ff("-f", "lavfi", "-i",
               "sine=frequency=330:sample_rate=48000:duration=2",
               "-c:a", "pcm_s16le", independent_music)
            original_metadata = v3.inspect(clean)
            picture_metadata = v3.inspect(picture)
            _, _, duration = v3.video_spec(picture_metadata)
            cues = [{"at": 1.0, "material": "paper", "gain_db": -30.0}]
            v3.render(picture, clean, {"paper": effect}, cues, output, duration,
                      music=independent_music)
            receipt = v3.verify_output(
                picture_metadata, original_metadata, v3.inspect(output), duration)
            self.assertEqual(receipt["video_stream_policy"],
                             "ffmpeg -c:v copy; video not recompressed")
            self.assertEqual(sample_rgb(output), sample_rgb(picture))
            self.assertNotEqual(sample_rgb(output), sample_rgb(clean))
            ff("-i", output, "-vn", "-t", "0.8", "-ar", "8000", "-ac", "1",
               "-c:a", "pcm_s16le", wav)
            keep = spectral_energy(wav, 440)
            discard = spectral_energy(wav, 1000)
            self.assertGreater(keep, discard * 10,
                               "V2's original 1000Hz audio was accidentally included")


if __name__ == "__main__":
    unittest.main()
