"""Source/owner/graph consistency of externally reviewed objective images.

This module does not interpret an image or decide whether a question needs one.
Only a separately frozen source obligation makes image evidence mandatory.
"""
from .image_evidence import check_image_region, image_manifest
from .answer_consistency import artifact_fingerprint


def image_ref(region):
    return {key: region[key] for key in ('image_id', 'sha256', 'box')}


def region_identity(region):
    return (region['image_id'], region['sha256'], tuple(region['box']))


def validate_objective_graph_shape(analysis):
    """Fail closed without core even for fully resealed malformed proof graphs."""
    graph=analysis['evidence_graph']
    ids=[n['id'] for n in graph['nodes']]
    if len(ids)!=len(set(ids)):
        raise ValueError('Repeated objective image proof node')
    known=set(ids); adjacency={nid:[] for nid in ids}; seen=set()
    for edge in graph['edges']:
        identity=(edge['from'],edge['to'],edge['type'])
        if edge['from'] not in known or edge['to'] not in known or identity in seen:
            raise ValueError('Dangling or repeated objective image proof edge')
        seen.add(identity); adjacency[edge['from']].append(edge['to'])
    colors={}
    def visit(nid):
        if colors.get(nid)==1:
            raise ValueError('Circular objective image proof')
        if colors.get(nid)==2: return
        colors[nid]=1
        for child in adjacency[nid]: visit(child)
        colors[nid]=2
    for nid in ids: visit(nid)


def validate_source_image_obligations(question, manifest, candidates=None):
    """Validate supplied source obligations without inventing an external review.

Projection-only renderers have no original bytes and pass manifest=None;
Analyzer/portable source consumers must supply a decoded original manifest.
"""
    requirements = question.get('required_image_evidence', [])
    if 'required_image_evidence' in question and not requirements:
        raise ValueError('Source image obligations must be nonempty when supplied')
    owners=set(question.get('options', {})) if candidates is None else set(candidates)
    seen = set()
    for obligation in requirements:
        owner = obligation['candidate']
        if owner not in owners:
            raise ValueError('Source image obligation has an unknown candidate owner')
        if manifest is not None:
            check_image_region(obligation, manifest)
        identity = (owner, region_identity(obligation))
        if identity in seen:
            raise ValueError('Repeated source image obligation')
        seen.add(identity)
    return seen


def validate_image_inputs(question, review, manifest):
    checks = {c['candidate']: c for c in review['candidate_checks']}
    seen = validate_source_image_obligations(question, manifest, checks)
    if review['schema_version'] != '1.1.0':
        if seen or any('image_evidence' in c for c in checks.values()):
            raise ValueError('Objective image evidence requires terminal review 1.1.0')
        return
    available = set()
    for owner, check in checks.items():
        regions = check.get('image_evidence', [])
        if 'image_evidence' in check and not regions:
            raise ValueError('Candidate image evidence cannot be an empty downgrade')
        for region in regions:
            check_image_region(region, manifest)
            if not region['observed'].strip():
                raise ValueError('Image observation must be a concrete external assertion')
            identity = (owner, region_identity(region))
            if identity in available:
                raise ValueError('Repeated candidate image region')
            available.add(identity)
    if not seen <= available:
        raise ValueError('Whole-question review dropped a source-required candidate image region')
    if not available:
        raise ValueError('Terminal review 1.1.0 requires at least one supplied image region')


def scope_fingerprint(report):
    if report['review']['schema_version'] == '1.0.0':
        return artifact_fingerprint(report['review'])
    return artifact_fingerprint({key: report[key] for key in
        ('review', 'image_manifest', 'required_image_evidence') if key in report})


def region_fingerprint(report, candidate, index):
    return artifact_fingerprint({'scope_sha256': scope_fingerprint(report),
                                 'candidate': candidate, 'region_index': index})


