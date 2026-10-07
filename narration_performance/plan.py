"""Finite performance intent, bound to the existing Student POV 0.3 script."""
from copy import deepcopy
import math

from video_contracts import ROOT, _validator, read, sha
from student_pov.realization import FUNCTIONS, SILENCE_EVENTS
from student_pov.validation import inspect_historical, validate_copy

VERSION = '0.1.0'
TONES = ('conversational', 'alert', 'focused', 'firm', 'curious', 'relieved', 'restrained')
KEY_BEATS = ('pain', 'interrupt', 'action', 'payoff', 'stop')
DEFAULTS = {
    'pain': ('alert', .62, .58, .55, 0, 500),
    'interrupt': ('firm', .72, .64, .82, 0, 250),
    'focus': ('focused', .50, .42, .65, 150, 250),
    'action': ('conversational', .66, .62, .72, 100, 200),
    'collapse': ('restrained', .40, .40, .85, 0, 500),
    'payoff': ('relieved', .62, .46, .94, 375, 500),
    'stop': ('firm', .40, .35, .96, 0, 600),
    'stamp': ('restrained', .42, .42, .95, 0, 400),
}
INTENT_KEYS = {'tone', 'energy', 'pace', 'certainty', 'emphasis', 'pause_before_ms', 'pause_after_ms'}
SCHEMA = ROOT / 'creative/voice-performance/narration-performance.schema.json'


def default_intent(function):
    tone, energy, pace, certainty, before, after = DEFAULTS[function]
    return dict(tone=tone, energy=energy, pace=pace, certainty=certainty,
                emphasis=[], pause_before_ms=before, pause_after_ms=after)


def check_intent(intent, transcript):
    if set(intent) != INTENT_KEYS or intent['tone'] not in TONES:
        raise ValueError('Unsupported performance intent or tone; no generic emotion API')
    for name in ('energy', 'pace', 'certainty'):
        value = intent[name]
        if type(value) not in (int, float) or not math.isfinite(value) or not 0 <= value <= 1:
            raise ValueError('Performance ' + name + ' must be finite within 0..1')
    for name in ('pause_before_ms', 'pause_after_ms'):
        if type(intent[name]) is not int or not 0 <= intent[name] <= 2000:
            raise ValueError('Performance pause must be integer milliseconds within 0..2000')
    emphasis = intent['emphasis']
    if (not isinstance(emphasis, list)
            or any(not isinstance(word, str) or not word or word not in transcript for word in emphasis)
            or len(emphasis) != len(set(emphasis))):
        raise ValueError('Emphasis must reference exact existing transcript text')


