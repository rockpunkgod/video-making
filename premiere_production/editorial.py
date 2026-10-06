"""Frozen AE handoff and final editing through the official upstream MCP server.

No teaching generation, no silent backend fallback, no publication command.
"""
from pathlib import Path
import re
import math
from video_contracts import read, write, sha
from creative_os.hero import validate_contract, validate_handoff, file_sha
from .router import BackendRouter
from .music import verify_gain_keys


def validate_audio_plan(audio, contract, excerpt):
    """Freeze every voice unit and audio source before final-cut operations."""
    duration = contract['canvas']['duration']
    if (audio['render_contract_sha'] != contract['render_contract_sha']
            or audio['final_copy_sha'] != contract['copy_lock']['final_copy_sha']):
        raise ValueError('Audio plan belongs to another visual revision or final copy')
    if audio['duration'] != duration or audio['fps'] != contract['canvas']['fps']:
        raise ValueError('Audio plan timing/profile differs from the Hero')
    units = {u['unit_id']:u for u in excerpt['units']}
    voice_ids = [v['unit_id'] for v in audio['voice']]
    if len(voice_ids) != len(set(voice_ids)) or set(voice_ids) != set(units):
        raise ValueError('Voice must cover every excerpt unit exactly once')
    previous_end = 0
    for voice in audio['voice']:
        unit = units[voice['unit_id']]
        if (file_sha(voice['path']) != voice['sha256']
                or voice['spoken_copy_sha'] != sha(unit['spoken_copy'])
                or voice['source_claim_refs'] != unit['source_claim_refs']):
            raise ValueError('Voice file/copy/binding drift')
        start,end = voice['start'],voice['end']
        if (not all(math.isfinite(t) for t in (start,end))
                or not 0 <= start < end <= duration or start < previous_end):
            raise ValueError('Voice timeline overlaps or exceeds the Hero')
        previous_end = end
    sfx = audio.get('sfx')
    if sfx and file_sha(sfx['path']) != sfx['sha256']:
        raise ValueError('Structural SFX changed after Audio Plan capture')
    music = audio.get('music')
    if music:
        if (file_sha(music['source_path']) != music['file_sha']
                or file_sha(music['clip_path']) != music['clip_sha']):
            raise ValueError('Recording changed after license/input capture')
        if audio.get('ducking',{}).get('status') == 'not_applicable':
            raise ValueError('Music cannot retain a no-music ducking declaration')
        behavior = audio.get('behavior',{})
        if behavior.get('mix_owner') != 'Premiere' or behavior.get('beat_sync') is not False:
            raise ValueError('Piano bed must be edited in Premiere without Beat Sync')
        keys = music.get('gain_keys',[])
        times = [k['time_seconds'] for k in keys]
        if (not keys or times != sorted(set(times)) or times[0] != 0
                or any(not math.isfinite(t) or not 0 <= t < duration for t in times)
                or any(not math.isfinite(k['level_db']) or not -96 <= k['level_db'] <= 0 for k in keys)):
            raise ValueError('Invalid native music gain envelope')
    return audio


def validate_audio_timeline(state, audio):
    """Verify placements the native API exposes; do not infer unseen source IDs."""
    if state.get('pagination',{}).get('truncated'):
        raise ValueError('Native timeline snapshot truncated')
    expected={0:[(Path(v['path']).name,v['start'],v['end']) for v in audio['voice']]}
    if audio.get('sfx'):
        expected[1]=[(Path(audio['sfx']['path']).name,0,audio['duration'])]
    if audio.get('music'):
        index=audio['music']['audio_track_index']
        if index in expected:
            raise ValueError('Music must occupy a separate audio track')
        expected[index]=[(Path(audio['music']['clip_path']).name,0,audio['duration'])]
    actual={t['index']:t['clips'] for t in state['audioTracks'] if t['clips']}
    if set(actual)!=set(expected):
        raise ValueError('Native audio tracks differ from the Audio Plan')
    for index,planned in expected.items():
        observed=actual[index]
        if len(observed)!=len(planned):
            raise ValueError('Native audio clip coverage differs from the Audio Plan')
        for clip,(name,start,end) in zip(observed,planned):
            if (clip['name']!=name or abs(clip['start']-start)>1/24
                    or abs(clip['end']-end)>1/24):
                raise ValueError('Native audio placement differs from the Audio Plan')
    return 'PASS_native_clip_names_placement_and_coverage'


