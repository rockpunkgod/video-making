"""Actual local excerpt mappings and picture/native-editorial handoff receipts."""
import argparse
import json
import math
from pathlib import Path
import shutil
import subprocess

import numpy as np
from PIL import Image

from produce import local, read, write, file_sha, sha
from premiere import inputs
from premiere_production.lossless_handoff import assemble as lossless_handoff, rec709_binding


def timecode(frame):
    seconds,part=divmod(frame,24);minutes,seconds=divmod(seconds,60);hours,minutes=divmod(minutes,60)
    return f'{hours:02d}:{minutes:02d}:{seconds:02d}:{part:02d}'


def color_audit(folder,name,picture,native,frames):
    directory=folder/'color-audits'/name;directory.mkdir(parents=True,exist_ok=True)
    target=directory/'COLOR_COMPARISON.json'
    binding={'picture_sha':file_sha(picture),'native_export_sha':file_sha(native)}
    if target.exists():
        prior=read(target)
        if prior['binding']!=binding:raise ValueError('Existing actual frame comparison binds other media')
        return prior
    points=(48,963,frames-48) if 'CONTEXT' in name else (72,432,frames-48)
    rows=[]
    for frame in points:
        arrays=[];paths=[]
        for kind,path in [('AE_PICTURE',picture),('PR_NATIVE',native)]:
            png=directory/f'{kind}_{frame:04d}.png'
            if png.exists():raise FileExistsError('Inspect existing QA captures before repeating extraction')
            subprocess.run(['ffmpeg','-v','error','-n','-ss',str(frame/24),'-i',str(path),
                '-frames:v','1',str(png)],check=True)
            with Image.open(png) as image:arrays.append(np.asarray(image.convert('RGB'),dtype=np.float32))
            paths.append(str(png))
        difference=arrays[0]-arrays[1]
        reference=np.median(arrays[0][100:200,100:200],axis=(0,1))
        observed=np.median(arrays[1][100:200,100:200],axis=(0,1))
        mse=float(np.mean(difference**2))
        row={'frame':frame,'timecode':timecode(frame),'captures':paths,
            'ae_background_rgb':reference.tolist(),'pr_background_rgb':observed.tolist(),
            'background_max_error':float(np.max(np.abs(reference-observed))),
            'whole_frame_mae':float(np.mean(np.abs(difference))),
            'psnr_db':round(10*math.log10(255**2/mse),4) if mse else None}
        row['within_compression_tolerance']=row['background_max_error']<=2 and row['whole_frame_mae']<=3
        rows.append(row)
    try:
        metadata=rec709_binding(native);metadata_status='PASS_EXPLICIT_REC709'
    except ValueError:
        metadata=None;metadata_status='MISSING_OR_DIFFERENT_NATIVE_COLOR_TAGS'
    result={'binding':binding,'rows':rows,'native_color_metadata':metadata,'metadata_status':metadata_status,
        'native_picture_accepted':all(r['within_compression_tolerance'] for r in rows) and metadata is not None,
        'scope':'Actual decoded frame/color comparison; not semantic or aesthetic approval',
        'human_visual_review':'PENDING','public_render_ready':False}
    write(target,result);return result


def validate_export_binding(name,receipt,audit,production,plan,workspace):
    variant=plan['variants'][name];sequence=workspace['sequences'][name]
    if (receipt['production_sha']!=production['production_sha']
            or audit['production_sha']!=production['production_sha']
            or receipt['av_plan_sha']!=plan['av_plan_sha'] or audit['av_plan_sha']!=plan['av_plan_sha']
            or receipt['sequence_id']!=sequence['id'] or audit['sequence']['id']!=sequence['id']
            or audit['sequence']['name']!=name or receipt['frames']!=variant['frames']
            or receipt['source_frames']!=variant['source_frames']
            or audit['status']!='PASS_NATIVE_TIMELINE' or sha(audit)!=receipt['native_audit_sha']):
        raise ValueError('Actual native export/timeline binding changed')


