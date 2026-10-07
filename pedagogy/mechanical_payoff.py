"""Pure projections of reviewed candidate state, never student behaviour.

The baseline is the frozen option domain, not an observed learner path. A
current candidate check closed by this active local elimination may reopen when
upstream changes. It does not remove reading, vocabulary, time, or later checks.
"""
from copy import deepcopy
from jsonschema import ValidationError
from content_os.candidates import engineering_gate, matching_reviews, source_gate
from video_contracts import pointer, review_semantics, sha, status_matches, verify_bundle

PROJECTION_VERSION = 'frozen-candidate-transition/0.1.0'

def _ref(bundle, path):
    return {'asset_id': bundle['asset_id'], 'pointer': path,
            'sha': sha(review_semantics(pointer(bundle, path)))}

def _active(bundle, status, kind, artifact_id):
    return all(any(row['artifact_id'] == artifact_id and row['status'] == 'active'
                   for row in manifest['lifecycle'][kind]) for manifest in (bundle, status))

def _span_matches(q, e):
    field = e['field']
    if field.startswith('option:'):
        text = q.get('options', {}).get(field.split(':', 1)[1])
    elif field.startswith('options.'):
        text = q.get('options', {}).get(field.split('.', 1)[1])
    else:
        text = q.get(field)
    return (isinstance(text, str) and type(e['start']) is int and type(e['end']) is int
            and 0 <= e['start'] < e['end'] <= len(text) and text[e['start']:e['end']] == e['quote'])

def frozen_candidate_transition(bundle, status, selection):
    """Pure function; None for incomplete, ambiguous, invalid, or unsupported inputs."""
    try:
        return _project(bundle, status, selection)
    except (AttributeError, KeyError, IndexError, TypeError, ValueError, ValidationError):
        return None

