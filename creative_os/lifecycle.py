"""Receive new manifests explicitly; never claim live external monitoring."""
from copy import deepcopy
from content_os.lifecycle import refresh
from .delivery import invalidation


def refresh_creative(package, delivery, previous_lock, timing_sha, statuses):
    upstream=refresh(package,statuses);inv=deepcopy(upstream['invalidation'])
    copy=invalidation(previous_lock,delivery,timing_sha)
    inv['teaching_stale'] |= copy['teaching_stale'];inv['editorial_stale'] |= copy['editorial_stale']
    inv['render_stale']=copy['render_stale'] or inv['teaching_stale'] or inv['editorial_stale']
    if copy['editorial_stale']:inv['reasons'].append('presentation_change:delivery_copy')
    if previous_lock.get('audio_timing_sha')!=timing_sha:inv['reasons'].append('timing_change:voice_or_pause')
    inv['reasons']=sorted(set(inv['reasons']))
    return {'invalidation':inv,'status_available':all(b['asset_id'] in statuses for b in package['source_items']),
            'copy_lock':copy['copy_lock'],'editorial_review_sha':None if inv['editorial_stale'] else previous_lock.get('editorial_review_sha'),
            'public_render_ready':False}
