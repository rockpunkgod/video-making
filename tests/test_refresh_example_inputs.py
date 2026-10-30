"""Synthetic example source binding controls; never real Case/learner credit."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from core.registry import ROOT, Registry
from scripts.refresh_example_inputs import MANIFEST, prepare_refresh, rebind_example, refresh


OLD='61bc9c3e15004639cb442c20e7946ca9631f14ce'
CURRENT='1c388a0596b13935ae7c6a1af00834915a8efa33'


def registry(commit, sid):
    return SimpleNamespace(index={'source_baseline':{'commit':commit}},
        methods={'SYNTHETIC':{'version':'1.0.0'}},
        sources={'sections':{sid:{'path':'synthetic.md','heading':'Synthetic rule',
                                'content':'## Synthetic rule\nExact synthetic action.\n','commit':commit}}})


class ExampleRefreshTests(unittest.TestCase):
    def setUp(self):
        self.previous=registry(OLD,'old-id'); self.current=registry(CURRENT,'new-id')
        self.value={'source_section_ids':['old-id'],'method_id':'SYNTHETIC','method_version':'1.0.0'}

    def test_rebind_uses_explicit_epoch_not_colliding_current_id(self):
        self.current.sources['sections']['old-id']={
            'path':'synthetic.md','heading':'Unrelated reused offset','content':'Different rule.\n'}
        self.assertEqual(rebind_example(self.value,self.previous,self.current)['source_section_ids'],['new-id'])
        self.assertEqual(self.value['source_section_ids'],['old-id'])

    def test_missing_old_id_missing_target_changed_content_and_ambiguity_reject(self):
        for mutation in ('missing_old','missing_target','changed','ambiguous','wrong_old_epoch','wrong_target_epoch'):
            with self.subTest(mutation=mutation):
                previous=deepcopy(self.previous); current=deepcopy(self.current)
                if mutation=='missing_old':previous.sources['sections'].clear()
                elif mutation=='missing_target':current.sources['sections'].clear()
                elif mutation=='changed':current.sources['sections']['new-id']['content']+='New instruction.\n'
                elif mutation=='wrong_old_epoch':previous.sources['sections']['old-id']['commit']=CURRENT
                elif mutation=='wrong_target_epoch':current.sources['sections']['new-id']['commit']=OLD
                else:current.sources['sections']['duplicate']=deepcopy(current.sources['sections']['new-id'])
                with self.assertRaises(ValueError):rebind_example(self.value,previous,current)

    def test_method_versions_are_never_automatically_upgraded(self):
        self.current.methods['SYNTHETIC']['version']='2.0.0'
        with self.assertRaisesRegex(ValueError,'no automatic upgrade'):
            rebind_example(self.value,self.previous,self.current)

    def fixture(self, second=False):
        temporary=TemporaryDirectory(prefix='synthetic-example-refresh-')
        self.addCleanup(temporary.cleanup); root=Path(temporary.name)
        (root/'examples').mkdir(); (root/'provenance').mkdir()
        names=['passage-lesson.synthetic.json']
        if second:names.append('question-lesson-course.json')
        manifest={'scope':'synthetic test only','examples':{}}
        for name in names:
            raw=(json.dumps(self.value)+'\n').encode()
            (root/'examples'/name).write_bytes(raw)
            manifest['examples'][name]={'source_commit':OLD,'sha256':hashlib.sha256(raw).hexdigest()}
        (root/MANIFEST).write_text(json.dumps(manifest)+'\n',encoding='utf-8')
        return root

    def test_manifest_preflight_refresh_and_current_epoch_rerun_are_idempotent(self):
        root=self.fixture()
        with patch('scripts.refresh_example_inputs.Registry',return_value=self.previous):
            report=refresh(root,self.current)
        self.assertEqual(report['updated'],['passage-lesson.synthetic.json'])
        manifest=json.loads((root/MANIFEST).read_bytes())
        identity=manifest['examples']['passage-lesson.synthetic.json']
        self.assertEqual(identity['source_commit'],CURRENT)
        self.assertEqual(identity['sha256'],hashlib.sha256((root/'examples/passage-lesson.synthetic.json').read_bytes()).hexdigest())
        with patch('scripts.refresh_example_inputs.Registry',side_effect=AssertionError('Must not guess old epoch')):
            updates,report=prepare_refresh(root,self.current)
        self.assertEqual(updates,{})
        self.assertEqual(report['updated'],[])

    def test_hash_mismatch_rejects_before_example_or_manifest_write(self):
        root=self.fixture(); path=root/'examples/passage-lesson.synthetic.json'
        path.write_bytes(path.read_bytes()+b' ')
        before={p.relative_to(root):p.read_bytes() for p in root.rglob('*') if p.is_file()}
        with self.assertRaisesRegex(ValueError,'explicit epoch manifest'):refresh(root,self.current)
        self.assertEqual(before,{p.relative_to(root):p.read_bytes() for p in root.rglob('*') if p.is_file()})

    def test_all_registered_examples_preflight_before_any_write(self):
        root=self.fixture(second=True)
        manifest=json.loads((root/MANIFEST).read_bytes())
        manifest['examples']['question-lesson-course.json']['sha256']='0'*64
        (root/MANIFEST).write_text(json.dumps(manifest),encoding='utf-8')
        before={p.relative_to(root):p.read_bytes() for p in root.rglob('*') if p.is_file()}
        with patch('scripts.refresh_example_inputs.Registry',return_value=self.previous):
            with self.assertRaisesRegex(ValueError,'explicit epoch manifest'):refresh(root,self.current)
        self.assertEqual(before,{p.relative_to(root):p.read_bytes() for p in root.rglob('*') if p.is_file()})

    def test_actual_reused_historical_offset_has_different_meaning(self):
        original=Registry(snapshot_commit='b04ebc26d7fa096404111a0bb12f6c77cc8525b9')
        previous=Registry(snapshot_commit=OLD); current=Registry()
        sid='dfb7dd8dc0c2e8a1'
        self.assertNotEqual(original.sources['sections'][sid]['heading'],previous.sources['sections'][sid]['heading'])
        bound=rebind_example({'source_section_ids':[sid]},previous,current)['source_section_ids'][0]
        self.assertEqual(current.sources['sections'][bound]['heading'],'过度推测')

    def test_checked_in_synthetic_lesson_is_current_and_both_actual_cli_renderers_run(self):
        updates,report=prepare_refresh()
        self.assertEqual(updates,{})
        self.assertEqual(report['updated'],[])
        for renderer in ('legacy-wechat','content-export'):
            with self.subTest(renderer=renderer):
                result=subprocess.run([sys.executable,'-X','utf8','-m','answer_engine','lesson',
                    'examples/passage-lesson.synthetic.json','--renderer',renderer],
                    cwd=ROOT,capture_output=True,text=True,encoding='utf-8')
                self.assertEqual(result.returncode,0,result.stderr)
                if renderer=='legacy-wechat':
                    self.assertIn('第31题选A，第32题选A，第33题选A',result.stdout)
                else:
                    output=json.loads(result.stdout)
                    self.assertEqual(output['lesson_id'],'synthetic-program-whole-passage-not-real-exam')
                    self.assertEqual(output['answer_summary'],[
                        {'number':number,'answer':'A'} for number in (31,32,33)])

    def test_registered_grammar_lesson_is_current_and_actual_cli_runs(self):
        updates,report=prepare_refresh()
        self.assertEqual(updates,{})
        self.assertEqual(report['updated'],[])
        manifest=json.loads((ROOT/MANIFEST).read_bytes())
        identity=manifest['examples']['question-lesson-course.json']
        self.assertEqual(identity['source_commit'],Registry().index['source_baseline']['commit'])
        self.assertEqual(identity['registration_basis']['source_commit'],OLD)
        result=subprocess.run([sys.executable,'-X','utf8','-m','answer_engine','analyze',
            'examples/question-lesson-course.json','--renderer','legacy-wechat'],
            cwd=ROOT,capture_output=True,text=True,encoding='utf-8')
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertIn('protection',result.stdout)


if __name__=='__main__':unittest.main()
