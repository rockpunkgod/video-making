"""Resolve authored focus cues into anchors for the existing native camera driver."""
from .shot_script import number


def camera_plan(script, layouts, style):
    objects = {o['id']: o for o in script['objects']}
    cues = []; previous = -1
    for cue in script.get('focus_cues', []):
        at = number(cue['at'], 'focus time')
        if not previous < at <= script['duration']:
            raise ValueError('Focus cues must be strictly ordered within shot')
        previous = at
        if cue['state'] not in ('read', 'search', 'recognize', 'hit', 'end'):
            raise ValueError('Unsupported cognitive camera state')
        plan = layouts[objects[cue['object_id']]['layout_id']]
        index = cue['window_index']
        if type(index) is not int or not 0 <= index < len(plan['focus_windows']):
            raise ValueError('Unknown focus window')
        bounds = plan['focus_windows'][index]['bounds']
        tier = {'read':'drift','search':'snap','recognize':'drift','hit':'hold','end':'hold'}[cue['state']]
        # The native driver owns camera distance, DOF and final projected glyph coordinates.
        cues.append(dict(cue, target_center=[(bounds['left']+bounds['right'])/2,
                                             (bounds['top']+bounds['bottom'])/2],
                         bounds=dict(bounds), speed_tier=tier,
                         speed_parameters=dict(style['motion']['speed_tiers'][tier]),
                         carry_speed=cue['state'] not in ('hit','end')))
    return dict(schema='camera-focus-handoff/v1', cues=cues,
                geometry='PROVISIONAL_REQUIRES_AE_MEASUREMENT',
                interpolation='existing_RCF_cameraKeys', native_speed_curve_verified=False)
