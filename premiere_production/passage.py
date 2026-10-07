"""Internal long-form export, separate from the unchanged short Hero contract."""
from pathlib import Path
from video_contracts import read,write,sha
from creative_os.hero import file_sha
from creative_os.passage_video import validate_plan


def check_sequence(sequence,settings,expected_id,duration):
    if (sequence['id']!=expected_id or sequence['pagination']['truncated']
            or abs(sequence['end']-duration)>1/48):
        raise ValueError('Unexpected or incomplete active sequence')
    if (settings['id']!=expected_id or settings['frameSizeHorizontal']!=1920
            or settings['frameSizeVertical']!=1080 or settings['timebase']!='10584000000'
            or settings['audioSampleRateHz']!=48000 or settings['audioChannelCount']!=2):
        raise ValueError('Long-form output profile changed')
    result=[]
    for kind in ('videoTracks','audioTracks'):
        clips=[clip for track in sequence[kind] for clip in track['clips']]
        if len(clips)!=1:raise ValueError('Long-form assembly needs exactly one verified clip per medium')
        c=clips[0]
        if c['start']!=0 or abs(c['duration']-duration)>1/48:
            raise ValueError('Media truncated or shifted')
        result.append(c)
    return result


def export_internal(client,request):
    plan=read(request['plan']);bundle=read(request['bundle'])
    validate_plan(plan,bundle,read(request['status']))
    assembly=read(request['assembly']);mix=read(request['mix'])
    duration=plan['canvas']['duration'];sequence_plan=None
    if request.get('sequence_plan'):
        from creative_os.passage_sequence import validate_sequence
        sequence_plan=read(request['sequence_plan']);validate_sequence(sequence_plan,plan,bundle,read(request['status']))
        duration=sequence_plan['canvas']['duration']
        if assembly.get('sequence_sha')!=sequence_plan['sequence_sha'] or mix.get('sequence_sha')!=sequence_plan['sequence_sha']:
            raise ValueError('Original-first media no longer match its presentation sequence')
    elif assembly.get('sequence_sha') or mix.get('sequence_sha'):
        raise ValueError('Original-first media require their sequence plan')
    if (assembly['plan_sha']!=plan['plan_sha'] or mix['plan_sha']!=plan['plan_sha']
            or assembly['voice_sha']!=mix['voice_sha']
            or file_sha(assembly['visual'])!=assembly['visual_sha']
            or file_sha(mix['mix'])!=mix['mix_sha']):
        raise ValueError('Final media no longer match the frozen plan')
    project=client.call('get_project_info')
    if Path(project['path']).resolve()!=Path(request['project']).resolve():
        raise ValueError('Active Premiere project changed')
    sequence=client.call('get_active_sequence');settings=client.call('get_sequence_settings')
    clips=check_sequence(sequence,settings,request['sequence_id'],duration)
    if [c['name'] for c in clips]!=[Path(assembly['visual']).name,Path(mix['mix']).name]:
        raise ValueError('Unexpected active media')
    for clip in clips:
        properties=client.call('get_clip_properties',{'node_id':clip['nodeId']})
        if (properties['inPoint']!=0 or properties['isSpeedReversed']
                or abs(properties['outPoint']-duration)>1/48):
            raise ValueError('Clip source range changed')
    output=Path(request['output']).resolve()
    if output.exists():raise ValueError('Preserve prior delivery')
    output.parent.mkdir(parents=True,exist_ok=True)
    preflight={'plan_sha':plan['plan_sha'],'project_sha':file_sha(request['project']),
        'sequence_sha':sequence_plan['sequence_sha'] if sequence_plan else None,
        'sequence':sequence,'settings':settings,'visual_sha':assembly['visual_sha'],'mix_sha':mix['mix_sha'],
        'preset_sha':file_sha(request['preset']),'public_render_ready':False}
    write(output.with_suffix('.preflight.json'),preflight)
    # No retry on timeout: inspect host and output before any further mutation.
    validate_plan(plan,bundle,read(request['status']))
    result=client.call('export_sequence',{'output_path':str(output),'preset_path':request['preset'],
        'range':'entire','overwrite':False,'timeout_minutes':15},timeout=960)
    validate_plan(plan,bundle,read(request['status']))
    receipt={'output':str(output),'sha256':file_sha(output),'native_export':result,
        'preflight_sha':sha(preflight),'public_render_ready':False,
        'teaching_release':'HOLD','source_display_release':'HOLD','editorial_release':'HOLD'}
    write(output.with_suffix('.receipt.json'),receipt);return receipt