def picture_with_complete_color_metadata(folder,name,picture,frames):
    """Repair only missing H.264 VUI fields; retain every decoded native pixel."""
    try:
        rec709_binding(picture)
        return picture,None
    except ValueError:
        pass
    directory=folder/'color-audits'/name
    target=directory/'AE_PICTURE_REC709.mp4';receipt_path=directory/'PICTURE_METADATA_CORRECTION.json'
    if receipt_path.exists():
        receipt=read(receipt_path)
        if receipt['source_sha']!=file_sha(picture) or receipt['output_sha']!=file_sha(target):
            raise ValueError('Previous picture metadata correction binds different bytes')
        rec709_binding(target)
        return str(target),receipt
    if target.exists():raise FileExistsError('Inspect unfinished metadata correction before continuing')
    stream=json.loads(subprocess.check_output(['ffprobe','-v','error','-select_streams','v:0',
        '-show_streams','-of','json',str(picture)]))['streams'][0]
    if (stream['codec_name']!='h264' or stream.get('color_range')!='tv' or stream.get('color_space')!='bt709'
            or stream.get('color_primaries') not in (None,'unknown','bt709')
            or stream.get('color_transfer') not in (None,'unknown','bt709')):
        raise ValueError('Only missing metadata on the known limited Rec709 picture may be completed')
    source_sha=file_sha(picture)
    command=['ffmpeg','-v','error','-n','-i',str(picture),'-map','0:v:0','-c','copy',
        '-bsf:v','h264_metadata=video_full_range_flag=0:colour_primaries=1:transfer_characteristics=1:matrix_coefficients=1',
        '-color_range','tv','-colorspace','bt709','-color_primaries','bt709','-color_trc','bt709',
        '-movflags','+write_colr',str(target)]
    subprocess.run(command,check=True)
    checks=[]
    for path in (picture,target):
        result=subprocess.check_output(['ffmpeg','-v','error','-xerror','-i',str(path),'-map','0:v:0',
            '-f','framemd5','pipe:1'],text=True)
        rows=[line for line in result.splitlines() if line and not line.startswith('#')]
        if len(rows)!=frames:raise ValueError('Metadata correction changed complete frame coverage')
        checks.append(sha(rows))
    if checks[0]!=checks[1] or file_sha(picture)!=source_sha:
        raise ValueError('Metadata-only correction changed native pixels, timing or source bytes')
    receipt={'kind':'MISSING_VUI_METADATA_COMPLETED_NO_REENCODE','source':str(picture),'source_sha':source_sha,
        'output':str(target),'output_sha':file_sha(target),'frames':frames,'decoded_frame_md5_rows_sha':checks[0],
        'decoded_pixels_and_timing':'IDENTICAL_ALL_FRAMES','color':rec709_binding(target),'command':command,
        'source_preserved':True,'public_render_ready':False}
    write(receipt_path,receipt)
    return str(target),receipt