def bind_final_display(manifest, excerpt, caption_path, frame_paths, attribution_text):
    """Freeze actual native caption wording and inspected display frames.

    This creates review inputs; it never signs a source/editorial release.
    """
    caption_text=Path(caption_path).read_text(encoding='utf-8-sig')
    blocks=re.split(r'\r?\n\s*\r?\n',caption_text.strip())
    lines=[]
    for block in blocks:
        parts=block.splitlines()
        if len(parts)<3 or '-->' not in parts[1]:
            raise ValueError('Native caption timing proof is not SRT')
        lines.append(''.join(parts[2:]))
    compact=lambda value: re.sub(r'\s','',value)
    if compact(''.join(lines)) != compact(''.join(u['spoken_copy'] for u in excerpt['units'])):
        raise ValueError('Actual displayed captions differ from bound voice copy')
    excerpts=[e for u in excerpt['units'] for e in u['visual_excerpts']]
    source_display={'displayed_excerpt_ids':['excerpt:'+sha(e) for e in excerpts],
                    'displayed_excerpt_refs':[e['ref'] for e in excerpts],
                    'displayed_text_sha':sha([e['text'] for e in excerpts]),
                    'displayed_image_sha':sha([file_sha(p) for p in frame_paths]),
                    'attribution_text':attribution_text,'release_review_id':None}
    result=dict(manifest)
    result['source_display']=source_display
    result['copy_lock']={'final_copy_sha':sha([manifest['final_copy_sha'],file_sha(caption_path)]),
                         'polished_from_sha':None,'editorial_review_sha':None,
                         'actual_caption_sha':file_sha(caption_path)}
    result['caption_verification']={'source':'native_Premiere_sidecar_and_burned_frames',
                                    'native_cue_count':len(lines),'wording':'PASS_exact_bound_voice_copy'}
    result['public_render_ready']=False
    return result


