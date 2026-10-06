"""Local accepted VoiceDesign profile, serial chunks, explicit frozen lesson only."""
import argparse
import json
import os
from pathlib import Path
import re
import subprocess
from video_contracts import read, write, sha
from video_contracts.passage import require_current
from creative_os.hero import file_sha


def main():
    p=argparse.ArgumentParser();p.add_argument('request');args=p.parse_args()
    request=read(args.request);bundle=read(request['bundle'])
    require_current(bundle,read(request['status']))
    profile=read(request['profile']);model_root=Path(request['model']);out=Path(request['output'])
    out.mkdir(parents=True,exist_ok=True)
    os.environ['HF_HUB_OFFLINE']='1';os.environ['OMP_NUM_THREADS']='8'
    import torch
    import soundfile as sf
    torch.set_num_threads(8);torch.set_num_interop_threads(2)
    from qwen_tts import Qwen3TTSModel
    print('Loading accepted local VoiceDesign model',flush=True)
    device=request.get('device','cpu')
    options={'max_memory':{0:request['gpu_budget'],'cpu':'8GiB'}} if device=='auto' else {}
    model=Qwen3TTSModel.from_pretrained(str(model_root),device_map=device,dtype=torch.bfloat16,
        attn_implementation='sdpa',low_cpu_mem_usage=True,**options)
    for s in bundle['payload']['review']['segments']:
        require_current(bundle,read(request['status']))
        sid=s['segment_id'];folder=out/sid;receipt=folder/'receipt.json'
        binding=sha({'bundle':bundle['semantic_binding_sha'],'segment':s,'profile':profile})
        if receipt.exists():
            prior=read(receipt)
            if prior['input_sha']!=binding or file_sha(prior['path'])!=prior['sha256']:
                raise ValueError('Existing voice is stale')
            continue
        if folder.exists(): raise ValueError('Uncertain voice chunk exists; inspect before retry')
        folder.mkdir();write(folder/'pending.json',{'input_sha':binding,'profile':profile,'text':s['text']})
        torch.manual_seed(profile['seed'])
        print('Generating',sid,flush=True)
        waves,sr=model.generate_voice_design(text=s['text'],language=profile['language'],
            instruct=profile['instruction'],max_new_tokens=4096,temperature=.85,top_p=.95)
        raw=folder/'raw.wav';sf.write(raw,waves[0],sr,subtype='PCM_16')
        def measure(path):
            r=subprocess.run(['ffmpeg','-hide_banner','-i',str(path),'-af',
              'loudnorm=I=-21.4:TP=-2:LRA=7:print_format=json','-f','null','-'],
              capture_output=True,text=True,encoding='utf-8',errors='replace',check=True)
            return json.loads(re.search(r'\{\s*"input_i".*?\}',r.stderr,re.S).group())
        m=measure(raw);gain=min(-21.4-float(m['input_i']),-2.2-float(m['input_tp']))
        dest=(folder/'voice.wav').resolve()
        subprocess.run(['ffmpeg','-v','error','-n','-i',str(raw),'-af',f'volume={gain}dB',
            '-ar','48000','-ac','1','-c:a','pcm_s16le',str(dest)],check=True)
        write(receipt,{'input_sha':binding,'profile_sha':sha(profile),'path':str(dest),
            'lesson_binding_sha':bundle['semantic_binding_sha'],
            'sha256':file_sha(dest),'raw_sha256':file_sha(raw),'text':s['text'],
            'duration':len(waves[0])/sr,'measurement':measure(dest),
            'provider':'local_qwen3_voice_design','identity_locked':False,'device':device,'torch_version':torch.__version__,
            'listening_review':'PENDING','public_render_ready':False})
        print('Complete',sid,round(len(waves[0])/sr,2),flush=True)


if __name__=='__main__':main()
