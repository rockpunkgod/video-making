"""Synthetic host identity reads; never launches or controls Adobe."""
from copy import deepcopy
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from ae_production.host_ownership import HostOwnership
from video_contracts import read, write


class HostOwnershipTests(unittest.TestCase):
    def setUp(self):
        tmp = TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.directory = Path(tmp.name)
        self.state = {'process_id': 123, 'project_path': 'synthetic.aep', 'target_id': 'comp:1'}
        self.lease = self.make()

    def make(self, host='after_effects', owner='synthetic-worker'):
        return HostOwnership(host, owner, 'synthetic-r1', self.state, self.directory)

    def test_one_owner_per_host_and_no_time_based_takeover(self):
        self.lease.acquire()
        with self.assertRaises(FileExistsError): self.make(owner='second').acquire()
        other = self.make(host='premiere')
        other.acquire()
        other.release(lambda: self.state)
        self.lease.release(lambda: self.state)
        self.make(owner='second').acquire()

    def test_switch_before_mutation_prevents_call(self):
        self.lease.acquire()
        self.state['project_path'] = 'unrelated.aep'
        calls = []
        with self.assertRaisesRegex(RuntimeError, 'identity changed'):
            self.lease.mutate(lambda: self.state, lambda: calls.append('called'))
        self.assertEqual(calls, [])
        self.assertEqual(read(self.lease.path)['state'], 'UNCERTAIN')

    def test_timeout_preserves_lock_and_does_not_retry(self):
        self.lease.acquire()
        calls = []
        def fail():
            calls.append(1)
            raise TimeoutError('synthetic native call applied unknown amount')
        with self.assertRaises(TimeoutError): self.lease.mutate(lambda: self.state, fail)
        with self.assertRaisesRegex(RuntimeError, 'uncertain'):
            self.lease.mutate(lambda: self.state, fail)
        with self.assertRaisesRegex(RuntimeError, 'uncertain'):
            self.lease.release(lambda: self.state)
        self.assertEqual(calls, [1])
        self.assertTrue(self.lease.path.exists())

    def test_explicit_project_transition_is_checked_after_call(self):
        self.lease.acquire()
        target = {**self.state, 'project_path': 'new.aep', 'target_id': 'comp:2'}
        self.lease.mutate(lambda: self.state, lambda: self.state.update(target), target_after=target)
        self.assertEqual(read(self.lease.path)['target'], target)
        self.lease.release(lambda: self.state)

    def test_wrong_post_mutation_identity_is_uncertain(self):
        self.lease.acquire()
        with self.assertRaises(RuntimeError):
            self.lease.mutate(lambda: self.state, lambda: self.state.update(target_id='unexpected'))
        self.assertTrue(self.lease.path.exists())

    def test_restarted_host_is_not_same_owner_target(self):
        self.lease.acquire()
        self.state['process_id'] = 456
        with self.assertRaises(RuntimeError): self.lease.release(lambda: self.state)

    def test_foreign_lock_never_deleted_or_overwritten(self):
        self.lease.acquire()
        foreign = deepcopy(self.lease.record)
        foreign['token'] = 'someone-else'
        write(self.lease.path, foreign)
        with self.assertRaises(RuntimeError): self.lease.release(lambda: self.state)
        self.assertEqual(read(self.lease.path), foreign)

    def test_explicit_native_identity_required(self):
        with self.assertRaises(ValueError):
            HostOwnership('after_effects', 'owner', 'revision', {'project_path': 'a'}, self.directory)
