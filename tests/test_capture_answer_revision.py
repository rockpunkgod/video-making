import hashlib
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

import yaml

from scripts.capture_answer_revision import capture, check_source_checkout, sections


class CaptureAnswerRevisionTests(unittest.TestCase):
    def setUp(self):
        self.temp = TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.repo = self.base/'consumer'
        self.source = self.base/'upstream'
        self.old = 'b'*40
        self.new = 'a'*40
        self.path = 'gaokao-english/references/reading-comprehension.md'
        self.raw = '# Reading\n\n## Verified action\nOriginal bounded rule.\n'
        self.write(self.repo/'provenance/ANSWER'/self.path,self.raw)
        self.write(self.source/self.path,self.raw)
        self.yaml('provenance/manifest.yaml',{'commit':self.old,'files':[
            {'path':self.path,'sha256':hashlib.sha256(self.raw.encode()).hexdigest()}]})
        self.yaml('method-registry/registry.yaml',{'source_baseline':{'commit':self.old},
            'source_sections':'method-registry/source-sections.yaml',
            'method_files':['method-registry/reading.yaml']})
        section = sections(self.raw)[1]
        self.yaml('method-registry/source-sections.yaml',{'sections':{
            'source-1':dict(section,path=self.path,commit=self.old)}})
        self.yaml('method-registry/reading.yaml',{'methods':[
            {'method_id':'R01','version':'1.1.0','source_name':'Verified action',
             'primary_role':'decider','method_type':'method','section_ids':['source-1']}]})
        self.yaml('cases/registry.yaml',{'case_files':['cases/R01/canonical/case.yaml']})
        self.yaml('cases/R01/canonical/case.yaml',{'case_id':'R01-canonical','status':'evidence_gap'})
        for path in ('source-risks','symptom-cues','grammar-tree','anti-rules'):
            self.yaml('method-registry/'+path+'.yaml',{})

    def write(self,path,text):
        path.parent.mkdir(parents=True,exist_ok=True)
        path.write_bytes(text.encode('utf-8'))

    def yaml(self,path,value):
        self.write(self.repo/path,yaml.safe_dump(value,sort_keys=False))

    def run_capture(self):
        with patch('scripts.capture_answer_revision.check_source_checkout',return_value=[self.path]):
            return capture(self.source,self.new,'2026-10-13',self.repo)

    def test_captures_both_sides_without_touching_current_runtime(self):
        before = {p.relative_to(self.repo).as_posix():p.read_bytes() for p in self.repo.rglob('*') if p.is_file()}
        self.write(self.source/self.path,self.raw.replace('bounded','changed bounded'))
        result = self.run_capture()
        self.assertEqual(result['changed_baseline_documents'],1)
        self.assertEqual(result['methods_with_changed_or_missing_sections'],1)
        for path,raw in before.items():
            self.assertEqual((self.repo/path).read_bytes(),raw)
        archived=self.repo/'provenance/runtime-snapshots'/self.old/'method-registry/reading.yaml'
        self.assertEqual(archived.read_bytes(),before['method-registry/reading.yaml'])
        audit=json.loads((self.repo/'provenance/upstream-revisions'/self.new/'migration-audit-v1.json').read_bytes())
        self.assertFalse(audit['completion'])
        self.assertEqual(audit['methods'][0]['runtime_migration'],'not_applied')

    def test_section_line_endings_do_not_create_false_semantic_changes(self):
        self.write(self.source/self.path,self.raw.replace('\n','\r\n'))
        result=self.run_capture()
        self.assertEqual(result['changed_baseline_documents'],1)
        self.assertEqual(result['methods_with_changed_or_missing_sections'],0)
        captured=self.repo/'provenance/upstream-revisions'/self.new/'files'/self.path
        self.assertEqual(captured.read_bytes(),self.raw.replace('\n','\r\n').encode())

    def test_missing_upstream_file_is_rejected_before_snapshot_write(self):
        with patch('scripts.capture_answer_revision.check_source_checkout',return_value=[]):
            with self.assertRaisesRegex(ValueError,'deleted a baseline source'):
                capture(self.source,self.new,'2026-10-13',self.repo)
        self.assertFalse((self.repo/'provenance/runtime-snapshots').exists())

    def test_changed_frozen_baseline_is_rejected(self):
        self.write(self.repo/'provenance/ANSWER'/self.path,'Changed historical bytes')
        with self.assertRaisesRegex(ValueError,'Frozen baseline source changed'):
            self.run_capture()
        self.assertFalse((self.repo/'provenance/upstream-revisions').exists())

    def test_rerun_is_idempotent_but_cannot_overwrite_snapshot(self):
        first=self.run_capture()
        self.assertEqual(first,self.run_capture())
        self.write(self.source/self.path,self.raw+'Modified same revision\n')
        with self.assertRaises(Exception):
            self.run_capture()
        captured=self.repo/'provenance/upstream-revisions'/self.new/'files'/self.path
        self.assertEqual(captured.read_bytes(),self.raw.encode())

    def test_source_checkout_must_match_explicit_commit(self):
        with patch('scripts.capture_answer_revision.subprocess.check_output',return_value=('c'*40+'\n')):
            with self.assertRaisesRegex(ValueError,'pinned upstream revision'):
                check_source_checkout(self.source,self.new)

    def test_source_checkout_must_be_clean(self):
        with patch('scripts.capture_answer_revision.subprocess.check_output',side_effect=[self.new+'\n',' M changed.md\n']):
            with self.assertRaisesRegex(ValueError,'uncommitted changes'):
                check_source_checkout(self.source,self.new)

    def test_source_checkout_wrong_repository_is_rejected(self):
        with patch('scripts.capture_answer_revision.subprocess.check_output',side_effect=[self.new+'\n','','https://github.com/another/repo.git\n']):
            with self.assertRaisesRegex(ValueError,'requested ANSWER repository'):
                check_source_checkout(self.source,self.new)

    def test_ambiguous_or_renamed_heading_requires_review(self):
        for text,state in [(self.raw.replace('Verified action','Different name'),'missing_or_renamed'),
                           (self.raw+'\n## Verified action\nAnother branch.\n','ambiguous_heading')]:
            with TemporaryDirectory() as separate:
                # Use a separate output root for each immutable capture.
                import shutil
                replica=Path(separate)/'consumer'
                shutil.copytree(self.repo,replica)
                self.write(self.source/self.path,text)
                with patch('scripts.capture_answer_revision.check_source_checkout',return_value=[self.path]):
                    capture(self.source,self.new,'2026-10-13',replica)
                audit=json.loads((replica/'provenance/upstream-revisions'/self.new/'migration-audit-v1.json').read_bytes())
                self.assertEqual(audit['methods'][0]['source_bindings'][0]['state'],state)


if __name__ == '__main__':
    unittest.main()
