"""Source-bound editorial continuity proof on the existing native picture.

The contract checks timing and provenance, never semantic understanding. All
real text, geometry and frame choices live in ignored local recipes.
"""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent))
import reading_pacing as pacing
from video_contracts import read, write, sha

FPS = 24
NAVIGATION = {'先看完整过程', '重看过程'}


def splice(mapping, bridges):
    slots = {}
    for b in bridges:
        at, count = b['parent_frame'], b['frames']
        if (type(at) is not int or type(count) is not int or not 0 < at < len(mapping)
                or count <= 12 or at in slots or b['source_frame'] != 0):
            raise ValueError('Unique internal bridge using the bound original question required')
        if not b.get('reason'):
            raise ValueError('Explicit cognitive handoff required')
        slots[at] = b
    rows, windows = [], {}
    for n, frame in enumerate(mapping):
        if n in slots:
            b = slots[n]
            start = len(rows)
            for k in range(b['frames']):
                row = dict(source_frame=0, bridge=b['id'], bridge_frame=k)
                # Only the new bridge blends; historical motion stays intact.
                if k < 6:
                    u = (k + 1) / 6
                    row.update(blend_frame=mapping[n-1], question_weight=u*u*(3-2*u))
                elif k >= b['frames']-6:
                    u = (k - (b['frames']-6) + 1) / 6
                    row.update(blend_frame=frame, question_weight=1-u*u*(3-2*u))
                rows.append(row)
            windows[b['id']] = [start, len(rows)]
        rows.append(dict(source_frame=frame, parent_frame=n))
    return rows, windows


def boundary(parent, bridges, end=False):
    return parent + sum(b['frames'] for b in bridges
                        if b['parent_frame'] < parent or (not end and b['parent_frame'] == parent))


def literal(item, source, bundle):
    if item.get('navigation'):
        if item['text'] not in NAVIGATION:
            raise ValueError('Navigation cannot introduce a teaching claim')
        return dict(text=item['text'], text_sha=sha(item['text']), authority='editorial_navigation')
    document = source if item['document'] == 'projection' else bundle
    value = document
    for key in item['pointer'].strip('/').split('/'):
        value = value[int(key)] if isinstance(value, list) else value[key]
    text = item['text']
    if not isinstance(value, str) or not text or text not in value:
        raise ValueError('Literal existing source span required')
    if item.get('task_context'):
        # The literal introductory span may live in the preceding question's
        # reviewed segment; it must explicitly name this question in context.
        target = item['context_target']
        if target not in value[:value.index(text)] or item['document'] != 'bundle':
            raise ValueError('Cross-segment task context is not a new method credential')
    start = value.index(text)
    return dict(text=text, text_sha=sha(text), source_document=item['document'],
                pointer=item['pointer'], span=[start,start+len(text)], source_field_sha=sha(value),
                authority=item.get('authority','existing_review_projection'),
                task_context=bool(item.get('task_context')))


def events(recipe, source, bundle, windows):
    result=[]
    for item in recipe['events']:
        row=literal(item,source,bundle)
        if 'bridge' in item:
            lo, hi=windows[item['bridge']]
            a=lo+item.get('start_offset',0); b=hi-item.get('end_offset',0)
        else:
            a=boundary(item['start_parent_frame'],recipe['bridges'])
            b=boundary(item['end_parent_frame'],recipe['bridges'],end=True)
        if not 0<=a<b or item['style'] not in ('Review','Memory','ActionOutput','Navigation','ComparedOption'):
            raise ValueError('Visible event range/style invalid')
        row.update(start_frame=a,end_frame=b,style=item['style'])
        result.append(row)
    captions=sorted((r for r in result if r['style']=='Review'),key=lambda r:r['start_frame'])
    if any(a['end_frame']>b['start_frame'] for a,b in zip(captions,captions[1:])):
        raise ValueError('Caption handoffs cannot overlap')
    return result


def validate_memory_carry(recipe, rows, windows):
    for bridge in recipe['bridges']:
        start,end=windows[bridge['id']]
        carried=[r for r in rows if r['style']=='Memory' and r['start_frame']<start
                 and r['end_frame']>=end+bridge['carry_after_frames']]
        if not carried:
            raise ValueError('Evidence memory must precede and survive the return to options')
        if any(r['authority']!='existing_review_projection' for r in carried):
            raise ValueError('No invented or navigation-only evidence memory')


