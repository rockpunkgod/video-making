"""Read-only free publication check; all inputs explicit, no auto publication."""
import argparse
from video_contracts import read, write
from content_os.showcase import decide, review_template


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('request')
    parser.add_argument('--statuses', nargs='+', required=True)
    parser.add_argument('--output', required=True)
    parser.add_argument('--review-template', choices=('teaching_claim', 'source_display', 'editorial', 'final_media'))
    args = parser.parse_args()
    request = read(args.request)
    statuses = {s['asset_id']: s for s in map(read, args.statuses)}
    result = (review_template(request, statuses, args.review_template)
              if args.review_template else decide(request, statuses))
    write(args.output, result)


if __name__ == '__main__':
    main()
