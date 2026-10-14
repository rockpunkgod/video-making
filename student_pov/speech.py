"""Editorial speech observations; never certify naturalness or teaching truth."""
import math
import re


def speech_lint(text, *, max_clause_characters=18):
    clauses = [part.strip() for part in re.split(r'[。？！!?\n]+', text) if part.strip()]
    warnings = []
    for index, clause in enumerate(clauses):
        # Original English names/quotations are reported separately, not shortened.
        count = len(re.findall(r'[\u3400-\u9fff]', clause))
        if count > max_clause_characters:
            warnings.append({'code': 'SPOKEN_SENTENCE_OVER_18', 'clause': index,
                             'characters': count, 'text': clause})
        if clause.count('、') > 2:
            warnings.append({'code': 'ENUMERATION_OVER_TWO', 'clause': index, 'text': clause})
    if ';' in text or '；' in text:
        warnings.append({'code': 'SEMICOLON_IN_SPEECH'})
    for word in ('我们', '同学们', '大家', '核', '拿掉', '换成了', '这里是在解释',
                 '可以发现', '由此可见', '综上', '值得注意的是'):
        if word in text:
            warnings.append({'code': 'PEER_VOICE_WORDING_REVIEW', 'phrase': word})
    if re.search(r'我当年|我高考时|我考了|我以前.*选错', text):
        warnings.append({'code': 'BIOGRAPHY_CLAIM_REVIEW'})
    return {'warnings': warnings, 'natural_speech_certified': False}


def narration_coverage(intervals, duration, *, timing_basis='actual', exemptions=None):
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
    approved = []
    for item in exemptions or []:
        if (set(item) != {'start', 'end', 'kind', 'reason', 'reviewer'}
                or item['kind'] not in ('reading', 'cognitive', 'intro', 'outro')
                or not isinstance(item['reason'], str) or not item['reason'].strip()
                or not isinstance(item['reviewer'], str) or not item['reviewer'].strip()):
            raise ValueError('Pause exemption requires type, duration, reason and reviewer')
        start, end = item['start'], item['end']
        if (any(isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v)
                for v in (start, end)) or not 0 <= start < end <= duration
                or not any(a <= start < end <= b for a, b in silences)
                or any(start < b and end > a for a, b in approved)):
            raise ValueError('Exemptions must be distinct intervals wholly inside actual silence')
        approved.append([start, end])
    unexempted = []
    for start, end in silences:
        at = start
        for a, b in sorted(approved):
            if start <= a < b <= end:
                if a > at: unexempted.append([at, a])
                at = b
        if at < end: unexempted.append([at, end])
    exempt_seconds = sum(b-a for a,b in approved)
    adjusted_duration = duration - exempt_seconds
    adjusted_coverage = voiced / adjusted_duration if adjusted_duration else None
    max_gap = max((b-a for a,b in unexempted), default=0)
    warnings = (['VOICE_COVERAGE_BELOW_55_PERCENT'] if adjusted_coverage is None or adjusted_coverage < .55 else [])
    if max_gap > 6: warnings.append('SILENCE_OVER_6_SECONDS')
    if exempt_seconds / duration > .2: warnings.append('EXEMPTIONS_OVER_20_PERCENT_REVIEW_EPISODE')
    if merged and merged[0][0] > 1 and any(a == 0 for a,b in unexempted):
        warnings.append('OPENING_VOICE_AFTER_ONE_SECOND')
    return {'timing_basis': timing_basis, 'voiced_seconds': voiced,
            'coverage': voiced / duration, 'target_coverage': 0.55,
            'adjusted_coverage': adjusted_coverage, 'exempt_seconds': exempt_seconds,
            'exemptions': exemptions or [], 'longest_unexempted_silence_seconds': max_gap,
            'longest_silence_seconds': longest, 'warnings': warnings,
            'review_status': 'REVIEW_REQUIRED' if warnings else 'CHECK_LINES_MET',
            'natural_speech_certified': False,
            'actual_delivery_pass': timing_basis == 'actual' and not warnings}
