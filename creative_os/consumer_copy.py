"""Consumer-facing presentation policy; provenance stays in metadata."""
from copy import deepcopy
import re


METHOD_CODE = re.compile(r'(?<![A-Za-z0-9])[RFG]\d{2}(?![A-Za-z0-9])', re.IGNORECASE)


def require_consumer_copy(excerpt, nodes):
    """Deterministic presentation lint, not teaching certification.

    Check visible/spoken strings only. Never strip method IDs from claims,
    source references, unit metadata, or frozen ANSWER assets.
    """
    strings = [(u['unit_id'] + '/' + key, u[key])
               for u in excerpt['units'] for key in ('spoken_copy', 'on_screen_copy')]
    strings += [(n['node_id'], n['text']) for n in nodes if n['kind'] == 'text']
    strings += [(u['unit_id'] + '/excerpt', e['text'])
                for u in excerpt['units'] for e in u.get('visual_excerpts', [])]
    for location, text in strings:
        if METHOD_CODE.search(text):
            raise ValueError('Internal method code in consumer copy: ' + location)


def project_consumer_contract(contract, package, manifest, statuses, old_full, old_excerpt,
                              full, excerpt, node_edits, revision):
    """Explicit copy revision, followed by the full frozen-source validation.

    Caller supplies newly authored, fidelity-reviewed delivery copy. This
    function neither invents replacement wording nor approves that wording.
    """
    from .hero import validate_contract, build_contract
    validate_contract(contract, package, manifest, statuses, old_full, old_excerpt)
    known = {n['node_id'] for n in contract['nodes'] if n['kind'] == 'text'}
    if set(node_edits) - known:
        raise ValueError('Consumer projection references an unknown text node')
    nodes = []
    for original in contract['nodes']:
        node = deepcopy(original)
        if node['node_id'] in node_edits:
            value = node_edits[node['node_id']]
            if value is None:
                continue
            if not isinstance(value, str) or not value.strip():
                raise ValueError('Explicit text or deletion required')
            node['text'] = value
        nodes.append(node)
    require_consumer_copy(excerpt, nodes)
    design = deepcopy(contract['design'])
    design['audience'] = 'consumer'
    design['consumer_copy_policy_version'] = '0.1.0'
    # Removing a branded stamp does not claim the original registered signature.
    design.pop('motion_identity', None)
    return build_contract(package, manifest, statuses, full, excerpt, design,
                          nodes, contract['beats'], contract['canvas']['duration'], revision)
