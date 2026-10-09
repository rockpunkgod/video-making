from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SHELL = shutil.which('pwsh') or shutil.which('powershell')

@unittest.skipUnless(SHELL, 'PowerShell is required for the local Windows inventory')
class OrganizedInventoryTests(unittest.TestCase):
    def invoke(self, source, output):
        return subprocess.run([
            SHELL, '-NoProfile', '-ExecutionPolicy', 'Bypass', '-File',
            str(ROOT/'scripts/inventory_organized_sources.ps1'),
            '-SourceRoot', str(source), '-OutputPath', str(output),
        ], capture_output=True, timeout=30)

    def test_inventory_preserves_existing_bytes_and_refuses_source_drift(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp); source=root/'source'; source.mkdir()
            raw=source/'synthetic.txt'; raw.write_bytes(b'source fixture')
            output=root/'private/manifest.json'
            initial=self.invoke(source,output)
            self.assertEqual(initial.returncode,0,initial.stderr.decode('utf-8',errors='replace'))
            before=output.read_bytes()
            repeated=self.invoke(source,output)
            self.assertEqual(repeated.returncode,0,repeated.stderr.decode('utf-8',errors='replace'))
            self.assertEqual(output.read_bytes(),before)
            raw.write_bytes(b'different source fixture')
            self.assertNotEqual(self.invoke(source,output).returncode,0)
            self.assertEqual(output.read_bytes(),before)

    def test_output_inside_original_source_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            source=Path(tmp)/'source'; source.mkdir()
            output=source/'forbidden/manifest.json'
            self.assertNotEqual(self.invoke(source,output).returncode,0)
            self.assertFalse(output.exists())

if __name__=='__main__': unittest.main()
