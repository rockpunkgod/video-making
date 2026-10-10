"""Small local audience ledger. Creative suggestions never approve publication.

All records are immutable, content-addressed JSON; SQLite transactions prevent
duplicate versions and races. Human identities are external declarations, as in
showcase reviews, and must be authenticated by the operator.
"""
from copy import deepcopy
import csv
from datetime import datetime, timezone, timedelta
import json
import math
from pathlib import Path
import sqlite3
import subprocess
from urllib.parse import urlparse

from video_contracts import sha, now, validate, seal, verify_seal
from content_os.showcase import feedback_template, file_sha, inspect_media
from creative_os.content_profiles import PROFILES, HARD_GATES
from creative_os.episode import validate_episode

VERSION = '0.2.0'
DIMENSIONS = {
    'Hook Strength': ('Hook', '当前真实问题是否建立继续看的理由'),
    'Information Clarity': ('Visual Impact', '题面、目标、焦点、关键证据是否易接收'),
    'First-person Flow': ('Narrative', '是否呈现连续真实操作而非课件讲解'),
    'Anticipation': ('Engagement', '信息期待是否建立在已见信息上'),
    'Cognitive Payoff': ('Cognitive Payoff', '有据动作的实际收益与视觉落点是否清晰'),
    'Rhythm & Holds': ('Voice Performance', '快慢、静默与声音是否服务观察和发现'),
    'Question Novelty': ('Narrative', '后续题目是否拥有独立观看价值'),
    'Memorability / Share Motivation': ('Memorability', '是否留下可辨识、值得记住或分享的动作'),
}
METRICS = {'views', 'average_watch_time', 'completion_rate', 'likes', 'saves',
           'shares', 'comments', 'follows'}
RELEASE_KEYS = {'title_version', 'cover_version', 'description_version'}


class _Connection(sqlite3.Connection):
    def __exit__(self, *args):
        try: return super().__exit__(*args)
        finally: self.close()


def dated(value):
    date = datetime.fromisoformat(value)
    if date.tzinfo is None: raise ValueError('Timezone-aware timestamp required')
    return date


def text_fields(value, names):
    if any(not isinstance(value.get(k), str) or not value[k].strip() for k in names):
        raise ValueError('Nonempty fields required: ' + ', '.join(names))


def number(value, minimum=0, maximum=None):
    if type(value) not in (float, int) or not math.isfinite(value) or value < minimum or (maximum is not None and value > maximum):
        raise ValueError('Finite numeric value outside permitted range')
    return value


def initial_rubric():
    return {'schema_version': VERSION, 'rubric_version': 'free-engagement-0.2.0',
        'content_profile': 'FREE_SHOWCASE', 'priority': 'Experience First',
        'base_dimensions': list(PROFILES['FREE_SHOWCASE']['rubric']),
        'hard_gates': list(HARD_GATES),
        'dimensions': {k: {'parent': v[0], 'definition': v[1]} for k, v in DIMENSIONS.items()},
        'shareability_parent': 'Shareability', 'weights': None,
        'confidence': 'LOW_EDITORIAL_JUDGEMENT', 'public_render_ready': False}


def learning_template(episode_id):
    """Extend the existing template, with UNKNOWN still distinct from zero."""
    return {**feedback_template(episode_id), 'learning_version': VERSION,
        't_plus_7_review': 'UNKNOWN', 'actual_media_mapping': 'UNAVAILABLE',
        'metrics': {k: None for k in sorted(METRICS)},
        'retention_curve': None, 'traffic_source': None,
        'human_taste': 'PENDING', 'teaching_effectiveness': 'NOT_ASSESSED'}


def verify_files(assets):
    if not assets: raise ValueError('Actual asset bindings required')
    for asset in assets:
        if file_sha(asset['path']) != asset['sha256']:
            raise ValueError('Bound asset bytes changed')


def cut_bindings(episode, copy, timeline, assets, media):
    return {'episode_sha': sha(episode), 'final_copy_sha': sha(copy),
        'native_timeline_sha': sha(timeline), 'assets_sha': sha(assets),
        'final_media_sha': file_sha(media) if media and Path(media).is_file() else None}


def encoded_frames(media):
    value = json.loads(subprocess.check_output(['ffprobe','-v','error','-select_streams','v:0',
        '-count_frames','-show_entries','stream=nb_read_frames,r_frame_rate','-of','json',str(media)],encoding='utf-8'))
    video = value['streams'][0]
    if video['r_frame_rate'] != '24/1': raise ValueError('Actual 24fps export required')
    return int(video['nb_read_frames'])


