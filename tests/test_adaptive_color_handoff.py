"""Actual RGB TIFF -> H.264 color handoff; synthetic patches, not teaching data."""
import importlib.util
import io
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from PIL import Image
from content_os.showcase import file_sha
from video_contracts import sha, write

MODULE = Path(__file__).resolve().parents[1] / 'ae/experiments/adaptive-episode/run.py'
SPEC = importlib.util.spec_from_file_location('adaptive_color', MODULE)
adapter = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(adapter)


@unittest.skipUnless(shutil.which('ffmpeg') and shutil.which('ffprobe'), 'Actual codec tools required')
class ColorHandoffTest(unittest.TestCase):
    def test_actual_package_preserves_patches_and_signals_bt709(self):
        with tempfile.TemporaryDirectory() as temp:
            folder = Path(temp); frames = folder / 'frames'; frames.mkdir()
            colors = [(243, 240, 233), (45, 116, 170), (218, 126, 60), (30, 36, 38)]
            image = Image.new('RGB', (3840, 2160))
            for index, color in enumerate(colors):
                image.paste(color, (index*960, 0, (index+1)*960, 2160))
            source = frames / 'FRAME_00000.tif'; image.save(source)
            project = folder / 'SYNTHETIC.aep'; project.write_bytes(b'synthetic saved project')
            transfer = {'spec_sha': 'synthetic', 'start_frame': 0, 'count': 1,
                        'frames': {source.name: file_sha(source)}}
            write(folder / 'transfer-00000.json', transfer)
            receipt = {'spec_sha': 'synthetic', 'frames': 1, 'duration': 1/24,
                       'canvas': [3840, 2160, 24], 'scratch': str(frames),
                       'native_project': str(project), 'project_sha': file_sha(project),
                       'transfers': [sha(transfer)]}
            write(folder / 'NATIVE_RENDER_RECEIPT.json', receipt)
            request = {'spec': {'spec_sha': 'synthetic', 'canvas': {'duration': 1/24}},
                       'project': str(project)}
            with patch.object(adapter, 'current', return_value=request):
                result = adapter.package(folder)
                # A completed picture is never silently overwritten.
                with self.assertRaisesRegex(ValueError, 'revision required'):
                    adapter.package(folder)
            data = subprocess.check_output(['ffmpeg', '-v', 'error', '-i', result['picture'],
                '-frames:v', '1', '-f', 'image2pipe', '-vcodec', 'png', 'pipe:1'])
            decoded = Image.open(io.BytesIO(data)).convert('RGB')
            self.assertEqual(decoded.size, (3840, 2160))
            for index, color in enumerate(colors):
                observed = decoded.getpixel((index*960+480, 1080))
                self.assertLessEqual(max(abs(a-b) for a, b in zip(color, observed)), 3,
                                     'Warm paper and blue/orange patches must survive the declared matrix')


if __name__ == '__main__':
    unittest.main()
