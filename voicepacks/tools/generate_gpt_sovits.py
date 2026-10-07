"""Optional producer. Video consumers only see its voice-delivery/v1 output."""
import argparse
import json
import math
import os
from pathlib import Path
import re
import sys

PROJECT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT))
from scripts.voice_delivery import asset, describe_clip, sha256, validate


def scripts_from(text_file=None, clips_file=None):
    if (text_file is None) == (clips_file is None):
        raise ValueError('Provide one transcript or one explicit clip list')
    rows = ([{'id': 'narration', 'text': Path(text_file).read_text(encoding='utf-8-sig').strip()}]
            if text_file is not None else json.loads(Path(clips_file).read_text(encoding='utf-8-sig')))
    seen = set()
    if not isinstance(rows, list) or not rows:
        raise ValueError('Expected a nonempty explicit clip list')
    for row in rows:
        if (not isinstance(row, dict) or set(row) != {'id', 'text'} or not isinstance(row['id'], str)
                or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.-]*', row['id'])
                or row['id'] in seen or not isinstance(row['text'], str) or not row['text'].strip()):
            raise ValueError('Clip IDs must be safe and unique, with nonempty text')
        seen.add(row['id'])
    return rows


def inference_request(profile, text, reference, prompt):
    settings = profile['settings']
    controls = {}
    for name, legacy, default in (('text_split_method', 'split_method', 'cut0'),
                                  ('fragment_interval', 'fragment_interval', 0.1)):
        if name in profile and legacy in settings and profile[name] != settings[legacy]:
            raise ValueError(f'Conflicting voice Profile control: {name}')
        controls[name] = profile.get(name, settings.get(legacy, default))
    if not isinstance(controls['text_split_method'], str) or not controls['text_split_method']:
        raise ValueError('Voice Profile text_split_method must be explicit nonempty text')
    gap = controls['fragment_interval']
    if type(gap) not in (int, float) or not math.isfinite(gap) or gap < 0:
        raise ValueError('Voice Profile fragment_interval must be finite and nonnegative')
    return dict(text=text, text_lang='zh', ref_audio_path=str(reference), prompt_text=prompt,
        prompt_lang='en' if profile.get('reference_language') == 'EN' else 'all_zh',
        **controls, batch_size=1, parallel_infer=True,
        **{key: settings[key] for key in ('seed', 'speed_factor', 'top_k', 'top_p',
                                         'temperature', 'repetition_penalty')})


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--pack', type=Path, required=True)
    parser.add_argument('--runtime', type=Path, required=True)
    scripts = parser.add_mutually_exclusive_group(required=True)
    scripts.add_argument('--text-file', type=Path)
    scripts.add_argument('--clips-file', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--cpu', action='store_true')
    args = parser.parse_args()
    pack, runtime, output = args.pack.resolve(), args.runtime.resolve(), args.output.resolve()
    rows = scripts_from(args.text_file, args.clips_file)
    input_path = (args.text_file or args.clips_file).resolve(); input_sha = sha256(input_path)
    if output.exists():
        raise FileExistsError('Choose a new output directory; existing takes are never overwritten')
    profile_file = pack / 'profile.json'
    profile_sha = sha256(profile_file)
    profile = json.loads(profile_file.read_text(encoding='utf-8'))
    if profile['engine'] != 'gpt-sovits/v2ProPlus':
        raise ValueError('This optional producer requires gpt-sovits/v2ProPlus')
    for relative, expected in profile['assets_sha256'].items():
        if sha256(asset(pack, relative)) != expected:
            raise ValueError(f'Voice-pack asset mismatch: {relative}; run git lfs pull if needed')
    if not (runtime / 'GPT_SoVITS').is_dir():
        raise ValueError('Expected a separate GPT-SoVITS runtime checkout')
    prompt = asset(pack, profile['reference_text']).read_text(encoding='utf-8-sig').strip()
    # Validate the effective controls before loading model weights. New packs
    # store split/fragment controls at the Profile root; older packs use settings.
    effective = inference_request(profile, rows[0]['text'], asset(pack, profile['reference']), prompt)
    # Resolve inputs before the runtime changes the working directory.
    os.chdir(runtime)
    sys.path[:0] = [str(runtime), str(runtime / 'GPT_SoVITS')]
    os.environ.update(HF_HUB_OFFLINE='1', HF_HUB_DISABLE_TELEMETRY='1',
                      version='v2ProPlus', language='zh_CN', is_g2pw='False')
    import numpy as np
    import soundfile as sf
    import torch
    from TTS_infer_pack.TTS import TTS, TTS_Config
    torch.set_num_threads(6)
    config = TTS_Config({'custom': dict(
        device='cpu' if args.cpu else 'cuda', is_half=not args.cpu, version='v2ProPlus',
        t2s_weights_path=str(asset(pack, profile['gpt'])),
        vits_weights_path=str(asset(pack, profile['sovits'])),
        bert_base_path=str(runtime / 'GPT_SoVITS/pretrained_models/chinese-roberta-wwm-ext-large'),
        cnhuhbert_base_path=str(runtime / 'GPT_SoVITS/pretrained_models/chinese-hubert-base'))})
    output.mkdir(parents=True, exist_ok=False)
    config.configs_path = str(output / 'inference_config.yaml')
    tts = TTS(config)
    clips, takes = [], []
    for row in rows:
        request = inference_request(profile, row['text'], asset(pack, profile['reference']), prompt)
        print('Generating bound clip: ' + row['id'], flush=True)
        chunks, rates = [], set()
        for rate, chunk in tts.run(request):
            rates.add(rate); chunk = np.asarray(chunk)
            scale = 32768.0 if chunk.dtype == np.int16 else 1.0
            chunks.append(chunk.astype(np.float32) / scale)
        if not chunks or len(rates) != 1:
            raise ValueError('Missing audio or inconsistent sample rates')
        audio = np.concatenate(chunks); peak = float(np.max(np.abs(audio)))
        if not np.isfinite(audio).all() or peak <= 0:
            raise ValueError('Invalid synthesized audio')
        # New training packs request no postprocessing except peak attenuation.
        # Preserve that policy; earlier packs retain their existing -3 dB target.
        gain = (min(1.0, 0.89 / peak) if profile.get('postprocessing', '').startswith('none;')
                else 10 ** (-3 / 20) / peak)
        audio *= gain; rate = rates.pop()
        name = row['id']; sf.write(output / (name + '.wav'), audio, rate, subtype='PCM_16')
        (output / (name + '.txt')).write_text(row['text'], encoding='utf-8')
        clips.append(describe_clip(output, name, name + '.wav', name + '.txt'))
        takes.append(dict(id=name, duration_seconds=len(audio)/rate, raw_peak=peak, applied_gain=gain))
    for relative, expected in profile['assets_sha256'].items():
        if sha256(asset(pack, relative)) != expected:
            raise ValueError('Voice-pack changed during generation')
    if sha256(input_path) != input_sha or sha256(profile_file) != profile_sha:
        raise ValueError('Input transcript changed during generation')
    delivery = dict(schema='voice-delivery/v1', clips=clips)
    (output / 'delivery.json').write_text(json.dumps(delivery, ensure_ascii=False, indent=2), encoding='utf-8')
    # Provider details stay in a separate receipt, outside the consumer contract.
    receipt = dict(engine=profile['engine'], profile_id=profile.get('profile_id'), profile_sha256=profile_sha,
                   assets_sha256=profile['assets_sha256'], settings=profile['settings'],
                   inference_parameters={k: v for k, v in effective.items()
                                         if k not in ('text', 'ref_audio_path', 'prompt_text')},
                   text_language='zh_mixed_with_english', input_sha256=input_sha,
                   takes=takes, torch_version=torch.__version__, device=str(config.device),
                   listening_review='PENDING', public_render_ready=False)
    (output / 'generation.json').write_text(json.dumps(receipt, ensure_ascii=False, indent=2), encoding='utf-8')
    validate(output / 'delivery.json')
    print(f'SAVED: {output / "delivery.json"}')


if __name__ == '__main__':
    main()