def validate_image_projection(analysis, question=None):
    """Validate both directions of owner-specific terminal image bindings."""
    report = analysis.get('question_verification')
    root = (analysis['evidence_graph']['nodes'] or [{}])[0]
    required = root.get('required_image_evidence', [])
    if question is not None:
        if (('required_image_evidence' in root) != ('required_image_evidence' in question)
                or required != question.get('required_image_evidence', [])):
            raise ValueError('Frozen image obligations differ from original question material')
    if report is None:
        if any(n['type']=='image_evidence' for n in analysis['evidence_graph']['nodes']):
            raise ValueError('Source image obligations cannot drop the terminal review')
        if required:
            if question is not None and question.get('question_verification_review') is not None:
                raise ValueError('Source-only image scan cannot drop a supplied terminal review')
            feedback=analysis.get('lesson_feedback')
            if (analysis['answer'] is not None or analysis['answer_verification']['closed']
                    or analysis['content_eligible'] or analysis['answer_confidence']!='low'
                    or analysis['status'] not in {'needs_evidence','incomplete_input'}
                    or analysis.get('review_scope') in {'external_whole_question_review','external_single_question_lesson'}
                    or any((n['type'].startswith('question_') and n['type']!='question_signal')
                           or n.get('review_id') for n in analysis['evidence_graph']['nodes'])
                    or (feedback and (feedback['scope']=='single_question_lesson'
                        or feedback['review']['segments'] or feedback['segment_bindings']
                        or feedback['grouping_execution_ids']))):
                raise ValueError('Source-only image scan cannot retain an answer, terminal or spoken proof')
            validate_objective_graph_shape(analysis)
            source=question if question is not None else {'required_image_evidence':required}
            validate_source_image_obligations(source,
                image_manifest(question) if question is not None else None,
                None if question is not None else root.get('candidate_ids',[]))
        return
    review = report['review']
    if review['schema_version'] != '1.1.0':
        if (required or 'image_manifest' in report or 'required_image_evidence' in report
                or any('image_evidence' in c for c in review['candidate_checks'])
                or any('image_evidence_ids' in b for b in report['candidate_bindings'])
                or any(n['type']=='image_evidence' for n in analysis['evidence_graph']['nodes'])):
            raise ValueError('Objective image evidence cannot downgrade to an old terminal interface')
        return
    manifest = report.get('image_manifest')
    if analysis.get('schema_version')!='1.9.0':
        raise ValueError('Objective image review requires analysis transport 1.9.0')
    if not isinstance(manifest, list):
        raise ValueError('Objective image review requires its verified image manifest')
    asset_ids = [a['image_id'] for a in manifest]
    if len(asset_ids) != len(set(asset_ids)):
        raise ValueError('Repeated projected original image')
    for asset in manifest:
        if any(type(asset[k]) is not int or asset[k] < 1 for k in ('width', 'height')):
            raise ValueError('Projected image dimensions must be positive integers')
    if (('required_image_evidence' in report) != ('required_image_evidence' in root)
            or report.get('required_image_evidence', []) != required):
        raise ValueError('Terminal image obligations differ from frozen question scope')
    if question is not None and image_manifest(question) != manifest:
        raise ValueError('Terminal image manifest differs from decoded original payloads')
    validate_image_inputs({'required_image_evidence': required} if required else {}, review, manifest)
    graph = analysis['evidence_graph']
    nodes = {n['id']: n for n in graph['nodes']}
    edges = {(e['from'], e['to'], e['type']) for e in graph['edges']}
    expected_ids = set()
    expected_edges = set()
    for check, binding in zip(review['candidate_checks'], report['candidate_bindings']):
        regions = check.get('image_evidence', [])
        ids = binding.get('image_evidence_ids')
        if not isinstance(ids, list) or len(ids) != len(regions) or len(ids) != len(set(ids)):
            raise ValueError('Candidate image graph coverage differs from its review')
        for index, (region, nid) in enumerate(zip(regions, ids)):
            node = nodes.get(nid, {})
            if (nid in expected_ids or node.get('type') != 'image_evidence'
                    or set(node) != {'id','type','label','candidate','review_id','image_ref','artifact_fingerprint'}
                    or node.get('candidate') != check['candidate']
                    or node.get('review_id') != review['review_id']
                    or node.get('label') != region['observed']
                    or node.get('image_ref') != image_ref(region)
                    or node.get('artifact_fingerprint') != region_fingerprint(report, check['candidate'], index)):
                raise ValueError('Candidate image evidence differs from its own region/observation payload')
            expected_ids.add(nid)
            expected_edges.add((nid, binding['review_node_id'], 'supports'))
        incoming = {(source, kind) for source, target, kind in edges
                    if target == binding['review_node_id'] and nodes[source]['type'] == 'image_evidence'}
        if incoming != {(nid, 'supports') for nid in ids}:
            raise ValueError('Candidate image evidence has missing, foreign or mistyped proof edges')
    if {n['id'] for n in nodes.values() if n['type'] == 'image_evidence'} != expected_ids:
        raise ValueError('Objective image graph contains unbound or dropped image nodes')
    validate_image_lesson(analysis, question)
    feedback=analysis.get('lesson_feedback')
    if feedback and feedback['scope']=='single_question_lesson':
        for binding in feedback['segment_bindings']:
            expected_edges.update((nid,binding['relation_node_id'],'supports')
                                  for nid in binding.get('image_evidence_ids',[]))
    actual_edges={(source,target,kind) for source,target,kind in edges if source in expected_ids}
    if actual_edges!=expected_edges or any(target in expected_ids for _,target,_ in edges):
        raise ValueError('Objective image proof edges exceed their terminal/spoken owners')


