"""Model-neutral adapter contract. v0.1 conservatively preserves teaching text."""
from copy import deepcopy
from typing import Protocol
from video_contracts import sha
from .director import NON_TEACHING_COPY, claim_guard, copy_payload


class LanguagePolisher(Protocol):
    def polish(self, package: dict) -> dict: ...


def polish(package, adapter: LanguagePolisher):
    before = deepcopy(package)
    result = adapter.polish(deepcopy(package))
    # Only non-teaching connective speech can change automatically in v0.1.
    expected = deepcopy(before)
    if len(result['semantic_scenes']) != len(before['semantic_scenes']):
        raise ValueError('Diff Guard: scene structure changed')
    for original, changed, target in zip(before['semantic_scenes'], result['semantic_scenes'], expected['semantic_scenes']):
        if original['spoken_text'] != changed['spoken_text']:
            if original['claim_refs'] or original['evidence_refs'] or changed['spoken_text'] not in NON_TEACHING_COPY:
                raise ValueError('Diff Guard: teaching copy changed; upstream review required')
            if claim_guard(changed['spoken_text'])['status'] != 'PASS':
                raise ValueError('Diff Guard: unsupported claim')
            target['spoken_text'] = changed['spoken_text']
            target['on_screen']['primary_text'] = changed['spoken_text']
    expected['voiceover'] = [{'scene_id': s['scene_id'], 'text': s['spoken_text']} for s in expected['semantic_scenes']]
    expected['content']['primary_hook'] = expected['semantic_scenes'][0]['spoken_text']
    expected['content']['cta'] = expected['semantic_scenes'][-1]['spoken_text']
    if result != expected:
        raise ValueError('Diff Guard: fields outside permitted copy edits changed')
    result['copy_lock']['polished_from_sha'] = sha(copy_payload(before))
    if copy_payload(result) != copy_payload(before):
        result['invalidation']['editorial_stale'] = True
        result['invalidation']['source_release_stale'] = True
        result['invalidation']['reasons'] = sorted(set(result['invalidation']['reasons'] + ['presentation_change:polisher']))
        result['pilot_status']['source_release'] = 'PENDING'
    result['copy_lock']['final_copy_sha'] = None
    result['copy_lock']['editorial_review_sha'] = None
    result['review']['editorial_review'] = None
    result['pilot_status']['editorial_release'] = 'PENDING'
    result['render_ready_for_publication'] = False
    result['status'] = 'draft'
    return result


class IdentityPolisher:
    def polish(self, package):
        return deepcopy(package)
