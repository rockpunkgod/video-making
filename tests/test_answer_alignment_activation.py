"""Synthetic write/rollback controls, not teaching acceptance."""
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from core.registry import Registry
from scripts.activate_answer_alignment import apply_payload, LOCK


class AlignmentActivationTests(unittest.TestCase):
    def setUp(self):
        self.temp=TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)/'repo'; self.root.mkdir()
        self.backup=Path(self.temp.name)/'backup'
        (self.root/'old.txt').write_bytes(b'old exact bytes\r\n')

    def test_scoped_write_has_exact_backups_and_removes_own_lock(self):
        journal=apply_payload(self.root,{'old.txt':b'new','new/file.txt':b'created'},self.backup)
        self.assertEqual((self.root/'old.txt').read_bytes(),b'new')
        self.assertEqual((self.backup/'old.txt').read_bytes(),b'old exact bytes\r\n')
        self.assertEqual(len(journal['assets']),2)
        self.assertFalse((self.root/LOCK).exists())

    def test_write_error_restores_existing_and_removes_only_own_new_files(self):
        original=Path.write_bytes
        def fail(path,raw):
            if path==self.root/'old.txt' and raw==b'broken':
                original(path,b'partial write')
                raise OSError('Synthetic partial-write failure')
            return original(path,raw)
        with patch.object(Path,'write_bytes',fail):
            with self.assertRaisesRegex(OSError,'partial-write'):
                apply_payload(self.root,{'new/file.txt':b'created','old.txt':b'broken'},self.backup)
        self.assertEqual((self.root/'old.txt').read_bytes(),b'old exact bytes\r\n')
        self.assertFalse((self.root/'new/file.txt').exists())
        self.assertFalse((self.root/LOCK).exists())

    def test_escape_and_duplicate_targets_are_rejected_before_writes(self):
        for payload in ({'../outside.txt':b'x'},{'old.txt':b'a','sub/../old.txt':b'b'}):
            with self.subTest(payload=payload),self.assertRaises(ValueError):
                apply_payload(self.root,payload,self.backup)
        self.assertEqual((self.root/'old.txt').read_bytes(),b'old exact bytes\r\n')

    def test_live_registry_cannot_read_mid_migration_but_history_can(self):
        lock=self.root/LOCK; lock.parent.mkdir(); lock.write_bytes(b'{}')
        with patch('core.registry.ROOT',self.root):
            with self.assertRaisesRegex(ValueError,'migration is in progress'): Registry()


if __name__=='__main__': unittest.main()
