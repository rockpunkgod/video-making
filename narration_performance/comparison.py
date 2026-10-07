"""Local A/B evidence and listening artifacts; never select a human preference."""
from copy import deepcopy
import html
from pathlib import Path
import subprocess
import wave

from scripts.voice_delivery import sha256
from video_contracts import read, sha, write
from premiere_production.student_voice import preflight, inspect_rendered_voice
from .adapter import verify_realization
from .plan import load_context, validate_plan
from .review import review_template, risk_qa


def voice_only(plan, target):
    """Actual placements, unchanged PCM and silence; no gain or time stretch."""
    target=Path(target)
    if target.exists():
        raise FileExistsError('Preserve existing A/B listening audio')
    data=bytearray(round(plan['duration']*48000)*2)
    for voice in plan['voices']:
        with wave.open(voice['path'],'rb') as audio:
            if (audio.getframerate(),audio.getnchannels(),audio.getsampwidth())!=(48000,1,2):
                raise ValueError('A/B voice-only requires the already checked native PCM profile')
            pcm=audio.readframes(audio.getnframes())
        start=round(voice['start']*48000)*2
        if start+len(pcm)>len(data):
            raise ValueError('A/B listening cannot truncate speech')
        data[start:start+len(pcm)]=pcm
    with wave.open(str(target),'wb') as output:
        output.setframerate(48000); output.setnchannels(1); output.setsampwidth(2); output.writeframes(data)


def verify_picture_pixels(a,b,output):
    frames=[]
    for label,path in (('A',a),('B',b)):
        decoded=subprocess.run(['ffmpeg','-v','error','-i',str(path),'-f','null','-'],
            capture_output=True,encoding='utf-8',check=True)
        if decoded.stderr.strip():
            raise ValueError('A/B complete media decode reported errors')
        data=subprocess.check_output(['ffmpeg','-v','error','-i',str(path),'-map','0:v:0','-f','framemd5','-'])
        (Path(output)/(label+'.framemd5')).write_bytes(data)
        frames.append([r for r in data.decode().splitlines() if not r.startswith('#')])
    if not frames[0] or frames[0]!=frames[1]:
        raise ValueError('A/B picture pixels changed; voice variable is no longer isolated')
    return {'status':'PASS_identical_decoded_picture','frames':len(frames[0]),'decode_errors':0}


