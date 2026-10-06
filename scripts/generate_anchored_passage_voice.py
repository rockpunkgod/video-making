"""Reuse ONE accepted reference prompt for all frozen narration segments.

Requires a local Qwen Base checkpoint. Speaker similarity is diagnostic only;
reference conditioning does not constitute a guarantee of perceived identity.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
from video_contracts import read,write,sha
from video_contracts.passage import require_current
from creative_os.hero import file_sha


def reference_binding(request):
    reference=request['reference']
    if file_sha(reference['audio'])!=reference['audio_sha'] or not reference['text'].strip():
        raise ValueError('Accepted voice reference changed or lacks transcript')
    config=read(Path(request['model'])/'config.json')
    if config.get('tts_model_type')!='base':raise ValueError('Reference conditioning requires the Base model')
    return sha({'audio_sha':reference['audio_sha'],'text':reference['text'],
                'model_sha':file_sha(Path(request['model'])/'model.safetensors'),
                'settings':request['settings']})


def measure(path):
    r=subprocess.run(['ffmpeg','-hide_banner','-i',str(path),'-vn','-af',
        'loudnorm=I=-21.4:TP=-2:LRA=7:print_format=json','-f','null','-'],
        capture_output=True,text=True,encoding='utf-8',errors='replace',check=True)
    return json.loads(re.search(r'\{\s*"input_i".*?\}',r.stderr,re.S).group())


def main():
    parser=argparse.ArgumentParser();parser.add_argument('request');args=parser.parse_args()
    request=read(args.request);bundle=read(request['bundle']);require_current(bundle,read(request['status']))
    bound_reference=reference_binding(request);out=Path(request['output']);out.mkdir(parents=True,exist_ok=True)
    os.environ['HF_HUB_OFFLINE']='1';os.environ['OMP_NUM_THREADS']='8'
    import torch
    import soundfile as sf
    import librosa
    from qwen_tts import Qwen3TTSModel
    torch.set_num_threads(8);torch.set_num_interop_threads(2)
    print('Loading local reference-conditioned Base model',flush=True)
    model=Qwen3TTSModel.from_pretrained(request['model'],device_map='cpu',dtype=torch.bfloat16,
        attn_implementation='sdpa',low_cpu_mem_usage=True)
    reference=request['reference'];prompt=model.create_voice_clone_prompt(ref_audio=reference['audio'],
        ref_text=reference['text'],x_vector_only_mode=False)
    prompt_sha=hashlib.sha256(prompt[0].ref_spk_embedding.float().cpu().numpy().tobytes()+
        prompt[0].ref_code.cpu().numpy().tobytes()).hexdigest()
    write(out/'reference-binding.json',{'reference_sha':bound_reference,'prompt_sha':prompt_sha,
        'reference_audio_sha':reference['audio_sha'],'reference_text_sha':sha(reference['text']),
        'conditioning':'same_reference_audio_text_codes_and_speaker_embedding','identity_guaranteed':False})
    def embedding(wave,sr):
        wave=librosa.resample(wave,orig_sr=sr,target_sr=model.model.speaker_encoder_sample_rate)
        with torch.inference_mode():return model.model.extract_speaker_embedding(wave,model.model.speaker_encoder_sample_rate)
    for segment in bundle['payload']['review']['segments']:
        require_current(bundle,read(request['status']))
        sid=segment['segment_id'];folder=out/sid;receipt=folder/'receipt.json'
        binding=sha({'bundle':bundle['semantic_binding_sha'],'segment':segment,'reference_sha':bound_reference,'prompt_sha':prompt_sha})
        if receipt.exists():
            previous=read(receipt)
            if previous['input_sha']!=binding or file_sha(previous['path'])!=previous['sha256']:
                raise ValueError('Stale anchored narration')
            continue
        if folder.exists():raise ValueError('Uncertain segment; inspect before rerunning')
        folder.mkdir();write(folder/'pending.json',{'input_sha':binding,'text':segment['text']})
        torch.manual_seed(request['settings']['seed'])
        print('Generating anchored',sid,flush=True)
        settings={k:v for k,v in request['settings'].items() if k!='seed'}
        waves,sr=model.generate_voice_clone(text=segment['text'],language='Chinese',voice_clone_prompt=prompt,**settings)
        sf.write(folder/'raw.wav',waves[0],sr,subtype='PCM_16')
        m=measure(folder/'raw.wav');gain=min(-21.4-float(m['input_i']),-2.2-float(m['input_tp']))
        dest=(folder/'voice.wav').resolve()
        subprocess.run(['ffmpeg','-v','error','-n','-i',str(folder/'raw.wav'),'-af',f'volume={gain}dB',
            '-ar','48000','-ac','1','-c:a','pcm_s16le',str(dest)],check=True)
        emb=embedding(waves[0],sr).float().reshape(1,-1)
        ref=prompt[0].ref_spk_embedding.float().reshape(1,-1)
        similarity=float(torch.nn.functional.cosine_similarity(emb,ref).item())
        old_similarity=None
        if request.get('previous_voice_root'):
            old=read(Path(request['previous_voice_root'])/sid/'receipt.json')
            data,rate=sf.read(old['path'],dtype='float32');old_emb=embedding(data,rate).float().reshape(1,-1)
            old_similarity=float(torch.nn.functional.cosine_similarity(old_emb,ref).item())
        write(receipt,{'input_sha':binding,'lesson_binding_sha':bundle['semantic_binding_sha'],
            'reference_sha':bound_reference,'prompt_sha':prompt_sha,'path':str(dest),'sha256':file_sha(dest),
            'text':segment['text'],'duration':len(waves[0])/sr,'measurement':measure(dest),
            'provider':'local_qwen3_base_reference_conditioned','reference_profile':reference['profile'],
            'speaker_similarity_diagnostic':similarity,'previous_similarity_diagnostic':old_similarity,
            'identity_guaranteed':False,'listening_review':'PENDING','public_render_ready':False})
        print('Complete',sid,round(len(waves[0])/sr,2),'reference cosine',round(similarity,3),'previous',round(old_similarity,3) if old_similarity else None,flush=True)


if __name__=='__main__':main()
