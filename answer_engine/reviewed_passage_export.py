"""Pure export of an explicitly authored ANSWER host lesson review; never analyzes."""
import argparse
from pathlib import Path
from video_contracts import read, write, now
from video_contracts.passage import export_bundle, status_manifest


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('review'); parser.add_argument('output')
    args=parser.parse_args(); out=Path(args.output)
    if out.exists(): raise ValueError('New export directory required')
    bundle=export_bundle(read(args.review),now())
    write(out/'bundle.json',bundle)
    write(out/'status.json',status_manifest(bundle,now()))
    print('Explicit host lesson exported; no solver or Registry mutation; internal use only')


if __name__=='__main__': main()
