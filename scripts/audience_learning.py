"""Local JSON request CLI. No publication, host mutation or teaching writer."""
import argparse
import json
from pathlib import Path

from video_contracts import read
from creative_os.audience_engagement import design_engagement
from content_os.engagement_learning import (AudienceLearning, learning_template, initial_rubric,
    inspect_final_cut, bind_media_beats)


def execute(command, request, *, root=None, synthetic=False):
    def doc(key): return read(request[key])
    def sources(): return {k: read(v) for k,v in request['statuses'].items()}
    if command == 'template': return learning_template(request['episode_id'])
    if command == 'rubric': return initial_rubric()
    if command == 'design': return design_engagement(doc('episode'), sources(), doc('direction'))
    if command == 'inspect':
        return inspect_final_cut(doc('episode'),sources(),doc('copy'),doc('timeline'),request['assets'],request.get('media'))
    if command == 'map':
        return bind_media_beats(doc('plan'),doc('episode'),sources(),doc('direction'),request['media'],
            doc('sequence'),doc('settings'),doc('voices'),doc('ranges'),doc('credential'))
    loop = AudienceLearning(root, synthetic=synthetic)
    if command == 'freeze':
        return {'record_id':loop.freeze(request['spec'],doc('episode'),sources(),doc('copy'),doc('timeline'),
            inspection=doc('inspection') if request.get('inspection') else None)}
    if command == 'publish': return {'record_id':loop.publish(request['prediction_id'],request['publication'])}
    if command == 'performance': return {'record_id':loop.performance(request['publication_id'],request['observation'])}
    if command == 'csv': return {'record_id':loop.import_csv(request['publication_id'],request['csv'],request['metadata'])}
    if command == 'feedback': return {'record_id':loop.feedback(request['prediction_id'],request['feedback'])}
    if command == 'score': return {'record_id':loop.score(request['prediction_id'],request['review'],inspection=doc('inspection') if request.get('inspection') else None)}
    if command == 'retro': return {'record_id':loop.retrospective(request['performance_id'],request['judgements'])}
    if command == 'beat-retro':
        return {'record_id':loop.beat_retrospective(request['performance_id'],doc('mapping'),doc('plan'),doc('episode'),
            sources(),doc('direction'),doc('sequence'),doc('settings'),request['media'])}
    if command == 'propose': return {'record_id':loop.propose_rule(request['proposal'])}
    if command == 'activate': return {'record_id':loop.activate_rule(request['proposal_id'],request['review'])}
    if command == 'review-rule': return {'record_id':loop.record_rule_review(request['proposal_id'],request['review'])}
    if command == 'handoff': return {'director_candidates':loop.director_candidates()}
    if command == 'records': return {'records':loop.records()}
    raise ValueError('Unknown audience command')


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command',choices=['template','rubric','design','inspect','map','freeze','publish','performance','csv','feedback','score','retro','beat-retro','propose','review-rule','activate','handoff','records'])
    parser.add_argument('request'); parser.add_argument('--root',default='local-data/audience-learning')
    parser.add_argument('--synthetic',action='store_true');parser.add_argument('--output')
    args=parser.parse_args()
    # Refuse overwrite BEFORE performing any ledger operation.
    if args.output and Path(args.output).exists(): parser.error('Use a new output path; records are immutable')
    result=execute(args.command,read(args.request),root=args.root,synthetic=args.synthetic)
    encoded=json.dumps(result,ensure_ascii=False,indent=2,allow_nan=False)+'\n'
    if args.output:
        out=Path(args.output);out.parent.mkdir(parents=True,exist_ok=True)
        with out.open('x',encoding='utf-8') as stream: stream.write(encoded)
    else: print(encoded)


if __name__=='__main__': main()
