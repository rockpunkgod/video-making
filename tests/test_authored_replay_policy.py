"""Synthetic user-bound replay omission; no Adobe or sensory approval."""
from copy import deepcopy
import json
from pathlib import Path
import tempfile
import unittest

from video_contracts import read,write
from scripts.voice_delivery import sha256
from ae_production.authored_episode import (
    USER_REPLAY_OMISSION_QUOTE,checked_author,validate_replay_policy,
)
from ae_production.authored_editorial import validate_editorial
from ae_production.authored_native import validate_native_replay_inventory
from tests import test_authored_episode as author_fixtures
from tests import test_teaching_focus as focus_fixtures
from creative_os.teaching_focus import resource_report
from ae_production.authored_episode import compile_clock


class AuthoredReplayPolicyTests(unittest.TestCase):
    def setUp(self):
        fixture=author_fixtures.AuthorBoundary(methodName='runTest');fixture.setUp()
        self.addCleanup(fixture.doCleanups);self.folder=fixture.folder
        self.author=fixture.author;self.bundles=fixture.bundles
        source_dir=tempfile.TemporaryDirectory();self.addCleanup(source_dir.cleanup)
        self.source=Path(source_dir.name)/'LATEST_USER_REQUEST.md'
        self.source.write_text('Synthetic captured request: 关键词亮起之后直接提取出来，然后'+USER_REPLAY_OMISSION_QUOTE,encoding='utf-8')

    def check(self):
        write(self.folder/'AV_AUTHOR.json',self.author)
        return checked_author(self.folder)

    def omit(self):
        ids={vid for scene in self.author['scenes'] if scene['kind']=='replay' for vid in scene['voice_ids']}
        self.author['scenes']=[scene for scene in self.author['scenes'] if scene['kind']!='replay']
        self.author['voices']=[voice for voice in self.author['voices'] if voice['id'] not in ids]

    def authorize(self):
        digest=sha256(self.source);path=str(self.source.resolve())
        self.author.setdefault('input_files',{})[path]=digest
        self.author['replay_policy']={'mode':'omitted_by_user','source':{'path':path,'sha256':digest},
                                      'quote':USER_REPLAY_OMISSION_QUOTE}

    def editorial(self,replay_scene):
        manifest={'authority':'internal_ai_editorial_only','human_approved':False,'source_files':{},
            'world_order':list(dict.fromkeys(scene['world'] for scene in self.author['scenes'])),
            'method_naming':'point_of_use','contract_version':'0.3.0',
            'teaching_selection':{world:{} for world in self.bundles},'replay_scene':replay_scene,
            'scenes':{scene['id']:{'world':scene['world'],'viewer_task':'Inspect the actual evidence.',
                'withheld_information':'Final verdict remains withheld.','consumed_decisions':{},
                'source_refs':deepcopy(scene['source_refs'])} for scene in self.author['scenes']}}
        path=self.folder/'EDITORIAL_MANIFEST.json';write(path,manifest)
        self.author['editorial']={'schema':'authored-editorial/v1','manifest':str(path),'sha256':sha256(path)}
        return path,manifest

    def native(self):
        scenes=deepcopy(self.author['scenes']);replays=[scene for scene in scenes if scene['kind']=='replay']
        p={'scenes':scenes,'candidate_events':[{'scene':s['id']} for s in scenes if s.get('event')]}
        audit={'replays':[{'scene':s['id'],'replay_of':s['replay_of'],'no_new_candidate_event':True} for s in replays],
               'extractions':[{'scene':s['id'],'replay':True} for s in replays]}
        layers=[{'name':'SOURCE_LIFT_first0','comment':json.dumps({'kind':'continuous_source_extraction'})}]
        for scene in replays:
            layers += [{'name':'REPLAY_CANDIDATE_'+scene['id']},
                       {'name':'SOURCE_LIFT_'+scene['id'],'comment':json.dumps({'kind':'replay_of_reviewed_comparison'})}]
        return p,audit,layers

    def test_legacy_default_remains_one_replay_and_editorial_exact_id(self):
        self.check();self.editorial('replay');self.check()
        self.assertEqual(validate_replay_policy(self.author)['expected_replays'],1)
        p,audit,layers=self.native()
        self.assertEqual(validate_native_replay_inventory(self.author,p,audit,layers)['replays'],1)

    def test_external_user_request_allows_zero_without_changing_public_authority(self):
        self.omit();self.authorize();self.check()
        result=validate_replay_policy(self.author,self.folder)
        self.assertEqual(result['expected_replays'],0)
        self.assertEqual(result['scope'],'replay_omission_only')
        self.assertFalse(result['human_approved']);self.assertFalse(result['public_render_ready'])
        self.assertFalse(self.author['public_render_ready'])
        p,audit,layers=self.native()
        self.assertEqual(validate_native_replay_inventory(self.author,p,audit,layers)['replays'],0)

    def test_missing_opt_in_cannot_remove_replay(self):
        self.omit()
        with self.assertRaisesRegex(ValueError,'one authored focused replay'):self.check()

    def test_legacy_default_still_rejects_two_replays(self):
        scene=deepcopy(next(s for s in self.author['scenes'] if s['kind']=='replay'))
        scene.update(id='second_replay',voice_ids=['second_replay'])
        self.author['scenes'].append(scene);self.author['voices'].append({'id':'second_replay','text':'Synthetic recall.'})
        with self.assertRaisesRegex(ValueError,'one authored focused replay'):self.check()

    def test_explicit_omission_cannot_leave_the_replay_in_place(self):
        self.authorize()
        with self.assertRaisesRegex(ValueError,'zero replay'):self.check()

    def test_agent_label_unknown_mode_or_approval_fields_are_not_authorization(self):
        self.omit();self.authorize();original=deepcopy(self.author['replay_policy'])
        for policy in ('omitted_by_user',{**original,'mode':'omitted_by_ai'},
                       {**original,'human_approved':True}):
            self.author['replay_policy']=policy
            with self.subTest(policy=policy),self.assertRaisesRegex(ValueError,'bound user replay omission'):
                self.check()

    def test_missing_input_binding_wrong_digest_and_relative_path_are_rejected(self):
        self.omit();self.authorize();self.author['input_files'].clear()
        with self.assertRaisesRegex(ValueError,'binding'):self.check()
        self.authorize();self.author['replay_policy']['source']['sha256']='0'*64
        with self.assertRaisesRegex(ValueError,'binding'):self.check()
        self.authorize();self.author['replay_policy']['source']['path']='LATEST_USER_REQUEST.md'
        with self.assertRaisesRegex(ValueError,'absolute external'):self.check()

    def test_request_file_is_rechecked_after_a_successful_author_validation(self):
        self.omit();self.authorize();self.check();self.source.write_text('Changed captured request.',encoding='utf-8')
        with self.assertRaisesRegex(ValueError,'Bound input changed'):self.check()

    def test_even_rebound_source_must_contain_the_exact_user_omission_instruction(self):
        self.omit();self.source.write_text('Synthetic request: keep the existing replay.',encoding='utf-8');self.authorize()
        with self.assertRaisesRegex(ValueError,'exact current user instruction'):self.check()
        self.source.write_text(USER_REPLAY_OMISSION_QUOTE,encoding='utf-8');self.authorize()
        self.author['replay_policy']['quote']='The agent decided to remove the replay.'
        with self.assertRaisesRegex(ValueError,'bound user replay omission'):self.check()

    def test_production_artifacts_cannot_supply_their_own_omission_permission(self):
        self.omit();self.source=self.folder/'USER_REQUEST.md'
        self.source.write_text(USER_REPLAY_OMISSION_QUOTE,encoding='utf-8');self.authorize()
        with self.assertRaisesRegex(ValueError,'own production artifacts'):self.check()

    def test_omission_does_not_bypass_missing_candidate_checks_or_final_closure(self):
        self.omit();self.authorize();self.author['scenes'][1].pop('event')
        with self.assertRaisesRegex(ValueError,'complete candidate checks'):self.check()

    def test_omission_still_requires_a_final_answer_for_every_question(self):
        self.omit();self.authorize()
        removed=next(s for s in self.author['scenes'] if s['world']=='second' and s['kind']=='answer')
        self.author['scenes'].remove(removed)
        self.author['voices']=[v for v in self.author['voices'] if v['id'] not in removed['voice_ids']]
        with self.assertRaisesRegex(ValueError,'close each question'):self.check()

    def test_editorial_requires_explicit_null_for_a_valid_zero_replay_selection(self):
        self.omit();self.authorize();path,manifest=self.editorial(None);self.check()
        self.assertIsNone(validate_editorial(self.author,self.bundles)['replay_scene'])
        for value in ('replay','MISSING'):
            if value=='MISSING':manifest.pop('replay_scene',None)
            else:manifest['replay_scene']=value
            write(path,manifest);self.author['editorial']['sha256']=sha256(path)
            with self.subTest(value=value),self.assertRaisesRegex(ValueError,'actual local replay'):
                validate_editorial(self.author,self.bundles)

    def test_editorial_null_does_not_authorize_an_unbound_omission(self):
        self.omit();self.editorial(None)
        with self.assertRaisesRegex(ValueError,'one authored focused replay'):
            validate_editorial(self.author,self.bundles)

    def test_native_zero_replay_rejects_stale_build_candidate_group_and_extraction(self):
        self.omit();self.authorize();p,audit,layers=self.native()
        variants=[]
        bad=deepcopy(audit);bad['replays']=[{'scene':'ghost','replay_of':'first0','no_new_candidate_event':True}]
        variants.append((bad,layers))
        variants.append((audit,layers+[{'name':'REPLAY_CANDIDATE_ghost'}]))
        variants.append((audit,layers+[{'name':'SOURCE_LIFT_ghost','comment':json.dumps({'kind':'replay_of_reviewed_comparison'})}]))
        bad=deepcopy(audit);bad['extractions']=[{'scene':'ghost','replay':True}];variants.append((bad,layers))
        for build,actual_layers in variants:
            with self.subTest(build=build,layers=actual_layers),self.assertRaisesRegex(ValueError,'inventory|layers|groups'):
                validate_native_replay_inventory(self.author,p,build,actual_layers)

    def test_native_replay_plan_cannot_rebind_the_author_selection_or_repeat_a_decision(self):
        p,audit,layers=self.native();p['scenes']=[s for s in p['scenes'] if s['kind']!='replay']
        with self.assertRaisesRegex(ValueError,'validated author choice'):
            validate_native_replay_inventory(self.author,p,audit,layers)
        p,audit,layers=self.native();p['candidate_events'].append({'scene':'replay'})
        with self.assertRaisesRegex(ValueError,'repeated a candidate decision'):
            validate_native_replay_inventory(self.author,p,audit,layers)

    def test_native_legacy_replay_needs_actual_layers_and_exact_no_new_event_flag(self):
        p,audit,layers=self.native();layers=[layer for layer in layers if not layer['name'].startswith('REPLAY_CANDIDATE_')]
        with self.assertRaisesRegex(ValueError,'candidate layers'):
            validate_native_replay_inventory(self.author,p,audit,layers)
        p,audit,layers=self.native();audit['replays'][0]['no_new_candidate_event']=1
        with self.assertRaisesRegex(ValueError,'native replay inventory'):
            validate_native_replay_inventory(self.author,p,audit,layers)

    def focus_clock_below_share_target(self):
        a,b,clips,alignment=focus_fixtures.fixture()
        passage=b['w']['source_snapshot']['passage']
        # Compile a genuine long necessary reading instead of falsifying the
        # measured clock or padding a scene to manufacture a percentage.
        a['scenes'][0]['reading_path']=[{'start':0,'end':len(passage),'quote':passage,
            'phrase':'','mode':'scope','move_seconds':1,'read_seconds':80}]
        self.author=a
        return compile_clock(a,clips,alignment)

    def test_user_omission_reports_real_missed_share_without_retiming_or_adding_replay(self):
        p=self.focus_clock_below_share_target()
        with self.assertRaisesRegex(ValueError,'most comparison'):resource_report(self.author,p)
        self.authorize();before=deepcopy(p);report=resource_report(self.author,p)
        row=report['questions'][0]
        self.assertLess(row['critical_attention_share'],.5)
        self.assertEqual(row['critical_attention_share'],row['seconds']['focus']/sum(row['seconds'].values()))
        self.assertFalse(row['target_met']);self.assertTrue(row['user_authorized_replay_omission'])
        self.assertFalse(report['user_authorized_replay_omission']['target_met'])
        self.assertEqual(report['user_authorized_replay_omission']['source_sha256'],sha256(self.source))
        self.assertEqual(p,before)
        self.assertEqual(p['scenes'][0]['reading_events'][0]['read_seconds'],80)
        self.assertFalse(any(s['kind']=='replay' for s in self.author['scenes']))
        self.assertEqual(row['verified_options'],['A','B','C','D'])

    def test_resource_share_exception_still_rechecks_source_and_real_motion_consumption(self):
        p=self.focus_clock_below_share_target();self.authorize()
        p['scenes'][0]['motion_treatment']='critical_comparison'
        with self.assertRaisesRegex(ValueError,'bypassed'):resource_report(self.author,p)
        p=self.focus_clock_below_share_target();self.authorize()
        self.source.write_text('Changed source.',encoding='utf-8')
        with self.assertRaisesRegex(ValueError,'binding changed'):resource_report(self.author,p)


if __name__=='__main__':unittest.main()
