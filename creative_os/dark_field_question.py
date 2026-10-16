"""Integrate the accepted field/lift grammar into one voiced 70-second review."""
import argparse
from copy import deepcopy
import json
from pathlib import Path

from .continuous_question import prepare
from .episode_build import ROOT
from video_contracts import read, write, sha
from ae_production.candidate_motion import audit_candidate_events


VOICE_STARTS = dict(A01=0, A03=416, A04=486, A05=555, A02=645, A06=747)
LIFTS = [(432, 474), (492, 540), (564, 612), (654, 702)]


def integrate(baseline, current):
    original = deepcopy(baseline)
    original.pop('proof', None)
    if original != current:
        raise ValueError('Accepted proof differs from current frozen inputs/status or style')
    plan = deepcopy(current)
    previous = {v['id']: [v['start_frame'], v['end_frame']] for v in plan['voices']}
    if set(previous) != set(VOICE_STARTS):
        raise ValueError('Expected the six existing exact voice clips')
    for v in plan['voices']:
        duration = v['end_frame'] - v['start_frame']
        v['start_frame'] = VOICE_STARTS[v['id']]
        v['end_frame'] = v['start_frame'] + duration
    plan['voices'].sort(key=lambda v: v['start_frame'])
    for a, b in zip(plan['voices'], plan['voices'][1:]):
        if a['end_frame'] > b['start_frame']:
            raise ValueError('Voice overlap; never truncate or stretch')
    slots = {v['id']: v for v in plan['voices']}
    for key, (start, end) in zip(('A03', 'A04', 'A05', 'A02'), LIFTS):
        if not slots[key]['start_frame'] <= start < end <= slots[key]['end_frame']:
            raise ValueError('Lift must complete within its actual voice slot')
    if slots['A06']['end_frame'] > 864:
        raise ValueError('Judgment voice must finish before restoration')
    plan['candidate_events'][0].update(compare_start=30, decision_start=35.25,
        decision_end=35.25+10/24, confirmation_start=35.75)
    # The existing audited action is unchanged; its presentation is rescheduled.
    plan['replay'].update(decision_start=50+(35.25-30)*10/6,
        confirmation_start=50+(35.75-30)*10/6, changes_candidate_state=False)
    plan['integration'] = dict(version='0.1', accepted_proof_sha=sha(baseline),
        timing_policy='same_wav_new_placements', previous_voice_windows=previous,
        new_voice_windows={v['id']: [v['start_frame'], v['end_frame']] for v in plan['voices']},
        lifts=[dict(voice_id=k, start_frame=s, end_frame=e, return_at=r)
               for k, (s, e), r in zip(('A03','A04','A05','A02'), LIFTS, (37,40,43,46))],
        field_frames=12, review_resolution=[1920,1080], master_render_allowed=False,
        replay=dict(source_start=30, source_end=36, start=50, end=60, visual_only=True),
        audio=dict(music=False, sfx=False, time_stretch=False, gain_change=False),
        captions=dict(font='NotoSansSC-Medium', size=36, text='#F2F0EA',
                      background='#20211F', background_opacity=60, baseline=970))
    return plan


def main():
    cli=argparse.ArgumentParser(description=__doc__)
    for key in ('request','direction','accepted','output'):cli.add_argument(key,type=Path)
    a=cli.parse_args()
    request=read(a.request);direction=read(a.direction)
    plan=integrate(read(a.accepted/'PLAN.json'),prepare(request,direction))
    bundle=read(request['sources'][direction['source']]['bundle'])
    plan['candidate_audit']=audit_candidate_events(plan['candidate_events'],{bundle['asset_id']:bundle})
    out=a.output.resolve();out.mkdir(parents=True,exist_ok=False)
    write(out/'PLAN.json',plan)
    source='\n'.join((ROOT/p).read_text(encoding='utf-8') for p in
        ('ae/lib/grammar.jsx','ae/lib/dark-field.jsx','ae/templates/dark-field-question.jsx'))
    (out/'build.jsx').write_text('var DQ_INPUT='+json.dumps(dict(plan=plan,output=out.as_posix()),ensure_ascii=True)+';\n'+source,encoding='utf-8')
    template=(ROOT/'ae/templates/shot-grammar-render.jsx').read_text(encoding='utf-8')
    (out/'render.jsx').write_text('var SHOT_PREVIEW_OUTPUT='+json.dumps(out.as_posix())+';\n'+template,encoding='utf-8')
    print(json.dumps(dict(output=str(out),voice_windows=plan['integration']['new_voice_windows'])))


if __name__=='__main__':main()
