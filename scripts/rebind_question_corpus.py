"""Rebind exact source identities for compatibility replay, never new approval.

Original questions, evidence, authors and English copy are preserved. Changed
method versions/contracts require reauthoring. Changed source sections require
the already recorded, exact before/after delta review; this still does not
create a new independent English review, Case admission or learner result.
"""
from copy import deepcopy
import hashlib
import json

from core.real_cases import material
from core.registry import ROOT

METHOD_CONTRACT = ('method_type', 'primary_role', 'secondary_roles', 'output_type',
    'trigger_cues', 'core_action', 'decision_rule', 'verification', 'stop_rule',
    'counterexamples', 'cannot_replace')


def digest_text(text):
    return hashlib.sha256(text.encode('utf-8')).hexdigest()


def approved_changes(previous, current):
    commit = current.index['source_baseline']['commit']
    path = ROOT/'provenance/runtime-alignments'/f'{commit}-reviewed.json'
    report = json.loads(path.read_bytes())
    if (report['from_commit'] != previous.index['source_baseline']['commit'] or
            report['to_commit'] != commit or report['status'] != 'applied'):
        raise ValueError('Explicit applied source-delta review required')
    result = {}
    for row in report['methods_reviewed']:
        old = previous.methods[row['method_id']]
        for change in row['source_deltas']:
            candidates = [previous.sources['sections'][sid] for sid in old['section_ids']
                          if previous.sources['sections'][sid]['heading'] == change['old_heading']]
            if len(candidates) != 1:
                raise ValueError('Ambiguous reviewed old source section')
            source = candidates[0]
            key = (source['path'], source['heading'])
            if key in result and result[key] != change:
                raise ValueError('Conflicting reviewed source deltas')
            result[key] = deepcopy(change)
    return result


def rebind_question(question, previous, current, changes):
    old_commit = previous.index['source_baseline']['commit']
    new_commit = current.index['source_baseline']['commit']
    used, source_changes = set(), {}

    def inspect(value):
        if isinstance(value, dict):
            if value.get('method_id'):
                used.add(value['method_id'])
            for child in value.values():
                inspect(child)
        elif isinstance(value, list):
            for child in value:
                inspect(child)
    inspect(question)
    used.update(question.get('requested_chain', []))
    for mid in used:
        if mid not in previous.methods or mid not in current.methods:
            raise ValueError('Unknown method in historical question: '+str(mid))
        old, new = previous.methods[mid], current.methods[mid]
        if old['version'] != new['version']:
            raise ValueError('Method version changed; no automatic upgrade: '+mid)
        if any(old.get(key) != new.get(key) for key in METHOD_CONTRACT):
            raise ValueError('Method contract changed; explicit reauthoring required: '+mid)

    def section_id(sid):
        old = previous.sources['sections'].get(sid)
        if old is None or old.get('commit') != old_commit:
            raise ValueError('Unknown source ID in explicit historical epoch')
        key = (old['path'], old['heading'])
        approval = changes.get(key)
        heading = approval['new_heading'] if approval else old['heading']
        matches = [(target, source) for target, source in current.sources['sections'].items()
                   if (source['path'], source['heading'], source['commit']) ==
                      (old['path'], heading, new_commit)]
        if len(matches) != 1:
            raise ValueError('Missing or ambiguous exact current source')
        target, new = matches[0]
        changed = old['content'] != new['content']
        if changed and (not approval or approval['before_sha256'] != digest_text(old['content']) or
                        approval['after_sha256'] != digest_text(new['content'])):
            raise ValueError('Changed source is not bound to its exact delta review')
        source_changes[sid] = {'old_id': sid, 'new_id': target, 'path': old['path'],
            'old_heading': old['heading'], 'new_heading': heading,
            'definition_content_changed': changed,
            'before_sha256': digest_text(old['content']), 'after_sha256': digest_text(new['content'])}
        return target

    def visit(value):
        if isinstance(value, list):
            return [visit(child) for child in value]
        if not isinstance(value, dict):
            return value
        result = {key: visit(child) for key, child in value.items()}
        if 'source_commit' in result:
            if result['source_commit'] != old_commit:
                raise ValueError('Foreign source epoch in historical annotation')
            result['source_commit'] = new_commit
        if 'method_version' in result and 'method_id' in result:
            if result['method_version'] != previous.methods[result['method_id']]['version']:
                raise ValueError('Historical annotation method version mismatch')
        if 'source_section_ids' in result:
            ids = result['source_section_ids']
            if not isinstance(ids, list) or len(ids) != len(set(ids)):
                raise ValueError('Invalid or duplicate source section list')
            result['source_section_ids'] = [section_id(sid) for sid in ids]
        return result
    rebound = visit(question)
    if material(rebound) != material(question):
        raise ValueError('Rebinding changed original question material')
    return rebound, {'question_id': question['question_id'],
        'from_commit': old_commit, 'to_commit': new_commit,
        'method_contracts_unchanged': sorted(used), 'source_bindings': list(source_changes.values()),
        'scope': 'source_identity_and_runtime_compatibility_only',
        'new_independent_English_review': False, 'new_case_admission': False,
        'new_blind_or_learner_credit': False}
