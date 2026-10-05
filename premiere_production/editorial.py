"""Frozen AE handoff and final editing through the official upstream MCP server.

No teaching generation, no silent backend fallback, no publication command.
"""
from pathlib import Path
import re
from video_contracts import read, write, sha
from creative_os.hero import validate_contract, validate_handoff, file_sha
from .router import BackendRouter


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
        receipt = read(r['render_receipt'])
        validate_handoff(receipt, contract, r['ae_project'])
        audio = read(r['audio_plan'])
        if audio['render_contract_sha'] != contract['render_contract_sha']:
            raise ValueError('Audio plan belongs to another visual revision')
        if audio['final_copy_sha'] != contract['copy_lock']['final_copy_sha']:
            raise ValueError('Audio plan belongs to another final copy')
        units = {u['unit_id']:u for u in excerpt['units']}
        for voice in audio['voice']:
            if (file_sha(voice['path']) != voice['sha256']
                    or voice['spoken_copy_sha'] != sha(units[voice['unit_id']]['spoken_copy'])
                    or voice['source_claim_refs'] != units[voice['unit_id']]['source_claim_refs']):
                raise ValueError('Voice file/copy/binding drift')
        music = audio.get('music')
        if music and (file_sha(music['source_path']) != music['file_sha']
                      or file_sha(music['clip_path']) != music['clip_sha']):
            raise ValueError('Recording changed after license/input capture')
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
