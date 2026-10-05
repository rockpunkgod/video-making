"""Optional explicit online scratch transport; not Astra or final human recording."""
import argparse
import asyncio
from pathlib import Path
import shutil
import subprocess
from video_contracts import read, write, sha


async def generate(request):
    import edge_tts  # Optional extra. Frozen consumers do not import this dependency.
    delivery=read(request['delivery']);out=Path(request['output_dir']).resolve()
    if not shutil.which('ffmpeg'):raise ValueError('ffmpeg is required to decode mono PCM16 WAV')
    out.mkdir(parents=True,exist_ok=True);recordings={};boundaries={}
    for u in delivery['units']:
        mp3=out/(u['unit_id']+'.mp3');wav=out/(u['unit_id']+'.wav');events=[]
        if mp3.exists() or wav.exists():raise ValueError('Scratch files already exist; use a new revision directory')
        with mp3.open('wb') as f:
            async for event in edge_tts.Communicate(u['spoken_copy'],request['voice'],rate=request.get('rate','+0%'),
                    boundary='SentenceBoundary',proxy=request.get('proxy')).stream():
                if event['type']=='audio':f.write(event['data'])
                else:events.append(event)
        subprocess.run([shutil.which('ffmpeg'),'-v','error','-i',str(mp3),'-ar','22050','-ac','1','-c:a','pcm_s16le',str(wav)],check=True)
        metadata=out/(u['unit_id']+'-boundaries.json');write(metadata,events)
        recordings[u['unit_id']]=str(wav);boundaries[u['unit_id']]=str(metadata)
    result={'provider':'microsoft_edge_online_via_edge_tts','library_version':edge_tts.__version__,
            'voice':request['voice'],'rate':request.get('rate','+0%'),'usage':'INTERNAL_SCRATCH_VOICE',
            'delivery_copy_sha':delivery['delivery_copy_sha'],'delivery_sha':sha(delivery),'not_final_human_voice':True,
            'recordings':recordings,'sentence_boundaries':boundaries}
    write(out/'voice-provenance.json',result);return result


def main():
    parser=argparse.ArgumentParser();parser.add_argument('request');args=parser.parse_args()
    asyncio.run(generate(read(args.request)))


if __name__=='__main__':main()
