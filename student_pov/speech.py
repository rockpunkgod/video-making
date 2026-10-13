"""Editorial speech observations; never certify naturalness or teaching truth."""
import math
import re


def speech_lint(text, *, max_clause_characters=18):
    clauses = [part.strip() for part in re.split(r'[。？！!?\n]+', text) if part.strip()]
    warnings = []
    for index, clause in enumerate(clauses):
        # Original English names/quotations are reported separately, not shortened.
        count = len(re.findall(r'[\u3400-\u9fffA-G]', clause))
        if count > max_clause_characters:
            warnings.append({'code': 'SPOKEN_SENTENCE_OVER_18', 'clause': index,
                             'characters': count, 'text': clause})
    if ';' in text or '；' in text:
        warnings.append({'code': 'SEMICOLON_IN_SPEECH'})
    return {'warnings': warnings, 'natural_speech_certified': False}


def narration_coverage(intervals, duration, *, timing_basis='actual'):
    """Measure union coverage, preserving intentional silence without padding VO."""
    if isinstance(duration, bool) or not math.isfinite(duration) or duration <= 0:
        raise ValueError('Positive finite duration required')
    if timing_basis not in ('actual', 'estimated'):
        raise ValueError('Timing basis must be actual or estimated')
    merged = []
    for start, end in sorted(intervals):
        if any(isinstance(v, bool) or not math.isfinite(v) for v in (start, end)) \
                or not 0 <= start < end <= duration:
            raise ValueError('Voice interval must be inside the episode')
        if merged and start <= merged[-1][1]:
            merged[-1][1] = max(merged[-1][1], end)
        else:
            merged.append([start, end])
    at = 0
    silences = []
    for start, end in merged:
        if start > at:
            silences.append([at, start])
        at = end
    if at < duration:
        silences.append([at, duration])
    voiced = sum(end - start for start, end in merged)
    longest = max((end - start for start, end in silences), default=0)
    return {'timing_basis': timing_basis, 'voiced_seconds': voiced,
            'coverage': voiced / duration, 'target_coverage': 0.55,
            'longest_silence_seconds': longest, 'warnings':
            (['VOICE_COVERAGE_BELOW_55_PERCENT'] if voiced / duration < 0.55 else [])
            + (['SILENCE_OVER_6_SECONDS'] if longest > 6 else []),
            'actual_delivery_pass': timing_basis == 'actual' and voiced / duration >= 0.55 and longest <= 6}
