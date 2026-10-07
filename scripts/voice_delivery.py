"""Engine-independent WAV/transcript handoff; no model runtime imports."""
import argparse
import hashlib
import json
from pathlib import Path
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
    parser.add_argument('delivery', type=Path)
    result = validate(parser.parse_args().delivery)
    print(f'PASS: {len(result["clips"])} clip(s)')
