"""Presentation intents for exact frozen course identities; never solves.

Call only after the normal bundle/action/review gates. Reference prose is for
editorial inspection; this consumer reads identity and motion fields only.
"""
from video_contracts import ROOT, read

CATALOG = ROOT / 'creative/method-choreography/course-method-mapping.json'
FALLBACK = 'show_bound_information'
OUTPUTS = {
    'locator': {'located_evidence'},
    'interpreter': {'interpretation'},
    'framework': {'framework_card'},
    'verifier': {'verification_result'},
}


def presentation_mapping(method, action):
    """A mapping grants no verdict, relabeling or renderer capability.

    Old epochs, merely related R/F/C IDs and ambiguous identities deliberately
    fall back. The frozen action keeps its evidence, text, output and Stop Rule.
    """
    catalog = read(CATALOG)
    if catalog['authority'] != 'presentation_mapping_only_not_teaching_truth':
        raise ValueError('Course mapping cannot acquire teaching authority')
    if (action.get('method_id') != method.get('method_id')
            or action.get('method_version') != method.get('version')
            or action.get('review_status') != 'reviewed'
            or action.get('state') != 'produced' or action.get('stop_applied')
            or not action.get('evidence_ids') or not action.get('stop_rule_check')):
        return None
    matches = []
    for row in catalog['methods']:
        source = row['source']
        if (method.get('source_name') != row['name']
                or method.get('question_type') != row['question_type']
                or action.get('role') != row['role']
                or row['role'] not in {method.get('primary_role'), *method.get('secondary_roles', [])}
                or (action.get('output') or {}).get('kind') not in OUTPUTS[row['role']]):
            continue
        if any(all(ref.get(k) == source[k] for k in ('commit', 'path', 'heading'))
               and ref.get('repository', '').removesuffix('.git').removesuffix('/')
                   == 'https://github.com/rockpunkgod/ANSWER'
               for ref in method.get('source_references', [])):
            matches.append(row)
    if len(matches) != 1:
        return None
    row = matches[0]
    return {k: row[k] for k in ('name', 'visual_intent', 'presentation_priority',
                                'renderer_status', 'independent_verdict')}


def action_visual_intent(bundle, action):
    method = next((m for m in bundle['methods'] if m['method_id'] == action['method_id']), None)
    mapping = presentation_mapping(method, action) if method else None
    return mapping['visual_intent'] if mapping else FALLBACK
