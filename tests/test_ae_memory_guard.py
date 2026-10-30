import os
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch
from ae_production.memory_guard import guarded_run,stop_reason,monitor_existing_render


class MemoryGuardTests(unittest.TestCase):
    def test_invalid_limits_are_rejected(self):
        with self.assertRaises(ValueError):guarded_run([],None,limit_gib=0)
        with self.assertRaises(ValueError):guarded_run([],None,minimum_free_gib=0)
        with self.assertRaises(ValueError):guarded_run([],None,limit_gib=300)

    def test_runtime_stop_lines_are_user_configured(self):
        self.assertEqual(stop_reason(2**29,2**30),'LOW_SYSTEM_MEMORY')
        self.assertIsNone(stop_reason(2**30,10*2**30))
        self.assertIsNone(stop_reason(4*2**30,20*2**30))
        self.assertEqual(stop_reason(4*2**30,11*2**30,limit_gib=10),'RENDER_PROCESS_BUDGET')

    def test_monitor_requires_a_real_window_identity(self):
        with self.assertRaises(ValueError):
            with monitor_existing_render(0,0):pass

    @unittest.skipUnless(os.name=='nt','native Windows job guard')
    def test_low_free_memory_never_launches_process(self):
        with patch('ae_production.memory_guard.available_memory',return_value=2**29), \
                patch('ae_production.memory_guard.subprocess.Popen') as launch:
            with self.assertRaises(RuntimeError):guarded_run(['unused'],None)
            launch.assert_not_called()

    @unittest.skipUnless(os.name=='nt','native Windows job guard')
    def test_new_owned_process_is_logged_and_exits(self):
        # Exercise the real owned Job/process/log path with a controlled memory
        # sample. Workstation pressure belongs to the separate low-memory gate
        # test, not this successful-lifecycle fixture. No Adobe is launched.
        with TemporaryDirectory() as folder, \
                patch('ae_production.memory_guard.available_memory',return_value=2*2**30):
            target=Path(folder)/'log.txt'
            result=guarded_run([sys.executable,'-c','print("synthetic owned process")'],target)
            self.assertEqual(result['exit_code'],0)
            self.assertTrue(result['existing_processes_untouched'])
            self.assertIn('synthetic owned process',target.read_text())
            self.assertEqual(result['minimum_free_limit_bytes'],2**30)
            self.assertEqual(result['minimum_free_bytes'],2*2**30)
            self.assertEqual(result['job_limit_bytes'],2**30)


if __name__=='__main__':unittest.main()
