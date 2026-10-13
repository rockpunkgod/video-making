import argparse
import json
import sys
from pathlib import Path
from core.registry import Registry,validate_schema
from core.analyzer import QuestionAnalyzer, PaperAnalyzer
from core.matcher import symptom_route
from renderers import render
from evaluation.harness import evaluate,load_records
from core.passage_lesson import PassageLessonAnalyzer
from renderers.passage import render_passage

def main():
    if hasattr(sys.stdout,'reconfigure'): sys.stdout.reconfigure(encoding='utf-8')
    parser = argparse.ArgumentParser(description='Evidence-grounded Gaokao Method Engine')
    commands = parser.add_subparsers(dest='command',required=True)
    for name in ('export-asset', 'export-status', 'export-current-status', 'export-method-application'):
        sub = commands.add_parser(name); sub.add_argument('input')
    for name in ['analyze','paper','lesson']:
        sub = commands.add_parser(name); sub.add_argument('input')
        if name in {'analyze','lesson'}: sub.add_argument('--renderer',choices=['structured','student','legacy-wechat','content-export'],default='structured')
    sub=commands.add_parser('method'); sub.add_argument('method_id')
    sub=commands.add_parser('course-identity'); sub.add_argument('source_heading')
    sub=commands.add_parser('symptom'); sub.add_argument('question_type'); sub.add_argument('symptom')
    sub.add_argument('--renderer',choices=['structured','student'],default='structured')
    sub=commands.add_parser('evaluate'); sub.add_argument('input'); sub.add_argument('--plan')
    sub=commands.add_parser('release-check'); sub.add_argument('input')
    sub=commands.add_parser('release-bindings'); sub.add_argument('input')
    commands.add_parser('validate')
    sub=commands.add_parser('case-coverage'); sub.add_argument('--private-catalog')
    sub=commands.add_parser('register-real-case'); sub.add_argument('request'); sub.add_argument('--dataset',required=True)
    args=parser.parse_args()
    if args.command == 'export-method-application':
        from answer_engine.method_application_export import FrozenMethodApplicationExporter
        from video_contracts import read
        result = FrozenMethodApplicationExporter().export_request(read(args.input))
        print(json.dumps(result, ensure_ascii=False, indent=2)); return
    if args.command in ('export-asset', 'export-status', 'export-current-status'):
        from answer_engine.frozen_export import FrozenAssetExporter, load_request
        exporter = FrozenAssetExporter()
        request = load_request(args.input)
        result = (exporter.export(request) if args.command == 'export-asset'
                  else exporter.status_current_epoch(request) if args.command=='export-current-status'
                  else exporter.status(request))
        print(json.dumps(result, ensure_ascii=False, indent=2)); return
    if args.command=='register-real-case':
        from core.real_cases import register
        print(json.dumps(register(args.dataset,args.request),ensure_ascii=False,indent=2)); return
    r=Registry()
    if args.command=='validate':
        from scripts.generate_assets import generate
        result = r.validate(); result.update(generate(check=True))
    elif args.command=='case-coverage': result=r.case_coverage(args.private_catalog)
    elif args.command in {'release-check','release-bindings'}:
        from core.release import read_json,check_release,release_bindings
        r.validate(); review=read_json(args.input); validate_schema('method-release',review)
        result=check_release(r,review) if args.command=='release-check' else release_bindings(r,review['method_id'],review['inputs'])
    elif args.command=='method': result={'card':r.methods[args.method_id],'full_source':r.full(args.method_id)}
    elif args.command=='course-identity': result=r.course_identity(args.source_heading)
    elif args.command=='symptom':
        if args.renderer=='student':
            from renderers.symptom import render_symptom
            print(render_symptom(args.question_type,args.symptom,r)); return
        result=symptom_route(args.question_type,args.symptom,r)
    elif args.command=='evaluate': result=evaluate(load_records(args.input),json.loads(Path(args.plan).read_text(encoding='utf-8')) if args.plan else None)
    else:
        value=json.loads(Path(args.input).read_text(encoding='utf-8-sig'))
        if args.command=='lesson':
            print(render_passage(PassageLessonAnalyzer(QuestionAnalyzer(r)).analyze(value),args.renderer,r)); return
        elif args.command=='paper': result=PaperAnalyzer(QuestionAnalyzer(r)).analyze(value)
        else:
            print(render(QuestionAnalyzer(r).analyze(value),args.renderer,r)); return
    print(json.dumps(result,ensure_ascii=False,indent=2))

if __name__=='__main__':
    try: main()
    except (ValueError,KeyError) as exc:
        print('Input rejected: '+str(exc),file=sys.stderr); sys.exit(2)