def build_plan(copy, spec, overrides=None):
    inspect_historical(copy)
    if copy['availability']['status'] != 'READY':
        raise ValueError('Performance cannot upgrade HOLD Copy or PAYOFF_UNSUPPORTED')
    if copy['schema_version'] != '0.3.0' or copy['method_id'] != 'R02' or copy['mode'] != 'worked_example':
        raise ValueError('Narration Performance v0.1 is R02 bounded worked_example only')
    if (spec['copy_lock']['final_copy_sha'] != copy['final_copy_sha']
            or spec['copy_sha'] != copy['copy_sha']
            or spec['plan_sha'] != copy['source_pedagogy_plan']['plan_sha']):
        raise ValueError('Performance production spec changed its frozen Copy binding')
    scenes = copy['final_script']; voiced = [s for s in scenes if s['vo']]
    slots = spec['direction']['voice_slots']
    if [(s['scene_id'], s['vo']) for s in voiced] != [(s['scene_id'], s['text']) for s in slots]:
        raise ValueError('Performance must use the exact existing Voice Slots')
    overrides = deepcopy(overrides or {})
    if not isinstance(overrides, dict) or set(overrides) - {s['scene_id'] for s in voiced}:
        raise ValueError('Performance cannot add VO to a silent cognitive beat')
    clips = []
    for scene in voiced:
        function = scene['cognitive_function']
        if function not in FUNCTIONS:
            raise ValueError('Unknown cognitive function')
        override = overrides.get(scene['scene_id'], {})
        if not isinstance(override, dict) or set(override) - {'intent', 'take_count'}:
            raise ValueError('Performance overrides may not rewrite Copy or teaching fields')
        supplied = override.get('intent', {})
        if not isinstance(supplied, dict) or set(supplied) - INTENT_KEYS:
            raise ValueError('Unknown performance control')
        intent = {**default_intent(function), **deepcopy(supplied)}
        check_intent(intent, scene['vo'])
        count = override.get('take_count', 2 if function in KEY_BEATS else 1)
        if type(count) is not int or not 1 <= count <= 3 or function not in KEY_BEATS and count != 1:
            raise ValueError('Only actual key beats may have up to three Takes')
        clips.append({'id': scene['scene_id'], 'scene_id': scene['scene_id'],
            'cognitive_function': function, 'transcript': scene['vo'], 'transcript_sha': sha(scene['vo']),
            'source_refs': {'pedagogy': deepcopy(scene['pedagogy_ref']),
                            'evidence': deepcopy(scene['evidence_ref'])},
            'intent': intent, 'take_policy': {'count': count, 'selection_status': 'PENDING_HUMAN_LISTENING'}})
    silence = deepcopy(copy['silence_candidates'])
    if any(s['event'] not in SILENCE_EVENTS for s in silence):
        raise ValueError('Unknown existing Silence Event')
    value = {'schema': 'narration-performance/v1', 'version': VERSION,
        'binding': {'method_id': copy['method_id'], 'plan_id': copy['source_pedagogy_plan']['plan_id'],
            'source_plan_sha': copy['source_pedagogy_plan']['plan_sha'],
            'source_analysis_sha': copy['source_analysis_sha'], 'copy_sha': copy['copy_sha'],
            'script_sha': copy['script_sha'], 'final_copy_sha': copy['final_copy_sha'],
            'production_spec_sha': spec['spec_sha'], 'teaching_semantic_sha': spec['semantic_binding_sha']},
        'global_voice': {'personality': 'bright_neutral_intelligent', 'melancholic_drift_forbidden': True,
                         'gain_is_not_energy': True},
        'clips': clips, 'silent_beats': [{'scene_id': s['scene_id'],
            'cognitive_function': s['cognitive_function'], 'pedagogy_refs': deepcopy(s['pedagogy_ref'])}
            for s in scenes if not s['vo']],
        'silence_events': silence, 'direction_overrides': overrides, 'copy_issue_candidates': [],
        'reference_bank': 'RESERVED_NOT_ENABLED', 'listening_review': 'PENDING',
        'final_voice_accepted': False, 'sample_delivery_allowed': False, 'public_render_ready': False}
    value['performance_sha'] = sha(value)
    value['performance_id'] = 'narration-performance:' + value['performance_sha']
    return value


def validate_plan(value, copy, spec):
    try:
        _validator(str(SCHEMA), SCHEMA.stat().st_mtime_ns).validate(value)
    except Exception as error:
        raise ValueError('Invalid narration performance schema: ' + str(error)) from error
    if value != build_plan(copy, spec, value['direction_overrides']):
        raise ValueError('Performance Plan changed its script, transcript, sources or intent binding')
    return value


def load_context(request):
    """Replay existing current-upstream gates; never run Analyzer/Registry."""
    from creative_os.student_sample import validate_spec
    copy, projection, pedagogy, bundle, status, spec = (read(request[k]) for k in
        ('copy', 'projection', 'plan', 'bundle', 'status', 'spec'))
    gate = validate_copy(copy, projection, pedagogy, bundle, status)
    if not gate['consumption_allowed']:
        raise ValueError('Performance requires current READY Copy; HOLD stays HOLD')
    validate_spec(spec, copy, projection, pedagogy, bundle, status)
    return copy, spec
