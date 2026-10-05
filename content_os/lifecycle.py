"""Synchronous refresh on supplied manifests, not a background observer."""
from copy import deepcopy
from video_contracts import sha, validate, verify_seal


def refresh(artifact, statuses):
    result = deepcopy(artifact)
    inv = result.setdefault('invalidation', {'teaching_stale': False, 'source_release_stale': False, 'editorial_stale': False, 'reasons': []})
    changes = []
    if 'copy_lock' in result and result['copy_lock'].get('final_copy_sha'):
        from .director import copy_payload
        from .release import displayed_text, display_payload
        if result['copy_lock']['final_copy_sha'] != sha(copy_payload(result)):
            inv['editorial_stale'] = True
            changes.append('presentation_change:final_copy')
        display = result['source_display']
        if display['displayed_text_sha'] != sha(displayed_text(result)) or display['displayed_image_sha'] != sha(display['images']):
            inv['source_release_stale'] = True
            inv['editorial_stale'] = True
            changes.append('presentation_change:actual_source_display')
        source_review = result.get('review', {}).get('source_review')
        if source_review and source_review.get('display_sha') != sha(display_payload(result)):
            inv['source_release_stale'] = True
            changes.append('presentation_change:reviewed_source_display')
    for b in result.get('source_items', []):
        st = statuses.get(b['asset_id'])
        if st is None:
            changes.append('status_unavailable:' + b['asset_id'])
            continue
        validate('artifact-status-manifest', st); verify_seal(st)
        if st['asset_id'] != b['asset_id']:
            raise ValueError('Status identity mismatch')
        if st['semantic_binding_sha'] != b['semantic_binding_sha'] or st['effective_status'] != 'ACTIVE':
            inv['teaching_stale'] = True; inv['editorial_stale'] = True
            changes.append('semantic_change:' + b['asset_id'] + ':' + st['effective_status'])
            changes.extend(st['invalidation_reasons'])
        if st['source_sha'] != sha(b['source']):
            inv['source_release_stale'] = True
            changes.append('rights_change:' + b['asset_id'])
        if st['presentation_sha'] != b['presentation_sha']:
            inv['editorial_stale'] = True
            changes.append('presentation_change:' + b['asset_id'])
    inv['reasons'] = sorted(set(inv['reasons'] + changes))
    if inv['teaching_stale']:
        result['status'] = 'stale'
        if 'engineering_pilot_eligible' in result:
            result['engineering_pilot_eligible'] = False
    if 'pilot_status' in result:
        if inv['teaching_stale']:
            result['pilot_status']['semantic_release'] = 'PENDING'
        if inv['source_release_stale']:
            result['pilot_status']['source_release'] = 'PENDING'
        if inv['editorial_stale']:
            result['pilot_status']['editorial_release'] = 'PENDING'
            result['copy_lock']['editorial_review_sha'] = None
        if changes or any(inv[k] for k in ('teaching_stale', 'source_release_stale', 'editorial_stale')):
            result['render_ready_for_publication'] = False
    return result


def refresh_catalog(catalog, statuses):
    """Catalog embeds artifacts; parent IDs cover render/pending-publication assets."""
    result = deepcopy(catalog)
    entries = result['entries']
    ids = {e['id'] for e in entries}
    if len(ids) != len(entries) or any(not set(e.get('parent_ids', [])) <= ids for e in entries):
        raise ValueError('Duplicate or missing catalog dependency')
    by_id = {e['id']: e for e in entries}
    pending, done = set(ids), set()
    while pending:
        ready = sorted(i for i in pending if set(by_id[i].get('parent_ids', [])) <= done)
        if not ready:
            raise ValueError('Catalog dependency cycle')
        for i in ready:
            e = by_id[i]
            e['artifact'] = refresh(e['artifact'], statuses)
            inv = e['artifact']['invalidation']
            for parent in e.get('parent_ids', []):
                previous = by_id[parent]['artifact']['invalidation']
                for key in ('teaching_stale', 'source_release_stale', 'editorial_stale'):
                    inv[key] |= previous[key]
                inv['reasons'] = sorted(set(inv['reasons'] + previous['reasons']))
            if any(inv[k] for k in ('teaching_stale', 'source_release_stale', 'editorial_stale')):
                e['artifact']['render_ready_for_publication'] = False
                e['artifact']['status'] = 'stale' if inv['teaching_stale'] else 'review_required'
            pending.remove(i); done.add(i)
    return result
