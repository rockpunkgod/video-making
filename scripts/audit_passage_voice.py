"""Local ASR diagnostic, never a substitute for listening or teaching review."""
import argparse
from pathlib import Path
import re
from difflib import SequenceMatcher
from video_contracts import read,write
from video_contracts.passage import require_current
from creative_os.hero import file_sha


def main():
    p=argparse.ArgumentParser();p.add_argument('request');args=p.parse_args();r=read(args.request)
    bundle=read(r['bundle']);require_current(bundle,read(r['status']))
    from faster_whisper import WhisperModel
    model=WhisperModel(r['asr_model'],device='cpu',compute_type='int8',cpu_threads=2)
    normalize=lambda s:re.sub(r'[^a-z0-9\u4e00-\u9fff]','',s.lower())
    for s in bundle['payload']['review']['segments']:
        folder=Path(r['voice_root'])/s['segment_id'];receipt=folder/'receipt.json';out=folder/'asr.json'
        if not receipt.exists():continue
        voice=read(receipt)
        if out.exists():
            if read(out)['audio_sha']!=voice['sha256']:raise ValueError('Stale ASR record')
            continue
        if file_sha(voice['path'])!=voice['sha256']:raise ValueError('Audio changed')
        segments,info=model.transcribe(voice['path'],language='zh',beam_size=5,
            word_timestamps=True,condition_on_previous_text=False)
        rows=[{'start':a.start,'end':a.end,'text':a.text,
               'words':[{'word':w.word,'start':w.start,'end':w.end} for w in (a.words or [])]} for a in segments]
        transcript=''.join(a['text'] for a in rows)
        ratio=SequenceMatcher(None,normalize(s['text']),normalize(transcript),autojunk=False).ratio()
        write(out,{'audio_sha':voice['sha256'],'rows':rows,'transcript':transcript,
            'text_similarity':ratio,'status':'DIAGNOSTIC_ONLY','independent_listening_review':False})
        print(s['segment_id'],round(ratio,3),transcript,flush=True)


if __name__=='__main__':main()