def inspect_final_cut(episode, statuses, copy, timeline, assets, media):
    """No final-cut approval without real decoded media and all actual tracks.

    assets requires subtitles, voice, music_sfx (explicit silence declaration is
    allowed), and native_receipts. Paths are read-only. No teaching writer exists.
    """
    audit = validate_episode(episode, statuses)
    if audit['engineering_status'] != 'PASS': raise ValueError('Current episode required')
    bindings = cut_bindings(episode, copy, timeline, assets, media)
    missing = [k for k in ('subtitles', 'voice', 'music_sfx', 'native_receipts') if not assets.get(k)]
    if set(timeline) != {'sequence','settings','voices'}:
        missing.append('actual_native_timeline_readback')
    result = {'schema_version': VERSION, 'kind': 'final_cut_inspection',
        'bindings': bindings, 'status': 'PENDING', 'missing': missing,
        'assets': deepcopy(assets), 'media_path': str(media) if media else None,
        'media_audit': None, 'human_taste': 'PENDING', 'public_render_ready': False}
    if not bindings['final_media_sha']:
        result['missing'].append('actual_mp4'); return result
    for kind, rows in assets.items():
        if kind not in ('subtitles', 'voice', 'music_sfx', 'native_receipts'):
            raise ValueError('Unsupported final asset category')
        if kind == 'music_sfx' and rows == [{'silence': True}]: continue
        if not rows: continue
        verify_files(rows)
    if missing: return result
    try:
        result['media_audit'] = inspect_media(media)
    except (ValueError, StopIteration, OSError, subprocess.CalledProcessError) as exc:
        result['missing'].append('complete_av_export: ' + str(exc)); return result
    if file_sha(media) != bindings['final_media_sha']:
        raise ValueError('Export changed during inspection')
    from premiere_production.cinema import audit_timeline
    result['timeline_audit'] = audit_timeline(timeline['sequence'],timeline['settings'],timeline['voices'],encoded_frames(media)/24)
    clips = [c for t in timeline['sequence'].get('videoTracks',[]) for c in t['clips']]
    if not clips: raise ValueError('Actual native picture clips required')
    result['native_source_shas'] = {c['mediaPath']:file_sha(c['mediaPath']) for c in clips}
    result['status'] = 'READY_FOR_REVIEW'
    return result


def bind_media_beats(plan, episode, statuses, direction, media, sequence, settings,
                     voices, ranges, credential):
    """Consume verified Premiere readback, actual export and human frame anchors.

    Half-open frame ranges; each anchor names its actual native clip. A master
    picture clip may cover several beats. Its subranges require human verification
    against the export, not interpolation of director estimates.
    """
    from creative_os.audience_engagement import validate_engagement
    from premiere_production.cinema import audit_timeline
    validate_engagement(plan, episode, statuses, direction)
    probe = inspect_media(media)
    total = encoded_frames(media)
    audit_timeline(sequence, settings, voices, total/24)
    bindings = {'episode_sha': sha(episode), 'engagement_plan_sha': sha(plan),
        'native_timeline_sha': sha(sequence), 'settings_sha': sha(settings),
        'media_sha': file_sha(media), 'ranges_sha': sha(ranges)}
    human_credential(credential, bindings)
    clips = [c for track in sequence['videoTracks'] for c in track['clips']]
    expected = {(q['question_id'], b['beat_id']) for q in plan['questions'] for b in q['beats']}
    keys = [(r['question_id'], r['beat_id']) for r in ranges]
    if len(keys) != len(set(keys)) or set(keys) != expected:
        raise ValueError('Exact per-question beat anchors required')
    rows = []
    for row in ranges:
        a, b = row['start_frame'], row['end_frame']
        if type(a) is not int or type(b) is not int or not 0 <= a < b <= total:
            raise ValueError('Actual frame range invalid')
        matches = [c for c in clips if c.get('nodeId') == row['native_clip_id']]
        if len(matches) != 1 or not matches[0].get('mediaPath'):
            raise ValueError('Unique actual native clip required')
        clip = matches[0]
        if a / 24 < clip['start'] - 1e-6 or b / 24 > clip['end'] + 1e-6:
            raise ValueError('Beat anchor lies outside its actual native clip')
        rows.append({'question_id': row['question_id'], 'beat_id': row['beat_id'],
            'actual_media': {'start_frame': a, 'end_frame': b, 'fps': 24,
                             'media_sha': bindings['media_sha']}})
    return seal({'schema_version': VERSION, 'kind': 'actual_media_beat_mapping',
        'bindings': bindings, 'ranges': rows, 'credential': deepcopy(credential),
        'status': 'VERIFIED_DECLARED_FRAME_ANCHORS', 'public_render_ready': False})


def validate_mapping(mapping, plan, episode, sequence, settings, media):
    verify_seal(mapping)
    b = mapping['bindings']
    if any(b[k] != v for k, v in {'episode_sha': sha(episode), 'engagement_plan_sha': sha(plan),
            'native_timeline_sha': sha(sequence), 'settings_sha': sha(settings),
            'media_sha': file_sha(media)}.items()):
        raise ValueError('Stale actual media mapping; rebind changed timeline/export')
    human_credential(mapping['credential'], b)
    return True


