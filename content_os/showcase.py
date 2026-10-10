"""Versioned, read-only publication decisions for scope-bound free content.

This module consumes frozen packages. It never writes a method or calls the
research-release checker. Human credentials are external assertions, not an
identity authentication service or an English semantic certifier.
"""
from datetime import datetime
import hashlib
import json
from pathlib import Path
import subprocess

from video_contracts import sha, validate, verify_seal
from .release import validate_package

POLICY = 'free_showcase_v1'
VERSION = '1.0.0'
CHECKS = {
    'teaching_claim': ('question', 'evidence', 'action', 'result_scope', 'role', 'required_stop', 'copy_consistency'),
    'source_display': ('excerpts', 'images', 'attribution', 'music_rights', 'voice_rights', 'display_scope'),
    'editorial': ('hook', 'voiceover', 'subtitles', 'visuals', 'music', 'scope_consistency'),
    'final_media': ('picture', 'audio_present', 'subtitles', 'frame_integrity', 'display_scope', 'encoded_version'),
}


def file_sha(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()


def inspect_media(path):
    """Inspect and fully decode the actual export; no manifest-only PASS."""
    probe = subprocess.run(['ffprobe', '-v', 'error', '-show_streams', '-show_format',
        '-of', 'json', str(path)], capture_output=True, text=True, check=True)
    value = json.loads(probe.stdout)
    video = next(s for s in value['streams'] if s['codec_type'] == 'video')
    audio = [s for s in value['streams'] if s['codec_type'] == 'audio']
    if (video['width'], video['height']) != (3840, 2160) or video['r_frame_rate'] not in ('24/1', '24000/1000'):
        raise ValueError('Showcase export must be 4K24')
    if not audio or float(value['format']['duration']) <= 0:
        raise ValueError('Actual export must contain audio and positive duration')
    subprocess.run(['ffmpeg', '-v', 'error', '-xerror', '-i', str(path), '-f', 'null', '-'],
                   capture_output=True, check=True)
    return {'status': 'PASS', 'duration': float(value['format']['duration']),
            'width': video['width'], 'height': video['height'], 'fps': '24/1',
            'audio_streams': len(audio), 'full_decode': True}


def bindings(request, statuses):
    package = request['package']
    for status in statuses.values():
        if status.get('kind') != 'reviewed_passage_status':
            validate('artifact-status-manifest', status)
        verify_seal(status)
    sources = [package['bundle']] if package.get('kind') == 'free_showcase_passage/v1' else package['source_items']
    teaching = {'sources': {b['asset_id']: b['semantic_binding_sha'] for b in sources}}
    teaching.update({k: package[k] for k in ('question_id', 'segment_ids', 'action_ids')}
                    if package.get('kind') == 'free_showcase_passage/v1' else
                    {k: package[k] for k in ('selections', 'claims')})
    display = {k: v for k, v in request['source_display'].items() if k != 'materials'}
    display['materials'] = [a['sha256'] for a in request['source_display']['materials']]
    upstream = {b['asset_id']: ({k: v for k, v in statuses[b['asset_id']].items()
        if k not in ('generated_at', 'content_sha', 'envelope_sha', 'provenance')}
        if b['asset_id'] in statuses else None) for b in sources}
    if request.get('content_profile') != 'FREE_SHOWCASE':
        raise ValueError('Free publication checker requires FREE_SHOWCASE; Paid needs its own review')
    return {'policy': POLICY, 'version': VERSION, 'content_profile': 'FREE_SHOWCASE',
        'teaching_sha': sha(teaching),
        'scope_sha': sha(request['scope']),
        'final_copy_sha': sha(request['final_copy']),
        'source_display_sha': sha(display),
        'picture_sha': request['media']['picture_sha'],
        'audio_sha': sha([a['sha256'] for a in request['media']['audio_assets']]),
        'final_media_sha': request['media']['sha256'],
        'production_receipt_sha': request['media']['production_receipt_sha'],
        'upstream_sha': sha(upstream)}


def review_template(request, statuses, kind):
    if kind not in CHECKS:
        raise ValueError('Unknown showcase review kind')
    return {'schema_version': VERSION, 'policy': POLICY, 'content_profile': 'FREE_SHOWCASE', 'kind': kind,
        'review_id': '', 'reviewer': '', 'reviewer_kind': 'human',
        'origin': 'external_human', 'reviewed_at': '', 'status': 'pending',
        'bindings': bindings(request, statuses),
        'checks': {k: 'pending' for k in CHECKS[kind]}, 'evidence_notes': ''}


def _review(review, kind, expected):
    if not review:
        return 'HOLD', 'missing_human_review'
    validate('showcase-review', review)
    if review['policy'] != POLICY or review['kind'] != kind:
        return 'HOLD', 'different_policy_or_review_kind'
    if review['bindings'] != expected:
        return 'HOLD', 'approval_invalidated_by_input_change'
    if review['status'] == 'fail' or 'fail' in review['checks'].values():
        return 'FAIL', 'review_rejected'
    try:
        date = datetime.fromisoformat(review['reviewed_at'])
        dated = date.tzinfo is not None
    except ValueError:
        dated = False
    if (review['status'] != 'pass' or review['reviewer_kind'] != 'human'
        or review['origin'] != 'external_human'
        or not dated
        or not all(review[k].strip() for k in ('review_id', 'reviewer', 'reviewed_at', 'evidence_notes'))
        or not all(review['checks'].get(k) == 'pass' for k in CHECKS[kind])):
        return 'HOLD', 'incomplete_or_nonhuman_credential'
    return 'PASS', 'current_external_human_credential'


def decide(request, statuses):
    """Recompute validity every time; never mutate packages or old approvals.

    First-use/Transfer observations are deliberately not inputs. A claimed
    identity still requires the operator's external audit, as in legacy gates.
    Every review binds all final inputs, conservatively expiring on any change.
    """
    if request.get('content_profile') != 'FREE_SHOWCASE':
        raise ValueError('Free publication checker requires FREE_SHOWCASE; Paid needs its own review')
    validate('showcase-request', request)
    if request['policy'] != POLICY:
        raise ValueError('Unsupported publication policy')
    expected = bindings(request, statuses)
    checks, hard = {}, []
    package = request['package']
    ctx = None
    try:
        if package.get('kind') == 'free_showcase_passage/v1':
            from .showcase_passage import context
            ctx = context(package, statuses)
        else:
            validate_package(package)
            ctx = {'sources': package['source_items'],
                'current': all(statuses[b['asset_id']]['asset_id'] == b['asset_id']
                    and statuses[b['asset_id']]['semantic_binding_sha'] == b['semantic_binding_sha']
                    and statuses[b['asset_id']]['effective_status'] == 'ACTIVE'
                    for b in package['source_items'] if b['asset_id'] in statuses),
                'source_current': all(statuses[b['asset_id']]['source_sha'] == sha(b['source'])
                    for b in package['source_items'] if b['asset_id'] in statuses),
                'available': all(b['asset_id'] in statuses for b in package['source_items']),
                'scope': package['content']['content_scope'],
                'claims': {c['claim_id'] for c in package['claims']},
                'required': {c['claim_id'] for c in package['claims'] if c['kind'] in ('actual_action', 'action_stop', 'stop_rule') and c['purpose'] != 'challenge'},
                'outputs': [a['output'] for b in package['source_items'] for sel in package['selections']
                    if sel['asset_id'] == b['asset_id'] for a in b['analysis']['execution_trace']
                    if a['execution_id'] in sel['action_ids'] and a.get('output')],
                'engineering': package['pilot_status']['engineering'] == 'PASS',
                'teaching_stale': package['invalidation']['teaching_stale']}
    except (ValueError, KeyError, IndexError) as error:
        hard.append('invalid_frozen_claims:' + str(error))
    ctx = ctx or {'current': False, 'available': False, 'scope': None, 'claims': set(),
                  'required': set(), 'outputs': [], 'engineering': False, 'teaching_stale': True,
                  'source_current': False}
    current, available = ctx['current'], ctx['available']
    if not current or ctx['teaching_stale']:
        hard.append('upstream_teaching_invalid')
    # A missing status retains replay, but provides no release decision.
    if not available and not ctx['teaching_stale']:
        hard = [r for r in hard if r != 'upstream_teaching_invalid']
    scope = request['scope']
    if scope['content_scope'] != ctx['scope']:
        hard.append('scope_does_not_match_frozen_package')
    if scope['result'] == 'answer' and scope['content_scope'] != 'full_solution':
        hard.append('helper_action_cannot_claim_answer')
    outputs = ctx['outputs']
    supported = {'locate': {'located_evidence'}, 'interpret': {'interpretation', 'framework_card'},
        'group': {'candidate_partition'}, 'reduce': {'candidate_decision'},
        'verify': {'verification_result'}, 'answer': {'candidate_decision'}}
    if not any(o['kind'] in supported[scope['result']] and
               (scope['result'] != 'reduce' or o.get('effect') == 'eliminate') for o in outputs):
        hard.append('result_not_supported_by_selected_action_output')
    claim_ids = ctx['claims']
    if not scope['claim_ids'] or not set(scope['claim_ids']) <= claim_ids:
        hard.append('unbound_showcase_claim')
    required = ctx['required']
    if not required <= set(scope['claim_ids']):
        hard.append('required_action_or_stop_binding_missing')
    if scope['claim_validity'] == 'FAIL':
        hard.append('claim_invalid')
    for kind in CHECKS:
        state, reason = _review(request['reviews'].get(kind), kind, expected)
        checks[kind] = {'status': state, 'reason': reason}
        if state == 'FAIL':
            hard.append(kind + ':review_rejected')
    rights = request['source_display']['rights']
    if 'denied' in rights.values():
        hard.append('source_rights_denied')
    if not all(value == 'approved' for value in rights.values()):
        checks['source_display'] = {'status': 'HOLD', 'reason': 'source_or_audio_rights_unknown'}
    if not ctx['source_current']:
        checks['source_display'] = {'status': 'HOLD', 'reason': 'current_source_binding_changed_reexport_required'}
    media = request['media']
    media_present = bool(media['path'] and media['sha256'])
    media_audit = None
    if media_present:
        try:
            if file_sha(media['path']) != media['sha256']:
                hard.append('final_media_bytes_changed')
            for asset in media['audio_assets']:
                if file_sha(asset['path']) != asset['sha256']:
                    hard.append('audio_asset_bytes_changed')
            for asset in request['source_display']['materials']:
                if file_sha(asset['path']) != asset['sha256']:
                    hard.append('source_material_bytes_changed')
            media_audit = inspect_media(media['path'])
        except (OSError, ValueError, StopIteration, subprocess.CalledProcessError):
            hard.append('bound_media_unavailable_or_decode_failed')
    else:
        checks['final_media'] = {'status': 'HOLD', 'reason': 'no_actual_export_bound'}
    if not media['audio_assets']:
        checks['final_media'] = {'status': 'HOLD', 'reason': 'missing_bound_audio_assets'}
    eligible = (available and current and scope['claim_validity'] == 'PASS'
                and ctx['engineering'] and media_present)
    state = 'BLOCKED' if hard else 'READY_FOR_HUMAN_REVIEW' if eligible else 'INTERNAL_ONLY'
    if eligible and not hard and all(c['status'] == 'PASS' for c in checks.values()):
        state = 'APPROVED_FOR_PUBLIC_EXPORT'
    result = {'schema_version': VERSION, 'policy': POLICY, 'content_profile': 'FREE_SHOWCASE', 'state': state,
        'review_status': 'PASS' if state == 'APPROVED_FOR_PUBLIC_EXPORT' else 'HOLD',
        'public_render_ready': state == 'APPROVED_FOR_PUBLIC_EXPORT',
        'checks': checks, 'blockers': sorted(set(hard)), 'bindings': expected,
        'method_generalizability': 'NOT_ASSESSED', 'method_maturity_changed': False,
        'legacy_release_unchanged': True, 'claim_lint_is_semantic_certification': False,
        'status_source_available': available}
    result['media_audit'] = media_audit
    result['decision_sha'] = sha(result)
    validate('showcase-decision', result)
    return result


def feedback_template(content_id):
    return {'schema_version': VERSION, 'content_id': content_id,
        'publication': 'NOT_PUBLISHED', 'platform': None, 'published_version': None,
        'selection_hypothesis': '', 'hook_type': '', 'payoff_type': '',
        'expected_advantage': '', 'retention': 'UNKNOWN', 'saves': 'UNKNOWN',
        'shares': 'UNKNOWN', 't_plus_3_review': 'UNKNOWN'}
