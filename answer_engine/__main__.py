import argparse
import json
import sys
from pathlib import Path
from core.registry import Registry
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
    for name in ['analyze','paper','lesson']:
        sub = commands.add_parser(name); sub.add_argument('input')
        if name in {'analyze','lesson'}: sub.add_argument('--renderer',choices=['structured','student','legacy-wechat','content-export'],default='structured')
    sub=commands.add_parser('method'); sub.add_argument('method_id')
    sub=commands.add_parser('symptom'); sub.add_argument('question_type'); sub.add_argument('symptom')
    sub=commands.add_parser('evaluate'); sub.add_argument('input'); sub.add_argument('--plan')
    commands.add_parser('validate')
    args=parser.parse_args()
    r=Registry()
    if args.command=='validate':
        from scripts.generate_assets import generate
        result = r.validate(); result.update(generate(check=True))
    elif args.command=='method': result={'card':r.methods[args.method_id],'full_source':r.full(args.method_id)}
    elif args.command=='symptom': result=symptom_route(args.question_type,args.symptom,r)
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