def human_credential(credential, bindings):
    text_fields(credential, ('reviewer', 'review_id', 'reviewed_at', 'evidence_notes'))
    dated(credential['reviewed_at'])
    if (credential.get('reviewer_kind') != 'human' or credential.get('origin') != 'external_human'
            or credential.get('status') != 'pass' or credential.get('watched_final') is not True
            or credential.get('bindings') != bindings):
        raise ValueError('Current external human viewing credential required')


class AudienceLearning:
    """Append-only local ledger; each API call validates inside one transaction."""
    def __init__(self, root, *, synthetic=False):
        self.root = Path(root).resolve()
        # Do not allow a database to appear in the Truth Domain by path accident.
        if self.root.name != 'audience-learning' or self.root.parent.name != 'local-data':
            raise ValueError('Use local-data/audience-learning as the private ledger root')
        self.root.mkdir(parents=True, exist_ok=True)
        self.db = self.root / ('synthetic.sqlite3' if synthetic else 'audience.sqlite3')
        self.synthetic = synthetic
        with self.connect() as con:
            con.executescript('''CREATE TABLE IF NOT EXISTS records (
                seq INTEGER PRIMARY KEY, id TEXT UNIQUE NOT NULL, kind TEXT NOT NULL,
                payload TEXT NOT NULL, previous_sha TEXT, record_sha TEXT NOT NULL);
                CREATE TRIGGER IF NOT EXISTS no_update BEFORE UPDATE ON records
                BEGIN SELECT RAISE(ABORT, 'immutable audience record'); END;
                CREATE TRIGGER IF NOT EXISTS no_delete BEFORE DELETE ON records
                BEGIN SELECT RAISE(ABORT, 'immutable audience record'); END;''')

    def connect(self):
        return sqlite3.connect(self.db, timeout=30, factory=_Connection)

    def records(self, con=None):
        if con is None:
            with self.connect() as connection: return self.records(connection)
        records, previous = [], None
        for _, ident, kind, payload, parent, digest in con.execute('SELECT * FROM records ORDER BY seq'):
            value = json.loads(payload)
            if parent != previous or sha({'id': ident, 'kind': kind, 'payload': value, 'previous_sha': parent}) != digest:
                raise ValueError('Audience ledger hash chain changed')
            records.append({'id': ident, 'kind': kind, 'payload': value}); previous = digest
        return records

    def get(self, ident, kind=None, con=None):
        matches = [r for r in self.records(con) if r['id'] == ident and (kind is None or r['kind'] == kind)]
        if len(matches) != 1: raise ValueError('Missing record or wrong kind: ' + ident)
        return matches[0]['payload']

    def _save(self, kind, payload, check=None):
        payload = deepcopy(payload)
        payload.update(schema_version=VERSION, data_domain='CREATIVE_LEARNING',
            data_label='SYNTHETIC TEST ONLY' if self.synthetic else 'OPERATOR_RECORDED',
            recorded_at=now(), public_render_ready=False)
        schema = {'prediction':'audience-experiment', 'performance':'audience-performance'}.get(kind)
        if schema: validate(schema, payload)
        ident = kind + ':' + sha(payload)
        with self.connect() as con:
            con.execute('BEGIN IMMEDIATE')
            records = self.records(con)
            if check: check(con, records)
            last = con.execute('SELECT record_sha FROM records ORDER BY seq DESC LIMIT 1').fetchone()
            previous = last[0] if last else None
            digest = sha({'id': ident, 'kind': kind, 'payload': payload, 'previous_sha': previous})
            con.execute('INSERT INTO records(id,kind,payload,previous_sha,record_sha) VALUES(?,?,?,?,?)',
                (ident, kind, json.dumps(payload, ensure_ascii=False, allow_nan=False), previous, digest))
        return ident

    def freeze(self, spec, episode, statuses, copy, timeline, *, inspection=None):
        text_fields(spec, ('experiment_id', 'episode_id', 'platform', 'cut_version', 'rubric_version', 'author'))
        text_fields(spec, RELEASE_KEYS)
        if validate_episode(episode, statuses)['engineering_status'] != 'PASS':
            raise ValueError('Current episode required')
        if spec.get('post_data_seen') is not False:
            raise ValueError('Known post-publication data cannot be a blind prediction')
        hypotheses = spec.get('hypotheses', [])
        if not hypotheses: raise ValueError('Explicit testable hypotheses required')
        seen = set()
        for h in hypotheses:
            text_fields(h, ('hypothesis_id', 'claim', 'affected_question', 'affected_beat', 'expected_advantage', 'possible_failure'))
            if h['hypothesis_id'] in seen: raise ValueError('Duplicate hypothesis')
            seen.add(h['hypothesis_id'])
            q = next((q for q in episode['questions'] if q['question_id'] == h['affected_question']), None)
            if not q or h['affected_beat'] not in {b['beat_id'] for b in q['narrative_beats']}:
                raise ValueError('Hypothesis refers to missing/cross-question beat')
            if not isinstance(h.get('evidence_to_collect'), list) or not h['evidence_to_collect'] or any(not isinstance(x, str) or not x.strip() for x in h['evidence_to_collect']):
                raise ValueError('Evidence collection plan required')
        allowed = {'experiment_id', 'episode_id', 'platform', 'cut_version', 'rubric_version', 'author',
                   'post_data_seen', 'hypotheses'} | RELEASE_KEYS
        if set(spec) - {'creative_rule_refs'} != allowed: raise ValueError('Unsupported prediction fields; no precise reach forecasts')
        for ident in spec.get('creative_rule_refs', []):
            if self.get(ident, 'activation')['rule_kind'] != 'CREATIVE_PATTERN':
                raise ValueError('Next episode references reviewed creative patterns only')
        final = inspection is not None and inspection.get('status') == 'READY_FOR_REVIEW'
        bindings = {'episode_sha': sha(episode), 'final_copy_sha': sha(copy),
                    'native_timeline_sha': sha(timeline), 'final_media_sha': None}
        if final:
            current_inspection = inspect_final_cut(episode, statuses, copy, timeline,
                inspection['assets'], inspection['media_path'])
            if current_inspection != inspection:
                raise ValueError('Stale or fabricated final-cut inspection')
            if any(inspection['bindings'][k] != bindings[k] for k in bindings if k != 'final_media_sha'):
                raise ValueError('Final-cut inspection binds another version')
            bindings = deepcopy(inspection['bindings'])
        payload = {**deepcopy(spec), **bindings,
            'prediction_status': 'FROZEN_FINAL_CUT' if final else 'PRE_PRODUCTION_HYPOTHESIS',
            'prediction_created_at': now(), 'publication_status': 'NOT_REGISTERED_AT_FREEZE',
            'confidence': 'LOW_EDITORIAL_JUDGEMENT',
            'inspection_sha': sha(inspection) if final else None,
            'inspection': deepcopy(inspection) if final else None,
            'frozen_copy': deepcopy(copy), 'frozen_timeline': deepcopy(timeline),
            'questions': {q['question_id']: [b['beat_id'] for b in q['narrative_beats']] for q in episode['questions']}}
        def check(con, records):
            rubric = initial_rubric()['rubric_version']
            active = [r['payload']['rubric']['rubric_version'] for r in records if r['kind'] == 'activation' and r['payload']['rule_kind'] == 'EVALUATION_RULE']
            if spec['rubric_version'] != (active[-1] if active else rubric):
                raise ValueError('Prediction must bind the currently effective rubric')
            for r in records:
                p = r['payload']
                if r['kind'] in ('publication', 'performance') and p.get('episode_id') == spec['episode_id']:
                    raise ValueError('Episode already published/observed; blind channel closed')
                if final and r['kind'] == 'publication' and p.get('media_sha') == bindings['final_media_sha']:
                    raise ValueError('Media already published/observed; changing episode ID cannot restore blindness')
                if r['kind'] == 'prediction' and all(p[k] == spec[k] for k in ('experiment_id','platform','cut_version')):
                    raise ValueError('Frozen prediction immutable; create a new cut_version')
        return self._save('prediction', payload, check)

    def publish(self, prediction_id, publication):
        text_fields(publication, ('platform_post_id', 'published_at', 'publication_url', 'registrar'))
        if set(publication) != {'platform_post_id','published_at','publication_url','registrar','media_sha','actual_publication'} | RELEASE_KEYS:
            raise ValueError('Unexpected publication field')
        if publication['actual_publication'] is not True or urlparse(publication['publication_url']).scheme not in ('http', 'https'):
            raise ValueError('Actual publication declaration and URL required')
        pub_date = dated(publication['published_at'])
        def check(con, records):
            pred = self.get(prediction_id, 'prediction', con)
            if pred['prediction_status'] != 'FROZEN_FINAL_CUT': raise ValueError('Planning hypothesis cannot be published as final prediction')
            if publication['media_sha'] != pred['final_media_sha'] or any(publication[k] != pred[k] for k in RELEASE_KEYS):
                raise ValueError('Published media/title/cover/description differs from frozen version')
            if file_sha(pred['inspection']['media_path']) != pred['final_media_sha']:
                raise ValueError('Frozen export bytes changed; freeze a new version')
            for assets in pred['inspection']['assets'].values():
                if assets != [{'silence':True}]: verify_files(assets)
            for path, digest in pred['inspection']['native_source_shas'].items():
                if file_sha(path) != digest: raise ValueError('Actual native source bytes changed')
            if pub_date <= dated(pred['prediction_created_at']) or pub_date > datetime.now(timezone.utc):
                raise ValueError('Actual publication must follow freeze and cannot be future dated')
            if any(r['kind'] == 'publication' and (r['payload']['prediction_id'] == prediction_id or
                    (r['payload']['platform'] == pred['platform'] and r['payload']['platform_post_id'] == publication['platform_post_id'])) for r in records):
                raise ValueError('Publication already registered')
        pred = self.get(prediction_id, 'prediction')
        return self._save('publication', {**deepcopy(publication), 'prediction_id': prediction_id,
            **{k: pred[k] for k in ('episode_id','platform','cut_version')},
            'publication_status': 'REGISTERED'}, check)

    def performance(self, publication_id, observation):
        pub = self.get(publication_id, 'publication')
        text_fields(observation, ('source', 'collected_at', 'window_start', 'window_end', 'window_label', 'platform', 'cut_version'))
        if set(observation) != {'source','collected_at','window_start','window_end','window_label','platform','cut_version',
                'is_real_observation','metrics','retention_curve','traffic_source'}:
            raise ValueError('Unexpected performance field')
        if observation['is_real_observation'] is not (not self.synthetic):
            raise ValueError('Real and SYNTHETIC TEST ONLY observations cannot mix')
        if any(observation[k] != pub[k] for k in ('platform','cut_version')):
            raise ValueError('Platform or cut version mismatch')
        a, b, c = map(dated, (observation['window_start'], observation['window_end'], observation['collected_at']))
        if not dated(pub['published_at']) <= a < b <= c <= datetime.now(timezone.utc):
            raise ValueError('Invalid observation statistical window/collection time')
        label = observation['window_label']
        if label not in ('T+3','T+7','T+30','CUSTOM'): raise ValueError('Unsupported statistical window')
        if label != 'CUSTOM' and (a != dated(pub['published_at']) or abs((b-a).total_seconds()-int(label[2:])*86400) > 1):
            raise ValueError('Named window must cover the exact publication age')
        metrics = observation['metrics']
        if not set(metrics) <= METRICS: raise ValueError('Unknown metric')
        for key, metric in metrics.items():
            if metric is None: continue
            if set(metric) != {'value','numerator','denominator','unit'}: raise ValueError('Metric provenance required')
            value = number(metric['value'], maximum=1 if key=='completion_rate' else None)
            number(metric['numerator'])
            if metric['denominator'] is not None:
                denominator = number(metric['denominator'], minimum=1e-12)
                if not math.isclose(value, metric['numerator']/denominator, rel_tol=1e-6, abs_tol=1e-9):
                    raise ValueError('Metric ratio disagrees with numerator/denominator')
            elif key in ('completion_rate','average_watch_time'):
                raise ValueError('Rate/average needs an explicit denominator')
            elif metric['numerator'] != value: raise ValueError('Count numerator disagrees')
            if key not in ('completion_rate','average_watch_time') and (metric['denominator'] is not None or int(value) != value):
                raise ValueError('Counts require integer numerator and no ratio denominator')
            expected_unit = 'ratio' if key=='completion_rate' else 'seconds' if key=='average_watch_time' else 'count'
            if metric['unit'] != expected_unit: raise ValueError('Metric unit mismatch')
        curve = observation['retention_curve']
        if curve is not None:
            text_fields(curve, ('source','time_basis'))
            if curve['time_basis'] != 'MEDIA_SECONDS' or not curve.get('points'): raise ValueError('Actual retention samples required')
            pred = self.get(pub['prediction_id'], 'prediction')
            if curve.get('media_sha') != pred['final_media_sha']: raise ValueError('Retention curve media version mismatch')
            previous = -1
            for point in curve['points']:
                second = number(point['second']); number(point['numerator']); denominator = number(point['denominator'], minimum=1e-12)
                if second > pred['inspection']['media_audit']['duration']:
                    raise ValueError('Retention sample lies beyond the bound actual media')
                number(point['rate'], maximum=1)
                if second <= previous or not math.isclose(point['rate'],point['numerator']/denominator,rel_tol=1e-6):
                    raise ValueError('Invalid retention samples/order')
                previous = second
        payload = {**deepcopy(observation), 'publication_id': publication_id,
            'episode_id': pub['episode_id'], 'prediction_id': pub['prediction_id'],
            'publication_age_days': (b-dated(pub['published_at'])).total_seconds()/86400,
            'missing_fields': sorted([k for k in METRICS if metrics.get(k) is None] +
                [k for k in ('retention_curve','traffic_source') if observation[k] is None]),
            'teaching_effectiveness': 'NOT_ASSESSED'}
        return self._save('performance', payload)

    def import_csv(self, publication_id, path, metadata):
        """One snapshot per CSV: metric,value,numerator,denominator,unit.

        Empty value is missing, never zero. Exact source file SHA is retained.
        """
        metrics = {}
        with Path(path).open(encoding='utf-8-sig', newline='') as stream:
            reader = csv.DictReader(stream)
            if reader.fieldnames != ['metric','value','numerator','denominator','unit']:
                raise ValueError('CSV header must be metric,value,numerator,denominator,unit')
            for row in reader:
                key = row.pop('metric')
                if key in metrics: raise ValueError('Duplicate CSV metric')
                if not row['value'].strip(): metrics[key] = None; continue
                metrics[key] = {k: (None if not v.strip() else float(v)) if k != 'unit' else v for k,v in row.items()}
        value = deepcopy(metadata); value['metrics'] = metrics
        value['source'] += '; CSV SHA256=' + file_sha(path)
        return self.performance(publication_id, value)

    def feedback(self, prediction_id, item):
        pred = self.get(prediction_id, 'prediction')
        text_fields(item, ('feedbacker','text','experience_issue','question_id','beat_id'))
        if set(item) != {'feedbacker','text','experience_issue','question_id','beat_id','media_sha','channel',
                         'watched_final','confirmed_summary','rechecked','teaching_issue'}:
            raise ValueError('Unexpected feedback field')
        if pred['final_media_sha'] is None or item['media_sha'] != pred['final_media_sha']:
            raise ValueError('Feedback must bind the actual watched version')
        if item['channel'] not in ('PLATFORM_COMMENT','EDITORIAL_SCREENING') or item['watched_final'] is not True:
            raise ValueError('Separate actual comments and actual editorial screenings')
        if item['question_id'] not in pred['questions'] or item['beat_id'] not in pred['questions'][item['question_id']]:
            raise ValueError('Feedback segment mismatch')
        for k in ('rechecked','confirmed_summary','teaching_issue'):
            if type(item[k]) is not bool: raise ValueError('Explicit feedback declaration required')
        def check(con, records):
            if item['channel'] == 'PLATFORM_COMMENT' and not any(r['kind']=='publication' and r['payload']['prediction_id']==prediction_id for r in records):
                raise ValueError('Platform comment requires actual publication')
        return self._save('feedback', {**deepcopy(item), 'prediction_id': prediction_id,
            'episode_id': pred['episode_id'], 'result_kind': 'teaching_issue_candidate' if item['teaching_issue'] else 'experience_feedback',
            'human_taste': 'PENDING'}, check)

    def score(self, prediction_id, review, *, inspection=None):
        pred = self.get(prediction_id, 'prediction')
        text_fields(review, ('reviewer','reviewer_kind','review_version','reviewed_at','stage'))
        dated(review['reviewed_at'])
        if set(review) != {'reviewer','reviewer_kind','review_version','reviewed_at','stage','watched_final','dimensions','human_credential'}:
            raise ValueError('Unexpected score field')
        if review['stage'] not in ('PRE_PRODUCTION','FINAL_CUT') or type(review['watched_final']) is not bool:
            raise ValueError('Explicit review stage/viewing status required')
        rubric = initial_rubric()
        for r in self.records():
            if r['kind']=='activation' and r['payload']['rule_kind']=='EVALUATION_RULE' and r['payload']['rubric']['rubric_version']==pred['rubric_version']:
                rubric = r['payload']['rubric']
        if set(review['dimensions']) != set(rubric['dimensions']): raise ValueError('All current rubric definitions required')
        for row in review['dimensions'].values():
            text_fields(row, ('evidence','recommended_edit','timecode','timecode_basis'))
            if row['timecode_basis'] not in ('PLANNED','ACTUAL_MEDIA'): raise ValueError('Explicit timecode basis required')
            grade = row['grade']
            if type(grade) in (int,float): number(grade, maximum=5)
            elif grade not in ('LOW','MEDIUM','HIGH','PENDING'): raise ValueError('Qualitative or 0–5 grade required')
        ready = review['stage'] == 'PRE_PRODUCTION'
        if review['stage']=='FINAL_CUT':
            if inspection and inspection.get('status')=='READY_FOR_REVIEW':
                if file_sha(inspection['media_path']) != inspection['bindings']['final_media_sha']:
                    raise ValueError('Final export changed since review')
                for kind, assets in inspection['assets'].items():
                    if assets != [{'silence':True}]: verify_files(assets)
                for path, digest in inspection['native_source_shas'].items():
                    if file_sha(path) != digest: raise ValueError('Actual native source bytes changed')
            ready = bool(inspection and inspection.get('status')=='READY_FOR_REVIEW' and review['watched_final'] and
                pred['inspection_sha']==sha(inspection))
            if ready and any(r['timecode_basis']!='ACTUAL_MEDIA' for r in review['dimensions'].values()):
                raise ValueError('Final-cut scores require actual media timecodes')
        taste = 'PENDING'
        if review.get('human_credential'):
            if not ready or review['stage']!='FINAL_CUT' or review['reviewer_kind']!='human':
                raise ValueError('Human taste cannot inherit planning/AI scores')
            human_credential(review['human_credential'], inspection['bindings'])
            if review['human_credential']['reviewer'] != review['reviewer']: raise ValueError('Reviewer identity mismatch')
            taste = 'PASS_EXTERNAL_DECLARATION'
        stored_review = deepcopy(review)
        if not ready:
            for row in stored_review['dimensions'].values(): row['grade'] = 'PENDING'
        return self._save('score', {'prediction_id': prediction_id, 'rubric_version':pred['rubric_version'],
            'review': stored_review, 'status': 'RECORDED_EDITORIAL_JUDGEMENT' if ready else 'PENDING',
            'human_taste': taste, 'overall_score': None})

    def retrospective(self, performance_id, judgements, *, mapping=None):
        observation = self.get(performance_id, 'performance')
        pred = self.get(observation['prediction_id'], 'prediction')
        hypotheses = {h['hypothesis_id']: h for h in pred['hypotheses']}
        if set(judgements) != set(hypotheses): raise ValueError('Review every frozen hypothesis')
        feedback = [r for r in self.records() if r['kind']=='feedback' and r['payload']['prediction_id']==observation['prediction_id']]
        available = {'metric:'+k for k in METRICS if observation['metrics'].get(k) is not None} | {r['id'] for r in feedback}
        rows = []
        for hid, row in judgements.items():
            text_fields(row, ('reason','next_director_edit'))
            if row['status'] not in ('INCONCLUSIVE','CONSISTENT','CONTRADICTED'):
                raise ValueError('No automatic causal verification')
            if not set(row['evidence_refs']) <= available: raise ValueError('Judgement cites unavailable evidence')
            if row['status'] != 'INCONCLUSIVE' and not row['evidence_refs']: raise ValueError('Evidence required')
            rows.append({'hypothesis_id': hid, 'frozen_hypothesis': hypotheses[hid], **deepcopy(row),
                'status_scope':'DESCRIPTIVE_NOT_CAUSAL', 'confidence':'LOW',
                'source_constraints':'保留必要 Evidence、Stop、Role 与实际动作范围；由 Director 审阅建议'})
        beat_status = 'UNAVAILABLE'
        if mapping is not None:
            # Mapping must be separately revalidated by bind/validate_mapping.
            raise ValueError('Use beat_retrospective with current media/timeline; no unchecked mapping')
        return self._save('retrospective', {'performance_id':performance_id,
            'episode_id':pred['episode_id'], 'prediction_id':observation['prediction_id'],
            'window_label':observation['window_label'], 'rows':rows,
            'beat_analysis':beat_status, 'human_taste':'PENDING', 'teaching_effectiveness':'NOT_ASSESSED'})

    def beat_retrospective(self, performance_id, mapping, plan, episode, statuses, direction, sequence, settings, media):
        from creative_os.audience_engagement import validate_engagement
        validate_engagement(plan, episode, statuses, direction)
        observation = self.get(performance_id, 'performance')
        pred = self.get(observation['prediction_id'], 'prediction')
        validate_mapping(mapping,plan,episode,sequence,settings,media)
        if pred['final_media_sha'] != mapping['bindings']['media_sha'] or pred['episode_sha'] != sha(episode):
            raise ValueError('Mapping binds another publication')
        curve = observation['retention_curve']
        rows=[]
        if curve:
            for r in mapping['ranges']:
                actual = r['actual_media']
                samples = [p for p in curve['points'] if actual['start_frame']/actual['fps'] <= p['second'] < actual['end_frame']/actual['fps']]
                rows.append({**deepcopy(r), 'observed_samples':samples,
                    'status':'DESCRIPTIVE_SAMPLES_ONLY' if samples else 'UNAVAILABLE',
                    'causal_attribution':'NOT_ESTABLISHED'})
        return self._save('beat_retrospective', {'performance_id':performance_id,
            'mapping_sha':sha(mapping),'status':'DESCRIPTIVE_SAMPLES_ONLY' if curve else 'UNAVAILABLE','rows':rows})

    def propose_rule(self, proposal):
        text_fields(proposal, ('rule_kind','rule','source','applicable_conditions','proposer'))
        if set(proposal) != {'rule_kind','rule','source','applicable_conditions','proposer','supporting_retros',
                             'opposing_retros','change_log','new_rubric'}:
            raise ValueError('Unsupported proposal fields; creative domain only')
        if proposal['rule_kind'] not in ('EVALUATION_RULE','CREATIVE_PATTERN'): raise ValueError('Separate learning outputs')
        supporting, opposing = proposal['supporting_retros'], proposal['opposing_retros']
        if not supporting or set(supporting) & set(opposing): raise ValueError('Evidence and explicit counterexamples required')
        for ident in supporting + opposing: self.get(ident, 'retrospective')
        episodes = {self.get(i, 'retrospective')['episode_id'] for i in supporting}
        if proposal['rule_kind']=='EVALUATION_RULE':
            rubric = proposal['new_rubric']; validate('audience-rubric', rubric)
            if not proposal['change_log'] or rubric.get('weights') is not None:
                raise ValueError('MVP supports documented qualitative rubric changes only')
            if rubric['rubric_version']==initial_rubric()['rubric_version']:
                raise ValueError('New rubric requires new version')
        elif proposal['new_rubric'] is not None: raise ValueError('Creative pattern is not a rubric')
        return self._save('proposal', {**deepcopy(proposal), 'confidence':'LOW',
            'state':'CROSS_EPISODE_CANDIDATE' if len(episodes)>1 else 'SINGLE_EPISODE_OBSERVATION',
            'effective_version':None})

    def activate_rule(self, proposal_id, review):
        proposal = self.get(proposal_id,'proposal')
        text_fields(review, ('reviewer','reviewer_kind','reviewed_at','evidence_notes','effective_version','overfit_check','holdout_plan'))
        dated(review['reviewed_at'])
        if set(review) != {'reviewer','reviewer_kind','reviewed_at','evidence_notes','effective_version','overfit_check',
                         'holdout_plan','origin','status','replay','bindings'}:
            raise ValueError('Unexpected independent review field')
        bindings = {'proposal_sha':sha(proposal)}
        if (review['reviewer_kind'] != 'human' or review.get('origin') != 'external_human' or review.get('status') != 'pass'
                or review['reviewer']==proposal['proposer'] or review['bindings']!=bindings):
            raise ValueError('Independent external human/editorial review required')
        supports = [self.get(i,'retrospective') for i in proposal['supporting_retros']]
        if len({r['episode_id'] for r in supports}) < 2:
            raise ValueError('Single episode/comment cannot establish a reusable rule')
        samples = proposal['supporting_retros'] + proposal['opposing_retros']
        if not set(samples) <= set(review['replay']): raise ValueError('Replay all supporting and opposing historical samples')
        comparison_keys = set()
        for ident, row in review['replay'].items():
            text_fields(row, ('old_evaluation','new_evaluation','reason'))
            if row.get('comparable') is not True: raise ValueError('Only comparable historical samples')
            retro = self.get(ident,'retrospective'); obs=self.get(retro['performance_id'],'performance')
            comparison_keys.add((obs['platform'],obs['window_label'],(dated(obs['window_end'])-dated(obs['window_start'])).total_seconds()))
        if len(comparison_keys) != 1: raise ValueError('Different platforms/statistical windows cannot be pooled')
        # Replay the whole comparable pool, including samples omitted by proposer.
        roster = set()
        for record in self.records():
            if record['kind'] != 'retrospective': continue
            obs = self.get(record['payload']['performance_id'], 'performance')
            key = (obs['platform'],obs['window_label'],(dated(obs['window_end'])-dated(obs['window_start'])).total_seconds())
            if key in comparison_keys: roster.add(record['id'])
        if set(review['replay']) != roster:
            raise ValueError('Replay the entire comparable historical pool, not selected winners')
        rubric = proposal['new_rubric'] if proposal['rule_kind']=='EVALUATION_RULE' else None
        if rubric and rubric['rubric_version']!=review['effective_version']: raise ValueError('Effective rubric version mismatch')
        def check(con, records):
            if any(r['kind']=='activation' and (r['payload']['proposal_id']==proposal_id or
                    (r['payload']['rule_kind']==proposal['rule_kind'] and r['payload']['effective_version']==review['effective_version'])) for r in records):
                raise ValueError('Immutable effective version already exists')
        return self._save('activation', {'proposal_id':proposal_id,'rule_kind':proposal['rule_kind'],
            'review':deepcopy(review),'effective_version':review['effective_version'],'rubric':rubric,
            'future_validation':'PENDING_HOLDOUT', 'statistical_validity':'NOT_ESTABLISHED'}, check)

    def record_rule_review(self, proposal_id, review):
        """Preserve rejections too; this record never makes a rule effective."""
        proposal = self.get(proposal_id, 'proposal')
        text_fields(review, ('reviewer','reviewer_kind','reviewed_at','evidence_notes'))
        dated(review['reviewed_at'])
        if (review.get('origin') != 'external_human' or review['reviewer_kind'] != 'human'
                or review['reviewer'] == proposal['proposer']
                or review.get('status') not in ('pass','reject')
                or review.get('bindings') != {'proposal_sha':sha(proposal)}):
            raise ValueError('Independent external review with exact proposal binding required')
        return self._save('rule_review', {'proposal_id':proposal_id,'review':deepcopy(review),
            'effective_version':None,'status':'RECORDED_NOT_ACTIVATED'})

    def director_candidates(self):
        """Explicit suggestions for next episode. No runtime parameters or claims."""
        result = []
        for r in self.records():
            if r['kind']=='activation' and r['payload']['rule_kind']=='CREATIVE_PATTERN':
                proposal = self.get(r['payload']['proposal_id'],'proposal')
                result.append({'rule':proposal['rule'],'applicable_conditions':proposal['applicable_conditions'],
                    'activation_id':r['id'],'confidence':'LOW','status':'REVIEWED_CREATIVE_SUGGESTION',
                    'future_validation':'PENDING_HOLDOUT'})
        return result