def write_overlay(folder, rows, focus):
    # SRT remains the lexical caption handoff; ASS includes transient memory.
    pacing.write_captions(folder,[r for r in rows if r['style']=='Review'])
    header=(folder/'review.ass').read_text(encoding='utf-8-sig').split('[Events]')[0]
    header+=('Style: Memory,Noto Sans SC,48,&H0058544C,&H0058544C,&H00FFFFFF,&H00000000,0,0,0,0,100,100,0,0,1,1,0,9,220,220,130,1\n'
             'Style: ActionOutput,Georgia,52,&H002E2C28,&H002E2C28,&H00FFFFFF,&H00000000,0,0,0,0,100,100,0,0,1,1,0,7,220,220,140,1\n'
             'Style: Navigation,Noto Sans SC,46,&H00817D75,&H00817D75,&H00FFFFFF,&H00000000,0,0,0,0,100,100,0,0,1,0,0,7,220,220,110,1\n'
             'Style: ComparedOption,Georgia,48,&H0058544C,&H0058544C,&H00FFFFFF,&H00000000,0,0,0,0,100,100,0,0,1,1,0,7,220,220,140,1\n'
             '[Events]\nFormat: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n')
    lines=[]
    for r in rows:
        text=pacing.wrap(r['text']) if r['style']=='Review' else r['text']
        text=text.replace('\\','\\\\').replace('{','\\{').replace('}','\\}').replace('\n','\\N')
        fade='{\\fad(160,160)}' if r['style']!='Review' else ''
        lines.append(f"Dialogue: 1,{pacing.timestamp(r['start_frame'])},{pacing.timestamp(r['end_frame'])},{r['style']},,0,0,0,,{fade}{text}")
    for f in focus:
        x,y,w,h=f['rect']
        # Comparison-blue short fill, never underline or early answer orange.
        drawing='{\\an7\\pos('+str(x)+','+str(y)+')\\p1\\bord0\\shad0\\1c&HBD9167&\\alpha&HAA&\\fad(160,160)}m 0 0 l '+str(w)+' 0 l '+str(w)+' '+str(h)+' l 0 '+str(h)+'{\\p0}'
        lines.append(f"Dialogue: 0,{pacing.timestamp(f['start_frame'])},{pacing.timestamp(f['end_frame'])},Review,,0,0,0,,{drawing}")
    (folder/'continuity.ass').write_text(header+'\n'.join(lines)+'\n',encoding='utf-8-sig')


def prepare(parent, folder, recipe):
    import integration
    parent,folder=pacing.local(parent),pacing.local(folder)
    if folder.exists():raise ValueError('Preserve older takes; use a new revision')
    old=read(parent/'pacing-plan.json'); digest=old['plan_sha']
    if sha({k:v for k,v in old.items() if k!='plan_sha'})!=digest:raise ValueError('Parent plan changed')
    spec=integration.current(Path(old['baseline']))
    source=spec['source'];bundle=read(spec['bundle'])
    rows,windows=splice(old['frame_mapping'],recipe['bridges'])
    overlay=events(recipe,source,bundle,windows)
    validate_memory_carry(recipe,overlay,windows)
    for r in overlay:
        if r['end_frame']>len(rows):raise ValueError('Event outside film')
    focus=[]
    for b in recipe['bridges']:
        lo,hi=windows[b['id']]
        ref=literal(b['focus_source'],source,bundle)
        focus.append(dict(ref,start_frame=hi-24,end_frame=hi-6,rect=b['focus_rect'],color='comparison_blue'))
    folder.mkdir(parents=True)
    write_overlay(folder,overlay,focus)
    plan=dict(schema='continuity-proof/v1',source_binding=old['source_binding'],
              parent=str(parent),parent_plan_sha=digest,baseline=old['baseline'],
              native_frames=old['native_frames'],native_manifest_sha=old['native_manifest_sha'],
              bundle_sha=pacing.file_sha(spec['bundle']),status_sha=pacing.file_sha(spec['status']),
              rows=rows,bridges=recipe['bridges'],bridge_windows=windows,events=overlay,focus=focus,
              recipe_sha=sha(recipe),overlay_sha=pacing.file_sha(folder/'continuity.ass'),
              srt_sha=pacing.file_sha(folder/'review.srt'),fps=24,duration=len(rows)/24,
              human_comprehension_review='PENDING',source_role=source['action']['role'],
              strict_two_method_relay='HOLD',final_voice_accepted=False,
              sample_delivery_allowed=False,public_render_ready=False)
    plan['plan_sha']=sha(plan);write(folder/'continuity-plan.json',plan)
    write(folder/'frozen-source.json',source)
    return dict(plan_sha=plan['plan_sha'],duration=plan['duration'],events=len(overlay))


