"""Offline structural tests for the isolated EP01 V3 natural-audio rebuild.

Does not encode the movie and does not constitute a listening test.
"""
import json
import io
import contextlib
import sys
from pathlib import Path
import tempfile
import unittest
from unittest import mock
import zipfile

from scripts import ep01_v3_soft_audio as v3


class TestEP01V3NaturalAudio(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)

    def make_cues(self, entries):
        p = self.root / "cues.json"
        p.write_text(json.dumps({"cues": entries}), encoding="utf-8")
        return p

    def test_video_spec_accepts_4k24(self):
        meta = {
            "format": {"duration": "275.04"},
            "streams": [
                {"codec_type": "video", "width": 3840, "height": 2160,
                 "r_frame_rate": "24/1", "codec_name": "h264"},
                {"codec_type": "audio", "codec_name": "aac"},
            ],
        }
        video, audio, duration = v3.video_spec(meta)
        self.assertEqual((video["width"], video["height"]), (3840, 2160))
        self.assertEqual(audio["codec_name"], "aac")
        self.assertEqual(duration, 275.04)

    def test_video_spec_rejects_other_fps(self):
        meta = {
            "format": {"duration": "10.0"},
            "streams": [
                {"codec_type": "video", "width": 3840, "height": 2160,
                 "r_frame_rate": "25/1", "codec_name": "h264"},
                {"codec_type": "audio", "codec_name": "aac"},
            ],
        }
        with self.assertRaises(RuntimeError):
            v3.video_spec(meta)

    def test_explicit_cues_sorted_with_material_defaults(self):
        cue_file = self.make_cues([
            {"at": 26.5, "material": "tap"},
            {"at": 4.0, "material": "paper", "gain_db": -31},
        ])
        cues, mode = v3.cue_sheet(cue_file, self.root / "dummy.mp4", 60.0)
        self.assertEqual([x["at"] for x in cues], [4.0, 26.5])
        self.assertEqual([x["material"] for x in cues], ["paper", "tap"])
        self.assertEqual(cues[0]["gain_db"], -31)
        self.assertEqual(mode, "explicit_unlistened")

    def test_rejects_unlicensed_external_fx_file(self):
        cue_file = self.make_cues([
            {"at": 5, "material": "paper", "file": "legacy_electronic_zap.wav"}
        ])
        with self.assertRaisesRegex(ValueError, "Legacy file-based FX"):
            v3.cue_sheet(cue_file, self.root / "dummy.mp4", 60.0)

    def test_rejects_too_loud_effect(self):
        cue_file = self.make_cues([
            {"at": 5, "material": "swish", "gain_db": -3}
        ])
        with self.assertRaisesRegex(ValueError, "too loud"):
            v3.cue_sheet(cue_file, self.root / "dummy.mp4", 60.0)

    def test_does_not_invent_cues_when_no_scene_changes_detected(self):
        with mock.patch.object(v3, "suggest_times", return_value=[]):
            with self.assertRaisesRegex(RuntimeError, "No detectable edit cues"):
                v3.cue_sheet(None, self.root / "dummy.mp4", 100.0)

    def test_automatic_cues_are_explicitly_unreviewed(self):
        with mock.patch.object(v3, "suggest_times", return_value=[12.0, 21.0]):
            cues, mode = v3.cue_sheet(None, self.root / "dummy.mp4", 100.0)
        self.assertEqual(len(cues), 2)
        self.assertEqual(mode, "automatic_scene_change_unreviewed")
        self.assertTrue(all(c["placement"] == mode for c in cues))

    def test_kenney_assets_are_selected_by_filename_from_offline_zip(self):
        archive = self.root / "foley.zip"
        with zipfile.ZipFile(archive, "w") as z:
            for fn, _ in v3.MATERIALS.values():
                z.writestr("RPGsounds_Kenney/Audio/" + fn, b"\x01\x02\x03")
            z.writestr("RPGsounds_Kenney/Audio/metalClick.ogg", b"not selected")
        target = self.root / "extracted"
        target.mkdir()
        paths, provenance = v3.prepare_foley(archive, target)
        self.assertEqual(set(paths), set(v3.MATERIALS))
        self.assertEqual(provenance["license"], "CC0-1.0")
        self.assertEqual(len(provenance["archive_sha256"]), 64)
        self.assertEqual(paths["paper"].read_bytes(), b"\x01\x02\x03")

    def test_v2_video_is_used_but_v2_audio_is_discarded(self):
        """FFmpeg input 0 provides picture only; input 1 provides original audio."""
        picture = self.root / "v2.mp4"
        clean = self.root / "clean.mp4"
        foley = self.root / "bookFlip1.ogg"
        result = self.root / "v3.mp4"
        cues = [{"at": 3.0, "material": "paper", "gain_db": -30.0}]
        seen = {}

        def capture(cmd, **kwargs):
            seen["cmd"] = cmd

        with mock.patch.object(v3, "command", side_effect=capture):
            v3.render(picture, clean, {"paper": foley}, cues, result, 25.0)

        cmd = seen["cmd"]
        self.assertEqual(cmd[cmd.index("-i") + 1], str(picture))
        self.assertEqual(cmd[cmd.index("-i", cmd.index("-i") + 1) + 1], str(clean))
        fg = cmd[cmd.index("-filter_complex") + 1]
        self.assertIn("[1:a:0]aresample", fg)
        self.assertNotIn("[0:a:0]", fg)
        self.assertIn("-c:v", cmd)
        self.assertEqual(cmd[cmd.index("-c:v") + 1], "copy")
        self.assertIn("0:v:0", cmd)

    def test_clean_voice_is_required_for_non_draft_cli(self):
        picture = self.root / "v2.mp4"
        picture.write_bytes(b"mock exists")
        out = self.root / "v3.mp4"
        with mock.patch.object(sys, "argv", [
            "ep01_v3_soft_audio.py", "--picture", str(picture), "--out", str(out)
        ]):
            with contextlib.redirect_stderr(io.StringIO()) as err:
                with self.assertRaises(SystemExit) as raised:
                    v3.main()
        self.assertEqual(raised.exception.code, 2)
        self.assertIn("Cannot guarantee removal of OPUS effects", err.getvalue())

    def test_clean_voice_cannot_be_the_v2_video(self):
        picture = self.root / "v2.mp4"
        picture.write_bytes(b"mock exists")
        with mock.patch.object(sys, "argv", [
            "ep01_v3_soft_audio.py", "--picture", str(picture),
            "--clean-voice", str(picture), "--out", str(self.root / "out.mp4")
        ]):
            with contextlib.redirect_stderr(io.StringIO()) as err:
                with self.assertRaises(SystemExit) as raised:
                    v3.main()
        self.assertEqual(raised.exception.code, 2)
        self.assertIn("cannot be the same file as the V2 picture", err.getvalue())

    def test_music_source_is_separate_and_ducked_not_recycled_old_mix(self):
        picture = self.root / "v2.mp4"
        voice = self.root / "voice_only.flac"
        music = self.root / "licensed_new_music.wav"
        foley = self.root / "bookFlip1.ogg"
        output = self.root / "v3.mp4"
        seen = {}

        def capture(cmd, **kwargs):
            seen["command"] = cmd

        with mock.patch.object(v3, "command", side_effect=capture):
            v3.render(picture, voice, {"paper": foley},
                      [{"at": 3.0, "material": "paper", "gain_db": -30.0}],
                      output, 25.0, music=music)
        cmd = seen["command"]
        indexes = [i for i, x in enumerate(cmd) if x == "-i"]
        self.assertEqual([cmd[i + 1] for i in indexes],
                         [str(picture), str(voice), str(music), str(foley)])
        fg = cmd[cmd.index("-filter_complex") + 1]
        self.assertIn("[2:a:0]", fg)
        self.assertIn("[3:a:0]", fg)
        self.assertIn("sidechaincompress", fg)
        self.assertNotIn("[0:a:0]", fg)
        self.assertIn("-c:v", cmd)
        self.assertEqual(cmd[cmd.index("-c:v") + 1], "copy")

    def test_audio_only_clean_source_is_valid_in_receipt(self):
        def metadata(audio_only=False):
            streams = [
                {"codec_type": "audio", "codec_name": "flac"}
            ]
            if not audio_only:
                streams.insert(0, {"codec_type": "video", "width": 3840, "height": 2160,
                                   "r_frame_rate": "24/1", "codec_name": "h264"})
            return {"format": {"duration": "20.0"}, "streams": streams}
        final = metadata()
        final["streams"][1]["codec_name"] = "aac"
        verified = v3.verify_output(metadata(), metadata(audio_only=True), final, 20.0)
        self.assertEqual(verified["original_audio_codec"], "flac")
        self.assertEqual(verified["new_audio_codec"], "aac")

    def test_final_receipt_must_not_claim_publication_approval(self):
        before = {
            "format": {"duration": "20.0"},
            "streams": [
                {"codec_type": "video", "width": 3840, "height": 2160,
                 "r_frame_rate": "24/1", "codec_name": "h264", "nb_frames": "480"},
                {"codec_type": "audio", "codec_name": "aac"}
            ],
        }
        after = json.loads(json.dumps(before))
        metadata = v3.verify_output(before, before, after, 20.0)
        self.assertEqual(metadata["video_stream_policy"],
                         "ffmpeg -c:v copy; video not recompressed")


if __name__ == "__main__":
    unittest.main()
