"""Engine-independent WAV/transcript handoff; no model runtime imports."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
import wave


def sha256(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b''):
            digest.update(chunk)
    return digest.hexdigest()


def asset(root, relative):
    path = (root / relative).resolve()
    if Path(relative).is_absolute() or not path.is_relative_to(root.resolve()):
        raise ValueError('Asset must remain inside the delivery directory')
    return path


def describe_clip(root, clip_id, audio, transcript, review='PENDING'):
    with wave.open(str(asset(root, audio)), 'rb') as handle:
        return dict(id=clip_id, audio=audio, audio_sha256=sha256(asset(root, audio)),
                    transcript=transcript, transcript_sha256=sha256(asset(root, transcript)),
                    duration_seconds=handle.getnframes() / handle.getframerate(),
                    sample_rate=handle.getframerate(), channels=handle.getnchannels(),
                    listening_review=review)


def validate(path):
    path = Path(path).resolve()
    delivery = json.loads(path.read_text(encoding='utf-8'))
    if delivery.get('schema') != 'voice-delivery/v1' or not delivery.get('clips'):
        raise ValueError('Expected a nonempty voice-delivery/v1 manifest')
    ids = set()
    for clip in delivery['clips']:
        if not clip['id'] or clip['id'] in ids:
            raise ValueError('Clip IDs must be nonempty and unique')
        ids.add(clip['id'])
        if clip['listening_review'] not in ('PENDING', 'USER_ACCEPTED', 'REJECTED'):
            raise ValueError('Unknown listening review state')
        measured = describe_clip(path.parent, clip['id'], clip['audio'], clip['transcript'],
                                 clip['listening_review'])
        for field in ('audio_sha256', 'transcript_sha256', 'sample_rate', 'channels'):
            if clip[field] != measured[field]:
                raise ValueError(f'{clip["id"]}: {field} mismatch')
        if abs(clip['duration_seconds'] - measured['duration_seconds']) > 1e-6:
            raise ValueError('Duration mismatch')
        if measured['duration_seconds'] <= 0 or not asset(path.parent, clip['transcript']).read_text(encoding='utf-8-sig').strip():
            raise ValueError('Empty audio or transcript')
    return delivery


def validate_user_recordings(path):
    """Verify supplied provenance and content-check bindings, not speaker biometrics.

    Declarations must come from actual recording/content checks. Software cannot
    infer human authorship, transcript correctness or listening quality from WAV.
    """
    path = Path(path).resolve(); delivery = validate(path)
    provenance = delivery.get('recording_source', {})
    if provenance.get('kind') != 'user_recording' or not provenance.get('speaker'):
        raise ValueError('Actual user-recording provenance is required; TTS is not a human take')
    declaration = provenance['declaration']
    if sha256(asset(path.parent, declaration['path'])) != declaration['sha256']:
        raise ValueError('Recording declaration changed')
    if not asset(path.parent,declaration['path']).read_text('utf-8-sig').strip():
        raise ValueError('Recording declaration is empty')
    sources = {s['id']:s for s in delivery['sources']}
    if len(sources) != len(delivery['sources']) or set(sources) != {c['id'] for c in delivery['clips']}:
        raise ValueError('Every human take needs one original source binding')
    for clip in delivery['clips']:
        source = sources[clip['id']]
        for key in ('original_audio', 'content_check'):
            item = source[key]
            if sha256(asset(path.parent,item['path'])) != item['sha256']:
                raise ValueError('Original recording or content-check evidence changed')
        if source['content_check']['status'] != 'MATCHED' or source['transcript_sha256'] != clip['transcript_sha256']:
            raise ValueError('Exact human recording content has not been checked')
        if source['derived_audio_sha256'] != clip['audio_sha256']:
            raise ValueError('Human take derivative changed')
        if 'recording_declaration' in source:
            item=source['recording_declaration'];p=asset(path.parent,item['path'])
            if sha256(p)!=item['sha256'] or not p.read_text('utf-8-sig').strip():
                raise ValueError('Selected take recording declaration changed or is empty')
        if not asset(path.parent,source['content_check']['path']).read_text('utf-8-sig').strip():
            raise ValueError('Content-check evidence is empty')
        # Recompute the actual conversion, rather than trusting a prose claim or
        # a re-bound hash of a trimmed take. This does not identify the speaker.
        expected=converted_pcm_sha256(asset(path.parent,source['original_audio']['path']))
        with wave.open(str(asset(path.parent,clip['audio'])),'rb') as wav:
            if (wav.getframerate(),wav.getnchannels(),wav.getsampwidth())!=(48000,1,2):
                raise ValueError('User recording derivative must be PCM16 mono 48000 Hz')
            actual=hashlib.sha256(wav.readframes(wav.getnframes())).hexdigest()
        if actual!=expected:
            raise ValueError('User recording derivative is not the complete unmodified conversion')
        if clip['listening_review'] == 'REJECTED':
            raise ValueError('Rejected human take cannot enter production')
    return delivery


def converted_pcm_sha256(source):
    result=subprocess.check_output(['ffmpeg','-v','error','-i',str(source),'-map','0:a:0','-vn',
        '-ar','48000','-ac','1','-c:a','pcm_s16le','-f','hash','-hash','sha256','-'],text=True)
    return result.strip().split('=',1)[1].lower()


def import_user_recordings(request_path, output):
    """Import actual recorded files into the existing portable delivery contract."""
    request_path = Path(request_path).resolve(); output = Path(output).resolve()
    spec = json.loads(request_path.read_text('utf-8-sig'))
    if spec.get('schema') != 'voice-delivery-import/v1' or spec.get('source_kind') != 'user_recording':
        raise ValueError('Explicit user-recording import required')
    if not isinstance(spec.get('speaker'),str) or not spec['speaker'].strip() or not spec.get('clips'):
        raise ValueError('Named speaker and actual takes required')
    if output.exists():raise FileExistsError('Preserve existing recordings; use a new delivery directory')
    def bound(item):
        p = Path(item['path'])
        if not p.is_absolute():p=request_path.parent/p
        if sha256(p) != item['sha256']:raise ValueError('Supplied recording input changed: '+str(p))
        return p
    declaration = bound(spec['declaration']); prepared=[]; ids=set()
    if not declaration.read_text('utf-8-sig').strip():raise ValueError('Recording declaration is empty')
    for clip in spec['clips']:
        ident = clip['id']
        if not re.fullmatch(r'[A-Za-z0-9_-]+',ident) or ident in ids:raise ValueError('Safe unique take ID required')
        ids.add(ident)
        audio=bound(clip['audio']); transcript=bound(clip['transcript']); evidence=bound(clip['content_check'])
        if (clip['content_check'].get('status')!='MATCHED' or not transcript.read_text('utf-8-sig').strip()
                or not evidence.read_text('utf-8-sig').strip()):
            raise ValueError('Actual transcript comparison required before import')
        probe=json.loads(subprocess.check_output(['ffprobe','-v','error','-show_streams','-show_format','-of','json',str(audio)]))
        if not any(s['codec_type']=='audio' for s in probe['streams']):raise ValueError('Recording has no audio stream')
        prepared.append((ident,audio,transcript,evidence,probe,clip))
    output.mkdir(parents=True)
    shutil.copyfile(declaration,output/'recording-declaration.txt')
    if sha256(output/'recording-declaration.txt')!=spec['declaration']['sha256']:
        raise ValueError('Recording declaration changed during import')
    clips=[];sources=[]
    for ident,audio,transcript,evidence,probe,binding in prepared:
        raw=Path('originals')/(ident+audio.suffix); (output/raw).parent.mkdir(exist_ok=True)
        shutil.copyfile(audio,output/raw)
        txt=ident+'.txt';wav=ident+'.wav';proof=ident+'-content-check.txt'
        shutil.copyfile(transcript,output/txt);shutil.copyfile(evidence,output/proof)
        for key,dest in [('audio',raw),('transcript',txt),('content_check',proof)]:
            if sha256(output/dest)!=binding[key]['sha256']:
                raise ValueError('Recording input changed during import')
        subprocess.run(['ffmpeg','-v','error','-n','-i',str(output/raw),'-map','0:a:0','-vn',
                        '-ar','48000','-ac','1','-c:a','pcm_s16le',str(output/wav)],check=True)
        clips.append(describe_clip(output,ident,wav,txt))
        sources.append({'id':ident,'original_audio':{'path':raw.as_posix(),'sha256':sha256(output/raw)},
            'original_probe':probe,'transcript_sha256':sha256(output/txt),'derived_audio_sha256':sha256(output/wav),
            'content_check':{'path':proof,'sha256':sha256(output/proof),'status':'MATCHED'},
            'conversion':'PCM16 mono 48000 Hz; no trim, speed or time-stretch filter',
            'speaker_identity_verified_by_software':False})
    delivery={'schema':'voice-delivery/v1','clips':clips,'sources':sources,
        'recording_source':{'kind':'user_recording','speaker':spec['speaker'],
            'declaration':{'path':'recording-declaration.txt','sha256':sha256(output/'recording-declaration.txt')}}}
    target=output/'delivery.json';target.write_text(json.dumps(delivery,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    validate_user_recordings(target)
    return {'delivery':str(target),'complete_takes':len(clips),'listening_review':'PENDING'}


def pad_to_video_frame(source, destination, fps=24):
    """Keep every PCM sample and append at most one frame of tail silence.

    Some native clip-placement APIs floor duration to video frames. Do not
    shorten speech to satisfy that quantization or silently overwrite a take.
    """
    source, destination = Path(source).resolve(), Path(destination).resolve()
    if destination.exists():
        raise FileExistsError('Preserve existing takes; choose a new padded output')
    with wave.open(str(source), 'rb') as media:
        params = media.getparams(); frames = media.getnframes(); rate = media.getframerate()
        if type(fps) is not int or fps <= 0 or rate % fps or params.sampwidth != 2:
            raise ValueError('PCM16 and an integer samples-per-video-frame profile required')
        data = media.readframes(frames)
    added = (-frames) % (rate // fps)
    destination.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(destination), 'wb') as out:
        out.setparams(params); out.writeframes(data + b'\0'*(added*params.nchannels*params.sampwidth))
    return {'source_sha256': sha256(source), 'output_sha256': sha256(destination),
            'source_frames': frames, 'output_frames': frames+added, 'sample_rate': rate,
            'fps': fps, 'added_silent_samples': added, 'padding_seconds': added/rate,
            'speech_samples_changed': False, 'speech_tempo_changed': False}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('delivery', type=Path, nargs='?')
    parser.add_argument('--import-request',type=Path)
    parser.add_argument('--output',type=Path)
    args=parser.parse_args()
    if args.import_request:
        if not args.output or args.delivery:parser.error('Import needs --output and no positional delivery')
        print(json.dumps(import_user_recordings(args.import_request,args.output),ensure_ascii=False))
    else:
        if not args.delivery:parser.error('A delivery manifest is required')
        result=validate(args.delivery)
        print(f'PASS: {len(result["clips"])} clip(s)')
