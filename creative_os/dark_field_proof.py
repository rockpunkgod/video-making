"""Prepare a bounded native AE light/lift proof from the existing frozen pipeline."""
import argparse
import json
from pathlib import Path
from .continuous_question import prepare
from .episode_build import ROOT
from video_contracts import read, write, sha


def contrast(a,b):
    def luminance(h):
        rgb=[int(h[i:i+2],16)/255 for i in (1,3,5)]
        return sum(w*(c/12.92 if c<=.04045 else ((c+.055)/1.055)**2.4)
                   for w,c in zip((.2126,.7152,.0722),rgb))
    x,y=sorted((luminance(a),luminance(b)))
    return (y+.05)/(x+.05)


def main():
    cli=argparse.ArgumentParser(description=__doc__)
    cli.add_argument('request',type=Path);cli.add_argument('direction',type=Path)
    cli.add_argument('output',type=Path);cli.add_argument('--prototype',action='store_true')
    args=cli.parse_args();plan=prepare(read(args.request),read(args.direction))
    if contrast('#F2F0EA','#17181A')<15:raise ValueError('Paper/ink contrast below 15:1')
    # Consume the three existing reviewed projections; this is not a new analysis.
    phrase=plan['projections'][2]
    if phrase['text']!='bring gifts':raise ValueError('This proof requires the selected existing phrase')
    plan['proof']={'version':'0.1','duration':20,'mode':'prototype' if args.prototype else 'library',
                   'contrast':contrast('#F2F0EA','#17181A'),'source_plan_sha':sha(plan),
                   'scope':'light_and_origin_motion_test_not_complete_solution'}
    out=args.output.resolve();out.mkdir(parents=True,exist_ok=False)
    write(out/'PLAN.json',plan)
    grammar=(ROOT/'ae/lib/grammar.jsx').read_text(encoding='utf-8')
    library=(ROOT/'ae/lib/dark-field.jsx').read_text(encoding='utf-8')
    template=(ROOT/'ae/templates/dark-field-proof.jsx').read_text(encoding='utf-8')
    if args.prototype:
        # Direct authored keyframes, before reusable function invocation. Keep
        # the exact same tracks for the later frame/property equality check.
        begin=library.index('    SG_keys(background')
        end=library.index('\n}\nfunction lift_phrase')
        template=template.replace('transition_to_dark_field(bgColor,originals,world,field);',
            '(function(){var background=bgColor,config=field;\n'+library[begin:end]+'\n})();')
        begin=library.index('    SG_locate(highlight')
        body=library[begin:library.rindex('\n}')]
        template=template.replace('lift_phrase(nodes,highlight,cfg)',
            '(function(){var originals=nodes,config=cfg;\n'+body+'\n})()')
        library=''
    data={'output':out.as_posix(),'plan':plan}
    (out/'build.jsx').write_text('var DF_INPUT='+json.dumps(data,ensure_ascii=True)+';\n'+grammar+'\n'+library+'\n'+template,encoding='utf-8')
    audit=(ROOT/'ae/templates/dark-field-audit.jsx').read_text(encoding='utf-8')
    (out/'audit.jsx').write_text('var DF_OUTPUT='+json.dumps(out.as_posix(),ensure_ascii=True)+';\n'+grammar+'\n'+audit,encoding='utf-8')
    print(json.dumps({'output':str(out),'contrast':plan['proof']['contrast']},ensure_ascii=True))


if __name__=='__main__':main()
