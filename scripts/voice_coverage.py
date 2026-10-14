"""Observe actual placed WAV coverage; no audio edits or listening approval."""
import argparse
import json
from pathlib import Path
import wave

from student_pov.speech import narration_coverage


def inspect(path):
    path = Path(path)
    timeline = json.loads(path.read_bytes())
    intervals = []
    for clip in timeline['clips']:
        audio = path.parent / clip['audio']
        with wave.open(str(audio), 'rb') as stream:
            duration = stream.getnframes() / stream.getframerate()
        intervals.append([clip['start'], clip['start'] + duration])
    return narration_coverage(intervals, timeline['duration'],
                              exemptions=timeline.get('exemptions', []))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('timeline', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    result = inspect(args.timeline)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    print(result['review_status'])


if __name__ == '__main__': main()
