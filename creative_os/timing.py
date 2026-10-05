"""Measured scratch narration, clause captions, holds and restrained scratch audio."""
from pathlib import Path
import array
import hashlib
import math
import re
import wave
from video_contracts import sha
from ae_production.layout import wrap

VERSION = '0.1.0'


def audio_info(path):
    with wave.open(str(path), 'rb') as f:
        if (f.getnchannels(), f.getsampwidth()) != (1, 2): raise ValueError('Scratch WAV must be mono PCM16')
        return {'duration': f.getnframes()/f.getframerate(), 'sample_rate': f.getframerate(),
                'frames': f.getnframes(), 'sha256': hashlib.sha256(Path(path).read_bytes()).hexdigest()}


def track_payload(track):
    return {k: ([{a: b for a, b in u.items() if a != 'audio_path'} for u in v] if k == 'units' else v)
            for k, v in track.items() if k != 'audio_timing_sha'}


def narration_track(delivery, recordings=None, readthrough=None, fps=24, provider='provided_internal_scratch_audio', sentence_boundaries=None):
    """WAV duration is measured; fallback requires an explicit read-through estimate."""
    units = []; start = 0
    for u in delivery['units']:
        if recordings:
            path = recordings[u['unit_id']]; info = audio_info(path)
            duration = info['duration']; kind = 'measured_scratch_tts_not_human_recording'
        else:
            estimate = (readthrough or {}).get(u['unit_id'], {})
            if not estimate.get('rationale') or estimate.get('duration', 0) <= 0:
                raise ValueError('No audio or explicit read-through timing')
            duration = estimate['duration']; kind = 'explicit_readthrough_estimate'
            path = None; info = {'sha256': None, 'duration': duration, 'sample_rate': None, 'frames': None}
        end = math.ceil((start + duration + u['pause_after']) * fps - 1e-9) / fps
        events = (sentence_boundaries or {}).get(u['unit_id'], [])
        clean = lambda s: re.sub(r'\s', '', s)
        if events and (clean(''.join(e['text'] for e in events)) != clean(u['spoken_copy']) or
                       any(e['type'] != 'SentenceBoundary' or e['offset'] < 0 or e['duration'] <= 0 or
                           (e['offset'] + e['duration']) / 10**7 > duration + .15 for e in events)):
            raise ValueError('Sentence boundaries do not match the actual narration')
        units.append({'unit_id': u['unit_id'], 'start': start, 'voice_end': start + duration, 'end': end,
                      'estimated_or_recorded_duration': duration, 'duration_kind': kind,
                      'pause': end-start-duration, 'breath': u['breath'], 'emphasis': u['emphasis'],
                      'audio_path': str(Path(path).resolve()) if path else None, 'audio': info,
                      'spoken_copy_sha': sha(u['spoken_copy']), 'sentence_boundaries': events})
        start = end
    track = {'version': VERSION, 'delivery_copy_sha': delivery['delivery_copy_sha'], 'fps': fps,
             'provider': provider if recordings else 'explicit_readthrough',
             'usage': 'INTERNAL_SCRATCH_VOICE', 'duration': start, 'units': units}
    track['audio_timing_sha'] = sha(track_payload(track)); return track


def validate_track(track, delivery, check_files=True):
    if track['delivery_copy_sha'] != delivery['delivery_copy_sha'] or track['audio_timing_sha'] != sha(track_payload(track)):
        raise ValueError('Narration timing/copy drift')
    if [u['unit_id'] for u in track['units']] != [u['unit_id'] for u in delivery['units']]: raise ValueError('Incomplete narration')
    if track['fps'] != 24: raise ValueError('Landscape timing must use 24 fps')
    elapsed = 0
    for t, u in zip(track['units'], delivery['units']):
        if (t['start'] != elapsed or t['spoken_copy_sha'] != sha(u['spoken_copy']) or
            t['voice_end'] <= t['start'] or t['end'] < t['voice_end'] or t['pause'] < u['pause_after']-1e-6 or
            abs(t['voice_end']-t['start']-t['estimated_or_recorded_duration']) > 1e-7 or
            abs(t['pause']-(t['end']-t['voice_end'])) > 1e-7 or
            abs(t['end']*24-round(t['end']*24)) > 1e-7):
            raise ValueError('Narration timing order/duration drift')
        if check_files and t['audio_path'] and audio_info(t['audio_path']) != t['audio']: raise ValueError('Scratch audio changed')
        if t['audio_path'] and abs(t['audio']['duration']-t['estimated_or_recorded_duration']) > 1e-7:
            raise ValueError('Measured narration duration drift')
        events=t.get('sentence_boundaries', []);previous=0
        if events and re.sub(r'\s','',''.join(e['text'] for e in events)) != re.sub(r'\s','',u['spoken_copy']):
            raise ValueError('Sentence boundary coverage drift')
        for e in events:
            if (e['type']!='SentenceBoundary' or e['offset'] < previous or e['duration'] <= 0 or
                (e['offset']+e['duration'])/10**7 > t['estimated_or_recorded_duration']+.15):
                raise ValueError('Sentence boundary order/duration drift')
            previous=e['offset']
        elapsed = t['end']
    if elapsed != track['duration']: raise ValueError('Narration total duration drift')


