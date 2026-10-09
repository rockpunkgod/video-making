import os
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch
from ae_production.memory_guard import guarded_run


class MemoryGuardTests(unittest.TestCase):
    def test_invalid_limits_are_rejected(self):
        with self.assertRaises(ValueError):guarded_run([],None,limit_gib=30)
        with self.assertRaises(ValueError):guarded_run([],None,minimum_free_gib=8)
        with self.assertRaises(ValueError):guarded_run([],None,limit_gib=14)

    @unittest.skipUnless(os.name=='nt','native Windows job guard')
    def test_low_free_memory_never_launches_process(self):
        with patch('ae_production.memory_guard.available_memory',return_value=2**30), \
                patch('ae_production.memory_guard.subprocess.Popen') as launch:
            with self.assertRaises(RuntimeError):guarded_run(['unused'],None)
            launch.assert_not_called()

    @unittest.skipUnless(os.name=='nt','native Windows job guard')
    def test_new_owned_process_is_logged_and_exits(self):
        with TemporaryDirectory() as folder:
            target=Path(folder)/'log.txt'
            result=guarded_run([sys.executable,'-c','print("synthetic owned process")'],target)
            self.assertEqual(result['exit_code'],0)
            self.assertTrue(result['existing_processes_untouched'])
            self.assertIn('synthetic owned process',target.read_text())


if __name__=='__main__':unittest.main()
