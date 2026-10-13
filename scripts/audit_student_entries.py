"""Inspect current student-entry evidence; presence is not semantic acceptance.

Read-only by default. No source, case, observation, readiness or promotion writes.
"""
import argparse
from collections import Counter
import json
from pathlib import Path

from core.registry import Registry
from scripts.generate_assets import build, guide_path

PRIORITY = ('R01', 'R02', 'R06', 'R09', 'F01', 'G01')


def audit(registry=None):
    registry = registry or Registry()
    registry.validate()
    assets = build(registry)
    rows = []
    for mid, method in registry.methods.items():
        student_path = guide_path(method)
        guide = assets.get(student_path, '')
        steps = method.get('four_step_card', {})
        # These are inspectable projections, not judgments of teaching quality.
        checks = {
            'symptom_present': bool(method.get('student_symptoms')),
            'trigger_present': bool(method.get('trigger_cues')) and bool(steps.get('start')),
            'first_action_present': bool(steps.get('first_cut')),
            'output_role_present': bool(method.get('output_type')),
            'decision_present': bool(steps.get('judge')),
            'stop_matches_card': bool(steps.get('stop')) and steps['stop'] == method['stop_rule'],
            'transfer_present': bool(method.get('transfer_pattern')),
            'visual_formula_present': bool(method.get('visual_formula')),
            'wrong_instinct_present': bool(method.get('common_wrong_instinct')),
            'anti_rule_present': bool(method.get('anti_rule')),
            'challenge_present': bool(method.get('challenge_prompt')),
            'counterexample_present': bool(method.get('counterexamples')),
            'all_short_forms_present': all(method.get('compact', {}).get(key) for key in ('10s','30s','90s')),
            'independent_guide_exposes_four_steps': all(
                f'{index}. {label}：{steps.get(key, "")}' in guide
                for index, (key, label) in enumerate(
                    [('start','启动'),('first_cut','第一刀'),('judge','判断'),('stop','停止')], 1)),
        }
        ready = method.get('student_ready') is True
        draft = method.get('source_alignment', {}).get('authored_first_contact_draft') is True
        rows.append({
            'method_id': mid, 'method_version': method['version'],
            'question_type': method['question_type'], 'method_type': method['method_type'],
            'primary_role': method['primary_role'], 'output_role': method['output_type'],
            'source_section_ids': method['section_ids'], 'guide_path': student_path,
            'entry_state': 'static_entry_ready' if ready else 'draft' if draft else 'held_for_reacceptance',
            'structural_checks': checks,
            'structural_gaps': [key for key, ok in checks.items() if not ok],
            'semantic_review': method.get('static_design_review', {}).get('status', 'missing'),
            'first_use_status': method.get('first_use_test', {}).get('final_result', 'missing'),
            'timed_delivery': 'unmeasured',
            'learner_acceptance': 'pending_real_participant_validation',
            'maturity_status': method['maturity_status'], 'practical_value': method['practical_value'],
        })
    return {
        'scope': 'current-epoch structural evidence only; not semantic, learner or release certification',
        'source_commit': registry.index['source_baseline']['commit'],
        'historical_registry': registry.is_historical,
        'method_count': len(rows),
        'entry_counts': dict(Counter(row['entry_state'] for row in rows)),
        'priority_entries': [row for row in rows if row['method_id'] in PRIORITY],
        'methods': rows,
        'final_status': 'PARTIAL',
        'engineering_complete': False,
        'missing_acceptance_evidence': [
            'current-source semantic consistency of compact, full and four-step entries',
            'complete real demonstration and unfamiliar transfer task for each priority entry',
            'measured 10/30/90-second delivery',
            'real participant communication, first-use, blind and baseline observations',
        ],
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    report = audit()
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    print(json.dumps({key: value for key, value in report.items()
                      if key not in ('methods','priority_entries')}, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
