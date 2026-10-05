"""Generate explicit v1 contract schemas; --check never writes."""
import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
S = {'type': 'string'}
N = {'type': 'number'}
B = {'type': 'boolean'}
O = {'type': 'object'}
H = {'type': 'string', 'pattern': '^[a-f0-9]{64}$'}


def arr(item): return {'type': 'array', 'items': item}
def enum(*items): return {'enum': list(items)}
def nullable(item): return {'anyOf': [item, {'type': 'null'}]}
def obj(props, optional=()):
    return {'type': 'object', 'properties': props, 'required': [p for p in props if p not in optional], 'additionalProperties': False}


def schemas():
    ref = obj({'asset_id': S, 'pointer': {'type': 'string', 'pattern': '^/'}})
    review_level = enum('unreviewed', 'ai_reviewed', 'human_reviewed', 'human_certified')
    semantic = obj({'level': review_level, 'independent_human_certified': B, 'reviewer_type': enum('ai_host', 'human', 'unknown')})
    sem_candidate = obj({**semantic['properties'], 'status': enum('usable_for_engineering_pilot', 'blocked')})
    effective = enum('ACTIVE', 'INCOMPLETE', 'WITHDRAWN', 'SUPERSEDED', 'STALE', 'BLOCKED')
    cause = nullable(obj({'why': S, 'which_parent': S, 'withdrawal_artifact_id': S, 'withdrawal_sha': H}))
    lifecycle = obj({
        'reviews': arr(obj({'artifact_id': S, 'status': enum('active', 'withdrawn', 'superseded'), 'withdrawal_refs': arr(S)})),
        'actions': arr(obj({'artifact_id': S, 'status': enum('active', 'blocked', 'withdrawn', 'superseded'), 'parent_artifacts': arr(S), 'cause': cause})),
        'decisions': arr(obj({'artifact_id': S, 'status': enum('active', 'blocked', 'withdrawn', 'superseded'), 'cause': cause})),
        'evidence': arr(obj({'artifact_id': S, 'status': enum('active', 'withdrawn', 'superseded')}))})
    source = obj({'usage_status': S, 'redistribution_status': S, 'source_reference': S, 'attribution_text': S})
    seal = {'content_sha': H, 'envelope_sha': H}
    bundle = obj({'schema_version': enum('1.0.0'), 'asset_id': S, 'generated_at': S,
        'source_snapshot': read_existing('question-input'), 'source': source, 'analysis': read_existing('question-analysis'),
        'methods': arr(read_existing('method-card')),
        'reviews': arr(obj({'artifact_id': S, 'sha': H, 'semantic_sha': H, 'level': review_level, 'phase': enum('blind', 'host_review', 'reveal', 'post_reveal'), 'record': O})),
        'withdrawals': arr(obj({'artifact_id': S, 'sha': H, 'record': O})), 'lifecycle': lifecycle,
        'history': arr(obj({'asset_id': S, 'content_sha': H,
                           'evaluation_phase': enum('blind', 'host_review', 'reveal', 'post_reveal'),
                           'reviews': arr(O), 'withdrawals': arr(O), 'lifecycle': lifecycle, 'effective_status': effective})),
        'evaluation_phase': enum('blind', 'host_review', 'reveal', 'post_reveal'), 'answer_visible_in_this_bundle': B,
        'semantic_review': semantic, 'binding_fingerprint': obj({'question_snapshot_sha': H, 'analysis_sha': H,
            'method_versions': {'type': 'object', 'additionalProperties': S}, 'evidence_graph_sha': H, 'execution_trace_sha': H,
            'active_review_set_sha': H, 'active_action_set_sha': H}),
        'state': obj({'effective_status': effective, 'blocking_reasons': arr(S), 'warnings': arr(S)}),
        'provenance': O, 'semantic_binding_sha': H, 'presentation_sha': H, **seal})
    status = obj({'schema_version': enum('1.0.0'), 'asset_id': S, 'generated_at': S, 'semantic_binding_sha': H,
        'source_sha': H, 'presentation_sha': H, 'question': obj({'snapshot_sha': H, 'status': effective}),
        'method_versions': {'type': 'object', 'additionalProperties': S}, 'lifecycle': lifecycle,
        'effective_status': effective, 'invalidation_reasons': arr(S), **seal})
    claim = obj({'claim_id': S, 'text': S, 'kind': S, 'method_id': S, 'asset_id': S, 'source_ref': ref,
                 'action_artifact_refs': arr(ref), 'evidence_refs': arr(ref), 'review_refs': arr(ref), 'purpose': enum('teaching', 'challenge')})
    selection = obj({'asset_id': S, 'method_id': S, 'action_ids': arr(S), 'purpose': enum('teaching', 'challenge')}, ('purpose',))
    invalidation = obj({'teaching_stale': B, 'source_release_stale': B, 'editorial_stale': B, 'reasons': arr(S)})
    scope = enum('full_solution', 'method_action_demo', 'boundary_demo', 'anti_rule_demo', 'challenge', 'method_comparison')
    gate = obj({'status': enum('PASS', 'HOLD', 'BLOCKED'), 'checks': {'type': 'object', 'additionalProperties': obj({'status': enum('PASS', 'FAIL'), 'reason': S, 'refs': arr(S)})},
                'blockers': arr(S), 'warnings': arr(S)})
    source_gate = obj({'internal_use': enum('PASS', 'BLOCKED'), 'public_usage_status': enum('review_required'), 'status': enum('PENDING'), 'human_review_required': B, 'source_states': arr(S)})
    rating = obj({'value': nullable({'type': 'number', 'minimum': 0, 'maximum': 10}), 'status': enum('known', 'unknown'), 'rationale': S, 'evidence': arr(S)}, ('evidence',))
    score = obj({'rubric_version': S, 'dimensions': {'type': 'object', 'additionalProperties': rating}, 'raw_score': nullable(N),
                 'known_dimension_count': {'type': 'integer', 'minimum': 0}, 'score_coverage': {'type': 'number', 'minimum': 0, 'maximum': 1}})
    candidate = obj({'schema_version': enum('1.0.0'), 'content_id': S, 'content_scope': scope, 'source_items': arr(bundle),
        'selections': arr(selection), 'claims': arr(claim), 'semantic_review': sem_candidate,
        'teaching_engineering_gate': obj({'status': enum('PASS', 'HOLD', 'BLOCKED'), 'items': arr(gate)}),
        'engineering_pilot_eligible': B, 'source_use': source_gate,
        'status': enum('production_candidate', 'blocked_teaching', 'review_required', 'stale'), 'risk_flags': arr(S),
        'invalidation': invalidation, 'content_score': score, 'production_feasibility': score,
        'pattern_id': S, 'duration_target': N}, ('content_score', 'production_feasibility', 'pattern_id', 'duration_target'))
    scene = obj({'scene_id': S, 'order': {'type': 'integer', 'minimum': 0},
        'scene_type': enum('HOOK', 'QUESTION', 'WRONG_INSTINCT', 'LOCATE', 'COMPARE', 'EVIDENCE', 'CORE_ACTION', 'METHOD_REVEAL', 'STOP_RULE', 'VERDICT', 'TRANSFER', 'CTA'),
        'spoken_text': S, 'on_screen': obj({'primary_text': S, 'secondary_text': S}), 'claim_refs': arr(S),
        'evidence_refs': arr(ref), 'visual_intent': S, 'method_visual': nullable(O), 'transition_intent': S,
        'duration_estimate': nullable({'type': 'number', 'minimum': 0})})
    display = obj({'displayed_excerpt_ids': arr(S), 'excerpts': arr(obj({'excerpt_id': S, 'ref': ref, 'text': S})),
        'displayed_text_sha': H, 'displayed_image_sha': H, 'images': arr(obj({'artifact_id': S, 'sha': H})),
        'attribution_text': S, 'release_review_id': nullable(S)})
    package = obj({'schema_version': enum('1.0.0'), 'version': S, 'content_id': S, 'package_id': S,
        'status': enum('draft', 'final_draft', 'teaching_locked', 'editorial_review', 'editorial_approved', 'locked', 'render_ready', 'stale', 'blocked', 'review_required'),
        'source_items': arr(bundle), 'selections': arr(selection), 'claims': arr(claim), 'semantic_review': sem_candidate,
        'content': obj({'content_scope': scope, 'pattern_id': enum('P01', 'P02', 'P03', 'P04', 'P05'), 'primary_hook': S, 'alternate_hooks': arr(S), 'cta': S}),
        'semantic_scenes': arr(scene), 'voiceover': arr(obj({'scene_id': S, 'text': S})),
        'timeline': arr(obj({'scene_id': S, 'start': N, 'end': N})), 'source_display': display,
        'production': obj({'duration_target': enum(30, 60, 90), 'actual_estimated_duration': nullable(N), 'aspect_ratio': enum('9:16'),
                           'platform_profile': S, 'template_family': S, 'timing_version': S}),
        'copy_lock': obj({'final_copy_sha': nullable(H), 'polished_from_sha': nullable(H), 'editorial_review_sha': nullable(H)}),
        'pilot_status': obj({'engineering': enum('PASS', 'PENDING', 'FAIL'), 'semantic_release': enum('PASS', 'PENDING'),
                              'source_release': enum('PASS', 'PENDING'), 'editorial_release': enum('PASS', 'PENDING')}),
        'review': obj({'teaching_review': arr(O), 'source_review': nullable(O), 'editorial_review': nullable(O)}),
        'render_ready_for_publication': B, 'invalidation': invalidation, 'manifest_ref': S,
        'claim_guard': obj({'status': enum('PASS', 'FAIL'), 'reasons': arr(S), 'scope': S})})
    manifest = obj({'schema_version': enum('1.0.0'), 'package_id': S, 'generated_at': S,
        'candidate_sha': H, 'package_sha': H,
        'inputs': arr(obj({'asset_id': S, 'content_sha': H, 'semantic_binding_sha': H,
                           'method_versions': {'type': 'object', 'additionalProperties': S}, 'review_ids': arr(S)})),
        'pattern_version': S, 'pattern_sha': H, 'rubric_version': S, 'ranking_policy_version': S,
        'director_version': S, 'timing_version': S, 'final_copy_sha': H})
    for contract in (candidate, package):
        for field in ('source_items', 'selections'):
            contract['properties'][field]['minItems'] = 1
    for field in ('claims', 'semantic_scenes'):
        package['properties'][field]['minItems'] = 1
    return {'schemas/frozen-asset-bundle.json': bundle, 'schemas/artifact-status-manifest.json': status,
            'video/schemas/content-candidate.json': candidate, 'video/schemas/video-package.json': package,
            'video/schemas/package-manifest.json': manifest}


def read_existing(name):
    value = json.loads((ROOT / 'schemas' / (name + '.json')).read_text(encoding='utf-8'))
    # Existing schemas use local $defs. Move them into this embedded resource using $id.
    return value


def main():
    parser = argparse.ArgumentParser(); parser.add_argument('--check', action='store_true'); args = parser.parse_args()
    for path, schema in schemas().items():
        schema = {'$schema': 'https://json-schema.org/draft/2020-12/schema', **schema}
        text = json.dumps(schema, ensure_ascii=False, indent=2) + '\n'
        destination = ROOT / path
        if args.check:
            if not destination.exists() or destination.read_text(encoding='utf-8') != text:
                raise ValueError('Schema generation drift: ' + path)
        else:
            destination.parent.mkdir(parents=True, exist_ok=True); destination.write_text(text, encoding='utf-8')


if __name__ == '__main__': main()
