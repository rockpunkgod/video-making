"""Synthetic source-only P3 contract tests; no real teaching facts."""
from copy import deepcopy
import unittest

from video_contracts import sha
from creative_os.shot_script import compile_shot_script
from creative_os.camera_plan import camera_plan
from creative_os.typeset import digest
from creative_os.semantic_text_layout import focus_windows


def fixture():
    style = dict(coordinates=dict(fps=24), layout=dict(focus_max_lines=9),
                 motion=dict(actions={k:dict(frames=n) for k,n in
                    [('locate',10),('lift',14),('compare',12),('eliminate',10),('return',16)]},
                    speed_tiers={k:dict(typical_duration_frames=n) for k,n in [('drift',36),('snap',6),('hold',24)]}),
                 depth=dict(light_dark=dict(dim_transition_frames=12, shadow_opacity=.67)))
    bundle = dict(source_snapshot=dict(passage='Synthetic words.', options={},question_id='synthetic'))
    words = [dict(text='Synthetic', start=0,end=9,x=0,y=0,w=100,size=46,line=0),
             dict(text='words.', start=10,end=16,x=110,y=0,w=70,size=46,line=0)]
    layout = dict(schema='typeset-plan/v1',source_sha256=digest(b'Synthetic words.'),style_sha256=sha(style),
                  words=words,focus_windows=focus_windows(words))
    script = dict(schema='shot-script/v1',fps=24,duration=8,objects=[dict(id='passage',text='Synthetic words.',
        layout_id='layout',source_ref=dict(asset_id='asset',pointer='/source_snapshot/passage',sha=sha('Synthetic words.')))],
        targets=[dict(id='word',object_id='passage',range=[0,9],text='Synthetic')],
        actions=[dict(id='dim',action='dim_world',at=1),dict(id='lift',action='lift',at=1,targets=['word']),
                 dict(id='compare',action='compare',at=2,targets=['word']),
                 dict(id='return',action='return',at=3,targets=['word']),dict(id='bright',action='brighten_world',at=4)],
        focus_cues=[dict(at=0,object_id='passage',window_index=0,state='read'),
                    dict(at=2,object_id='passage',window_index=0,state='hit')])
    return script, {'asset':bundle}, {'layout':layout}, style


class ShotTests(unittest.TestCase):
    def test_repeatable_and_inputs_unchanged(self):
        args=fixture(); before=deepcopy(args)
        one=compile_shot_script(*args)
        self.assertEqual(one,compile_shot_script(*args)); self.assertEqual(args,before)
        self.assertFalse(one['public_render_ready']); self.assertEqual(one['native_render_status'],'NOT_RUN')

    def test_frozen_edit_rejected(self):
        args=fixture(); args[1]['asset']['source_snapshot']['passage']='Changed'
        with self.assertRaises(ValueError):compile_shot_script(*args)

    def test_word_omission_rejected(self):
        args=fixture(); args[2]['layout']['words'].pop()
        with self.assertRaises(ValueError):compile_shot_script(*args)

    def test_wrong_slice_rejected(self):
        args=fixture(); args[0]['targets'][0]['text']='New claim'
        with self.assertRaises(ValueError):compile_shot_script(*args)

    def test_style_change_requires_new_layout(self):
        args=fixture(); args[3]['depth']['light_dark']['shadow_opacity']=.2
        with self.assertRaises(ValueError):compile_shot_script(*args)

    def test_invalid_transitions(self):
        for replacement in ('dim_world','brighten_world'):
            args=fixture(); args[0]['actions'][1]=dict(id='bad',action=replacement,at=1.2)
            with self.assertRaises(ValueError):compile_shot_script(*args)

    def test_return_must_finish_before_brighten(self):
        args=fixture(); args[0]['actions'][-1]['at']=3.2
        with self.assertRaises(ValueError):compile_shot_script(*args)

    def test_no_overlapping_target_actions(self):
        args=fixture(); args[0]['actions'][2]['at']=1.2
        with self.assertRaises(ValueError):compile_shot_script(*args)

    def test_time_bounds(self):
        for at in (-1, float('nan'), True, 9):
            args=fixture(); args[0]['actions'][0]['at']=at
            with self.assertRaises(ValueError):compile_shot_script(*args)

    def test_unbound_elimination_rejected(self):
        args=fixture(); args[0]['actions'][2].update(action='eliminate',candidate_event_index=0)
        with self.assertRaises(ValueError):compile_shot_script(*args)

    def test_whole_option_elimination_projects_existing_action(self):
        s,b,l,t=fixture(); bundle=b['asset']
        bundle['source_snapshot']['options']={'A':'Synthetic words.','B':'Other'}
        action=dict(execution_id='remove-a',output=dict(kind='candidate_decision',candidate='A',effect='eliminate'))
        bundle['source_snapshot']['action_executions']=[action]
        s['objects'][0]['source_ref']['pointer']='/source_snapshot/options/A'
        s['targets'][0].update(range=[0,16],text='Synthetic words.')
        s['candidate_events']=[dict(scene_id='scene',question_id='synthetic',candidate='A',effect='eliminate',
            compare_start=1,decision_start=2,decision_end=2+10/24,confirmation_start=3,
            source_refs=[dict(asset_id='asset',pointer='/source_snapshot/action_executions/0',sha=sha(action))])]
        s['actions'][2].update(action='eliminate',candidate_event_index=0)
        result=compile_shot_script(s,b,l,t)
        self.assertEqual(result['audit']['candidate_audit']['events'][0]['after'],['B'])
        s['objects'][0]['source_ref']['pointer']='/source_snapshot/passage'
        with self.assertRaises(ValueError):compile_shot_script(s,b,l,t)

    def test_camera_carry_and_hold(self):
        s,b,l,t=fixture(); plan=camera_plan(s,l,t)
        self.assertTrue(plan['cues'][0]['carry_speed']); self.assertFalse(plan['cues'][1]['carry_speed'])
        self.assertFalse(plan['native_speed_curve_verified'])

    def test_camera_window_and_order(self):
        for patch in (dict(window_index=-1),dict(at=0),dict(state='dramatic')):
            s,b,l,t=fixture(); s['focus_cues'][1].update(patch)
            with self.assertRaises(ValueError):camera_plan(s,l,t)


if __name__ == '__main__':
    unittest.main()