def segment_image_ids(segment, analysis):
    """Resolve canonical candidate/region-index references, never copied claims."""
    terminal = analysis.get('question_verification')
    checks = {c['candidate']: c for c in terminal['review']['candidate_checks']} if terminal else {}
    bindings = {b['candidate']: b for b in terminal['candidate_bindings']} if terminal else {}
    expected = [(cid, i) for cid in segment['candidate_ids']
                for i in range(len(checks.get(cid, {}).get('image_evidence', [])))]
    refs = segment.get('image_evidence', [])
    actual = [(r['candidate'], r['region_index']) for r in refs]
    if (len(actual) != len(set(actual)) or set(actual) != set(expected)
            or any(type(index) is not int for _, index in actual)):
        raise ValueError('Spoken comparison must bind every own candidate image region exactly once')
    ids = []
    for owner, index in actual:
        observed = checks[owner]['image_evidence'][index]['observed']
        if observed not in segment['text']:
            raise ValueError('Spoken comparison must preserve its bound external image observation')
        ids.append(bindings[owner]['image_evidence_ids'][index])
    return ids


def validate_image_lesson(analysis, question=None):
    """Portable complete-lesson checks for the new visual delivery path."""
    terminal = analysis.get('question_verification')
    image_candidates = {c['candidate'] for c in terminal['review']['candidate_checks']
                        if c.get('image_evidence')} if terminal else set()
    feedback = analysis.get('lesson_feedback')
    supplied = question.get('lesson_review') if question is not None else None
    if (not image_candidates and (not supplied or supplied['schema_version']!='1.2.0')
            and (not feedback or feedback['review']['schema_version']!='1.2.0')):
        return
    if feedback is None:
        if supplied is not None:
            raise ValueError('Frozen visual lesson cannot drop the supplied lesson review')
        return
    review = feedback['review']
    if question is not None and supplied is None:
        raise ValueError('Frozen visual lesson has no original supplied lesson review')
    if not image_candidates and review['schema_version'] != '1.2.0':
        return
    if feedback['scope'] != 'single_question_lesson':
        if review['segments'] or feedback['segment_bindings'] or feedback['grouping_execution_ids']:
            raise ValueError('Partial visual lesson must withhold all spoken segments')
        if supplied is not None:
            if {k:v for k,v in review.items() if k != 'segments'} != {k:v for k,v in supplied.items() if k != 'segments'}:
                raise ValueError('Frozen withheld visual lesson differs from original review')
        return
    if review['schema_version'] != '1.2.0':
        raise ValueError('Image-dependent complete spoken lesson requires lesson review 1.2.0')
    if supplied is not None and review != supplied:
        raise ValueError('Frozen visual lesson differs from original complete lesson review')
    if (review['review_status'] != 'reviewed' or not analysis['answer_verification']['closed']
            or not analysis['answer'] or not terminal or terminal['state'] != 'reviewed'):
        raise ValueError('Complete visual lesson requires its reviewed closed terminal')
    graph = analysis['evidence_graph']
    nodes = {n['id']:n for n in graph['nodes']}
    edges = {(e['from'],e['to'],e['type']) for e in graph['edges']}
    bindings = feedback['segment_bindings']
    segments = review['segments']
    if (len({s['segment_id'] for s in segments}) != len(segments)
            or [b['segment_id'] for b in bindings] != [s['segment_id'] for s in segments]):
        raise ValueError('Visual lesson segment bindings differ from the complete review')
    checks = {c['candidate']:c for c in terminal['review']['candidate_checks']}
    targets = {b['candidate']:b for b in terminal['candidate_bindings']}
    trace = {x['execution_id']:x for x in analysis['execution_trace']}
    consumed = {trace[x['execution_id']]['method_id'] for x in terminal['consumed_artifacts']}
    used, actions, evidenced, stopped, compared, image_compared = set(), set(), set(), set(), set(), set()
    all_evidence = []
    for segment, binding in zip(segments, bindings):
        sid = segment['segment_id']
        claim, relation = nodes.get(binding['claim_node_id'], {}), nodes.get(binding['relation_node_id'], {})
        if (claim.get('type') != 'candidate_claim' or claim.get('candidate') != 'spoken_segment:'+sid
                or claim.get('label') != segment['text'] or relation.get('type') != 'relation'
                or not relation.get('reviewed') or relation.get('artifact_fingerprint') != artifact_fingerprint(segment)
                or (claim.get('id'), relation.get('id'), 'supports') not in edges):
            raise ValueError('Visual spoken segment changed or detached from its exact graph payload')
        ids = binding['evidence_ids']
        if ([nodes.get(nid, {}).get('span') for nid in ids] != segment['evidence']
                or any(nodes.get(nid, {}).get('type') != 'source_evidence'
                       or (nid, relation['id'], 'supports') not in edges for nid in ids)):
            raise ValueError('Visual spoken source spans differ from graph bindings')
        all_evidence.extend(ids)
        if segment.get('segment_scope') == 'whole_question':
            candidates = segment['candidate_ids']
            if (segment['terminal_review_id'] != terminal['review']['review_id']
                    or relation.get('review_id') != segment['terminal_review_id'] or relation.get('method_id')
                    or len(candidates) != len(set(candidates)) or not set(candidates) <= set(checks)
                    or not consumed <= actions):
                raise ValueError('Visual spoken comparison borrowed a terminal/candidate/method owner')
            if not any(s['field']=='passage' and s['quote'] in segment['text'] for s in segment['evidence']):
                raise ValueError('Visual spoken comparison lost its passage quotation')
            for cid in candidates:
                check, target = checks[cid], targets[cid]
                if (cid not in segment['text'] or target['effect']=='undetermined'
                        or check['backfill_verdict']!='supports'
                        or (target['verification_node_id'],relation['id'],'supports') not in edges
                        or not all(any(s['field']==span['field'] and s['start']<=span['start']
                                       and span['end']<=s['end'] for s in segment['evidence']) for span in check['evidence'])):
                    raise ValueError('Visual spoken comparison lost its own decisive candidate proof')
            image_ids = segment_image_ids(segment, analysis)
            if binding.get('image_evidence_ids') != image_ids:
                raise ValueError('Spoken image bindings differ from canonical terminal regions')
            compared.update(candidates)
            image_compared.update(set(candidates) & image_candidates)
        else:
            mid = segment['method_id']
            if relation.get('method_id') != mid or relation.get('review_id'):
                raise ValueError('Visual lesson method segment changed its owner')
            used.add(mid)
            if (not any(m['method_id']==mid and m['trigger_verified'] for m in analysis['method_matches'])
                    or mid not in analysis['method_versions']
                    or not any(n['type']=='question_signal' and n.get('method_id')==mid
                               and n.get('reviewed') and (n['id'],relation['id'],'supports') in edges
                               for n in nodes.values())):
                raise ValueError('Visual lesson method segment lost its independent trigger/current method')
            if segment['function']=='action': actions.add(mid)
            if segment['function'] in {'evidence','comparison'}:
                if mid not in actions or not any(s['quote'] in segment['text'] for s in segment['evidence']):
                    raise ValueError('Visual lesson evidence must follow its actual method action')
                evidenced.add(mid)
            if segment['function']=='stop': stopped.add(mid)
            for index in segment['relation_indices']:
                rows = analysis['candidate_analysis']
                if type(index) is not int or not 0 <= index < len(rows):
                    raise ValueError('Unknown visual lesson candidate relation')
                row = rows[index]
                if row['method_id']!=mid or row['effect']=='undetermined' or row['candidate'] not in segment['text']:
                    raise ValueError('Visual lesson borrowed a candidate relation')
                if not any(n['type']=='relation' and n.get('method_id')==mid
                           and n.get('candidate')==row['candidate'] and n.get('reviewed')
                           and (n['id'],relation['id'],'supports') in edges for n in nodes.values()):
                    raise ValueError('Visual lesson lost its own candidate-relation graph edge')
                if segment['function']=='comparison': compared.add(row['candidate'])
            image_ids = []
            if 'image_evidence_ids' in binding:
                raise ValueError('Method segments cannot acquire objective image-decider credit')
        incoming = {(source, kind) for source, target, kind in edges
                    if target==relation['id'] and nodes[source]['type']=='image_evidence'}
        if incoming != {(nid,'supports') for nid in image_ids}:
            raise ValueError('Spoken visual proof has missing, foreign or mistyped image edges')
    if (feedback['evidence_ids'] != all_evidence or not used or not used<=actions
            or not used<=evidenced or not used<=stopped or not image_candidates<=image_compared
            or not set(analysis['answer_verification']['retained_candidates']+
                       analysis['answer_verification']['eliminated_candidates'])<=compared):
        raise ValueError('Complete visual lesson lost method/stop/candidate/image coverage')
