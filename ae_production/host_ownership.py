"""Cooperative, per-Adobe-host ownership for a single production revision.

No scheduler, expiry, implicit retry or takeover. Other clients must opt into
the same lock directory; a native identity read detects manual project changes.
An uncertain mutation deliberately leaves the lock for explicit reconciliation.
"""
import json
from copy import deepcopy
import hashlib
import os
from pathlib import Path
from uuid import uuid4

from video_contracts import ROOT, read, write


class HostOwnership:
    def __init__(self, host, owner, revision, target, directory=None):
        if host not in ('after_effects', 'premiere'):
            raise ValueError('Known Adobe host required')
        if not owner or not revision or not isinstance(target, dict) or not target:
            raise ValueError('Owner, revision and explicit native identity required')
        if any(value is None for value in target.values()):
            raise ValueError('Native identity must be explicit, including an empty project')
        if (not {'process_id', 'project_path', 'target_id'} <= target.keys()
                or type(target['process_id']) is not int or target['process_id'] <= 0):
            raise ValueError('Host process, project and comp/sequence identity required')
        root = Path(directory) if directory is not None else ROOT / 'local-data/adobe-host-ownership'
        self.path = root / (host + '.json')
        self.record = {'host': host, 'owner': owner, 'revision': revision,
                       'token': uuid4().hex, 'controller_pid': os.getpid(),
                       'target': dict(target), 'state': 'OWNED'}
        self.acquired = False

    def acquire(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        # Exclusive creation is atomic. An existing or partial record is never
        # treated as expired, even if its controller process no longer exists.
        with self.path.open('x', encoding='utf-8') as stream:
            json.dump(self.record, stream, ensure_ascii=False, sort_keys=True)
            stream.write('\n')
        self.acquired = True
        return dict(self.record)

    @classmethod
    def reconcile_completed(cls, host, owner, revision, token, target, reader,
                            completion_evidence, directory=None, *, expected_state='UNCERTAIN'):
        """Explicitly resume the same token after independently verified completion.

        This never replays a mutation, expires a lease or changes its owner.
        The caller must first audit the completed native result. Evidence files
        are byte-bound here and the live identity is read twice. An uncertain
        partial result needs a different, explicit recovery decision. An explicit
        OWNED checkpoint may also be continued after its prior controller has
        stopped between completed calls; it is never selected automatically.
        """
        lease = cls(host, owner, revision, target, directory)
        previous = read(lease.path)
        if expected_state not in ('UNCERTAIN','OWNED'):
            raise ValueError('Explicit completed or uncertain checkpoint required')
        if (previous.get('state') != expected_state
                or any(previous.get(k) != v for k, v in
                       {'host': host, 'owner': owner, 'revision': revision, 'token': token}.items())):
            raise RuntimeError('Reconciliation requires the same checkpoint owner, state and token')
        if previous['target']['process_id'] != target['process_id']:
            raise RuntimeError('A restarted host cannot reconcile the original mutation')
        if not completion_evidence:
            raise ValueError('Independent completed-result evidence required')
        for path, expected in completion_evidence.items():
            actual = hashlib.sha256(Path(path).read_bytes()).hexdigest()
            if actual != expected:
                raise ValueError('Completion evidence bytes changed')
        observed = lease._inspect(reader, target)
        lease._inspect(reader, target)
        if read(lease.path) != previous:
            raise RuntimeError('Ownership changed during reconciliation')
        lease.record = {**deepcopy(previous), 'state': 'OWNED', 'target': dict(target),
            'controller_pid': os.getpid(), 'reconciliation': {
                'resolution': 'COMPLETED_VERIFIED', 'mutation_replayed': False,
                'previous_record': deepcopy(previous), 'observed': observed,
                'completion_evidence': dict(completion_evidence)}}
        write(lease.path, lease.record)
        lease.acquired = True
        return lease

    def _owned(self):
        if not self.acquired or read(self.path) != self.record:
            raise RuntimeError('Adobe host ownership changed or was not acquired')
        if self.record['state'] != 'OWNED':
            raise RuntimeError('Native state uncertain; inspect and reconcile before retry')

    @classmethod
    def recover_failed_dispatch(cls, host, owner, revision, token, reader, mutation,
                                evidence_path, evidence_sha, *, target_after, directory=None,
                                partial_state_evidence=None):
        """One explicit server-issued script recovery, retaining the occupied token.

        This is not timeout reconciliation or a generic retry. A byte-bound AE
        recovery receipt must prove a terminal script error with an error line.
        The caller reviews the partial state and supplies the corrected recovery
        operation. OWNED is restored only after its independent native readback.
        """
        root=Path(directory) if directory is not None else ROOT/'local-data/adobe-host-ownership'
        previous=read(root/(host+'.json'))
        if (previous.get('state')!='UNCERTAIN' or any(previous.get(k)!=v for k,v in
                {'host':host,'owner':owner,'revision':revision,'token':token}.items())):
            raise RuntimeError('Failed recovery requires the same uncertain owner and token')
        if hashlib.sha256(Path(evidence_path).read_bytes()).hexdigest()!=evidence_sha:
            raise ValueError('Server failure evidence changed')
        evidence=read(evidence_path);last=evidence['attempts'][-1]
        if (not evidence.get('recoveryId') or last.get('ok') is not False
                or last.get('disposition')!='failed' or type(last.get('errorLine')) is not int
                or last['errorLine']<=0 or 'timeout' in last.get('error','').lower()
                or Path(evidence['sourceProjectPath']).resolve()!=Path(previous['target']['project_path']).resolve()):
            raise ValueError('A terminal script failure in this project is required; not a timeout')
        lease=cls(host,owner,revision,previous['target'],directory)
        lease.record=deepcopy(previous);lease.acquired=True
        inspect_target=previous['target']
        if partial_state_evidence is not None:
            # A failed new-project save can leave a fully built, unsaved project.
            # Bind the separately read native identity rather than pretending
            # it is still the old project or claiming the build completed.
            path,digest=partial_state_evidence
            if hashlib.sha256(Path(path).read_bytes()).hexdigest()!=digest:
                raise ValueError('Partial native state evidence changed')
            partial=read(path)
            inspect_target=partial.get('identity',{})
            if (partial.get('recovery_id')!=evidence['recoveryId']
                    or partial.get('state')!='INSPECTED_PARTIAL_NOT_COMPLETED'
                    or not {'process_id','project_path','target_id'}<=inspect_target.keys()
                    or inspect_target['process_id']!=previous['target']['process_id']
                    or not partial.get('compositions') or not partial.get('plan_sha256')):
                raise ValueError('Explicit same-failure partial project evidence required')
        lease._inspect(reader,inspect_target);lease._inspect(reader,inspect_target)
        if read(lease.path)!=previous:raise RuntimeError('Owner changed before explicit recovery')
        try:
            result=mutation(evidence['recoveryId'])
            expected=target_after(result)
            if (not {'process_id','project_path','target_id'}<=expected.keys()
                    or expected['process_id']!=previous['target']['process_id']
                    or any(v is None for v in expected.values())):
                raise ValueError('Same host and explicit recovery destination required')
            lease._inspect(reader,expected)
            if read(lease.path)!=previous:raise RuntimeError('Owner changed during explicit recovery')
        except BaseException as error:
            lease._uncertain(error);raise
        lease.record={**previous,'state':'OWNED','controller_pid':os.getpid(),'target':dict(expected),
            'reconciliation':{'resolution':'FAILED_DISPATCH_RECOVERED','recovery_id':evidence['recoveryId'],
                'failure_evidence':str(evidence_path),'failure_evidence_sha':evidence_sha,
                'partial_state_evidence':list(partial_state_evidence) if partial_state_evidence else None,
                'previous_record':previous}}
        write(lease.path,lease.record)
        return lease,result

    def _inspect(self, reader, expected):
        actual = reader()
        if not isinstance(actual, dict) or any(actual.get(k) != v for k, v in expected.items()):
            raise RuntimeError('Native host/project/target identity changed')
        return actual

    def _uncertain(self, error):
        if not self.path.exists() or read(self.path) != self.record:
            return  # Never overwrite another owner's record after an intervention.
        self.record['state'] = 'UNCERTAIN'
        self.record['failure_type'] = type(error).__name__
        write(self.path, self.record)

    def mutate(self, reader, mutation, *, target_after=None):
        """Read identity immediately before and after exactly one native call.

        A deliberate project switch supplies its expected destination up front.
        Opening/building a project is itself a mutation and must use this path.
        Adobe can allocate a new comp/sequence ID only during the call. In that
        case target_after may derive the expected identity from the native
        mutation result; the independent reader must still confirm it. A caller
        must never use that reader itself to manufacture the expected identity.
        """
        self._owned()
        def destination(value):
            expected = dict(value)
            if (not {'process_id', 'project_path', 'target_id'} <= expected.keys()
                    or any(v is None for v in expected.values())
                    or type(expected['process_id']) is not int or expected['process_id'] <= 0):
                raise ValueError('Explicit destination identity required')
            return expected
        expected = None if callable(target_after) else destination(
            self.record['target'] if target_after is None else target_after)
        try:
            self._inspect(reader, self.record['target'])
            result = mutation()
            if callable(target_after):
                expected = destination(target_after(result))
            self._inspect(reader, expected)
            self._owned()
        except BaseException as error:
            self._uncertain(error)
            raise
        self.record['target'] = expected
        write(self.path, self.record)
        return result

    def release(self, reader):
        self._owned()
        try:
            self._inspect(reader, self.record['target'])
        except BaseException as error:
            self._uncertain(error)
            raise
        # Cooperative owners cannot replace an occupied lock. A changed record
        # must not be deleted, including after a manual host intervention.
        self._owned()
        self.path.unlink()
        self.acquired = False
