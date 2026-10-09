"""Freeze supplied locating annotations and explicit review; no analysis or mutation."""
import argparse
from pathlib import Path
from video_contracts import read, write, now, sha
from video_contracts.locating_trace import freeze, trace_status


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for key in ('review', 'bundle', 'status', 'output'): p.add_argument(key)
    p.add_argument('--request', required=True, help='Existing bound upstream request, never generated here')
    a = p.parse_args(); out = Path(a.output)
    if out.exists(): raise ValueError('Fresh export directory required; preserve review history')
    packet=read(a.review); request=read(a.request)
    request_sha=sha({k:v for k,v in request.items() if k!='request_sha'})
    if (request.get('request_sha')!=request_sha or packet['review']['request_sha']!=request_sha
            or request['question_id']!=packet['binding']['question_id']
            or any(request['binding'][k]!=v for k,v in packet['binding'].items() if k!='question_id')):
        raise ValueError('Review must bind the existing source request')
    trace = freeze(packet, read(a.bundle), read(a.status), now())
    write(out/'trace.json', trace); write(out/'status.json', trace_status(trace, now()))
    print('Reviewed locating trace frozen; internal engineering only')


if __name__ == '__main__': main()
