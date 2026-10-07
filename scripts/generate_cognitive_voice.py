"""One continuous take of frozen Hero copy using the accepted local reference."""
import argparse
import os
import subprocess
from pathlib import Path

from video_contracts import read,write,sha
from creative_os.hero import file_sha
from ae_production.cognitive_execution import validate_inputs
from .generate_anchored_passage_voice import reference_binding,measure


def main():
    parser=argparse.ArgumentParser();parser.add_argument('request');request=read(parser.parse_args().request)
    production=read(request['production']);spec=validate_inputs(production)
    units=read(production['excerpt'])['units'];text=' '.join(u['spoken_copy'] for u in units)
    reference_sha=reference_binding(request);out=Path(request['output']).resolve()
    if out.exists():raise ValueError('Preserve voice take history; choose a new output')
    out.mkdir(parents=True);write(out/'pending.json',dict(text_sha=sha(text),spec_sha=spec['spec_sha'],reference_sha=reference_sha))
    os.environ['HF_HUB_OFFLINE']='1';os.environ['OMP_NUM_THREADS']='8'
    import torch
    import soundfile as sf
    from qwen_tts import Qwen3TTSModel
    torch.set_num_threads(8);torch.set_num_interop_threads(2)
    print('Loading the accepted reference voice',flush=True)
    model=Qwen3TTSModel.from_pretrained(request['model'],device_map='cpu',dtype=torch.bfloat16,
        attn_implementation='sdpa',low_cpu_mem_usage=True)
    prompt=model.create_voice_clone_prompt(ref_audio=request['reference']['audio'],
        ref_text=request['reference']['text'],x_vector_only_mode=False)
    torch.manual_seed(request['settings']['seed'])
    settings={k:v for k,v in request['settings'].items() if k!='seed'}
    print('Generating one continuous frozen take',flush=True)
    waves,sr=model.generate_voice_clone(text=text,language='Chinese',voice_clone_prompt=prompt,**settings)
    sf.write(out/'raw.wav',waves[0],sr,subtype='PCM_16')
    m=measure(out/'raw.wav');gain=min(-20-float(m['input_i']),-2-float(m['input_tp']))
    dest=out/'COGNITIVE_VOICE.wav'
    subprocess.run(['ffmpeg','-v','error','-n','-i',str(out/'raw.wav'),'-af',f'volume={gain}dB',
        '-ar','48000','-ac','1','-c:a','pcm_s16le',str(dest)],check=True)
    validate_inputs(production)
    write(out/'receipt.json',dict(spec_sha=spec['spec_sha'],final_copy_sha=spec['copy_lock']['final_copy_sha'],
        reference_sha=reference_sha,path=str(dest),sha256=file_sha(dest),text=text,text_sha=sha(text),
        units=[dict(unit_id=u['unit_id'],spoken_copy=u['spoken_copy'],claim_refs=u['source_claim_refs']) for u in units],
        duration=len(waves[0])/sr,provider='local_qwen3_base_one_continuous_reference_conditioned_take',
        measurement=measure(dest),listening_review='PENDING',identity_guaranteed=False,public_render_ready=False))
    print('Continuous voice complete',round(len(waves[0])/sr,2),'seconds',flush=True)


if __name__=='__main__':main()
