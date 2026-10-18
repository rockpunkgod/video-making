"""Synthetic host identity reads; never launches or controls Adobe."""
from copy import deepcopy
import hashlib
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

    def failed_evidence(self, disposition='failed', error='Synthetic script error'):
        path=self.directory/'server-recovery.json'
        write(path,{'recoveryId':'abcdef','sourceProjectPath':self.state['project_path'],
                    'attempts':[{'ok':False,'disposition':disposition,'errorLine':12,'error':error}]})
        return path,hashlib.sha256(path.read_bytes()).hexdigest()

    def make_uncertain(self):
        self.lease.acquire()
        def failed():raise RuntimeError('Synthetic script dispatch returned failure')
        with self.assertRaises(RuntimeError):self.lease.mutate(lambda:self.state,failed)

    def test_known_failed_script_recovery_retains_token_until_readback(self):
        self.make_uncertain();path,digest=self.failed_evidence();calls=[]
        recovered,result=HostOwnership.recover_failed_dispatch('after_effects','synthetic-worker','synthetic-r1',
            self.lease.record['token'],lambda:self.state,lambda identifier:calls.append(identifier),path,digest,
            target_after=lambda value:self.state,directory=self.directory)
        self.assertEqual(calls,['abcdef']);self.assertEqual(recovered.record['token'],self.lease.record['token'])
        self.assertEqual(recovered.record['state'],'OWNED');recovered.release(lambda:self.state)

    def test_inspected_unsaved_build_can_be_preserved_and_original_restored(self):
        self.make_uncertain();path,digest=self.failed_evidence();original=dict(self.state)
        self.state.update(project_path='',target_id='comp:2')
        partial=self.directory/'partial.json'
        write(partial,{'identity':dict(self.state),'state':'INSPECTED_PARTIAL_NOT_COMPLETED',
                      'recovery_id':'abcdef','compositions':[{'id':2}], 'plan_sha256':'bound-plan'})
        evidence=(partial,hashlib.sha256(partial.read_bytes()).hexdigest())
        recovered,_=HostOwnership.recover_failed_dispatch('after_effects','synthetic-worker','synthetic-r1',
            self.lease.record['token'],lambda:self.state,lambda identifier:self.state.update(original),path,digest,
            target_after=lambda value:original,directory=self.directory,partial_state_evidence=evidence)
        self.assertEqual(read(recovered.path),recovered.record)
        recovered.release(lambda:self.state)
        self.assertFalse(recovered.path.exists())

    def test_failed_script_recovery_rejects_timeout_or_wrong_owner(self):
        self.make_uncertain();path,digest=self.failed_evidence(error='timeout after dispatch');calls=[]
        with self.assertRaises(ValueError):HostOwnership.recover_failed_dispatch('after_effects','synthetic-worker','synthetic-r1',
            self.lease.record['token'],lambda:self.state,lambda identifier:calls.append(identifier),path,digest,
            target_after=lambda value:self.state,directory=self.directory)
        path,digest=self.failed_evidence()
        with self.assertRaises(RuntimeError):HostOwnership.recover_failed_dispatch('after_effects','another-worker','synthetic-r1',
            self.lease.record['token'],lambda:self.state,lambda identifier:calls.append(identifier),path,digest,
            target_after=lambda value:self.state,directory=self.directory)
        self.assertEqual(calls,[]);self.assertEqual(read(self.lease.path)['state'],'UNCERTAIN')

    def test_failed_recovery_wrong_post_identity_preserves_uncertainty(self):
        self.make_uncertain();path,digest=self.failed_evidence()
        with self.assertRaises(RuntimeError):HostOwnership.recover_failed_dispatch('after_effects','synthetic-worker','synthetic-r1',
            self.lease.record['token'],lambda:self.state,lambda identifier:self.state.update(target_id='unexpected'),path,digest,
            target_after=lambda value:{**self.state,'target_id':'expected'},directory=self.directory)
        self.assertEqual(read(self.lease.path)['state'],'UNCERTAIN')

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

    def test_native_generated_target_id_needs_independent_readback(self):
        self.lease.acquire()
        def create():
            self.state['target_id'] = 'comp:allocated-by-adobe'
            return {'comp_id': 'allocated-by-adobe'}
        self.lease.mutate(lambda: self.state, create,
            target_after=lambda result: {**self.state, 'target_id': 'comp:' + result['comp_id']})
        self.assertEqual(self.lease.record['target']['target_id'], 'comp:allocated-by-adobe')
        with self.assertRaisesRegex(RuntimeError, 'identity changed'):
            self.lease.mutate(lambda: self.state, lambda: {'comp_id': 'wrong-native-return'},
                target_after=lambda result: {**self.state, 'target_id': 'comp:' + result['comp_id']})
        self.assertEqual(read(self.lease.path)['state'], 'UNCERTAIN')

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

    def uncertain_with_evidence(self):
        self.lease.acquire()
        self.lease._uncertain(TimeoutError('completed after client timed out'))
        evidence = self.directory / 'completed-audit.json'
        evidence.write_text('{"status":"PASS"}', encoding='utf-8')
        return {str(evidence): hashlib.sha256(evidence.read_bytes()).hexdigest()}

    def reconcile(self, evidence, token=None, reader=None):
        return HostOwnership.reconcile_completed('after_effects', 'synthetic-worker',
            'synthetic-r1', token or self.lease.record['token'], self.state,
            reader or (lambda: self.state), evidence, self.directory)

    def test_completed_reconciliation_preserves_owner_token_and_original_error(self):
        evidence = self.uncertain_with_evidence()
        previous = deepcopy(read(self.lease.path))
        resumed = self.reconcile(evidence)
        self.assertEqual(resumed.record['token'], previous['token'])
        self.assertEqual(resumed.record['reconciliation']['previous_record'], previous)
        self.assertFalse(resumed.record['reconciliation']['mutation_replayed'])
        resumed.release(lambda: self.state)

    def test_reconciliation_rejects_foreign_token_or_changed_evidence(self):
        evidence = self.uncertain_with_evidence()
        previous = read(self.lease.path)
        with self.assertRaises(RuntimeError): self.reconcile(evidence, token='foreign')
        Path(next(iter(evidence))).write_text('changed', encoding='utf-8')
        with self.assertRaises(ValueError): self.reconcile(evidence)
        self.assertEqual(read(self.lease.path), previous)

    def test_reconciliation_checks_live_identity_and_concurrent_ownership(self):
        evidence = self.uncertain_with_evidence()
        previous = read(self.lease.path)
        with self.assertRaises(RuntimeError):
            self.reconcile(evidence, reader=lambda: {**self.state, 'target_id': 'wrong'})
        foreign = {**previous, 'token': 'foreign'}
        def changed_owner():
            write(self.lease.path, foreign)
            return self.state
        with self.assertRaises(RuntimeError): self.reconcile(evidence, reader=changed_owner)
        self.assertEqual(read(self.lease.path), foreign)

    def test_owned_checkpoint_requires_explicit_state_and_preserves_token(self):
        evidence = self.uncertain_with_evidence()
        previous = read(self.lease.path); previous['state']='OWNED'; write(self.lease.path,previous)
        with self.assertRaises(RuntimeError): self.reconcile(evidence)
        resumed=HostOwnership.reconcile_completed('after_effects','synthetic-worker','synthetic-r1',
            previous['token'],self.state,lambda:self.state,evidence,self.directory,expected_state='OWNED')
        self.assertEqual(resumed.record['token'],previous['token'])
        self.assertEqual(resumed.record['reconciliation']['previous_record']['state'],'OWNED')
        resumed.release(lambda:self.state)
