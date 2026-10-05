"""Publish metadata/counts only; copyrighted exam text remains local."""
import argparse
import json
from pathlib import Path
from scripts.ingest_exam_sources import ROOT
from scripts.collect_exam_cases import review_summary
from scripts.apply_exam_withdrawals import load_metadata
from scripts.collect_action_reviews import load_metadata as load_action_metadata
from scripts.collect_action_reviews import load_chain_metadata

def latest(directory,prefix):
    def version(path):
        import re
        match=re.search(r'-v(\d+(?:\.\d+)*)\.json$',path.name)
        parts=[int(x) for x in match[1].split('.')] if match else [1,0,0]
        return tuple((parts+[0,0,0])[:3])
    paths=list(directory.glob(prefix+'.json'))+list(directory.glob(prefix+'-v*.json'))
    return max(paths,key=version) if paths else None

def summary(dataset):
    directory=Path(dataset)
    manifest=json.loads((directory/'source-manifest.json').read_text(encoding='utf-8'))
    papers=[]
    for entry in manifest['papers']:
        exam=entry['exam_id']; result_directory=directory/'results'/exam
        result_path=latest(result_directory,'reveal')
        result=json.loads(result_path.read_text(encoding='utf-8')) if result_path else {}
        contributions=latest(result_directory,'contribution-summary')
        extra=json.loads(contributions.read_text(encoding='utf-8')) if contributions else {}
        if not result: result=extra
        # Normalize derived metadata only; never rewrite frozen adapter artifacts.
        merged={**result,**extra}
        aliases={'new_question_count':'written_questions','answered_count':'mechanical_answered_count',
                 'unresolved_count':'mechanical_unresolved_count','method_trigger_failure':'trigger_failure'}
        # Deliberately whitelist fields; never serialize raw inputs/predictions/keys.
        row={key:entry[key] for key in ['exam_id','year','exam_name','usage_status','source_ids']}
        row['status']='source_frozen_structure_pending' if not result else result.get('status','PARTIAL')
        row['result_artifact']=result_path.relative_to(directory).as_posix() if result_path else None
        prediction_path=directory/'predictions'/exam/'blind.json'
        row['blind_prediction_frozen']=prediction_path.is_file()
        row['blind_reveal_completed']=row['blind_prediction_frozen'] and result_path is not None
        for key in ['new_question_count','question_type_counts','objective_count','answered_count','blind_answer_match',
                    'matched_count','wrong_answer_count','unresolved_count','structurally_safe_abstention_count',
                    'safe_abstention','evidence_failure','method_trigger_failure','boundary_failure',
                    'new_real_case_count','filled_case_slots','remaining_core_unregistered_slots',
                    'method_case_contributions','prediction_sha256','blank_source_sha256','reveal_source_sha256']:
            row[key]=merged.get(key,merged.get(aliases.get(key,'')))
        row['source_issue']=entry['source_issue']+merged.get('source_issue',[])
        audit_path=result_directory/'source-audit.json'
        if audit_path.is_file():
            audit=json.loads(audit_path.read_text(encoding='utf-8'))
            row['source_issue']+=audit.get('source_issue',[])
            row['source_completeness']=audit.get('source_completeness')
        host_path=result_directory/'host-review-summary.json'
        host=json.loads(host_path.read_text(encoding='utf-8')) if host_path.is_file() else extra
        for key in ['host_reviewed_question_count','host_reviewed_answered_count','host_reviewed_reference_match_count']:
            row[key]=host.get(key,result.get(key))
        if row['host_reviewed_question_count'] is None and host.get('reviewed_prediction_sha256'):
            row['host_reviewed_question_count']=host.get('host_reviewed_answered_count')
        if row['host_reviewed_reference_match_count'] is None:
            row['host_reviewed_reference_match_count']=host.get('host_reviewed_match_count',result.get('host_reviewed_match_count'))
        row['case_review']=review_summary(directory,exam)
        row['negative_review_execution']=load_metadata(directory,exam)
        row['post_reveal_action_reviews']=load_action_metadata(directory,exam)
        row['post_reveal_chain_reviews']=load_chain_metadata(directory,exam)
        papers.append(row)
    return {'schema_version':'1.0.0','status':'PARTIAL','source_papers':len(papers),
        'source_files':len(manifest['sources']),'completed_blind_reveal_papers':sum(x['blind_reveal_completed'] for x in papers),
        'new_question_count':sum(x['new_question_count'] or 0 for x in papers),
        'host_reviewed_question_count':sum(x['host_reviewed_question_count'] or 0 for x in papers),
        'host_reviewed_answered_count':sum(x['host_reviewed_answered_count'] or 0 for x in papers),
        'host_reviewed_reference_match_count':sum(x['host_reviewed_reference_match_count'] or 0 for x in papers),
        'real_student_observation_count':0,'new_registered_cases':0,
        'case_review_candidate_count':sum((x['case_review'] or {}).get('case_candidate_count',0) for x in papers),
        'post_reveal_ai_reviewed_question_count':sum(bool(x['case_review'] and x['case_review'].get('semantic_review_question_id')) for x in papers),
        'negative_review_withheld_question_count':sum(bool(x['negative_review_execution'] and x['negative_review_execution']['answer_withheld']) for x in papers),
        'post_reveal_helper_action_review_count':sum(len(x['post_reveal_action_reviews']) for x in papers),
        'post_reveal_chain_review_count':sum(len(x['post_reveal_chain_reviews']) for x in papers),
        'scope':'actual local source ingestion and engine regression metadata; not semantic or learner certification',
        'sources':[{key:s[key] for key in ['source_id','exam_id','kind','filename','bytes','sha256','extraction_sha256','source_reference','download_reference','usage_status','answer_authority']} for s in manifest['sources']],
        'papers':papers}

def main():
    p=argparse.ArgumentParser(); p.add_argument('--dataset',default=str(ROOT/'local-data/exams-2020-2025'))
    p.add_argument('--output',default=str(ROOT/'evaluation/reports/exam-ingestion.json'))
    args=p.parse_args(); result=summary(args.dataset)
    # Derived public metadata may be regenerated; frozen local source is read-only.
    path=Path(args.output); path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({key:result[key] for key in ['status','source_papers','source_files','completed_blind_reveal_papers','new_question_count']}))

if __name__=='__main__': main()
