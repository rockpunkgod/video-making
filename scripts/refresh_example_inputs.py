"""Rebind editable interface examples; never alter private frozen observations."""
import json
from core.registry import ROOT,Registry
from scripts.plan_answer_alignment import RELOCATIONS

FILES=('question-action-course.json','question-lesson-course.json','passage-lesson.synthetic.json',
       'writing-image.synthetic.json','writing-review.synthetic.json','writing-word-count.synthetic.json')


def refresh():
    current=Registry(); old=Registry(snapshot_commit='b04ebc26d7fa096404111a0bb12f6c77cc8525b9')
    changes=[]
    def section_ids(sid):
        s=old.sources['sections'][sid]
        headings=RELOCATIONS.get(s['path'],{}).get(s['heading'],[s['heading']])
        result=[]
        for heading in headings:
            candidates=[key for key,row in current.sources['sections'].items()
                        if row['path']==s['path'] and row['heading']==heading]
            if len(candidates)!=1: raise ValueError('Example source binding is missing or ambiguous')
            result.extend(candidates)
        return result
    def visit(value):
        if isinstance(value,list): return [visit(x) for x in value]
        if not isinstance(value,dict): return value
        result={k:visit(v) for k,v in value.items()}
        if 'method_version' in result and 'method_id' in result:
            mid=result['method_id']
            if result['method_version'] not in {old.methods[mid]['version'],current.methods[mid]['version']}:
                raise ValueError('Unknown example method version')
            result['method_version']=current.methods[mid]['version']
        if 'source_section_ids' in result:
            result['source_section_ids']=list(dict.fromkeys(
                key for sid in result['source_section_ids'] for key in section_ids(sid)))
        return result
    for name in FILES:
        path=ROOT/'examples'/name; raw=path.read_text(encoding='utf-8')
        value=visit(json.loads(raw))
        text=json.dumps(value,ensure_ascii=False,indent=2)+'\n'
        if text!=raw: path.write_text(text,encoding='utf-8'); changes.append(name)
    return {'scope':'editable examples only; not new case/learner evidence','updated':changes}


if __name__=='__main__': print(json.dumps(refresh(),ensure_ascii=False))
