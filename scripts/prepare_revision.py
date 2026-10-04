"""Prepare source-bound card revisions as apply_patch text; never write files.

Authoring input is temporary editorial data, not a second runtime registry.
Existing sources, roles and maturity remain immutable in this operation.
"""
import argparse
import json
from pathlib import Path
import sys
import yaml
from core.registry import ROOT

FIELDS={'judge','stop','wrong','anti','counter','visual','challenge','ten','thirty','benefit','transfer'}

def patch(path, old, new):
    target=(ROOT/path).as_posix()
    if old is None:
        return '*** Begin Patch\n*** Add File: '+target+'\n'+''.join('+'+line+'\n' for line in new.splitlines())+'*** End Patch'
    return '*** Begin Patch\n*** Update File: '+target+'\n@@\n'+''.join('-'+line+'\n' for line in old.splitlines())+''.join('+'+line+'\n' for line in new.splitlines())+'*** End Patch'

def prepare(module, updates):
    if module not in {'reading','seven-five','cloze','grammar','application-writing','continuation-writing'}:
        raise ValueError('Unsupported module')
    path='method-registry/'+module+'.yaml'
    old=(ROOT/path).read_text(encoding='utf-8'); data=yaml.safe_load(old)
    idxpath='method-registry/registry.yaml'; idxold=(ROOT/idxpath).read_text(encoding='utf-8'); index=yaml.safe_load(idxold)
    known={m['method_id'] for m in data['methods']}
    if not updates or not set(updates)<=known: raise ValueError('Unknown or empty revision IDs')
    patches=[]
    for m in data['methods']:
        mid=m['method_id']
        if mid not in updates: continue
        u=updates[mid]
        if set(u)!=FIELDS or any(not isinstance(v,str) or not v.strip() for v in u.values()):
            raise ValueError('Incomplete editorial fields: '+mid)
        if m['version']!='1.0.0': raise ValueError('Unexpected prior version: '+mid)
        history='method-registry/history/'+mid+'/1.0.0.yaml'
        if (ROOT/history).exists(): raise ValueError('Snapshot already exists: '+mid)
        patches.append(patch(history,None,yaml.safe_dump(m,allow_unicode=True,sort_keys=False)))
        m['version']='1.1.0'; index['methods'][mid]['version']='1.1.0'
        m.update(decision_rule=u['judge'],stop_rule=u['stop'],common_wrong_instinct=u['wrong'],anti_rule=u['anti'],counterexamples=[u['counter']],failure_cases=[u['wrong'],u['stop']],visual_formula=u['visual'],challenge_prompt=u['challenge'],transfer_pattern=u['transfer'])
        m['verification']=m['core_action']+'。'+u['judge']+' '+u['stop']
        m['four_step_card']={'start':m['trigger_cues'][0],'first_cut':m['core_action'],'judge':u['judge'],'stop':u['stop']}
        m['compact']={'10s':u['ten'],'30s':u['thirty'],'90s':m['student_symptoms'][0]+'时，先确认：'+m['trigger_cues'][0]+'。第一刀：'+m['core_action']+'。产物 '+m['output_type']+'：'+u['judge']+' 停止：'+u['stop']+' 反例（关系示意，不是真题）：'+u['counter']+' 迁移：'+u['transfer']+' 挑战：'+u['challenge']}
        m['entry_copy']=m['student_symptoms'][0]+'时，第一眼先找：'+m['trigger_cues'][0]+'。手上先做：'+m['core_action']+'。做完得到 '+m['output_type']+'，不是通用答案。'+u['judge']+' 什么时候停：'+u['stop']+' 换题仍这样做：'+u['transfer']
        m['levels']={'L1':m['core_action'],'L2':u['judge'],'L3':u['stop'],'L4':u['transfer']}
        m['full'].update(summary=u['judge'],source_boundary=u['stop'],boundaries=[u['stop'],u['counter']])
        m['practicality_gate'].update(trigger=m['trigger_cues'][0],action=m['core_action'],output=m['output_type']+'；'+u['judge'],stop=u['stop'],transfer=u['transfer'],efficiency=u['benefit'],misuse_cost='未经实测；'+u['wrong']+'会导致误判；须先核触发、执行Stop，不允许辅助产物越级定案。')
        m['evaluation']['primary_benefit_hypothesis']=u['benefit']
        m['student_ready']=True
        m['static_design_review']={'status':'source_bound_editorial_review','source_section_ids':list(m['section_ids']),'participant_validation':'pending_real_participant_validation','example_scope':'schematic source boundary, not a verified exam'}
        m['change_reason']='逐项依据冻结源章节补齐学生入口、具体判据与边界；静态就绪，不升级成熟度或声称真人效果'
        for casepath in m['cases'].values():
            cp=ROOT/casepath; oldcase=cp.read_text(encoding='utf-8'); case=yaml.safe_load(oldcase)
            case.update(expected_action=m['core_action'],stop_rule=m['stop_rule'])
            patches.append(patch(casepath,oldcase,yaml.safe_dump(case,allow_unicode=True,sort_keys=False)))
    patches.append(patch(path,old,yaml.safe_dump(data,allow_unicode=True,sort_keys=False)))
    patches.append(patch(idxpath,idxold,yaml.safe_dump(index,allow_unicode=True,sort_keys=False)))
    return patches

if __name__=='__main__':
    parser=argparse.ArgumentParser(); parser.add_argument('module'); parser.add_argument('--offset',type=int,default=0); parser.add_argument('--size',type=int,default=18000)
    args=parser.parse_args()
    if args.offset<0 or not 1<=args.size<=20000: parser.error('Invalid output slice')
    if hasattr(sys.stdout,'reconfigure'): sys.stdout.reconfigure(encoding='utf-8')
    serialized=json.dumps(prepare(args.module,json.load(sys.stdin)),ensure_ascii=False)
    print(json.dumps({'total':len(serialized),'slice':serialized[args.offset:args.offset+args.size]},ensure_ascii=False))
