"""Align an existing voice-delivery using the installed offline Whisper model.

Extracted from the private production diagnostic. Forced alignment supplies
caption timing, while independent unprompted ASR preserves audible-text doubts.
Neither procedure signs a human listening review.
"""
import argparse
from difflib import SequenceMatcher
import json
import os
from pathlib import Path
import re
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from scripts.voice_delivery import validate, asset, sha256
from video_contracts import write


def spans(text, maximum=25):
    result=[]; start=0
    for match in re.finditer(r'[，,。！？；：?;:](?:[”」])?', text):
        end=match.end()
        if end-start>maximum:
            while end-start>maximum:
                split=start+maximum
                while split>start+8 and text[split-1].isascii() and text[split].isascii() and text[split-1].isalnum() and text[split].isalnum(): split-=1
                result.append((start,split));start=split
        result.append((start,end));start=end
    if start<len(text):result.append((start,len(text)))
    return result


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('delivery',type=Path)
    p.add_argument('--model',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    args=p.parse_args();delivery=validate(args.delivery);binding=sha256(args.delivery)
    if args.output.exists():
        existing=json.loads(args.output.read_text('utf-8'))
        if existing['delivery_sha256']!=binding:raise ValueError('Existing alignment belongs to another delivery')
        print('Existing byte-bound alignment retained');return
    os.environ.update(HF_HUB_OFFLINE='1',TRANSFORMERS_OFFLINE='1',HF_DATASETS_OFFLINE='1',TOKENIZERS_PARALLELISM='false')
    from faster_whisper import WhisperModel
    from faster_whisper.audio import decode_audio,pad_or_trim
    from faster_whisper.tokenizer import Tokenizer
    from opencc import OpenCC
    cc=OpenCC('t2s')
    def norm(text):return re.sub(r'[^a-z0-9\u4e00-\u9fff]','',cc.convert(text).lower())
    model=WhisperModel(str(args.model),device='cpu',compute_type='int8',cpu_threads=4,local_files_only=True)
    tokenizer=Tokenizer(model.hf_tokenizer,model.model.is_multilingual,task='transcribe',language='zh')
    rows=[];details=args.output.parent/'voice-alignment-details';details.mkdir(exist_ok=True)
    for clip in delivery['clips']:
        cache=details/(clip['id']+'-'+clip['audio_sha256'][:12]+'.json')
        legacy=details/(clip['id']+'.json')
        if not cache.exists() and legacy.exists():
            previous=json.loads(legacy.read_text('utf-8'))
            if previous['audio_sha256']==clip['audio_sha256'] and previous['transcript_sha256']==clip['transcript_sha256']:
                rows.append(previous);continue
        if cache.exists():
            row=json.loads(cache.read_text('utf-8'))
            if row['audio_sha256']!=clip['audio_sha256'] or row['transcript_sha256']!=clip['transcript_sha256']:raise ValueError('Stale alignment detail')
            rows.append(row);continue
        wav=asset(args.delivery.parent,clip['audio']);text=asset(args.delivery.parent,clip['transcript']).read_text('utf-8-sig').strip()
        duration=clip['duration_seconds']
        if duration>29.5:raise ValueError('Split the authored take at a natural sentence boundary; alignment window exceeds 30 seconds: '+clip['id'])
        heard,_=model.transcribe(str(wav),language='zh',beam_size=5,temperature=0,initial_prompt=None,condition_on_previous_text=False,word_timestamps=True,vad_filter=False)
        recognized=''.join(s.text for s in heard)
        features=model.feature_extractor(decode_audio(str(wav),sampling_rate=model.feature_extractor.sampling_rate))
        words=model.find_alignment(tokenizer,[tokenizer.encode(text)],model.encode(pad_or_trim(features)),min(features.shape[-1]-1,model.feature_extractor.nb_max_frames))[0]
        if ''.join(w['word'] for w in words)!=text:raise ValueError('Alignment changed transcript')
        cursor=0
        for w in words:w['text_start']=cursor;cursor+=len(w['word']);w['text_end']=cursor
        cues=[]
        for lo,hi in spans(text):
            ws=[w for w in words if w['text_end']>lo and w['text_start']<hi and norm(w['word'])]
            if not ws:continue
            start=max(0,float(min(w['start'] for w in ws)));end=min(duration,float(max(w['end'] for w in ws)))
            if end<=start:
                write(details/(clip['id']+'-failed-'+clip['audio_sha256'][:12]+'.json'),{'transcript':text,'heard':recognized,'words':words,'empty_text':text[lo:hi]})
                raise ValueError('Nonpositive aligned speech span: '+clip['id'])
            value=text[lo:hi]
            cues.append({'text':value,'text_start':lo,'text_end':hi,'start':start,'end':end,
                         'display_lines':[value], 'timing_basis':'actual_audio_attention_alignment'})
        if ''.join(c['text'] for c in cues)!=text:raise ValueError('Caption coverage incomplete')
        row={'id':clip['id'],'audio_sha256':clip['audio_sha256'],'transcript_sha256':clip['transcript_sha256'],
             'transcript':text,'cues':cues,'duration_seconds':duration,'unprompted_asr':recognized,
             'normalized_similarity':SequenceMatcher(None,norm(text),norm(recognized),autojunk=False).ratio(),
             'human_listening_review':'PENDING','forced_alignment_is_not_pronunciation_verification':True}
        write(cache,row);rows.append(row)
        print(json.dumps({'clip':clip['id'],'similarity':round(row['normalized_similarity'],3),'heard':recognized},ensure_ascii=False),flush=True)
    if sha256(args.delivery)!=binding:raise ValueError('Delivery changed during alignment')
    write(args.output,{'delivery_sha256':binding,'model':str(args.model.resolve()),'network_used':False,'human_listening_review':'PENDING','clips':rows})


if __name__=='__main__':main()