def _project(bundle, status, selection):
    if not isinstance(bundle, dict) or not isinstance(status, dict):
        return None
    if (not isinstance(selection, dict) or set(selection) != {'method_id','action_ids'}
            or not isinstance(selection['method_id'], str) or not selection['method_id']
            or not isinstance(selection['action_ids'], list) or len(selection['action_ids']) != 1
            or not isinstance(selection['action_ids'][0], str) or not selection['action_ids'][0]
            or bundle.get('kind') == 'frozen_reviewed_passage'):
        return None
    verify_bundle(bundle)
    if (status is None or not status_matches(bundle, status)
            or status['question']['status'] != 'ACTIVE'
            or status['question']['snapshot_sha'] != bundle['binding_fingerprint']['question_snapshot_sha']
            or bundle['state']['effective_status'] != 'ACTIVE'
            or source_gate([bundle])['internal_use'] != 'PASS'):
        return None
    mid, aid = selection['method_id'], selection['action_ids'][0]
    if engineering_gate(bundle, {'asset_id': bundle['asset_id'], **selection},
                        'method_action_demo', status)['status'] != 'PASS':
        return None
    methods = [(i,m) for i,m in enumerate(bundle['methods']) if m['method_id'] == mid]
    if len(methods) != 1:
        return None
    mi, m = methods[0]
    if (m['primary_role'] != 'decider' or status['method_versions'].get(mid) != m['version']
            or not isinstance(m.get('stop_rule'), str) or not m['stop_rule'].strip()):
        return None
    q,a = bundle['source_snapshot'], bundle['analysis']
    if q['question_id'] != a['question_id'] or not isinstance(q.get('options'), dict) or len(q['options']) < 2:
        return None
    selected = [(i,x) for i,x in enumerate(a['execution_trace']) if x['execution_id'] == aid]
    decisions = [x for x in a['execution_trace'] if (x.get('output') or {}).get('kind') == 'candidate_decision']
    if len(selected) != 1 or len(decisions) != 1 or decisions[0]['execution_id'] != aid:
        return None
    ai,x = selected[0]
    o = x.get('output') or {}
    if (x['method_id'] != mid or x['method_version'] != m['version'] or x['role'] != 'decider'
            or x['state'] != 'produced' or x['review_status'] != 'reviewed' or x['stop_applied'] is not False
            or o.get('kind') != 'candidate_decision' or o.get('effect') != 'eliminate'
            or o.get('candidate') not in q['options'] or type(o.get('relation_index')) is not int
            or not isinstance(x.get('stop_rule_check'), str) or not x['stop_rule_check'].strip()
            or not _active(bundle, status, 'actions', aid)):
        return None
    relations = q.get('relations', [])
    rows = a['candidate_analysis']
    input_decisions = [z for z in q.get('action_executions', [])
                       if (z.get('output') or {}).get('kind') == 'candidate_decision']
    if (len(relations) != 1 or o['relation_index'] != 0 or len(rows) != 1
            or len(input_decisions) != 1 or input_decisions[0]['execution_id'] != aid
            or input_decisions[0]['output'] != o):
        return None
    c = o['candidate']
    if any(row.get('method_id') != mid or row.get('candidate') != c or row.get('effect') != 'eliminate'
           for row in (relations[0],rows[0])):
        return None
    if relations[0].get('review_status') != 'reviewed' or not _active(bundle,status,'decisions','relation:0'):
        return None
    by_id = {z['execution_id']:z for z in a['execution_trace']}
    if len(by_id) != len(a['execution_trace']):
        return None
    positions = {row['execution_id']: i for i, row in enumerate(a['execution_trace'])}
    pending,seen = [(aid, parent) for parent in x['input_artifact_ids']],set()
    while pending:
        child, parent = pending.pop()
        if (parent not in by_id or positions[parent] >= positions[child]
                or not _active(bundle,status,'actions',parent)):
            return None
        if parent in seen:
            continue
        seen.add(parent)
        z = by_id[parent]
        if z['state'] != 'produced' or z['review_status'] != 'reviewed' or z['stop_applied'] is not False:
            return None
        pending += [(parent, dependency) for dependency in z['input_artifact_ids']]
    v = a['answer_verification']
    before = sorted(q['options'])
    after = [candidate for candidate in before if candidate != c]
    unresolved = v['unresolved_candidates']
    if (a['answer'] is not None or v['closed'] is not False or v['candidate_coverage_complete'] is not False
            or v['unique_supported_candidate'] is not False or v['retained_candidates'] != []
            or v['eliminated_candidates'] != [c] or len(unresolved) != len(set(unresolved))
            or set(unresolved) != set(after)):
        return None
    ap = '/analysis/execution_trace/' + str(ai)
    ep = [ap + '/evidence/' + str(i) for i in range(len(x['evidence']))]
    if not ep or not all(_span_matches(q,e) for e in x['evidence']):
        return None
    nodes = {n['id']:n for n in a['evidence_graph']['nodes'] if n['type'] == 'source_evidence'}
    if (not x['evidence_ids'] or len(x['evidence_ids']) != len(x['evidence'])
            or len(x['evidence_ids']) != len(set(x['evidence_ids']))):
        return None
    for eid,span in zip(x['evidence_ids'],x['evidence']):
        if eid not in nodes or nodes[eid].get('span') != span or not _active(bundle,status,'evidence',eid):
            return None
    reviews = []
    for ri,cred in matching_reviews(bundle, {'asset_id':bundle['asset_id'], **selection}):
        r = cred['record']
        if r.get('method_id') != mid or r.get('method_version') != m['version'] or r.get('question_id') != q['question_id']:
            continue
        if not _active(bundle,status,'reviews',cred['artifact_id']):
            return None
        sr = r.get('semantic_review', {})
        ro,rs = sr.get('output',{}),sr.get('stop',{})
        if (sr.get('trigger',{}).get('valid') is False
                or sr.get('action',{}).get('valid') is not True or sr.get('evidence',{}).get('valid') is not True
                or ro.get('valid') is not True or ro.get('primary_role') != 'decider'
                or ro.get('output_type') != 'decide' or ro.get('artifact') != 'candidate_decision'
                or ro.get('candidate') != c or ro.get('effect') != 'eliminate'
                or not isinstance(ro.get('claim_limit'), str) or not ro['claim_limit'].strip()
                or rs.get('valid') is not True or rs.get('stop_applied') is not False
                or rs.get('action_output_usable') is not True):
            return None
        reviews.append(ri)
    if not reviews or not isinstance(m.get('four_step_card',{}).get('first_cut'), str) or not m['four_step_card']['first_cut'].strip():
        return None
    mp = '/methods/' + str(mi)
    rp = ['/reviews/' + str(i) for i in reviews]
    cp = rp[0] + '/record/semantic_review/output/claim_limit'
    action_refs = [_ref(bundle, ap)]
    evidence_refs = [_ref(bundle,p) for p in ep]
    review_refs = [_ref(bundle,p) for p in rp]
    opt_ref,out_ref,ver_ref = (_ref(bundle,p) for p in ('/source_snapshot/options',ap+'/output','/analysis/answer_verification'))
    stop_paths = [mp+'/stop_rule',ap+'/stop_rule_check']
    def wid(candidate):
        return 'current_candidate_check:' + candidate
    def bound(row, refs):
        return {**row,'source_refs':deepcopy(refs),'action_artifact_refs':deepcopy(action_refs),
                'evidence_refs':deepcopy(evidence_refs),'review_refs':deepcopy(review_refs)}
    after_work = [wid(candidate) for candidate in after]
    stop_ids = ['method_stop_condition','action_stop_condition']
    record = {
        'scope':{'question_id':q['question_id'],'method_id':mid,'method_version':m['version'],
                 'action_ids':[aid],'stage':'current_candidate','claim_scope':'local_candidate'},
        'origin':'frozen_candidate_transition','projection_version':PROJECTION_VERSION,
        'baseline_kind':'structural_candidate_state','baseline_measured':False,
        'temporal_learner_path_asserted':False,'learner_transfer_validated':False,
        'first_action_transferable':True,
        'first_action_transferability_basis':'existing_frozen_method_action_template_only',
        'first_action_ref':_ref(bundle,mp+'/four_step_card/first_cut'),
        'payoff_type':'TYPE_A',
        'baseline_path':[bound({'step_id':'frozen-option-domain','text':' / '.join(before),
                               'candidate_ids':before,'work_ids':[wid(candidate) for candidate in before]},[opt_ref])],
        'method_path':[bound({'step_id':'unresolved-after-local-elimination','text':' / '.join(after),
                             'candidate_ids':after,'work_ids':after_work},[out_ref,ver_ref])],
        'removed_steps':[bound({'work_id':wid(c),'text':c,
                               'scope':'current_candidate_check_closed_by_this_active_elimination',
                               'reopen_on_upstream_change':True},[out_ref,ver_ref])],
        'remaining_steps':[bound({'work_id':wid(candidate),'text':q['options'][candidate],
                                  'candidate_id':candidate,'scope':'unresolved_candidate_check'},
                                 [_ref(bundle,'/source_snapshot/options/'+candidate.replace('~','~0').replace('/','~1')),ver_ref])
                           for candidate in after]+[
                               bound({'work_id':sid,'text':pointer(bundle,p),'scope':'stop_condition'},[_ref(bundle,p)])
                               for sid,p in zip(stop_ids,stop_paths)],
        'cognitive_work':{'removed':[wid(c)],'deferred':[],'still_required':after_work+stop_ids},
        'reduction':bound({'before':len(before),'after':len(after),'unit':'candidate',
                           'before_ids':before,'after_ids':after},[opt_ref,out_ref,ver_ref]),
        'allowed_claim':pointer(bundle,cp),'allowed_claim_refs':[_ref(bundle,cp)],
        'cognitive_relief_line':pointer(bundle,cp),'cognitive_relief_refs':[_ref(bundle,cp)],
        'evidence_pointers':ep,
        'output_anchors':[{'output_index':0,'pointer':'/'+k,'sha':sha(o[k])} for k in ('kind','candidate','effect')],
        'answer_scope':{'may_output_final_answer':False,'answer':None,'closed':False,
                        'remaining_candidates':after,'source_refs':[ver_ref]},
        'stop_refs':[_ref(bundle,p) for p in stop_paths],
        'prohibited_inferences':['observed_student_baseline','reading_removed','vocabulary_removed','time_saved',
                                 'measured_cognitive_load_gain','remaining_candidate_correct','final_answer',
                                 'permanent_elimination_after_upstream_change']}
    return {'record':record,'origin':record['origin'],'baseline_kind':record['baseline_kind'],
            'baseline_measured':False,
            'source_refs':[opt_ref,out_ref,ver_ref,_ref(bundle,cp),_ref(bundle,mp+'/four_step_card/first_cut'),
                           _ref(bundle,'/source_snapshot/relations/0')],
            'action_artifact_refs':action_refs,'evidence_refs':evidence_refs,'review_refs':review_refs}
