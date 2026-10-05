"""Versioned presentation profiles; these are simulations, not platform policy."""
from copy import deepcopy
from video_contracts import ROOT,read


def resolve_profile(requested=None):
    catalog=read(ROOT/'ae/design/platform-profiles.json')
    name=requested.get('platform') if isinstance(requested,dict) else requested or 'CN_VERTICAL_GENERIC'
    if name not in catalog['profiles']:raise ValueError('Unknown platform profile')
    result=deepcopy(catalog['base'])
    for key,value in catalog['profiles'][name].items():
        result[key].update(value) if isinstance(value,dict) else result.update({key:value})
    result.update(platform=name,version=catalog['version'],status=catalog['status'])
    if isinstance(requested,dict) and requested!=result:raise ValueError('Platform profile drift; update the versioned catalog')
    for rect in [result['safe_area_profile']['core']]+result['ui_overlay_profile']['exclusion_rects']:
        x,y,w,h=rect
        if min(x,y)<0 or min(w,h)<=0 or x+w>1080 or y+h>1920:raise ValueError('Invalid platform rectangle')
    return result


def intersection(a,b):
    x=max(a[0],b[0]);y=max(a[1],b[1]);right=min(a[0]+a[2],b[0]+b[2]);bottom=min(a[1]+a[3],b[1]+b[3])
    if right<=x or bottom<=y:raise ValueError('layout_overflow: platform / brand intersection empty')
    return [x,y,right-x,bottom-y]
