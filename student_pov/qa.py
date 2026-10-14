"""Explanation suppression deletes duplicate copy, never a required boundary."""
from copy import deepcopy
import re

from video_contracts import sha


def planned_scene_observations(sequence, payoff, *, first_action_ref, payoff_ref, tell_now_ids,
                               tell_now_items=None):
    """Observe planned scene fields, never rendered frames or student experience.

    A bound Payoff alone does not make a reduction visible. Its before/after
    paths must occur in the planned screens, with supported removed work at
    Collapse. These string/structure checks still require actual visual review.
    """
    required_boundaries = set(tell_now_ids)
    action_present = any(row['cognitive_function'] == 'action' and bool(row['vo'])
        and first_action_ref in row['pedagogy_ref'] and bool(row['evidence_ref'])
        and bool(row['screen_copy']) for row in sequence)
    focus_present = any(row['cognitive_function'] == 'focus' and bool(row['vo'])
        and bool(row['pedagogy_ref']) and bool(row['evidence_ref'])
        and bool(row['screen_copy']) and row['motion_function'] == 'focus_existing_evidence'
        for row in sequence)
    required_text = {item['item_id']: item['text'] for item in tell_now_items or []}
    shown_boundaries = {item for row in sequence if row['screen_copy']
        and row['cognitive_function'] in ('focus', 'action', 'stop')
        for item in row['tell_now_boundary_ids']
        if not required_text or required_text.get(item) in row['screen_copy']}
    student_path = action_present and focus_present and bool(required_boundaries) \
        and required_boundaries <= shown_boundaries
    reduction_visible = False
    if payoff:
        before = {row['text'] for row in payoff['baseline_path']}
        after = {row['text'] for row in payoff['method_path']}
        removed = set(payoff['cognitive_work']['removed'])
        screens_so_far = set()
        for row in sequence:
            screens_so_far.update(row['screen_copy'])
            if (row['cognitive_function'] == 'collapse'
                    and row['motion_function'] == 'supported_cognitive_reduction'
                    and payoff_ref in row['pedagogy_ref'] and row['evidence_ref']
                    and row['output_state'] and before and after and before != after
                    and before <= screens_so_far and after <= set(row['screen_copy'])
                    and removed and removed <= set(row['removed_work'])):
                reduction_visible = True
    return {'cognitive_reduction_visible': reduction_visible,
            'student_pov_present': bool(student_path),
            'observation_scope': 'planned_scene_structure_only',
            'actual_visual_review': 'PENDING', 'student_experience_review': 'PENDING'}


def suppression_qa(realization, coverage):
    """Return a review candidate only, never an approved/mutated release.

    `coverage` is explicit editorial input; the tool cannot see Motion by itself.
    Changed scripts must be resealed/re-reviewed by the caller, not released here.
    """
    allowed = {'scene_id', 'visual_expressed', 'motion_expressed', 'evidence_expressed',
               'next_action_depends', 'note'}
    by_id = {r['scene_id']: r for r in coverage}
    if len(by_id) != len(coverage) or any(set(r) != allowed for r in coverage):
        raise ValueError('Unique complete explicit redundancy coverage required')
    candidates, protected = [], []
    draft = deepcopy(realization['final_script'])
    for scene in draft:
        row = by_id.get(scene['scene_id'])
        if not row or scene['vo'] is None:
            continue
        if any(type(row[k]) is not bool for k in ('visual_expressed', 'motion_expressed',
                                                 'evidence_expressed', 'next_action_depends')):
            raise ValueError('Coverage flags must be explicit booleans')
        if scene['cognitive_function'] == 'stop' or scene['tell_now_boundary_ids']:
            protected.append(scene['scene_id'])
            continue
        if (row['visual_expressed'] and row['motion_expressed'] and row['evidence_expressed']
                and not row['next_action_depends']):
            candidates.append({'scene_id': scene['scene_id'], 'code': 'EXPLANATION_REDUNDANT',
                               'original_vo': scene['vo'], 'coverage': deepcopy(row)})
            scene['vo'] = None
    return {'status': 'REVIEW_CANDIDATE', 'source_copy_sha': realization['copy_sha'],
            'suppressed_candidate_sha': sha(draft), 'final_script_candidate': draft,
            'redundant': candidates, 'protected_tell_now_scenes': protected,
            'existing_copy_approval_invalid_for_candidate': bool(candidates),
            'public_render_ready': False}


