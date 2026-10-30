"""Synthetic transport/defect controls, not image semantics or learner trials."""
from copy import deepcopy
import ast
import base64
import hashlib
from io import BytesIO
import json
import subprocess
import sys
import unittest
import yaml
from unittest.mock import patch

from PIL import Image
from jsonschema.exceptions import ValidationError
from core.analyzer import QuestionAnalyzer, PaperAnalyzer
from core.registry import Registry, ROOT
from core.question_verification import material_fingerprint
from renderers import render
from tests import test_terminal_lesson as lesson_fixtures
from tests.test_image_evidence import visual_fixture
from tests import test_frozen_answer_consistency as frozen_fixtures
from video_contracts import verify_bundle, seal, sha, semantic_payload, status_matches
from video_contracts.answer_consistency import artifact_fingerprint, validate_frozen_answer
from video_contracts.image_evidence import image_manifest, check_image_region
from video_contracts.objective_images import scope_fingerprint, region_fingerprint

MODES = ('structured','student','legacy-wechat','content-export')


def synthetic_question(registry):
    factory=lesson_fixtures.TerminalLessonTests(); factory.registry=registry
    q=factory.question()
    q['original_images']=deepcopy(visual_fixture('应用文')['original_images'])
    asset=q['original_images'][0]
    boxes=[[0,0,10,10],[10,0,20,10],[0,10,20,30]]
    q['required_image_evidence']=[{'candidate':cid,'image_id':asset['image_id'],
        'sha256':asset['sha256'],'box':box} for cid,box in zip(q['options'],boxes)]
    terminal=q['question_verification_review']
    terminal.update(schema_version='1.1.0',material_sha256=material_fingerprint(q))
    for check,requirement,observed in zip(terminal['candidate_checks'],q['required_image_evidence'],
            ['合成外部观察甲','合成外部观察乙','合成外部观察丙']):
        check['image_evidence']=[{key:value for key,value in requirement.items() if key!='candidate'}]
        check['image_evidence'][0]['observed']=observed
    q['lesson_review']['schema_version']='1.2.0'
    segment=q['lesson_review']['segments'][2]
    segment['image_evidence']=[{'candidate':cid,'region_index':0} for cid in q['options']]
    segment['text']+='合成外部观察甲，合成外部观察乙，合成外部观察丙。'
    return q


class ObjectiveImageEvidenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.registry=Registry(); cls.engine=QuestionAnalyzer(cls.registry)

    def question(self): return synthetic_question(self.registry)

    def source_question(self):
        q=self.question()
        for key in ('question_verification_review','lesson_review','action_executions','observations','requested_chain'):
            q.pop(key,None)
        return q

    def reject_renderers(self, analysis):
        for mode in MODES:
            with self.subTest(mode=mode),self.assertRaises((ValueError,ValidationError)):
                render(analysis,mode,self.registry)

    def frozen_helper(self):
        helper=frozen_fixtures.FrozenAnswerConsistencyTests()
        helper.registry=self.registry; helper.engine=self.engine
        from answer_engine.frozen_export import FrozenAssetExporter
        helper.exporter=FrozenAssetExporter()
        return helper

    def test_complete_visual_transport_has_own_graph_and_portable_lesson(self):
        q=self.question(); before=deepcopy(q); analysis=self.engine.analyze(q)
        self.assertEqual(q,before)
        self.assertEqual(analysis['schema_version'],'1.9.0')
        self.assertEqual(analysis['answer'],'A')
        self.assertEqual(analysis['lesson_feedback']['scope'],'single_question_lesson')
        self.assertEqual(analysis['candidate_analysis'],[])
        self.assertEqual(analysis['method_chain'][0]['role'],'interpreter')
        report=analysis['question_verification']
        self.assertEqual(report['required_image_evidence'],q['required_image_evidence'])
        image_ids=[nid for b in report['candidate_bindings'] for nid in b['image_evidence_ids']]
        self.assertEqual(len(image_ids),3); self.assertEqual(len(set(image_ids)),3)
        for mode in MODES:
            output=render(analysis,mode,self.registry)
            self.assertNotIn(q['original_images'][0]['data_base64'],output)
        self.assertEqual(json.loads(render(analysis,'content-export',self.registry))['export_schema_version'],'1.9.0')
        helper=self.frozen_helper(); req=helper.request(q); helper.rebind_synthetic_review(req)
        with patch.object(QuestionAnalyzer,'analyze',side_effect=AssertionError('must not solve')):
            bundle=helper.exporter.export(req); verify_bundle(bundle)
            self.assertEqual(helper.exporter.status(req)['effective_status'],'ACTIVE')
        self.assertTrue(set(image_ids)<={e['artifact_id'] for e in bundle['lifecycle']['evidence']})
        paper=PaperAnalyzer(self.engine).analyze({'paper_id':'synthetic-image-paper','questions':[q]})
        self.assertEqual(paper['method_coverage']['R03']['reviewed_decision_question_ids'],[])
        from content_os.candidates import engineering_gate
        gate=engineering_gate(bundle,{'method_id':'R03','action_ids':['interpret']},'full_solution',
                              helper.exporter.status(req))
        self.assertNotEqual(gate['status'],'PASS')
        self.assertIn('candidate_closure',gate['blockers'])
        self.assertIn('answer_attribution_recorded',gate['blockers'])

    def test_source_obligations_cannot_be_removed_by_provider_or_old_terminal(self):
        q=self.question()
        def provider(value,registry):
            value.pop('required_image_evidence'); return value
        with self.assertRaisesRegex(ValueError,'cannot replace original.*required_image_evidence'):
            QuestionAnalyzer(self.registry,review_provider=provider).analyze(q)
        for mutation in ('old_review','missing_region','empty_region','missing_candidate','empty_required'):
            q=self.question()
            if mutation=='old_review':
                q['question_verification_review']['schema_version']='1.0.0'
                for c in q['question_verification_review']['candidate_checks']: c.pop('image_evidence')
            elif mutation=='missing_region': q['question_verification_review']['candidate_checks'][1].pop('image_evidence')
            elif mutation=='empty_region': q['question_verification_review']['candidate_checks'][1]['image_evidence']=[]
            elif mutation=='missing_candidate': q['required_image_evidence'][0]['candidate']='X'
            else: q['required_image_evidence']=[]
            if 'question_verification_review' in q:
                q['question_verification_review']['material_sha256']=material_fingerprint(q)
            with self.subTest(mutation=mutation),self.assertRaises((ValueError,ValidationError)):
                self.engine.analyze(q)

    def test_clean_source_only_obligation_is_unresolved_in_question_paper_and_portable_export(self):
        q=self.source_question(); before=deepcopy(q); a=self.engine.analyze(q)
        self.assertEqual(q,before)
        self.assertEqual(a['status'],'needs_evidence'); self.assertIsNone(a['answer'])
        self.assertFalse(a['answer_verification']['closed']); self.assertFalse(a['content_eligible'])
        self.assertNotIn('question_verification',a)
        root=a['evidence_graph']['nodes'][0]
        self.assertEqual(root['required_image_evidence'],q['required_image_evidence'])
        self.assertEqual(root['material_sha256'],material_fingerprint(q))
        self.assertFalse(any(n['type']=='image_evidence' for n in a['evidence_graph']['nodes']))
        for mode in MODES:
            text=render(a,mode,self.registry)
            self.assertNotIn('最后这一题选',text)
        paper=PaperAnalyzer(self.engine).analyze({'paper_id':'synthetic-source-image','questions':[q]})
        self.assertIsNone(paper['questions'][0]['answer'])
        self.assertEqual(paper['questions'][0]['status'],'needs_evidence')
        self.assertEqual(paper['evidence_complete_count'],0)
        self.assertEqual(paper['case_candidates'],[])
        helper=self.frozen_helper(); request=helper.request(q)
        self.assertEqual(request['reviews'],[])
        bundle=helper.exporter.export(request); verify_bundle(bundle)
        self.assertEqual(bundle['source_snapshot']['required_image_evidence'],q['required_image_evidence'])
        self.assertEqual(helper.exporter.status(request)['effective_status'],'INCOMPLETE')
        validate_frozen_answer(q,a)

    def test_source_only_still_validates_original_assets_obligations_and_provider_immutability(self):
        for mutation in ('unknown_owner','missing_asset','wrong_hash','outside','duplicate'):
            q=self.source_question(); requirement=q['required_image_evidence'][0]
            if mutation=='unknown_owner': requirement['candidate']='X'
            elif mutation=='missing_asset': q.pop('original_images')
            elif mutation=='wrong_hash': requirement['sha256']='0'*64
            elif mutation=='outside': requirement['box']=[0,0,99,99]
            else: q['required_image_evidence'].append(deepcopy(requirement))
            with self.subTest(mutation=mutation),self.assertRaises((ValueError,ValidationError)):
                self.engine.analyze(q)
        def strip_source(q,registry): q.pop('required_image_evidence'); return q
        with self.assertRaisesRegex(ValueError,'cannot replace original.*required_image_evidence'):
            QuestionAnalyzer(self.registry,review_provider=strip_source).analyze(self.source_question())
        def old_review(q,registry):
            review=deepcopy(self.question()['question_verification_review']); review['schema_version']='1.0.0'
            for c in review['candidate_checks']: c.pop('image_evidence')
            q['question_verification_review']=review
            return q
        with self.assertRaisesRegex(ValueError,'cannot downgrade to text'):
            QuestionAnalyzer(self.registry,review_provider=old_review).analyze(self.source_question())

    def test_source_only_cannot_be_a_terminal_deletion_or_source_obligation_downgrade(self):
        q=self.question(); q.pop('question_verification_review')
        with self.assertRaisesRegex(ValueError,'closed question'):
            self.engine.analyze(q)  # A whole-question lesson cannot survive its terminal.
        full=self.engine.analyze(self.question())
        for mutation in ('answer','lesson','image_proof'):
            a=deepcopy(full); a.pop('question_verification')
            if mutation!='answer':
                a.update(answer=None,answer_confidence='low',content_eligible=False,status='needs_evidence')
                a['answer_verification']['closed']=False
            if mutation=='image_proof': a['lesson_feedback']=None
            with self.subTest(mutation=mutation): self.reject_renderers(a)
        helper=self.frozen_helper()
        for mutation in ('drop_root_requirement','drop_question_requirement','closed_source','supplied_review_missing_projection','borrow_owner_from_relation_annotation'):
            req=helper.request(self.source_question()); a=req['analysis']
            if mutation=='drop_root_requirement': a['evidence_graph']['nodes'][0].pop('required_image_evidence')
            elif mutation=='drop_question_requirement': req['question'].pop('required_image_evidence')
            elif mutation=='closed_source':
                a.update(answer='A',answer_confidence='medium',content_eligible=True,status='reviewed')
                a['answer_verification']['closed']=True
            elif mutation=='borrow_owner_from_relation_annotation':
                q=req['question']; q['options'].pop('C')
                span={'field':'passage','start':0,'end':len(q['passage']),'quote':q['passage']}
                q['relations']=[{'method_id':'R03','candidate':'C','effect':'undetermined','claim':'gamma',
                    'evidence':[span],'decision_rule_check':'synthetic annotation','stop_rule_check':'no external decision',
                    'verification':'unresolved synthetic relation','reviewer':'synthetic probe','review_status':'unreviewed'}]
                a['evidence_graph']['nodes'][0]['material_sha256']=material_fingerprint(q)
            else:
                # A clean held projection cannot pretend the originally supplied
                # terminal+whole lesson never existed, even after resealing.
                req['question']=self.question()
            with self.subTest(mutation=mutation): helper.rejected_at_boundaries(req)
        for mutation in ('different_required_box','duplicate_requirement','empty_new_interface'):
            q=self.question()
            if mutation=='different_required_box': q['required_image_evidence'][0]['box']=[1,1,2,2]
            elif mutation=='duplicate_requirement': q['required_image_evidence'].append(deepcopy(q['required_image_evidence'][0]))
            else:
                q.pop('required_image_evidence')
                for c in q['question_verification_review']['candidate_checks']: c.pop('image_evidence')
            q['question_verification_review']['material_sha256']=material_fingerprint(q)
            with self.subTest(mutation=mutation),self.assertRaises((ValueError,ValidationError)):
                self.engine.analyze(q)

    def test_bad_assets_regions_and_required_identities_are_rejected(self):
        for mutation in ('unknown_asset','wrong_hash','negative','outbounds','reversed','float','bool','missing_asset','duplicate_asset','mime','base64','garbage','truncated','frame'):
            q=self.question(); region=q['question_verification_review']['candidate_checks'][0]['image_evidence'][0]
            asset=q['original_images'][0]
            if mutation=='unknown_asset': region['image_id']='unknown'
            elif mutation=='wrong_hash': region['sha256']='0'*64
            elif mutation=='negative': region['box']=[-1,0,10,10]
            elif mutation=='outbounds': region['box']=[0,0,21,30]
            elif mutation=='reversed': region['box']=[10,0,0,10]
            elif mutation=='float': region['box']=[0.5,0,10,10]
            elif mutation=='bool': region['box']=[False,0,10,10]
            elif mutation=='missing_asset': q['original_images']=[]
            elif mutation=='duplicate_asset': q['original_images'].append(deepcopy(asset))
            elif mutation=='mime': asset['mime_type']='image/jpeg'
            elif mutation=='base64': asset['data_base64']='not base64!'
            else:
                if mutation=='garbage': raw=b'not an image'
                elif mutation=='truncated': raw=base64.b64decode(asset['data_base64'])[:35]
                else:
                    output=BytesIO(); Image.new('RGB',(20,30),'white').save(output,'PNG',save_all=True,
                        append_images=[Image.new('RGB',(20,30),'black')],duration=10,loop=0)
                    raw=output.getvalue()
                asset.update(data_base64=base64.b64encode(raw).decode(),sha256=hashlib.sha256(raw).hexdigest())
            q['question_verification_review']['material_sha256']=material_fingerprint(q)
            with self.subTest(mutation=mutation),self.assertRaises((ValueError,ValidationError)):
                self.engine.analyze(q)

    def test_portable_decoder_limits_and_integer_region_gate(self):
        q=self.question(); manifest=image_manifest(q)
        for kwargs in ({'max_bytes':2},{'max_pixels':10}):
            with self.assertRaises(ValueError): image_manifest(q,**kwargs)
        for value in (False,0.1):
            region=deepcopy(q['required_image_evidence'][0]); region['box'][0]=value
            with self.assertRaises(ValueError): check_image_region(region,manifest)

    def test_optional_regions_need_no_source_obligation_but_are_not_legacy_fields(self):
        q=self.question(); q.pop('required_image_evidence')
        q['question_verification_review']['material_sha256']=material_fingerprint(q)
        a=self.engine.analyze(q)
        self.assertNotIn('required_image_evidence',a['question_verification'])
        self.assertNotIn('required_image_evidence',a['evidence_graph']['nodes'][0])
        validate_frozen_answer(q,a)
        q['question_verification_review']['schema_version']='1.0.0'
        with self.assertRaises(ValidationError): self.engine.analyze(q)
        q=self.question(); q['lesson_review']['schema_version']='1.1.0'
        with self.assertRaises(ValidationError): self.engine.analyze(q)

    def test_images_do_not_replace_semantic_artifacts_or_override_stop(self):
        q=self.question(); q.pop('lesson_review')
        span=q['observations'][0]['evidence'][0]
        q['requested_chain']=['R13']; q['observations'][0]['method_id']='R13'
        q['action_executions'][0].update(method_id='R13',role='locator',
            output={'kind':'located_evidence','spans':[span]})
        q['question_verification_review']['source_section_ids']=self.registry.methods['R13']['section_ids']
        with self.assertRaisesRegex(ValueError,'cannot alone decide'): self.engine.analyze(q)
        for key,value in [('review_status','unreviewed'),('stop_applied',True)]:
            q=self.question(); q.pop('lesson_review'); q['question_verification_review'][key]=value
            a=self.engine.analyze(q)
            self.assertIsNone(a['answer']); self.assertFalse(a['content_eligible'])
            self.assertNotIn('最后这一题选',render(a,'student',self.registry))
        q=self.question(); q.pop('required_image_evidence'); q.pop('lesson_review')
        q['question_verification_review']['schema_version']='1.0.0'
        for c in q['question_verification_review']['candidate_checks']: c.pop('image_evidence')
        q['question_verification_review']['material_sha256']=material_fingerprint(q)
        a=self.engine.analyze(q)
        self.assertEqual(a['schema_version'],'1.8.0')
        self.assertNotIn('image_manifest',a['question_verification'])

    def test_same_physical_region_has_distinct_candidate_owned_nodes(self):
        q=self.question()
        for c,r in zip(q['question_verification_review']['candidate_checks'],q['required_image_evidence']):
            c['image_evidence'][0]['box']=[0,0,20,30]; r['box']=[0,0,20,30]
        q['question_verification_review']['material_sha256']=material_fingerprint(q)
        a=self.engine.analyze(q)
        ids=[b['image_evidence_ids'][0] for b in a['question_verification']['candidate_bindings']]
        self.assertEqual(len(set(ids)),3)

    def test_four_candidate_seven_region_shape_and_split_spoken_coverage(self):
        q=self.question(); terminal=q['question_verification_review']
        q['options']['D']='synthetic delta'
        check=deepcopy(terminal['candidate_checks'][-1]); check.update(candidate='D',claim=q['options']['D'])
        check['image_evidence'][0]['observed']='合成外部观察丁'
        terminal['candidate_checks'].append(check)
        source=deepcopy(q['required_image_evidence'][-1]); source['candidate']='D'
        q['required_image_evidence'].append(source)
        for check in terminal['candidate_checks'][:3]:
            region=deepcopy(check['image_evidence'][0]); region['box']=[1,1,2,2]
            region['observed']='第二处'+check['candidate']+'合成外部观察'
            check['image_evidence'].append(region)
            q['required_image_evidence'].append({'candidate':check['candidate'],
                **{k:v for k,v in region.items() if k!='observed'}})
        terminal['material_sha256']=material_fingerprint(q)
        segment=q['lesson_review']['segments'][2]
        segment['candidate_ids']=['A','B','C','D']
        segment['image_evidence']=[{'candidate':c['candidate'],'region_index':i}
            for c in terminal['candidate_checks'] for i in range(len(c['image_evidence']))]
        segment['text']+='D合成外部观察丁，第二处A合成外部观察，第二处B合成外部观察，第二处C合成外部观察。'
        # Two spoken comparisons each own exactly their candidate regions.
        second=deepcopy(segment); second['segment_id']='terminal-CD'; second['candidate_ids']=['C','D']
        second['image_evidence']=[r for r in second['image_evidence'] if r['candidate'] in {'C','D'}]
        segment['candidate_ids']=['A','B']
        segment['image_evidence']=[r for r in segment['image_evidence'] if r['candidate'] in {'A','B'}]
        q['lesson_review']['segments'].insert(3,second)
        a=self.engine.analyze(q)
        self.assertEqual(sum(len(b['image_evidence_ids']) for b in a['question_verification']['candidate_bindings']),7)
        self.assertEqual(a['lesson_feedback']['scope'],'single_question_lesson')
        validate_frozen_answer(q,a)

    def test_renderers_reject_owner_observation_scope_and_graph_corruption(self):
        base=self.engine.analyze(self.question())
        for mutation in ('owner','observed','image_ref','hash','region_id','drop_node','drop_edge','foreign_edge','foreign_action','wrong_edge_type','extra_node','manifest','drop_manifest','drop_required','root_required','rehash_graph','old_transport'):
            a=deepcopy(base); report=a['question_verification']; b=report['candidate_bindings'][0]
            nid=b['image_evidence_ids'][0]; nodes=a['evidence_graph']['nodes']
            node=next(n for n in nodes if n['id']==nid); edges=a['evidence_graph']['edges']
            if mutation=='owner': node['candidate']='B'
            elif mutation=='observed': report['review']['candidate_checks'][0]['image_evidence'][0]['observed']='changed'
            elif mutation=='image_ref': node['image_ref']['box']=[1,1,2,2]
            elif mutation=='hash': node['image_ref']['sha256']='0'*64
            elif mutation=='region_id': b['image_evidence_ids'][0]=report['candidate_bindings'][1]['image_evidence_ids'][0]
            elif mutation=='drop_node': nodes.remove(node)
            elif mutation=='drop_edge': edges[:]=[e for e in edges if not(e['from']==nid and e['to']==b['review_node_id'])]
            elif mutation=='foreign_edge': edges.append({'from':nid,'to':report['candidate_bindings'][1]['review_node_id'],'type':'supports'})
            elif mutation=='foreign_action': edges.append({'from':nid,'to':a['execution_trace'][0]['artifact_node_id'],'type':'supports'})
            elif mutation=='wrong_edge_type':
                next(e for e in edges if e['from']==nid and e['to']==b['review_node_id'])['type']='locates'
            elif mutation=='extra_node': clone=deepcopy(node); clone['id']='extra-image'; nodes.append(clone)
            elif mutation=='manifest': report['image_manifest'][0]['width']=99
            elif mutation=='drop_manifest': report.pop('image_manifest')
            elif mutation=='drop_required': report.pop('required_image_evidence')
            elif mutation=='root_required': nodes[0].pop('required_image_evidence')
            elif mutation=='old_transport': a['schema_version']='1.8.0'
            else: node['label']='changed'; node['artifact_fingerprint']=region_fingerprint(report,'A',0)
            with self.subTest(mutation=mutation): self.reject_renderers(a)

    def test_spoken_segments_require_canonical_regions_observations_and_complete_coverage(self):
        for mutation in ('missing_refs','wrong_owner','wrong_index','repeated','missing_observation','old_version'):
            q=self.question(); s=q['lesson_review']['segments'][2]
            if mutation=='missing_refs': s.pop('image_evidence')
            elif mutation=='wrong_owner': s['image_evidence'][0]['candidate']='X'
            elif mutation=='wrong_index': s['image_evidence'][0]['region_index']=9
            elif mutation=='repeated': s['image_evidence'].append(deepcopy(s['image_evidence'][0]))
            elif mutation=='missing_observation': s['text']=s['text'].replace('合成外部观察甲','changed')
            else: q['lesson_review']['schema_version']='1.1.0'; s.pop('image_evidence')
            with self.subTest(mutation=mutation),self.assertRaises((ValueError,ValidationError)):
                self.engine.analyze(q)
        q=self.question(); q['lesson_review']['review_status']='unreviewed'
        q['lesson_review']['segments'][2].pop('image_evidence')
        a=self.engine.analyze(q)
        self.assertEqual(a['lesson_feedback']['scope'],'unreviewed')
        self.assertEqual(a['lesson_feedback']['review']['segments'],[])
        self.assertNotIn('最后这一题选',render(a,'student',self.registry))
        q=self.question(); q.pop('lesson_review'); a=self.engine.analyze(q)
        self.assertIn('逐步讲解还没齐',render(a,'student',self.registry))

    def test_portable_rejects_rehashed_source_terminal_and_lesson_defects(self):
        helper=self.frozen_helper()
        for mutation in ('swapped_source','drop_source_requirement','drop_terminal_region','wrong_candidate','observed','lesson_text','drop_lesson','lesson_ref','drop_spoken_edge','drop_spoken_binding','method_text','missing_stop','drop_node','method_trigger_edge','duplicate_edge'):
            req=helper.request(self.question()); q,a=req['question'],req['analysis']; report=a['question_verification']
            s=a['lesson_feedback']['review']['segments'][2]; binding=a['lesson_feedback']['segment_bindings'][2]
            if mutation=='swapped_source':
                output=BytesIO(); Image.new('RGB',(20,30),'red').save(output,'PNG'); raw=output.getvalue()
                q['original_images'][0].update(data_base64=base64.b64encode(raw).decode(),sha256=hashlib.sha256(raw).hexdigest())
            elif mutation=='drop_source_requirement': a['evidence_graph']['nodes'][0].pop('required_image_evidence'); report.pop('required_image_evidence')
            elif mutation=='drop_terminal_region': report['review']['candidate_checks'][0].pop('image_evidence')
            elif mutation=='wrong_candidate': report['candidate_bindings'][0]['image_evidence_ids']=report['candidate_bindings'][1]['image_evidence_ids']
            elif mutation=='observed': report['review']['candidate_checks'][0]['image_evidence'][0]['observed']='changed'
            elif mutation=='lesson_text': s['text']+='changed'
            elif mutation=='drop_lesson': a['lesson_feedback']=None
            elif mutation=='lesson_ref': s['image_evidence'][0]['candidate']='B'
            elif mutation=='drop_spoken_edge':
                nid=binding['image_evidence_ids'][0]
                a['evidence_graph']['edges'][:]=[e for e in a['evidence_graph']['edges'] if not(e['from']==nid and e['to']==binding['relation_node_id'])]
            elif mutation=='drop_spoken_binding': binding.pop('image_evidence_ids')
            elif mutation=='method_text': a['lesson_feedback']['review']['segments'][0]['text']+='changed'
            elif mutation=='drop_node':
                nid=report['candidate_bindings'][0]['image_evidence_ids'][0]
                a['evidence_graph']['nodes'][:]=[n for n in a['evidence_graph']['nodes'] if n['id']!=nid]
            elif mutation=='method_trigger_edge':
                target=a['lesson_feedback']['segment_bindings'][0]['relation_node_id']
                nodes={n['id']:n for n in a['evidence_graph']['nodes']}
                a['evidence_graph']['edges'][:]=[e for e in a['evidence_graph']['edges'] if not(e['to']==target and nodes[e['from']]['type']=='question_signal')]
            elif mutation=='duplicate_edge': a['evidence_graph']['edges'].append(deepcopy(a['evidence_graph']['edges'][-1]))
            else:
                a['lesson_feedback']['review']['segments'].pop()
                a['lesson_feedback']['segment_bindings'].pop()
            with self.subTest(mutation=mutation): helper.rejected_at_boundaries(req)

    def test_legacy_text_and_writing_four_outputs_are_byte_identical(self):
        # Preserve the original eight golden hashes and their actual Registry
        # conditions; metadata/presentation updates must not rewrite history.
        registry=Registry(snapshot_commit='1c388a0596b13935ae7c6a1af00834915a8efa33')
        for mid in registry.methods:
            registry.methods[mid]=yaml.safe_load((ROOT/f'method-registry/history/{mid}/editorial-before-20261028.yaml').read_text(encoding='utf-8'))
        factory=lesson_fixtures.TerminalLessonTests(); factory.registry=registry
        engine=QuestionAnalyzer(registry)
        cases={'text':factory.question(),'writing':visual_fixture('应用文')}
        expected={
            'text':['062325a72fa2ff5c8ae58cddf56c48f5c1e1b4188644fbe359d72906a962132f','edfe8e47fa604a8e3057502ecbb0cd67eb43028570973f866d5846cbd9a58ae6','edfe8e47fa604a8e3057502ecbb0cd67eb43028570973f866d5846cbd9a58ae6','bd14c871aa3e8f88cdfdcbdd820e3b2b5e799565006ad949371f249a4757282c'],
            'writing':['1afdf8932b4294686f8d1dc7743adcad509401ab2f52f98536d313c0801324ed','67031465eb0ae488feb9b777c17ff3117417d5a3674d3c1eff027b460f313487','c12be59c2cd58daf7bde7b6c3e99af353d8d76fd7f334ba84df01eec894efa30','aa59693d723840d9ccb7df748db62af6d3ebed94c581c250558bfa1e35a06c57']}
        for name,q in cases.items():
            a=engine.analyze(q)
            for mode,digest in zip(MODES,expected[name]):
                self.assertEqual(hashlib.sha256(render(a,mode,registry).encode()).hexdigest(),digest,(name,mode))

    def test_current_source_keeps_legacy_student_visible_text_and_writing(self):
        factory=lesson_fixtures.TerminalLessonTests();factory.registry=self.registry
        cases={'text':factory.question(),'writing':visual_fixture('应用文')}
        expected={
            'text':['edfe8e47fa604a8e3057502ecbb0cd67eb43028570973f866d5846cbd9a58ae6']*2,
            'writing':['67031465eb0ae488feb9b777c17ff3117417d5a3674d3c1eff027b460f313487','c12be59c2cd58daf7bde7b6c3e99af353d8d76fd7f334ba84df01eec894efa30']}
        for name,q in cases.items():
            a=self.engine.analyze(q)
            for mode,digest in zip(('student','legacy-wechat'),expected[name]):
                self.assertEqual(hashlib.sha256(render(a,mode,self.registry).encode()).hexdigest(),digest,(name,mode))

    def test_portable_modules_do_not_import_core_registry_or_solver(self):
        for filename in ('image_evidence.py','objective_images.py','answer_consistency.py'):
            tree=ast.parse((ROOT/'video_contracts'/filename).read_text('utf-8'))
            for node in ast.walk(tree):
                if isinstance(node,ast.ImportFrom):
                    self.assertNotIn((node.module or '').split('.')[0],{'core','answer_engine','renderers'})
        process=subprocess.run([sys.executable,'-c',
            "import sys; from video_contracts.objective_images import validate_image_projection; "
            "assert not any(n.split('.')[0] in {'core','answer_engine','renderers'} for n in sys.modules)"],cwd=ROOT,capture_output=True,text=True)
        self.assertEqual(process.returncode,0,process.stderr)

    def test_resealed_image_lifecycle_and_status_cannot_drop_graph_evidence(self):
        helper=self.frozen_helper(); req=helper.request(self.question()); helper.rebind_synthetic_review(req)
        bundle=helper.exporter.export(req); status=helper.exporter.status(req)
        self.assertTrue(status_matches(bundle,status))
        bad=deepcopy(bundle)
        image_ids={n['id'] for n in req['analysis']['evidence_graph']['nodes'] if n['type']=='image_evidence'}
        bad['lifecycle']['evidence']=[e for e in bad['lifecycle']['evidence'] if e['artifact_id'] not in image_ids]
        bad['semantic_binding_sha']=sha(semantic_payload(bad)); bad=seal(bad)
        with self.assertRaisesRegex(ValueError,'image evidence lifecycle'): verify_bundle(bad)
        status['lifecycle']['evidence'].pop(); status=seal(status)
        self.assertFalse(status_matches(bundle,status))

    def test_fresh_process_portable_checks_valid_and_fully_resealed_defective_image(self):
        helper=self.frozen_helper(); req=helper.request(self.question()); helper.rebind_synthetic_review(req)
        bundle=helper.exporter.export(req)
        from tests import test_frozen_answer_closure as closure_fixtures
        a=deepcopy(req['analysis'])
        next(n for n in a['evidence_graph']['nodes'] if n['type']=='image_evidence')['label']='changed'
        bad=closure_fixtures.FrozenAnswerClosureTests().resealed_bundle(bundle,a)
        source_bundle=helper.exporter.export(helper.request(self.source_question()))
        program=("import json,sys; from video_contracts import verify_bundle; "
                 "assert not any(n.split('.')[0] in {'core','answer_engine','renderers'} for n in sys.modules); "
                 "verify_bundle(json.load(sys.stdin))")
        for value,valid in ((bundle,True),(source_bundle,True),(bad,False)):
            result=subprocess.run([sys.executable,'-X','utf8','-c',program],input=json.dumps(value),
                text=True,capture_output=True,cwd=ROOT,timeout=30)
            self.assertEqual(result.returncode==0,valid,result.stderr)
            if not valid: self.assertIn('ValueError',result.stderr)


if __name__=='__main__': unittest.main()