def create_comparison(request):
    context=read(request['performance_context']); copy,spec=load_context(context)
    performance=validate_plan(read(context['performance_plan']),copy,spec)
    raw,generation,realization,receipts=verify_realization(performance,context['raw_delivery'])
    baseline=read(request['baseline_index'])
    before=read(request['unchanged_inputs'])
    changed=[p for p,expected in before.items() if sha256(p)!=expected]
    if changed:
        raise ValueError('A/B changed frozen teaching input or original asset: '+changed[0])
    a_request=read(baseline['request']); b_request=read(request['production_request'])
    *_,a_plan=preflight(a_request); *_,b_plan=preflight(b_request)
    if a_plan['final_copy_sha']!=b_plan['final_copy_sha'] or a_plan['spec_sha']!=b_plan['spec_sha']:
        raise ValueError('A/B Copy or picture bindings differ')
    a_audit=read(request['baseline_native_audit'])
    b_audit=read(Path(b_request['video_output']).with_suffix('.receipt.json'))
    if (a_audit['music_keyframes']!=b_audit['music_keyframes']
            or a_audit['project_sha']!=baseline['project_sha']
            or b_audit['project_sha']!=sha256(b_request['project'])
            or b_audit['output_sha']!=sha256(b_request['video_output'])):
        raise ValueError('A/B native project or existing music envelope changed')
    for kind in ('preview','project','audition'):
        if sha256(baseline[kind])!=baseline[kind+'_sha']:
            raise ValueError('Baseline A changed after binding')
    output=Path(request['output']).resolve(); output.mkdir(parents=True,exist_ok=False)
    pixels=verify_picture_pixels(baseline['preview'],b_request['video_output'],output)
    a_wave=output/'A_VOICE_ONLY.wav'; b_wave=output/'B_VOICE_ONLY.wav'
    voice_only(a_plan,a_wave); voice_only(b_plan,b_wave)
    timing=read(b_request['performance_timing']); selection=read(b_request['performance_selection'])
    audit_clips=[]
    for selected,voice,timed in zip(selection['clips'],b_plan['voices'],timing['clips']):
        take=receipts[selected['take_id']]
        execution=deepcopy(take['engine_realization'])
        for name in ('pause_before_ms','pause_after_ms'):
            execution[name]={'status':'APPROXIMATED','control':'verified_native_Premiere_placement',
                'intent_ms':take['performance_intent'][name], 'actual_ms':timed[name+'_actual'],
                'window_lead_ms':timed['window_lead_ms'],
                'reason':'frame quantization and existing visual/protected silence take precedence'}
        audit_clips.append({'scene_id':voice['id'],'selected_take_id':selected['take_id'],
            'performance_intent':take['performance_intent'],'engine_realization':execution,
            'actual_speed_factor':take['inference_parameters']['speed_factor'],
            'actual_start':voice['start'],'actual_end':voice['end'],'audio_sha256':voice['sha256'],
            'source_take_audio_sha256':take['audio_sha256'],'take_receipt_sha':take['take_receipt_sha']})
    outputs={}
    for label,index,voice_plan,audio in [('A',baseline,a_plan,a_wave),('B',b_request,b_plan,b_wave)]:
        preview=index['preview'] if label=='A' else index['video_output']
        outputs[label]={'preview':preview,'preview_sha256':sha256(preview),
            'project':index['project'],'project_sha256':sha256(index['project']),
            'voice_only':str(audio),'voice_only_sha256':sha256(audio),'voice_plan_sha':voice_plan['voice_plan_sha']}
    result={'schema':'narration-performance-comparison/v1','version':'0.1.0',
        'binding':performance['binding'],'performance_sha':performance['performance_sha'],
        'baseline_profile':baseline['model_profile'],
        'profile_sha256':generation['profile_sha256'],'assets_sha256':generation['assets_sha256'],
        'performance_realization_sha':realization['realization_sha'],'timing_sha':timing['timing_sha'],
        'selection_sha':selection['selection_sha'],'outputs':outputs,'selected_clips':audit_clips,
        'picture_check':pixels,'music_envelope_unchanged':True,'protected_input_count':len(before),
        'protected_inputs_unchanged':True,'caption_timing':timing['caption_timing_scope'],
        'encoded_voice_check':{'A':inspect_rendered_voice(outputs['A']['preview'],a_plan),
                               'B':b_audit['encoded_voice_check']},
        'baseline_timeline_receipt_sha256':sha256(request['baseline_native_audit']),
        'performance_timeline_receipt_sha256':sha256(Path(b_request['video_output']).with_suffix('.receipt.json')),
        'listening_review':'PENDING','performance_version_status':'EXPERIMENT_NOT_FROZEN',
        'final_voice_accepted':False,'sample_delivery_allowed':False,'public_render_ready':False}
    result['comparison_sha']=sha(result)
    write(output/'comparison.json',result)
    write(output/'performance-review.json',review_template(result))
    write(output/'performance-risk.json',risk_qa(performance,timing))
    write(output/'final-performance-realization.json',{'performance_sha':performance['performance_sha'],
        'comparison_sha':result['comparison_sha'],'selected_clips':audit_clips,
        'listening_review':'PENDING','final_voice_accepted':False,'sample_delivery_allowed':False,'public_render_ready':False})
    question_html=''.join('<li>'+html.escape(q['question'])+'</li>' for q in review_template(result)['questions'])
    page='''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width">
<title>口播 A/B 试听</title><style>body{margin:40px auto;max-width:1180px;padding:0 24px;background:#f4f0e7;color:#243530;font:17px/1.65 system-ui,sans-serif}h1{font-weight:550}.grid{display:grid;grid-template-columns:1fr 1fr;gap:28px}video,audio{width:100%}h2{font-size:22px}p{max-width:900px}li{margin:8px 0}a{color:#496357}@media(max-width:850px){.grid{grid-template-columns:1fr}}</style>
<h1>口播 A/B 试听</h1><p>两版保留同一题目、文案、画面、钢琴和声音模型。B 只试小幅推理语速与认知停顿，语气、重音和确定感没有直接后端控制。</p><div class="grid">'''
    for label,title in [('A','现有最新试听'),('B','认知节奏实验')]:
        item=outputs[label]
        page+='<section><h2>'+label+' · '+title+'</h2><video controls preload="metadata" src="'+html.escape(Path(item['preview']).as_uri(),quote=True)+'"></video>'
        page+='<p>闭眼试听：原时间线，去掉钢琴，保留完整人声和停顿。</p><audio controls preload="metadata" src="'+label+'_VOICE_ONLY.wav"></audio></section>'
    page+='</div><p>请比较：更像聪明的人在旁边带着做题吗？没有明显偏好就停止增加功能。当前仍是内部实验，不记录为最终声音或公开放行。</p><ol>'+question_html+'</ol></html>'
    (output/'试听对照.html').write_text(page,encoding='utf-8')
    questions='\n'.join(str(i+1)+'. '+q['question']+' — PENDING' for i,q in enumerate(review_template(result)['questions']))
    (output/'HUMAN_LISTENING_REVIEW.md').write_text('# R02 A/B Human Listening Review\n\n'+questions+
        '\n\nPreference: PENDING\n\nNO_MELANCHOLIC_DRIFT: PENDING\n\nANTI_OVERACTING: PENDING\n\n'+
        'Comparison SHA: '+result['comparison_sha']+'\n\nfinal_voice_accepted=false / sample_delivery_allowed=false / public_render_ready=false\n',encoding='utf-8')
    return result
