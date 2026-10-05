import argparse
import json
from pathlib import Path
import sys
from video_contracts import read, write, sha, now, validate
from .candidates import make_candidate
from .scoring import rate, rank
from .director import build_draft, finalize_copy, manifest
from .polisher import IdentityPolisher, polish
from .release import ae_contract, apply_reviews, validate_package
from .lifecycle import refresh_catalog


def run_pipeline(request, output):
    """Paths resolved by CLI loader; Python callers pass decoded contracts."""
    statuses = {s['asset_id']: s for s in request['statuses']}
    candidate = make_candidate(request['bundles'], request['selections'], statuses, request.get('content_scope', 'method_action_demo'))
    out = Path(output)
    if not candidate['engineering_pilot_eligible']:
        write(out / 'candidate.json', candidate)
        return {'engineering': 'BLOCKED', 'candidate': str(out / 'candidate.json')}
    candidate = rate(candidate, request['content_ratings'], request['feasibility_ratings'])
    candidate['pattern_id'] = request.get('pattern_id', 'P02')
    candidate['duration_target'] = request.get('duration_target', 60)
    draft = build_draft(candidate, statuses, candidate['pattern_id'], candidate['duration_target'])
    polished = polish(draft, IdentityPolisher())
    package = finalize_copy(polished)
    validate_package(package)
    files = {'candidate.json': candidate, 'rank.json': rank([candidate]), 'draft-package.json': draft,
             'video-package.json': package, 'manifest.json': manifest(package, candidate)}
    for name, value in files.items():
        write(out / name, value)
    return {'engineering': package['pilot_status']['engineering'], 'package': str(out / 'video-package.json'),
            'semantic_release': 'PENDING', 'source_release': 'PENDING', 'editorial_release': 'PENDING'}


def main():
    if hasattr(sys.stdout, 'reconfigure'): sys.stdout.reconfigure(encoding='utf-8')
    parser = argparse.ArgumentParser(description='Frozen-input Video Production OS')
    sub = parser.add_subparsers(dest='command', required=True)
    p = sub.add_parser('produce'); p.add_argument('request'); p.add_argument('--output', required=True)
    p = sub.add_parser('rank'); p.add_argument('candidates', nargs='+')
    p = sub.add_parser('refresh-upstream'); p.add_argument('catalog'); p.add_argument('--statuses', nargs='+', required=True); p.add_argument('--output', required=True)
    p = sub.add_parser('review'); p.add_argument('package'); p.add_argument('--statuses', nargs='+', required=True); p.add_argument('--source'); p.add_argument('--editorial'); p.add_argument('--output', required=True)
    p = sub.add_parser('handoff'); p.add_argument('package'); p.add_argument('--statuses', nargs='+', required=True); p.add_argument('--internal', action='store_true'); p.add_argument('--output', required=True)
    p = sub.add_parser('validate'); p.add_argument('package')
    p = sub.add_parser('teaching-issue'); p.add_argument('artifact_id'); p.add_argument('--reason', required=True); p.add_argument('--refs', nargs='+', required=True); p.add_argument('--output', required=True)
    args = parser.parse_args()
    if args.command == 'produce':
        path = Path(args.request); request = read(path)
        request['bundles'] = [read(path.parent / x) for x in request['bundles']]
        request['statuses'] = [read(path.parent / x) for x in request['statuses']]
        result = run_pipeline(request, args.output)
    elif args.command == 'rank':
        result = rank([read(x) for x in args.candidates])
    elif args.command == 'teaching-issue':
        from .issues import teaching_issue_candidate
        result = teaching_issue_candidate(args.artifact_id, args.reason, args.refs)
        write(args.output, result)
    elif args.command == 'validate':
        validate_package(read(args.package)); result = {'structural_validation': 'PASS', 'semantic_certification': 'not_asserted'}
    else:
        statuses = {s['asset_id']: s for s in [read(x) for x in args.statuses]}
        if args.command == 'refresh-upstream':
            result = refresh_catalog(read(args.catalog), statuses)
        elif args.command == 'review':
            original = read(args.package)
            old_manifest = read(Path(args.package).parent / original['manifest_ref'])
            validate('package-manifest', old_manifest)
            if old_manifest['package_sha'] != sha(original):
                raise ValueError('Manifest does not bind input package')
            result = apply_reviews(original, statuses, read(args.source) if args.source else None, read(args.editorial) if args.editorial else None)
            updated_manifest = {**old_manifest, 'generated_at': now(), 'package_sha': sha(result),
                                'final_copy_sha': result['copy_lock']['final_copy_sha']}
            write(Path(args.output).parent / result['manifest_ref'], updated_manifest)
        else:
            result = ae_contract(read(args.package), statuses, args.internal)
        write(args.output, result)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    try: main()
    except (ValueError, KeyError) as exc:
        print('Input rejected: ' + str(exc), file=sys.stderr); sys.exit(2)
