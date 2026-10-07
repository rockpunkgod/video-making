"""Optional producer. Video consumers only see its voice-delivery/v1 output."""
import argparse
import json
import os
from pathlib import Path
import sys

PROJECT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT))
from scripts.voice_delivery import asset, describe_clip, sha256, validate


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--pack', type=Path, required=True)
    parser.add_argument('--runtime', type=Path, required=True)
    parser.add_argument('--text-file', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--cpu', action='store_true')
    args = parser.parse_args()
    pack, runtime, output = args.pack.resolve(), args.runtime.resolve(), args.output.resolve()
    text = args.text_file.read_text(encoding='utf-8-sig').strip()
    if not text:
        raise ValueError('Script is empty')
    if output.exists():
        raise FileExistsError('Choose a new output directory; existing takes are never overwritten')
    profile_file = pack / 'profile.json'
    profile = json.loads(profile_file.read_text(encoding='utf-8'))
    if profile['engine'] != 'gpt-sovits/v2ProPlus':
        raise ValueError('This optional producer requires gpt-sovits/v2ProPlus')
    for relative, expected in profile['assets_sha256'].items():
        if sha256(asset(pack, relative)) != expected:
            raise ValueError(f'Voice-pack asset mismatch: {relative}; run git lfs pull if needed')
    if not (runtime / 'GPT_SoVITS').is_dir():
        raise ValueError('Expected a separate GPT-SoVITS runtime checkout')
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
    settings = profile['settings']
    request = dict(text=text, text_lang='zh', ref_audio_path=str(asset(pack, profile['reference'])),
                   prompt_text=asset(pack, profile['reference_text']).read_text(encoding='utf-8-sig').strip(),
                   prompt_lang='all_zh', text_split_method=settings['split_method'], batch_size=1,
                   parallel_infer=True, **{key: settings[key] for key in (
                       'seed', 'speed_factor', 'fragment_interval', 'top_k', 'top_p',
                       'temperature', 'repetition_penalty')})
    chunks, rates = [], set()
    for rate, chunk in tts.run(request):
        rates.add(rate)
        chunks.append(np.asarray(chunk, dtype=np.float32))
    if not chunks or len(rates) != 1:
        raise ValueError('Missing audio or inconsistent sample rates')
    audio = np.concatenate(chunks)
    peak = float(np.max(np.abs(audio)))
    if not np.isfinite(audio).all() or peak <= 0:
        raise ValueError('Invalid synthesized audio')
    audio *= 10 ** (-3 / 20) / peak
    sf.write(output / 'narration.wav', audio, rates.pop(), subtype='PCM_16')
    (output / 'narration.txt').write_text(text, encoding='utf-8')
    delivery = dict(schema='voice-delivery/v1', clips=[describe_clip(
        output, 'narration', 'narration.wav', 'narration.txt')])
    (output / 'delivery.json').write_text(json.dumps(delivery, ensure_ascii=False, indent=2), encoding='utf-8')
    # Provider details stay in a separate receipt, outside the consumer contract.
    receipt = dict(engine=profile['engine'], profile_sha256=sha256(profile_file),
                   assets_sha256=profile['assets_sha256'], settings=settings,
                   torch_version=torch.__version__, device=str(config.device))
    (output / 'generation.json').write_text(json.dumps(receipt, ensure_ascii=False, indent=2), encoding='utf-8')
    validate(output / 'delivery.json')
    print(f'SAVED: {output / "narration.wav"}')


if __name__ == '__main__':
    main()