def render(folder):
    import integration
    folder=pacing.local(folder);plan=read(folder/'continuity-plan.json')
    digest=plan.pop('plan_sha')
    if sha(plan)!=digest:raise ValueError('Continuity plan changed')
    spec=integration.current(Path(plan['baseline']))
    if pacing.file_sha(spec['bundle'])!=plan['bundle_sha'] or pacing.file_sha(spec['status'])!=plan['status_sha']:
        raise ValueError('Frozen upstream changed')
    if pacing.file_sha(folder/'continuity.ass')!=plan['overlay_sha'] or pacing.file_sha(folder/'review.srt')!=plan['srt_sha']:
        raise ValueError('Copy/display mutation requires new review')
    baseline=Path(plan['baseline']);manifest=read(baseline/'native-frame-shas.json')
    if sha(manifest)!=plan['native_manifest_sha']:raise ValueError('Native manifest changed')
    frames=Path(plan['native_frames'])
    def verify(i):
        name=f'FRAME_{i:05}.tif'
        if pacing.file_sha(frames/name)!=manifest[name]:raise ValueError('Native bytes changed')
    with ThreadPoolExecutor(max_workers=8) as pool:list(pool.map(verify,set(r['source_frame'] for r in plan['rows'])))
    linked=frames.parent.parent/folder.name/'continuity-frames';linked.mkdir(parents=True,exist_ok=False)
    for n,r in enumerate(plan['rows']):
        target=linked/f'FRAME_{n:05}.tif';source=frames/f"FRAME_{r['source_frame']:05}.tif"
        if 'blend_frame' in r:
            a=Image.open(frames/f"FRAME_{r['blend_frame']:05}.tif").convert('RGB')
            b=Image.open(source).convert('RGB')
            Image.blend(a,b,r['question_weight']).save(target,compression='tiff_lzw')
        else:os.link(source,target)
    movie=folder/'Q33_CONTINUOUS_PROCESS_4K.mp4'
    if movie.exists():raise ValueError('Never overwrite a take')
    subprocess.run(['ffmpeg','-hide_banner','-loglevel','warning','-threads','1','-filter_threads','1',
                    '-framerate','24','-i',str(linked/'FRAME_%05d.tif'),'-vf','ass=continuity.ass','-an',
                    '-c:v','libx264','-threads','4','-preset','fast','-crf','16','-pix_fmt','yuv420p',
                    '-movflags','+faststart',str(movie)],cwd=folder,check=True)
    streams=json.loads(subprocess.check_output(['ffprobe','-v','error','-count_frames','-show_streams','-of','json',str(movie)]))['streams']
    if len(streams)!=1 or streams[0]['codec_type']!='video':raise ValueError('Silent proof only')
    v=streams[0]
    if (v['width'],v['height'],v['r_frame_rate'],int(v['nb_read_frames']))!=(3840,2160,'24/1',len(plan['rows'])):
        raise ValueError('Encoded frame/timing mismatch')
    subprocess.run(['ffmpeg','-v','error','-threads','1','-i',str(movie),'-f','null','-'],check=True)
    receipt=dict(plan_sha=digest,movie=str(movie),movie_sha=pacing.file_sha(movie),
                 duration=plan['duration'],frames=len(plan['rows']),audio_streams=0,full_decode='PASS',
                 native_frames_preserved=len(read(Path(plan['parent'])/'pacing-plan.json')['frame_mapping']),
                 bridge_frames=sum(b['frames'] for b in plan['bridges']),blend_frames=24,
                 comprehension_review='PENDING',sample_delivery_allowed=False,public_render_ready=False)
    write(folder/'render-receipt.json',receipt)
    return receipt


if __name__=='__main__':
    parser=argparse.ArgumentParser();sub=parser.add_subparsers(dest='command',required=True)
    p=sub.add_parser('prepare');p.add_argument('parent');p.add_argument('output');p.add_argument('recipe')
    p=sub.add_parser('render');p.add_argument('output')
    args=parser.parse_args()
    print(json.dumps(prepare(args.parent,args.output,read(args.recipe)) if args.command=='prepare'
                     else render(args.output),ensure_ascii=False))