class EditorialSession:
    def __init__(self, router, request):
        self.router, self.request = router, request
        self.preflight()

    def preflight(self):
        r = self.request
        contract = read(r['contract'])
        excerpt = read(r['excerpt'])
        validate_contract(contract, read(r['package']), read(r['manifest']),
                          {k: read(v) for k,v in r['statuses'].items()},
                          read(r['full_delivery']), excerpt)
        from creative_os.consumer_copy import require_consumer_copy
        require_consumer_copy(excerpt, contract['nodes'])
        receipt = read(r['render_receipt'])
        validate_handoff(receipt, contract, r['ae_project'])
        audio = read(r['audio_plan'])
        validate_audio_plan(audio, contract, excerpt)
        return contract, receipt, excerpt, audio

    def call(self, operation, inputs=None):
        # Re-read supplied current status before each pipeline operation. This
        # does not pretend that a local snapshot senses external withdrawals.
        self.preflight()
        try:
            return self.router.execute(operation, inputs or {}, sequence_id=self.request['sequence_id'])
        finally:
            write(self.request['edit_receipts'], self.router.receipts)

    def replace_motion(self, item_id, sections):
        """Same source render carried across existing final-cut boundaries."""
        duration = self.preflight()[0]['canvas']['duration']
        if (not sections or sections[0][0] != 0 or sections[-1][1] != duration
                or any(a >= b for a,b in sections)
                or any(a[1] != b[0] for a,b in zip(sections, sections[1:]))):
            raise ValueError('Sections must cover the motion continuously')
        for start,end in sections:
            self.call('overwrite_clip', {'item_id':item_id, 'start_seconds':start,
                                        'track_index':0, 'audio_track_index':0})
            clips = self.call('get_active_sequence')['videoTracks'][0]['clips']
            clip = next(c for c in clips if abs(c['start']-start) < 1e-6)
            node = clip['nodeId']
            if end < duration:
                self.call('trim_clip', {'node_id':node, 'new_out_seconds':end})
            if start:
                self.call('trim_clip', {'node_id':node, 'new_in_seconds':start})
                self.call('move_clip', {'node_id':node, 'new_start_seconds':start})
            actual = self.call('get_clip_properties', {'node_id':node})
            if any(abs(actual[key]-value) > 1/24 for key,value in
                   [('start',start),('end',end),('inPoint',start),('outPoint',end)]):
                raise ValueError('Native source/timeline trim mismatch')

    def export_internal(self, output, preset):
        output, preset = Path(output).resolve(), Path(preset).resolve()
        if Path(output).exists():
            raise ValueError('Export a new revision rather than overwrite history')
        self.call('save_project')
        self.call('validate_export_preset', {'preset_path':str(preset)})
        audio = self.preflight()[3]
        state = self.call('get_active_sequence')
        audio_verification = {'timeline':validate_audio_timeline(state,audio)}
        if audio.get('music'):
            music_clip = next(t for t in state['audioTracks'] if t['index']==audio['music']['audio_track_index'])['clips'][0]
            properties = self.call('get_clip_properties', {'node_id':music_clip['nodeId']})
            volume = next(e for e in properties['effects'] if e.get('matchName','').startswith('Internal Volume'))
            parameters = self.call('get_effect_properties', {'node_id':music_clip['nodeId'], 'effect_name':volume['matchName']})
            level = next(p['displayName'] for p in parameters['properties'] if p['displayName'] in ('Level','Nivel','级别'))
            native_keys = self.call('get_keyframes', {'node_id':music_clip['nodeId'],
                                      'effect_name':volume['matchName'], 'property_name':level})
            audio_verification['music_keys'] = verify_gain_keys(native_keys,audio['music']['gain_keys'])
            audio_verification['native_music_keys_sha'] = sha(native_keys)
        result = self.call('export_sequence', {'output_path':str(output), 'preset_path':str(preset),
                                               'range':'entire', 'timeout_minutes':3})
        if not Path(output).is_file() or not Path(output).stat().st_size:
            raise ValueError('Native export did not produce media')
        contract, receipt, excerpt, audio = self.preflight()
        return {'usage':'INTERNAL_CREATIVE_PREVIEW', 'render_contract_sha':contract['render_contract_sha'],
                'motion_render_sha':receipt['output_sha'], 'audio_plan_sha':sha(audio),
                'final_copy_sha':sha([contract['copy_lock']['final_copy_sha'], file_sha(self.request['captions'])]),
                'output_path':str(Path(output).resolve()), 'output_sha':file_sha(output),
                'native_export_result':result, 'human_taste_review':'PENDING',
                'audio_verification':audio_verification,
                'music_license_gate':audio.get('music',{}).get('music_license_gate','HOLD'),
                'teaching_release':'HOLD', 'source_display_release':'HOLD', 'editorial_release':'HOLD',
                'public_render_ready':False}


def main():
    import argparse
    from .mcp import PremiereMcpClient
    parser=argparse.ArgumentParser();parser.add_argument('request');args=parser.parse_args()
    r=read(args.request)
    client=PremiereMcpClient(r['endpoint'], Path(r['token_file']).read_text().strip())
    client.initialize()
    router=BackendRouter(client, preferred=r.get('backend'))
    if Path(r['edit_receipts']).exists():
        router.receipts=read(r['edit_receipts'])
        if router.receipts and router.receipts[-1].get('result',{}).get('outcome')=='uncertain':
            raise ValueError('Prior uncertain edit requires explicit reconciliation')
    session=EditorialSession(router,r)
    result=session.export_internal(r['output'],r['export_preset'])
    write(r['production_manifest'],result)


if __name__=='__main__':
    main()
