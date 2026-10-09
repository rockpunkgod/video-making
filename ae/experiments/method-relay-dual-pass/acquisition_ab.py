"""Silent P0 comparisons from actual native AE TIFF ranges, without P2 assembly."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
import zipfile

import run as relay
from video_contracts import read, write


def verify_movie(path, frames, width=1920, height=1080):
    result=subprocess.run(['ffprobe','-v','error','-count_frames','-show_streams','-of','json',str(path)],
                          capture_output=True,text=True,check=True)
    streams=json.loads(result.stdout)['streams']
    if (len(streams)!=1 or streams[0]['codec_type']!='video'
            or int(streams[0]['nb_read_frames'])!=frames or streams[0]['r_frame_rate']!='24/1'
            or [streams[0]['width'],streams[0]['height']]!=[width,height]):
        raise ValueError('Silent comparison must preserve every directed native frame at real speed')
    subprocess.run(['ffmpeg','-v','error','-i',str(path),'-f','null','-'],check=True)
    return {'path':str(path),'sha256':relay.file_sha(path),'frames':frames,'fps':24,
            'width':width,'height':height,'duration':frames/24,'audio_streams':0}


def extract_native(archive,manifest,first,end,folder):
    """Only verified, explicitly numbered frames; never extract ZIP paths blindly."""
    folder.mkdir(exist_ok=False);names=[]
    for name in manifest:
        match=re.fullmatch(r'FRAME_(\d{5})\.tif',name)
        if not match:raise ValueError('Only flat native TIFF frame names are accepted')
        if first<=int(match[1])<end:names.append(name)
    names.sort()
    if names!=['FRAME_'+str(i).zfill(5)+'.tif' for i in range(first,end)]:
        raise ValueError('Missing exact native frames for the absolute-time comparison')
    with zipfile.ZipFile(archive) as z:
        for name in names:
            data=z.read(name)
            if hashlib.sha256(data).hexdigest()!=manifest[name]:raise ValueError('Native source frame hash mismatch')
            (folder/name).write_bytes(data)
    return names


def encode_frames(folder,first,count,target,width=1920,height=1080):
    # Bound TIFF decoding independently: default decoder parallelism can exhaust
    # memory on native 4K frames while Adobe retains its scene cache.
    subprocess.run(['ffmpeg','-v','error','-n','-threads','1','-filter_threads','1','-framerate','24','-start_number',str(first),
        '-i',str(folder/'FRAME_%05d.tif'),'-frames:v',str(count),'-an','-c:v','libx264',
        '-threads','4','-crf','16','-pix_fmt','yuv420p',str(target)],check=True)
    return verify_movie(target,count,width,height)


def clean_extracted(folder,names,output):
    # Original archives remain untouched; these are this run's verified copies.
    for name in names:
        path=(folder/name).resolve()
        if path.parent!=folder.resolve() or not path.is_relative_to(output):raise ValueError('Unsafe temporary frame path')
    for name in names:(folder/name).unlink()
    folder.rmdir()


def approved_baseline(baseline,accepted_pr,review_path):
    r=relay.current(baseline);receipt=read(baseline/'render-receipt.json')
    relay.validate_native(r,read(baseline/'native-audit.json'))
    review=read(review_path);proof=read(accepted_pr/'picture-preservation.json')
    movie=accepted_pr/'METHOD_RELAY_DUAL_PASS.mp4'
    if (review.get('reviewer')!='user' or review.get('visual_experience_review')!='USER_ACCEPTED_OVERALL_VISUAL_PREVIEW'
            or not review.get('exact_feedback') or review['video_sha256']!=relay.file_sha(movie)
            or proof['encoded_movie_sha']!=review['video_sha256']
            or proof['native_picture_sha']!=receipt['output_sha']
            or receipt['output_sha']!=relay.file_sha(receipt['output'])
            or receipt['project_sha']!=relay.file_sha(receipt['project'])
            or receipt['archive_sha']!=relay.file_sha(baseline/'NATIVE_TIFF_DUAL.zip')
            or receipt['frame_manifest_sha']!=relay.file_sha(baseline/'native-frame-shas.json')):
        raise ValueError('A must trace to the accepted old visual preview, not an unapproved newer movie')
    return {'request':r,'render':receipt,'human_feedback_sha':relay.file_sha(review_path),
            'accepted_movie_sha':review['video_sha256'],'picture_preservation_sha':relay.file_sha(accepted_pr/'picture-preservation.json'),
            'approval_scope':'overall_old_visual_preview_only_not_new_B_or_individual_V1_V6'}


def prepare(baseline,candidate,accepted_pr,review_path,output):
    baseline=relay.local(baseline);candidate=relay.local(candidate);accepted_pr=relay.local(accepted_pr)
    review_path=relay.local(review_path);output=relay.local(output)
    a=approved_baseline(baseline,accepted_pr,review_path);r=relay.current(candidate)
    relay.validate_native(r,read(candidate/'native-audit.json'))
    if (not r.get('native_acquisition_geometry') or r['fixture_sha']!=a['request']['fixture_sha']
            or r['trajectory_sha']!=a['request']['trajectory_sha']):
        raise ValueError('A and B must use the same supplied text and teaching-free synthetic trajectory')
    output.mkdir(parents=True,exist_ok=False);movies={};sources={}
    from PIL import Image, ImageDraw, ImageFont
    header=Image.new('RGB',(3840,72),'#F8F7F2');draw=ImageDraw.Draw(header)
    font=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',28)
    draw.text((60,20),'A  /  accepted v0.1.1 picture',font=font,fill='#25313B')
    draw.text((1980,20),'B  /  Evidence Acquisition v0.2  -  pending review',font=font,fill='#25313B')
    header_path=output/'comparison-labels.png';header.save(header_path)
    for label,(first,end) in relay.ACQUISITION_RANGES.items():
        name='FAST' if label.startswith('FAST') else 'GUIDED';count=end-first
        receipt=read(candidate/('render-receipt-'+label+'.json'));span=relay.render_span(r,label)
        archive=candidate/('NATIVE_TIFF_'+label+'.zip');manifest_path=candidate/('native-frame-shas-'+label+'.json')
        if (receipt['spec_sha']!=r['spec_sha'] or receipt['frame_range']!=span['frame_range']
                or receipt['frames']!=count or receipt['native']['done'] is not True
                or receipt['output_sha']!=relay.file_sha(receipt['output'])
                or receipt['project_sha']!=relay.file_sha(receipt['project'])
                or receipt['archive_sha']!=relay.file_sha(archive)
                or receipt['frame_manifest_sha']!=relay.file_sha(manifest_path)):
            raise ValueError('B needs completed, hash-bound actual native P0 ranges')
        native_a=read(baseline/'native-frame-shas.json');fa=output/('native-A-'+name)
        names=extract_native(baseline/'NATIVE_TIFF_DUAL.zip',native_a,first,end,fa)
        movies['A_'+name+'_CONTINUOUS']=encode_frames(fa,first,count,output/('A_'+name+'_CONTINUOUS.mp4'))
        short=53 if name=='FAST' else 129
        movies['A_'+name+'_LOCATE']=encode_frames(fa,first,short,output/('A_'+name+'_LOCATE.mp4'))
        clean_extracted(fa,names,output)
        fb=output/('native-B-'+name);native_b=read(manifest_path)
        names=extract_native(archive,native_b,first,end,fb)
        movies['B_'+name+'_LOCATE']=encode_frames(fb,first,short,output/('B_'+name+'_LOCATE.mp4'))
        clean_extracted(fb,names,output)
        b=output/('B_'+name+'_CONTINUOUS.mp4');shutil.copy2(receipt['output'],b)
        movies['B_'+name+'_CONTINUOUS']=verify_movie(b,count)
        ab=output/('AB_'+name+'.mp4')
        subprocess.run(['ffmpeg','-v','error','-n','-i',movies['A_'+name+'_CONTINUOUS']['path'],'-i',str(b),
            '-loop','1','-framerate','24','-i',str(header_path),'-filter_complex',
            '[0:v][1:v]hstack=inputs=2[ab];[2:v][ab]vstack=inputs=2[v]',
            '-map','[v]','-frames:v',str(count),'-an','-c:v','libx264','-threads','4','-crf','16','-pix_fmt','yuv420p',str(ab)],check=True)
        movies['AB_'+name]=verify_movie(ab,count,3840,1152)
        loop=output/('B_'+name+'_LOCATE_LOOP.mp4')
        subprocess.run(['ffmpeg','-v','error','-n','-stream_loop','2','-i',movies['B_'+name+'_LOCATE']['path'],
            '-an','-c','copy',str(loop)],check=True)
        movies['B_'+name+'_LOCATE_LOOP']=verify_movie(loop,short*3)
        sources[name]={'absolute_frame_range':[first,end],'locate_lift_frame_range':[first,first+short],
            'A_frame_shas':{n:s for n,s in native_a.items() if n in native_b},'B_frame_manifest_sha':relay.file_sha(manifest_path),
            'B_native_receipt_sha':relay.file_sha(candidate/('render-receipt-'+label+'.json')),
            'B_project':receipt['project'],'B_project_sha':receipt['project_sha']}
    result={'kind':'source_evidence_acquisition_p0_silent_comparison','version':'0.2.0',
        'baseline_spec_sha':a['request']['spec_sha'],'candidate_spec_sha':r['spec_sha'],
        'fixture_sha':r['fixture_sha'],'trajectory_sha':r['trajectory_sha'],
        'baseline_accepted_movie_sha':a['accepted_movie_sha'],'baseline_feedback_sha':a['human_feedback_sha'],
        'baseline_picture_preservation_sha':a['picture_preservation_sha'],'sources':sources,'movies':movies,
        'comparison_policy':'same_absolute_range_and_real_speed_no_rescale_no_hit_realign',
        'loop_policy':'three_literal_repeats_reset_at_cut_not_extra_search_or_source',
        'human_visual_review':'PENDING','p2_integrated':False,'listening_review':'DEFERRED_BY_USER',
        'synthetic_case_certified':False,'final_voice_accepted':False,'sample_delivery_allowed':False,
        'production_eligible':False,'public_render_ready':False}
    write(output/'comparison-receipt.json',result);return result


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('baseline');p.add_argument('candidate');p.add_argument('output')
    p.add_argument('--accepted-pr',required=True);p.add_argument('--review',required=True);a=p.parse_args()
    result=prepare(a.baseline,a.candidate,a.accepted_pr,a.review,a.output)
    print(json.dumps({'receipt':str(Path(a.output)/'comparison-receipt.json'),'movies':list(result['movies'])},ensure_ascii=True))