def deliver(folder,names=None):
    production,plan,pictures,workspace=inputs(folder,True)
    exports=read(folder/'EXPORT_INDEX.json')
    if exports['production_sha']!=production['production_sha']:raise ValueError('Native export revision changed')
    names=list(plan['variants']) if names is None else names
    if not names or not set(names)<=exports['exports'].keys():raise ValueError('Explicit completed native exports required')
    directory=folder/'delivery';directory.mkdir(exist_ok=True)
    index_path=folder/'DELIVERY_INDEX.json'
    index=read(index_path) if index_path.exists() else {'production_sha':production['production_sha'],'deliveries':{}}
    if index['production_sha']!=production['production_sha'] or set(names)&index['deliveries'].keys():
        raise ValueError('Never replace existing delivered variants')
    for name in names:
        receipt=exports['exports'][name];variant=plan['variants'][name];picture=pictures['pictures'][name]
        audit=read(folder/'premiere-audits'/(name+'.json'))
        validate_export_binding(name,receipt,audit,production,plan,workspace)
        if file_sha(receipt['output'])!=receipt['output_sha']:
            raise ValueError('Actual native export bytes changed')
        color=color_audit(folder,name,picture['path'],receipt['output'],variant['frames'])
        target=directory/(name+'_4K24.mp4')
        if target.exists():raise FileExistsError('Preserve delivered media')
        if color['native_picture_accepted']:
            shutil.copyfile(receipt['output'],target)
            if file_sha(target)!=receipt['output_sha']:raise ValueError('Native delivery copy differs')
            handoff={'kind':'NATIVE_PR_EXPORT','output':str(target),'output_sha':file_sha(target),
                'full_decode':receipt['encoded']['status']}
        else:
            final_picture,metadata_correction=picture_with_complete_color_metadata(folder,name,picture['path'],variant['frames'])
            handoff=lossless_handoff(final_picture,receipt['output'],target,variant['frames'])
            handoff['kind']='LOSSLESS_AE_PICTURE_PLUS_NATIVE_PR_AUDIO'
            if metadata_correction:handoff['picture_metadata_correction']=metadata_correction
            handoff['native_pr_picture_limitation']=color['metadata_status'] if all(r['within_compression_tolerance'] for r in color['rows']) else 'OBSERVED_NATIVE_PR_COLOR_DIFFERENCE'
        start,end=variant['source_frames']
        segments=[]
        if name.startswith('NEW'):
            cut=production['insert']['original_frame'];extra=production['insert']['frames']
            for lo,hi,original,kind in [(start,min(end,cut),start,'CLOCK_CORRESPONDENCE'),
                    (max(start,cut),min(end,cut+extra),None,'INSERTED_OBSERVATION_TIME'),
                    (max(start,cut+extra),end,max(start,cut+extra)-extra,'CLOCK_CORRESPONDENCE')]:
                if hi>lo:segments.append({'output_frames':[lo-start,hi-start],
                    'original_episode_frames':[original,original+hi-lo] if original is not None else None,'kind':kind})
        else:segments=[{'output_frames':[0,variant['frames']],'original_episode_frames':[start,end],
            'kind':'EXACT_OLD_TIMING_WITH_EXPLANATORY_CAPTIONS_OMITTED' if name.endswith('_VISUAL') else 'EXACT_OLD_TIMING_INTERVAL'}]
        voices=[]
        for v in variant['voices']:
            actual=next(c for c in audit['source_items'] if c['name']==v['native_name'])
            encoded=next(c for c in receipt['encoded']['voice_presence']['voices'] if c['id']==v['id'])
            native_samples=[round(actual['startSeconds']*48000),round(actual['endSeconds']*48000)]
            voices.append({'id':v['id'],'path':v['path'],'sha256':v['sha256'],
                'native_clip_id':actual['nodeId'],'native_project_item_id':actual['source']['nodeId'],
                'source_sample_range':[0,round(v['duration']*48000)],
                'native_timeline_sample_range':native_samples,
                'encoded_correlated_sample_window':[s+encoded['codec_offset_samples'] for s in native_samples],
                'encoded_voice_check':encoded,
                'actual_start_seconds':actual['startSeconds'],'actual_end_seconds':actual['endSeconds'],
                'native_speed':actual['speed'],'source_complete':True})
        mapping={'variant':name,'mapping_revision':3,'interval_convention':'ZERO_BASED_END_EXCLUSIVE',
            'actual_canvas':[3840,2160,24],'actual_frames':variant['frames'],
            'actual_duration_seconds':variant['frames']/24,'output_frame_range':[0,variant['frames']],
            'output_timecode_range':[timecode(0),timecode(variant['frames'])],
            'native_source_comp_id':read(folder/'NATIVE_IDENTITY.json')['source_comp_id'] if name.startswith('NEW') else production['baseline_comp_id'],
            'native_excerpt_comp_id':picture['comp_id'],'native_episode_frame_range':[start,end],
            'native_episode_timecode_range':[timecode(start),timecode(end)],
            'native_premiere_sequence_id':receipt['sequence_id'],'clock_segments':segments,
            'clock_mapping_does_not_assert_pixel_identity':True,
            'review_presentation_changes':['EXPLANATORY_CAPTIONS_MASKED_IN_NATIVE_AE','ALL_VO_OMITTED']
                if name.endswith('_VISUAL') else ['BOUNDED_REVIEWED_B06_MOTION_AND_TIMING'] if name.startswith('NEW') else [],
            'complete_voice_takes':voices,'captions':variant['captions'],'srt_path':variant['srt_path'],'srt_sha':variant['srt_sha'],
            'candidate_prefix':production['full_candidate_prefix_audit'],
            'audience_learning_loop_human_anchor':'PENDING','public_render_ready':False}
        write(directory/(name+'_ACTUAL_MAPPING.json'),mapping)
        item={'media':str(target),'media_sha':file_sha(target),'mapping':str(directory/(name+'_ACTUAL_MAPPING.json')),
            'mapping_sha':sha(mapping),'native_export_receipt_sha':sha(receipt),'color_audit_sha':sha(color),
            'native_pr_picture_sha':audit['picture_sha'],
            'delivery_video_parent_sha':file_sha(receipt['output'] if color['native_picture_accepted'] else final_picture),
            'handoff':handoff,'human_visual_review':'PENDING','human_listening_review':'PENDING','public_render_ready':False}
        index['deliveries'][name]=item
        index.update({'AE_project':production['project'],'PR_project':workspace['project'],
            'interval_convention':'ZERO_BASED_END_EXCLUSIVE',
            'scope':'SIX_BOUNDED_AB_EXCERPTS_ONLY','G3':'STOPPED_PENDING_HUMAN_VIEWING_AND_LISTENING'
                if len(index['deliveries'])==6 else 'G2_INCOMPLETE','public_render_ready':False})
        write(index_path,index)
        print({'delivered':name,'frames':variant['frames'],'handoff':handoff['kind']},flush=True)
    return {'deliveries':len(index['deliveries']),'G3':index['G3'],'public_render_ready':False}


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('folder');parser.add_argument('--variants',nargs='+')
    args=parser.parse_args();print(deliver(local(args.folder),args.variants))