def frozen_answer_binding(bundle, status):
    """Project a reviewed, closed answer from a frozen asset for draft narration.

    A Reveal key, a retained candidate or an exporter success alone is insufficient.
    This is an engineering consumption check, never a public release credential.
    """
    from content_os.candidates import engineering_gate
    from video_contracts import status_matches, verify_bundle

    verify_bundle(bundle)
    if status is None or not status_matches(bundle, status):
        raise ValueError('Current frozen answer status required')
    analysis = bundle['analysis']
    answer = analysis['answer']
    selections = []
    for method in bundle['methods']:
        mid = method['method_id']
        actions = [a['execution_id'] for a in analysis['execution_trace']
                   if a['method_id'] == mid and (a.get('output') or {}).get('candidate') == answer
                   and (a.get('output') or {}).get('effect') == 'retain']
        if not actions:
            continue
        # Include the complete reviewed sequence, not just the winning option.
        selection = {'method_id': mid, 'action_ids': [a['execution_id']
            for a in analysis['execution_trace'] if a['method_id'] == mid
            and a['state'] == 'produced' and a['review_status'] == 'reviewed']}
        decisions = {a['output']['candidate'] for a in analysis['execution_trace']
                     if a['execution_id'] in selection['action_ids'] and a.get('output')
                     and a['output']['kind'] == 'candidate_decision'}
        if decisions != set(bundle['source_snapshot'].get('options', {})):
            continue
        if engineering_gate(bundle, selection, 'full_solution', status)['status'] == 'PASS':
            selections.append(selection)
    if answer is None or not selections:
        raise ValueError('Frozen reviewed full-solution closure required')
    return {'answer': answer, 'asset_id': bundle['asset_id'],
            'answer_sha': sha(answer), 'semantic_binding_sha': bundle['semantic_binding_sha'],
            'status_content_sha': status['content_sha'], 'selections': selections,
            'public_render_ready': False}


def answer_letters(text):
    """Conservative literal answer-claim lint; not a semantic truth recognizer."""
    pattern = (r'(?:选(?:择)?\s*|答案(?:已经)?(?:是|为|确定为)\s*)([A-G])'
               r'|([A-G])\s*(?:就是|是)答案|(?:^|[。！？\n])\s*就是\s*([A-G])')
    letters = []
    for match in re.finditer(pattern, text):
        prefix = text[max(0, match.start() - 8):match.start()]
        if re.search(r'(?:不|别|不能|不该|不应|不要|不能直接|不要直接)$', prefix):
            continue
        letters.append(next(value for value in match.groups() if value is not None))
    return letters


def lint_copy(text, role, may_answer, *, frozen_answer=None):
    flags = []
    if re.search(r'一招秒杀|必考|90%的学生|所有.*都必须|做阅读不用背单词|阅读不用词汇', text):
        flags.append('prohibited_or_generalized_claim')
    # This v0.2 interface has no bound statistics or heat-evidence channel.
    # Structural path/candidate counts remain allowed; invented rates do not.
    if re.search(r'\d+(?:\.\d+)?\s*[%％]|热门|爆火|全网都在做', text):
        flags.append('unbound_statistic_or_heat_claim')
    if role != 'decider' and re.search(r'答案出来|答案就在|直接排|这一招就够|找到.*就能选', text):
        flags.append('role_overclaim')
    if not may_answer and re.search(r'答案出来|答案就在|所以填|词形.*确定了', text):
        flags.append('answer_scope_overclaim')
    if re.search(r'确认角色.*Evidence.*Review|定位.*角色识别.*边界检查.*Review', text, re.S):
        flags.append('expert_chain_leakage')
    if re.search(r'\b(?:provenance|decider|reducer|verifier|framework)\b|review:[A-Za-z0-9]', text, re.I):
        flags.append('expert_chain_leakage')
    if frozen_answer is not None:
        if any(letter != frozen_answer for letter in answer_letters(text)):
            flags.append('frozen_answer_mismatch')
    return sorted(set(flags))
