"""Finite visual intentions over the existing physics and brand registries."""
import hashlib

from video_contracts import ROOT, read, sha
from method_choreography.registry import registry as choreography_registry
from creative_os.motion_identity import registry as identity_registry

VERSION = '0.2.0'
SCHEMA = 'cognitive-direction/v0.2'
PROJECTION_SCHEMA = 'cognitive-direction-projection/v0.2'
DIRECTORY = ROOT / 'creative/schemas'
HUMAN_DIMENSIONS = (
    'pov_present', 'ppt_feel', 'method_action_visible', 'visual_focus_clear',
    'payoff_impact', 'motion_too_busy', 'swiss_identity', 'memorable_visual', 'notes',
)


def policy():
    value = read(ROOT / 'creative/cognitive-direction.json')
    physics, _, bindings = choreography_registry()
    grammar, identity = identity_registry()
    if (value['version'] != VERSION
            or value['authority'] != 'visual_direction_only_not_teaching_truth'):
        raise ValueError('Direction has no teaching authority')
    if {k: set(v) for k, v in physics['families'].items()} != {
            k: set(v) for k, v in value['operation_intents'].items()}:
        raise ValueError('Direction vocabulary must match existing Cognitive Physics')
    if (not set(value['brand_grammar_refs']) <= {g['id'] for g in grammar['grammar']}
            or bindings['motion_identity_sha'] != sha(identity)
            or bindings['brand_grammar_sha'] != sha(grammar)):
        raise ValueError('Current Motion Identity / Brand Grammar required')
    legacy = ROOT / 'creative_os/cognitive_pov.py'
    return value, {
        'direction_policy_sha': sha(value),
        'direction_schema_sha': sha(read(DIRECTORY / 'cognitive-direction.v0.2.json')),
        'legacy_cognitive_pov_version': '0.1.0',
        'legacy_cognitive_pov_sha': hashlib.sha256(legacy.read_bytes()).hexdigest(),
    }


def semantic_payload(value):
    return {k: v for k, v in value.items() if k not in (
        'direction_id', 'direction_sha', 'projection_sha', 'generated_at',
        'content_sha', 'envelope_sha',
    )}
