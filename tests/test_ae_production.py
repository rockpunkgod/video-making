"""Synthetic V8 contract controls; real AE evidence stays in ignored local-data."""
from copy import deepcopy
from pathlib import Path
import unittest
import json
from unittest.mock import Mock
import tempfile
from core.registry import Registry
from core.analyzer import QuestionAnalyzer
from answer_engine.frozen_export import FrozenAssetExporter
from tests.test_execution import seven_chain_fixture
from content_os.candidates import make_candidate
from content_os.director import build_draft,finalize_copy,manifest
from video_contracts import ROOT,read,sha,seal
from ae_production.contract import build_contract,validate_contract
from ae_production.layout import wrap,pages,slots,subtitle_cues,LayoutOverflow


class AEProductionTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        registry=Registry(); q=seven_chain_fixture(); a=QuestionAnalyzer(registry).analyze(q)
        r={'question':q,'analysis':a,'methods':[deepcopy(registry.methods[mid]) for mid in a['method_versions']],
           'reviews':[{'question_id':q['question_id'],'input_sha256':sha(q),'analysis_sha256':sha(a),'reviewer_kind':'AI',
                       'reviewer':'SYNTHETIC V8 CONTROL','evaluation_phase':'post_reveal'}],
           'withdrawals':[],'evaluation_phase':'post_reveal','source':{'usage_status':'internal_only','redistribution_status':'redistribution_not_verified','attribution_text':'SYNTHETIC ONLY','source_reference':'program-only'}}
        exp=FrozenAssetExporter(); b=exp.export(r); cls.statuses={b['asset_id']:exp.status(r)}
        candidate=make_candidate([b],[{'asset_id':b['asset_id'],'method_id':'F01','action_ids':['group-sentence']}],cls.statuses)
        cls.package=finalize_copy(build_draft(candidate,cls.statuses)); cls.manifest=manifest(cls.package,candidate)
        cls.design=read(ROOT/'ae/design/swiss-academic-motion.json')
        if not Path(cls.design['font']['measurement_file']).exists():
            linux=Path('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf')
            if not linux.exists(): raise unittest.SkipTest('No explicitly measured test font available')
            cls.design['font']['measurement_file']=str(linux)
            cls.design['font']['postscript']='DejaVuSans'

    def contract(self): return build_contract(self.package,self.manifest,self.statuses,self.design)

    def test_repeat_and_upstream_immutability(self):
        before=sha([self.package,self.manifest,self.statuses]); a=self.contract();b=self.contract()
        self.assertEqual(a,b);self.assertEqual(before,sha([self.package,self.manifest,self.statuses]))
        self.assertFalse(a['public_render_ready']); self.assertEqual(a['usage'],'INTERNAL_ENGINEERING_PREVIEW')

    def test_revision_changes_render_identity_without_copy_change(self):
        a=self.contract();b=build_contract(self.package,self.manifest,self.statuses,self.design,revision=2)
        self.assertNotEqual(a['render_id'],b['render_id']);self.assertEqual(a['final_copy_sha'],b['final_copy_sha'])

    def test_manifest_wrong_package_rejected(self):
        m=deepcopy(self.manifest);m['package_sha']='0'*64
        with self.assertRaises(ValueError):build_contract(self.package,m,self.statuses,self.design)

    def test_missing_status_rejected(self):
        with self.assertRaises((ValueError,KeyError)):build_contract(self.package,self.manifest,{},self.design)

    def test_withdrawal_blocks_rerender(self):
        rc=self.contract(); statuses=deepcopy(self.statuses)
        for key,st in list(statuses.items()):st['effective_status']='WITHDRAWN';statuses[key]=seal(st)
        with self.assertRaises(ValueError):validate_contract(rc,self.package,self.manifest,statuses)

    def test_package_stale_cannot_be_rendered(self):
        p=deepcopy(self.package);p['invalidation']['teaching_stale']=True;m=deepcopy(self.manifest);m['package_sha']=sha(p)
        with self.assertRaises(ValueError):build_contract(p,m,self.statuses,self.design)

    def test_component_copy_tamper_rejected(self):
        rc=self.contract();rc['scenes'][0]['components'][0]['content']['text']='Invented teaching claim'
        with self.assertRaises(ValueError):validate_contract(rc,self.package,self.manifest,self.statuses)

    def test_role_tamper_rejected(self):
        rc=self.contract();rc['methods'][0]['role']='decider'
        with self.assertRaises(ValueError):validate_contract(rc,self.package,self.manifest,self.statuses)

    def test_stop_cannot_be_removed(self):
        rc=self.contract();rc['scenes']=[s for s in rc['scenes'] if s['scene_type']!='STOP_RULE']
        with self.assertRaises(ValueError):validate_contract(rc,self.package,self.manifest,self.statuses)

    def test_typed_output_preserved(self):
        rc=self.contract(); originals=[s['method_visual'] for s in self.package['semantic_scenes'] if s['method_visual']]
        outputs=[s['typed_output'] for s in rc['scenes'] if s['typed_output']]
        self.assertTrue(all(o in outputs for o in originals));self.assertTrue(any(c['component_type']=='OPTION_GROUP_GRID' for s in rc['scenes'] for c in s['components']))

    def test_subtitle_complete_synced_and_readable(self):
        rc=self.contract()
        for s,t in zip(self.package['semantic_scenes'],self.package['timeline']):
            cues=[c for c in rc['subtitles'] if c['scene_id']==s['scene_id']]
            self.assertEqual(''.join(c['text'] for c in cues),s['spoken_text'])
            self.assertTrue(all(len(c['lines'])<=2 and c['start']>=t['start'] and c['end']<=t['end'] for c in cues))

    def test_layout_stress_exact_characters(self):
        cases=['short','word '*120,'supercalifragilisticexpialidocious'*8,'中文 English 混排'*30,
               'line one\nline two','one\ntwo\nthree','one\ntwo\nthree\nfour',
               'A B C D E F G','Evidence '*150,'长字幕 with English '*80]
        for text in cases:
            with self.subTest(text=text[:20]):
                pg=pages(text,888,512,'Body',self.design)
                self.assertEqual(''.join(''.join(x) for x in pg),text)
                self.assertTrue(all(len(x)*64<=512 for x in pg))
        with self.assertRaises(LayoutOverflow):slots('long '*300,[96,352,888,64],'Body',self.design)

    def test_subtitle_unreadable_time_blocks(self):
        with self.assertRaises(LayoutOverflow):subtitle_cues('中文 '*300,0,1,'s',self.design)

    def test_no_teaching_modules_in_production(self):
        import ast
        for path in (ROOT/'ae_production').glob('*.py'):
            tree=ast.parse(path.read_text(encoding='utf-8'))
            for node in ast.walk(tree):
                if isinstance(node,ast.ImportFrom):self.assertFalse((node.module or '').startswith(('core','answer_engine')))
                if isinstance(node,ast.Import):self.assertFalse(any(a.name.startswith(('core','answer_engine')) for a in node.names))

    def test_actual_ae_contract_file_drift_rejected(self):
        from ae_production.execution import verify_composition
        rc=self.contract(); actual=deepcopy(rc);actual['methods'][0]['role']='decider'
        client=Mock();client.call.return_value={'content':json.dumps({'comment':json.dumps({k:rc[k] for k in ('render_id','package_id','package_sha','template_version')}),'contract_text':json.dumps(actual)})}
        with self.assertRaises(ValueError):verify_composition(client,'12',rc)

    def test_withdrawal_propagates_to_registered_preview(self):
        from ae_production.catalog import register_preview,refresh_preview_index
        rc=self.contract();statuses=deepcopy(self.statuses)
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'index.json'
            register_preview(path,self.package,rc,Path(tmp)/'preview.mp4',self.statuses)
            for key,st in list(statuses.items()):st['effective_status']='WITHDRAWN';statuses[key]=seal(st)
            index=refresh_preview_index(path,statuses)
            render=next(e['artifact'] for e in index['entries'] if e['kind']=='render')
            self.assertTrue(render['invalidation']['teaching_stale']);self.assertEqual(render['status'],'stale')
            self.assertFalse(render['render_ready_for_publication'])

if __name__=='__main__':unittest.main()