def captions(delivery, track, design):
    cues = []; style = design['typography']['Subtitle']
    for u, t in zip(delivery['units'], track['units']):
        if t.get('sentence_boundaries'):
            cursor = 0
            for event_index, event in enumerate(t['sentence_boundaries']):
                # Preserve exact authored whitespace while comparing TTS boundary text without it.
                target = re.sub(r'\s', '', event['text']); begin = cursor; matched = ''
                while cursor < len(u['spoken_copy']) and matched != target:
                    ch = u['spoken_copy'][cursor]; cursor += 1
                    if not ch.isspace(): matched += ch
                if matched != target: raise ValueError('Boundary text drift')
                phrase = u['spoken_copy'][begin:cursor]
                lines = wrap(phrase, 1536, style['size'], design['font']['measurement_file'],
                             max_units=28, variation=design['font'].get('variation'), cjk=True)
                groups = [lines[i:i+2] for i in range(0, len(lines), 2)]
                start = t['start'] + event['offset']/10**7
                finish = min(t['voice_end'], start + event['duration']/10**7)
                if event_index+1 < len(t['sentence_boundaries']):
                    finish = min(finish, t['start']+t['sentence_boundaries'][event_index+1]['offset']/10**7)
                total = sum(len(''.join(g)) for g in groups)
                for g in groups:
                    end = start + (finish - (t['start'] + event['offset']/10**7))*len(''.join(g))/total
                    cues.append({'cue_id': u['unit_id']+':caption:'+str(len(cues)), 'unit_id': u['unit_id'],
                                 'start': start, 'end': end, 'lines': g, 'text': ''.join(g),
                                 'source_claim_refs': u['source_claim_refs'], 'evidence_refs': u['evidence_refs'],
                                 'alignment': 'tts_sentence_boundary' if len(groups)==1 else 'tts_sentence_boundary_with_estimated_page_split'})
                    start = end
            if cursor != len(u['spoken_copy']): raise ValueError('Uncovered narration boundary')
            continue
        phrases = re.findall(r'[^。！？；，]+[。！？；，]?|[。！？；，]', u['spoken_copy'])
        groups = []
        for phrase in phrases:
            lines = wrap(phrase, 1536, style['size'], design['font']['measurement_file'],
                         max_units=28, variation=design['font'].get('variation'), cjk=True)
            groups.extend([lines[i:i+2] for i in range(0, len(lines), 2)])
        weights = [max(1, len(''.join(g))) for g in groups]; total = sum(weights); at = t['start']
        for i, (g, weight) in enumerate(zip(groups, weights)):
            end = t['voice_end'] if i == len(groups)-1 else at+(t['voice_end']-t['start'])*weight/total
            if end-at < 4/24: raise ValueError('Caption too fast')
            cues.append({'cue_id': u['unit_id']+':caption:'+str(i), 'unit_id': u['unit_id'],
                         'start': at, 'end': end, 'lines': g, 'text': ''.join(g),
                         'source_claim_refs': u['source_claim_refs'], 'evidence_refs': u['evidence_refs'],
                         'alignment': 'clause_weight_estimated_within_measured_unit_not_forced_alignment'})
            at = end
        if ''.join(c['text'] for c in cues if c['unit_id'] == u['unit_id']) != u['spoken_copy']:
            raise ValueError('Caption lost delivery characters')
    return cues


def cue_sheet(delivery, track):
    rows = []
    for u, t in zip(delivery['units'], track['units']):
        rows.append({'kind': 'VO', 'unit_id': u['unit_id'], 'start': t['start'], 'end': t['voice_end'],
                     'provenance': 'local_generated_scratch_not_final_human_voice'})
        rows.append({'kind': 'silence', 'unit_id': u['unit_id'], 'start': t['voice_end'], 'end': t['end'],
                     'reason': 'breath_and_stable_reading_hold'})
        if u['intent'] in ('regroup', 'routing', 'rewire'):
            rows.append({'kind': 'structural_click', 'unit_id': u['unit_id'],
                         'start': min(t['start']+2, t['voice_end']), 'end': min(t['start']+2, t['voice_end'])+0.06,
                         'reason': 'one_structural_settle_not_every_object', 'peak_dbfs': -36,
                         'provenance': 'procedural_scratch_sine_envelope'})
    return {'version': VERSION, 'audio_timing_sha': track['audio_timing_sha'], 'cues': rows,
            'transition_accent': 'omitted_no_semantic_need', 'soft_impact': 'omitted_no_semantic_need',
            'ambient_bed': 'omitted_no_licensed_music', 'music_release': 'PENDING', 'public_render_ready': False}


def mix_scratch(track, sheet, output):
    validate_files = [audio_info(t['audio_path']) for t in track['units']]
    rates = {i['sample_rate'] for i in validate_files}
    if len(rates) != 1: raise ValueError('Scratch sample rates must match')
    rate = rates.pop(); samples = array.array('h', [0]) * math.ceil(track['duration']*rate)
    for t in track['units']:
        with wave.open(t['audio_path'], 'rb') as f:
            src = array.array('h'); src.frombytes(f.readframes(f.getnframes()))
        start = round(t['start']*rate)
        for i, value in enumerate(src): samples[start+i] = value
    for cue in sheet['cues']:
        if cue['kind'] != 'structural_click': continue
        start = round(cue['start']*rate); count = round(0.06*rate)
        for i in range(count):
            value = round(32767*10**(-36/20)*math.sin(2*math.pi*480*i/rate)*math.sin(math.pi*i/count)**2)
            if start+i < len(samples): samples[start+i] = max(-32768, min(32767, samples[start+i]+value))
    with wave.open(str(output), 'wb') as f:
        f.setnchannels(1); f.setsampwidth(2); f.setframerate(rate); f.writeframes(samples.tobytes())
    return {'path': str(Path(output).resolve()), **audio_info(output), 'usage': 'INTERNAL_SCRATCH_VOICE',
            'cue_sheet_sha': sha(sheet), 'audio_timing_sha': track['audio_timing_sha']}
