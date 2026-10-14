"""Audit existing private Case bindings against current rules without migrating them.

Historical validation and current admission are separate. No action, review,
catalog, question, observation or method status is written or re-versioned.
"""
import argparse
from collections import Counter
import json
from pathlib import Path

from core.registry import ROOT, Registry
from core.real_cases import (private_root, load_catalog, artifact, _runtime_contexts,
                             validate_request, digest)

CORE_FIELDS=('method_type','primary_role','secondary_roles','trigger_cues','core_action',
             'decision_rule','verification','stop_rule','counterexamples','cannot_replace')


def audit(dataset,registry=None):
    registry=registry or Registry()
    registry.validate()
    if registry.is_historical:
        raise ValueError('Current epoch audit requires the live Registry')
    root=private_root(dataset)
    catalog=load_catalog(root,registry=registry)
    contexts=_runtime_contexts(root)
    rows=[]
    for ref in catalog['cases']:
        record=artifact(root,ref)
        request_ref=record['registration_request_ref']
        request=artifact(root,request_ref)
        context=contexts.get((request_ref['path'],request_ref['sha256']))
        previous=context['registry'] if context else registry
        mid=request['method_id']; old=previous.methods[mid]; current=registry.methods[mid]
        changes=[key for key in CORE_FIELDS if old.get(key)!=current.get(key)]
        try:
            validate_request(root,request,registry)
            admission='current_structural_admission_passed'
            rejection=None
        except ValueError as exc:
            admission='current_binding_rejected'
            rejection=str(exc)
        rows.append({
            'case_id':record['case_id'],'question_id':request['canonical_question_id'],
            'method_id':mid,'case_type':request['case_type'],
            'case_ref':ref,'registration_request_ref':request_ref,
            'historical_method_version':request['method_version'],
            'historical_source_commit':previous.index['source_baseline']['commit'],
            'current_method_version':current['version'],
            'current_source_commit':registry.index['source_baseline']['commit'],
            'changed_core_fields':changes,
            'current_admission':admission,'current_rejection_reason':rejection,
            'next_review':{
                'when_to_start':current['four_step_card']['start'],
                'first_action':current['four_step_card']['first_cut'],
                'decision':current['four_step_card']['judge'],
                'stop':current['four_step_card']['stop'],
                'required':'explicit current-version action and independent review, retaining the original question',
            },
            'semantic_reacceptance':'not_established_by_this_audit',
            'new_blind_sample':False,'promotion_applied':False,
        })
    # The authoritative catalog must remain byte-identical after all checks.
    if catalog['revision']:
        path=root/'real-case-catalog'/f"catalog-{catalog['revision']:06d}.json"
        if digest(path.read_bytes())!=catalog['sha256']:
            raise ValueError('Catalog changed during audit; report is not a stable frontier')
    return {
        'scope':'historical validation and current structural admission only; not English or learner certification',
        'source_commit':registry.index['source_baseline']['commit'],
        'catalog_revision':catalog['revision'],'catalog_sha256':catalog['sha256'],
        'historical_catalog_validation':'PASS','case_count':len(rows),
        'historical_analysis_replay_policy':catalog.get('historical_analysis_replay_policy'),
        'admission_counts':dict(Counter(row['current_admission'] for row in rows)),
        'method_counts':dict(Counter(row['method_id'] for row in rows)),
        'cases':rows,'new_case_count':0,'new_blind_sample_count':0,
        'learner_validation':'pending_real_participant_validation','method_promotion_applied':False,
    }


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--dataset',required=True,type=Path)
    parser.add_argument('--output',type=Path)
    args=parser.parse_args(); report=audit(args.dataset)
    if args.output:
        output=args.output.resolve()
        if not output.is_relative_to((ROOT/'local-data').resolve()):
            raise ValueError('Keep the private case audit under local-data')
        if output.exists():
            raise ValueError('Refuse to overwrite an existing audit')
        output.parent.mkdir(parents=True,exist_ok=True)
        with output.open('x',encoding='utf-8') as stream:
            json.dump(report,stream,ensure_ascii=False,indent=2)
            stream.write('\n')
    print(json.dumps({key:value for key,value in report.items() if key!='cases'},ensure_ascii=False,indent=2))
