"""Cooperative, per-Adobe-host ownership for a single production revision.

No scheduler, expiry, implicit retry or takeover. Other clients must opt into
the same lock directory; a native identity read detects manual project changes.
An uncertain mutation deliberately leaves the lock for explicit reconciliation.
"""
import json
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

    def _owned(self):
        if not self.acquired or read(self.path) != self.record:
            raise RuntimeError('Adobe host ownership changed or was not acquired')
        if self.record['state'] != 'OWNED':
            raise RuntimeError('Native state uncertain; inspect and reconcile before retry')

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
        """
        self._owned()
        expected = dict(self.record['target'] if target_after is None else target_after)
        if (not {'process_id', 'project_path', 'target_id'} <= expected.keys()
                or any(v is None for v in expected.values())
                or type(expected['process_id']) is not int or expected['process_id'] <= 0):
            raise ValueError('Explicit destination identity required')
        try:
            self._inspect(reader, self.record['target'])
            result = mutation()
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
