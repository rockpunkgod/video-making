"""Conservative, versioned disclosure rules; no invented risk scores."""
import re

VERSION = '0.1.0'
MODES = ('first_touch', 'worked_example', 'counterexample', 'boundary',
         'transfer', 'hard_case', 'review')
CHANNELS = ('video', 'lesson', 'card', 'wechat')
GOLDEN_METHODS = ('R01', 'R02', 'R06', 'R09', 'F01', 'G01')
CASE_CONTENT_MATRIX = {
    'canonical': ('first_touch', 'worked_example'),
    'counterexample': ('counterexample',),
    'boundary': ('boundary',),
    'transfer': ('transfer',),
    'hard': ('hard_case',),
}
MODE_CASE = {'counterexample': 'counterexample', 'boundary': 'boundary',
             'transfer': 'transfer', 'hard_case': 'hard'}
RISK_LEVELS = ('low', 'medium', 'high', 'unknown')
FIRST_TOUCH_BUDGET = {'core_actions': 2, 'primary_boundary': 1,
                      'memory_phrase': 1, 'primary_evidence_cluster': 1,
                      'simultaneous_concepts': 3, 'max_item_characters': 180,
                      'max_memory_characters': 80}
INTERNAL_CODE = re.compile(r'(?<![A-Za-z0-9])[RFCGWS]\d{2}(?![A-Za-z0-9])')
ENGINE_FIELDS = ('method_id', 'method_version', 'role', 'review_refs',
                 'evidence_refs', 'source_analysis_sha', 'release_state')
PROHIBITED_CHANGES = ('answer_mutation', 'evidence_addition', 'role_upgrade',
    'stop_removal', 'certainty_upgrade', 'maturity_upgrade',
    'hidden_required_boundary', 'new_case', 'semantic_rewrite')


def surface_text(text):
    """Only typed implementation labels are translated/removed.

    This deliberately does not shorten sentences, change quantifiers, delete
    caveats, paraphrase English, or decide which clauses are important.
    """
    text = INTERNAL_CODE.sub('', text)
    return text.replace('word_answer', '填词答案').strip()


def disclosure(risk, *, engineering=False, current_stop=False):
    if set(risk) != {'frequency', 'severity', 'current_relevance'} or any(
            v not in RISK_LEVELS for v in risk.values()):
        raise ValueError('Risk must use low/medium/high/unknown, without numeric scores')
    if engineering:
        return 'ENGINE_ONLY', 'Typed implementation metadata; never a student rule'
    if current_stop or risk['current_relevance'] == 'high':
        return 'TELL_NOW', 'Current action Stop or explicitly current boundary'
    if 'unknown' in risk.values():
        return 'TELL_NOW', 'Unknown risk is not low risk'
    if risk['severity'] == 'high':
        return 'TELL_NOW', 'Severe risk retained until a separate human disclosure decision'
    if risk['current_relevance'] == 'medium' or risk['frequency'] == 'high':
        return 'TELL_NOW', 'Relevant or frequent caveat'
    return 'TELL_LATER', 'Explicit bound risk assessment permits deferred teaching'


def overload(metrics, items):
    failures = [k for k, v in metrics.items()
                if k in FIRST_TOUCH_BUDGET and v > FIRST_TOUCH_BUDGET[k]]
    if any(len(i['text']) > FIRST_TOUCH_BUDGET['max_item_characters'] for i in items):
        failures.append('long_student_explanation')
    memory = next((i for i in items if i['item_id'] == 'memory_phrase'), None)
    if memory and len(memory['text']) > FIRST_TOUCH_BUDGET['max_memory_characters']:
        failures.append('long_memory_phrase')
    if any(INTERNAL_CODE.search(i['text']) for i in items):
        failures.append('internal_method_identifier')
    return sorted(set(failures))


def claim_lint(text, role):
    """Deterministic lint only, never semantic truth certification."""
    if re.search(r'秒杀|必考|百分之百|100%|都必须|直接出答案', text):
        return ['unsupported_absolute_or_performance_claim']
    overclaim = r'做到这里答案就是|找到原句就能选|找到这句话就能选|所以填具体词|到这里词形就确定'
    if role != 'decider' and re.search(overclaim, text):
        return ['auxiliary_role_overclaim']
    return []
