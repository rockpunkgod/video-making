"""Private, append-only research Case registration over frozen exam artifacts.

This module makes no claim about answer authority, English semantics, reviewers'
identity, redistribution rights, or learner outcomes. It never writes public cases.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import re

from .registry import ROOT, CASE_TYPES, Registry, validate_schema
from .analyzer import QuestionAnalyzer
from .evidence import validate_graph
from .execution import validate_execution_trace


STATUS = 'reviewed_real_exam_case'
CHECKS = ('trigger', 'action', 'evidence', 'role', 'stop', 'case_type')
CATALOG = 'real-case-catalog'
HEX64 = re.compile(r'^[0-9a-f]{64}$')
SAFE_ID = re.compile(r'^[A-Za-z0-9][A-Za-z0-9_-]*$')


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def json_digest(value) -> str:
    return digest(json.dumps(value, ensure_ascii=False, sort_keys=True,
                             separators=(',', ':')).encode('utf-8'))


def private_root(dataset):
    root = Path(dataset).resolve()
    if not root.is_dir() or root == ROOT.resolve() or root.is_relative_to((ROOT/'cases').resolve()):
        raise ValueError('Private dataset must be an existing private directory')
    # The caller explicitly supplies --dataset for outside-repository private data.
    if root.is_relative_to(ROOT.resolve()) and not root.is_relative_to((ROOT/'local-data').resolve()):
        raise ValueError('Repository dataset must live under local-data')
    return root


def private_file(root, relative, expected_hash=None):
    if not isinstance(relative, str) or not relative or Path(relative).is_absolute():
        raise ValueError('Expected a private dataset-relative file')
    path = (root/relative).resolve()
    if not path.is_relative_to(root) or not path.is_file():
        raise ValueError('Missing or escaped private artifact: '+relative)
    raw = path.read_bytes()
    if expected_hash is not None and (not isinstance(expected_hash,str) or not HEX64.fullmatch(expected_hash)
                                     or digest(raw) != expected_hash):
        raise ValueError('Private artifact fingerprint mismatch: '+relative)
    return path, raw


def artifact(root, ref):
    if not isinstance(ref, dict):
        raise ValueError('Artifact reference must be an object')
    if not isinstance(ref.get('sha256'),str) or not HEX64.fullmatch(ref['sha256']):
        raise ValueError('Artifact sha256 is required')
    _, raw = private_file(root, ref.get('path'), ref['sha256'])
    return json.loads(raw)


def pointer(document, path):
    if not isinstance(path, str) or not path.startswith('/'):
        raise ValueError('Explicit JSON pointer required')
    value = document
    for part in path[1:].split('/'):
        if re.search(r'~(?![01])',part):
            raise ValueError('Invalid JSON pointer escape')
        part = part.replace('~1', '/').replace('~0', '~')
        try:
            if isinstance(value,list):
                if not part.isdigit() or (len(part)>1 and part[0]=='0'):
                    raise ValueError('Invalid JSON array index')
                value = value[int(part)]
            else:
                value = value[part]
        except (ValueError, IndexError, KeyError, TypeError) as exc:
            raise ValueError('JSON pointer does not resolve: '+path) from exc
    return value


MATERIAL_FIELDS = ('question_id', 'question_type', 'stem', 'passage', 'options',
                   'given_word', 'student_text', 'continuation_starters',
                   'original_images', 'student_symptoms')


def material(question):
    return {key: question[key] for key in MATERIAL_FIELDS if key in question}


def text_leaves(question):
    result = {}
    for field in ('stem','passage','given_word','student_text'):
        if isinstance(question.get(field),str) and question[field].strip():
            result['/'+field] = question[field]
    for field in ('options','continuation_starters'):
        value=question.get(field)
        if isinstance(value,dict):
            for key,item in value.items():
                if isinstance(item,str) and item.strip(): result['/'+field+'/'+str(key)]=item
        elif isinstance(value,list):
            for index,item in enumerate(value):
                if isinstance(item,str) and item.strip(): result['/'+field+'/'+str(index)]=item
    return result


def frozen_question(blind, request):
    if blind.get('pass') not in {'blind', 'host_reviewed_blind'} and blind.get('phase') not in {
            'agent_before_reference_read_source_only_freeze',
            'source_only_before_reference_read'}:
        raise ValueError('Prediction is not a frozen pre-reveal pass')
    question = pointer(blind, request.get('blind_question_pointer'))
    if not isinstance(question, dict) or question.get('question_id') != request['question_id']:
        raise ValueError('Frozen blind question identity mismatch')
    if json_digest(material(question)) != request.get('question_input_sha256'):
        raise ValueError('Frozen core question material fingerprint mismatch')
    return question


def source_check(root, source, question, blind):
    if not isinstance(source, dict):
        raise ValueError('Source binding required')
    if not isinstance(source.get('pdf_sha256'),str) or not HEX64.fullmatch(source['pdf_sha256']):
        raise ValueError('Source PDF sha256 required')
    private_file(root, source.get('pdf_path'), source['pdf_sha256'])
    binding = source.get('question_binding')
    if not isinstance(binding, dict):
        raise ValueError('Exact source question binding required')
    document = artifact(root, {'path': binding.get('document_path'),
                               'sha256': binding.get('document_sha256')})
    if pointer(document,binding.get('pdf_sha256_pointer')) != source['pdf_sha256']:
        raise ValueError('Frozen source text is not bound to source PDF fingerprint')
    content = pointer(document, binding.get('text_pointer'))
    field_bindings = binding.get('fields')
    leaves = text_leaves(question)
    if not isinstance(content,str) or not isinstance(field_bindings,dict) or set(field_bindings)!=set(leaves):
        raise ValueError('Every source question text field needs exact binding')
    for field, expected in leaves.items():
        spans = field_bindings[field]
        if not isinstance(spans,list) or not spans:
            raise ValueError('Exact source spans required: '+field)
        pieces=[]
        for span in spans:
            start, end, quote = span.get('start'), span.get('end'), span.get('quote')
            if not isinstance(start,int) or not isinstance(end,int) or start<0 or end<=start or \
                    content[start:end]!=quote or not quote:
                raise ValueError('Exact source span replay failed: '+field)
            pieces.append(quote)
        if ''.join(pieces)!=expected:
            raise ValueError('Source spans do not reproduce frozen question field: '+field)
    exam_id=blind.get('exam_id',blind.get('paper_id'))
    if source.get('exam_id') != exam_id or source.get('question_id') != question['question_id']:
        raise ValueError('Source exam/question identity mismatch')
    top_source = blind.get('source_sha256')
    if 'source_sha256' in blind and top_source != source['pdf_sha256']:
        raise ValueError('Frozen blind top-level source PDF fingerprint mismatch')
    bindings = blind.get('source_bindings', {})
    existing = bindings.get(question['question_id'], {})
    if existing and existing.get('source_sha256') != source.get('pdf_sha256'):
        raise ValueError('Frozen blind source PDF fingerprint mismatch')
    if top_source is None and not existing:
        raise ValueError('Frozen blind source PDF fingerprint required')
    if source.get('usage_status') != 'local_research_only' or source.get('answer_authority') not in {
            'third_party_unverified','user_supplied_unverified'}:
        raise ValueError('Private rights and unverified reference authority required')


def _review_checks(review, method, request, blind):
    if review.get('stage') != 'post_reveal_case_review' or review.get('reviewer_kind') != 'AI':
        raise ValueError('Independent post-reveal Case Review required')
    paper_agent = blind.get('reviewer_agent') or blind.get('paper_agent')
    if not paper_agent or review.get('paper_agent') != paper_agent or \
            not review.get('reviewer') or review.get('reviewer') == paper_agent or \
            review.get('independent_from_paper_agent') is not True:
        raise ValueError('Case reviewer must be distinct from paper agent')
    checks = review.get('checks')
    if not isinstance(checks, dict) or any(checks.get(k) is not True for k in CHECKS):
        raise ValueError('All six own-method Case Review checks must pass')
    if review.get('pass_scope') != 'private_research_case_only' or review.get('case_type') != request['case_type'] or \
            not review.get('case_type_reason'):
        raise ValueError('Case type and private review scope must be explicit')
    if not isinstance(review.get('trigger'),str) or not review['trigger'].strip() or \
            not isinstance(review.get('action'),str) or not review['action'].strip() or \
            not isinstance(review.get('evidence'),list) or not review['evidence']:
        raise ValueError('Case Review needs own trigger, action and evidence')
    for key in ('question_id', 'method_id', 'method_version'):
        if review.get(key) != request.get(key):
            raise ValueError('Case Review identity mismatch: '+key)
    if review.get('canonical_question_id') != request['canonical_question_id']:
        raise ValueError('Canonical question ID not independently reviewed')
    if review.get('role') != method['primary_role'] or review.get('stop_rule') != method['stop_rule']:
        raise ValueError('Case Review role/stop differs from current method')
    for key in ('blind_sha256', 'reveal_sha256', 'action_sha256'):
        if review.get(key) != request[key[:-7]]['sha256']:
            raise ValueError('Case Review fingerprint mismatch: '+key)


def validate_request(root, request, registry=None):
    registry = registry or Registry()
    if not isinstance(request, dict):
        raise ValueError('Case registration request must be an object')
    required = {'question_id', 'canonical_question_id', 'method_id', 'method_version', 'case_type', 'source',
                'blind', 'blind_question_pointer', 'question_input_sha256',
                'reveal', 'action', 'case_review'}
    if not required <= set(request) or request['case_type'] not in CASE_TYPES:
        raise ValueError('Incomplete Case registration request or invalid type')
    if not isinstance(request['canonical_question_id'], str) or not request['canonical_question_id'].strip():
        raise ValueError('Stable canonical question ID required')
    method = registry.methods.get(request['method_id'])
    if method is None or method['version'] != request['method_version']:
        raise ValueError('Method identity/version mismatch')
    blind = artifact(root, request['blind'])
    question = frozen_question(blind, request)
    exam_id = blind.get('exam_id',blind.get('paper_id'))
    if not isinstance(exam_id,str) or not exam_id:
        raise ValueError('Frozen blind exam/paper identity required')
    if question['question_type'] != method['question_type']:
        raise ValueError('Question/method type mismatch')
    source_check(root, request['source'], question, blind)
    reveal = artifact(root, request['reveal'])
    has_comparison='original_comparison_ref' in reveal
    has_reference_pdf='reference_pdf_ref' in reveal
    if has_comparison != has_reference_pdf:
        raise ValueError('Reveal adapter requires both original comparison and reference PDF bindings')
    if has_comparison:
        comparison_ref=reveal['original_comparison_ref']
        reference_pdf_ref=reveal['reference_pdf_ref']
        artifact(root,comparison_ref)
        if not isinstance(reference_pdf_ref,dict) or not isinstance(reference_pdf_ref.get('sha256'),str) or \
                not HEX64.fullmatch(reference_pdf_ref['sha256']):
            raise ValueError('Reveal reference PDF fingerprint required')
        private_file(root,reference_pdf_ref.get('path'),reference_pdf_ref['sha256'])
    if reveal.get('exam_id',reveal.get('paper_id')) != exam_id or reveal.get('prediction_sha256') != request['blind']['sha256']:
        raise ValueError('Reveal does not bind frozen blind prediction')
    matches = [q for q in reveal.get('questions', []) if q.get('question_id') == request['question_id']]
    if len(matches) != 1 or not matches[0].get('reference_answer') or matches[0].get('official_answer') or \
            matches[0].get('answer_authority') not in {'third_party_compilation_not_official',
                                                        'third_party_unverified','user_supplied_unverified'}:
        raise ValueError('Revealed reference answer identity missing or duplicated')
    action = artifact(root, request['action'])
    if (action.get('exam_id',action.get('paper_id')), action.get('question_id'), action.get('method_id'),
            action.get('method_version')) != (exam_id, request['question_id'],
                                            request['method_id'], request['method_version']):
        raise ValueError('Own action identity mismatch')
    if action.get('mechanical_prediction_sha256') != request['blind']['sha256']:
        raise ValueError('Own action does not bind blind prediction')
    if material(question) != material(action['question']):
        raise ValueError('Post-reveal action changed frozen core question material')
    analysis = action['analysis']
    validate_schema('question-analysis',analysis)
    if QuestionAnalyzer(registry).analyze(action['question']) != analysis:
        raise ValueError('Current analyzer replay differs from frozen own action')
    validate_graph(analysis['evidence_graph'], action['question'])
    validate_execution_trace(analysis, registry)
    own = [x for x in analysis['execution_trace'] if x['method_id'] == request['method_id']
           and x['state'] == 'produced' and x['role'] == method['primary_role']]
    if not own:
        stopped=[x for x in analysis['execution_trace'] if x['method_id']==request['method_id']
                 and x['state']=='stopped' and x['role']==method['primary_role']]
        if request['case_type'] not in {'counterexample','boundary'} or not stopped:
            raise ValueError('Own typed action or reviewed Stop trace is required')
        own=stopped
    elif not all(isinstance(x.get('output'),dict) and x['output'].get('kind') for x in own):
        raise ValueError('Own typed produced action is required')
    review = artifact(root, request['case_review'])
    _review_checks(review, method, request, blind)
    if request['case_type']=='counterexample' and not review.get('negative_trigger_confirmed'):
        raise ValueError('Counterexample needs explicit negative trigger review')
    if request['case_type']=='boundary' and not review.get('boundary_stop_confirmed'):
        raise ValueError('Boundary needs explicit Stop review')
    if review.get('action_analysis_sha256') != json_digest(analysis) or \
            review.get('evidence_graph_sha256') != json_digest(analysis['evidence_graph']) or \
            review.get('replay_analysis_sha256') != json_digest(analysis) or \
            sorted(review.get('own_execution_ids', [])) != sorted(x['execution_id'] for x in own):
        raise ValueError('Case Review does not bind typed action and graph')
    if review.get('source_pdf_sha256') != request['source']['pdf_sha256'] or \
            review.get('source_document_sha256') != request['source']['question_binding']['document_sha256']:
        raise ValueError('Case Review source version mismatch')
    if review.get('pre_reveal_prediction_unchanged') is not True or review.get('answer_backfit_excluded') is not True or \
            review.get('own_method_credit_only') is not True:
        raise ValueError('Blind integrity and independent method credit review required')
    return method, question, review


def expected_case_id(request, review, registry):
    inventory=registry.case_inventory()
    existing=[c for c in inventory.values()
              if c['method_id']==request['method_id'] and c['case_type']==request['case_type']
              and isinstance(c.get('source'),dict)
              and c['source'].get('question_id')==request['question_id']]
    if existing and request.get('existing_case_id')!=existing[0]['case_id']:
        raise ValueError('Existing public Case ID must be explicitly reused')
    if request.get('existing_case_id'):
        public_path,public=next(((p,c) for p,c in inventory.items()
                                 if c['case_id']==request['existing_case_id']),(None,None))
        if public is None or public['method_id']!=request['method_id'] or public['case_type']!=request['case_type'] or \
                review.get('public_case_match') is not True or \
                request.get('existing_case_sha256')!=digest((ROOT/public_path).read_bytes()) or \
                review.get('public_case_sha256')!=request['existing_case_sha256']:
            raise ValueError('Public short Case reuse requires explicit independent match')
    case_id=request.get('existing_case_id') or request.get('case_id') or \
        '-'.join([request['question_id'],request['method_id'],request['case_type']])
    if not isinstance(case_id,str) or not SAFE_ID.fullmatch(case_id):
        raise ValueError('Unsafe private Case ID')
    return case_id


def expected_record(request, request_ref, method, question, review, case_id):
    key=[request['canonical_question_id'],request['method_id'],request['case_type'],request['method_version']]
    return {'case_id':case_id,'method_id':request['method_id'],
            'question_type':question['question_type'],'source':request['source'],
            'question':None,'answer':None,'trigger':review['trigger'],
            'evidence':review['evidence'],'method_role':method['primary_role'],
            'expected_action':review['action'],'expected_output':method['output_type'],
            'stop_rule':method['stop_rule'],'case_type':request['case_type'],
            'status':STATUS,'notes':review['case_type_reason'],
            'registration_key':key,
            'frozen_refs':{k:request[k] for k in ('blind','reveal','action','case_review')},
            'registration_request_ref':request_ref,
            'review_scope':'private_AI_reviewed',
            'learner_validation':'pending_real_participant_validation',
            'redistribution_rights':'not_verified'}


def _check_canonical_binding(request, bindings):
    identity = request['question_input_sha256']
    canonical = request['canonical_question_id']
    if identity in bindings and bindings[identity] != canonical:
        raise ValueError('Frozen question canonical ID conflict')
    bindings[identity] = canonical


def _catalog_paths(root):
    directory = root/CATALOG
    return sorted(directory.glob('catalog-*.json')) if directory.is_dir() else []


def load_catalog(dataset):
    root = private_root(dataset)
    paths = _catalog_paths(root)
    if not paths:
        if (root/CATALOG/'cases').exists() and any((root/CATALOG/'cases').iterdir()):
            raise ValueError('Orphan private Case file; catalog revision was not committed')
        return {'revision': 0, 'cases': [], 'aliases': [], 'sha256': None}
    numbered = []
    for path in paths:
        suffix = path.stem.removeprefix('catalog-')
        if not suffix.isdigit():
            raise ValueError('Invalid catalog revision filename')
        numbered.append((int(suffix), path))
    numbered.sort()
    if [n for n, _ in numbered] != list(range(1, len(numbered)+1)):
        raise ValueError('Catalog revisions are missing or duplicated')
    previous = None
    result = None
    preceding_refs = []
    preceding_aliases = []
    seen_keys=set(); seen_ids=set(); registry=Registry()
    canonical_bindings={}
    validated_records={}
    validated_requests={}

    def checked_request(ref):
        if not isinstance(ref,dict):
            raise ValueError('Case request binding missing')
        identity=(ref.get('path'),ref.get('sha256'))
        if identity not in validated_requests:
            request=artifact(root,ref)
            validated_requests[identity]=(request,*validate_request(root,request,registry))
        return validated_requests[identity]

    for number, path in numbered:
        raw = path.read_bytes(); entry = json.loads(raw)
        refs=entry.get('cases'); aliases=entry.get('aliases',[])
        if entry.get('revision') != number or entry.get('previous_sha256') != previous or not isinstance(refs,list) or \
                not isinstance(aliases,list) or refs[:len(preceding_refs)] != preceding_refs or \
                aliases[:len(preceding_aliases)] != preceding_aliases or \
                (len(refs)-len(preceding_refs),len(aliases)-len(preceding_aliases)) not in {(1,0),(0,1)}:
            raise ValueError('Catalog revision chain mismatch')
        if len(refs)>len(preceding_refs):
            case_ref=refs[-1]
            record=artifact(root,case_ref)
            if record.get('status') != STATUS:
                raise ValueError('Catalog contains non-private reviewed Case')
            validate_schema('case', record)
            request_ref=record.get('registration_request_ref')
            request,method,question,review=checked_request(request_ref)
            _check_canonical_binding(request, canonical_bindings)
            case_id=expected_case_id(request,review,registry)
            if record != expected_record(request,request_ref,method,question,review,case_id):
                raise ValueError('Private Case differs from validated request')
            key=tuple(record['registration_key'])
            if key in seen_keys or record['case_id'] in seen_ids:
                raise ValueError('Duplicate private Case key or ID')
            seen_keys.add(key); seen_ids.add(record['case_id'])
            validated_records[(case_ref['path'],case_ref['sha256'])]=record
        else:
            alias=aliases[-1]
            request,_,_,review=checked_request(alias.get('registration_request_ref'))
            _check_canonical_binding(request, canonical_bindings)
            original=next((record for record in validated_records.values() if
                           record['case_id']==alias.get('case_id') and
                           record['registration_key']==alias.get('registration_key')),None)
            source_alias=request.get('source_alias')
            if alias.get('registration_key') != [request['canonical_question_id'],request['method_id'],
                                                  request['case_type'],request['method_version']] or \
                    tuple(alias['registration_key']) not in seen_keys or \
                    alias.get('source_pdf_sha256') != request['source']['pdf_sha256'] or \
                    original is None or not isinstance(source_alias,dict) or \
                    source_alias.get('case_id')!=original['case_id'] or \
                    source_alias.get('old_pdf_sha256')!=original['source']['pdf_sha256'] or \
                    source_alias.get('new_pdf_sha256')!=request['source']['pdf_sha256'] or \
                    review.get('source_alias_reconciled') is not True or \
                    request['source']['pdf_sha256']==original['source']['pdf_sha256']:
                raise ValueError('Source alias reconciliation mismatch')
            if any(a['registration_key']==alias['registration_key'] and
                   a['source_pdf_sha256']==alias['source_pdf_sha256'] for a in preceding_aliases):
                raise ValueError('Duplicate source alias')
        preceding_refs=refs
        preceding_aliases=aliases
        previous = digest(raw); result = entry
    result['sha256'] = previous
    case_dir=root/CATALOG/'cases'
    actual={p.resolve() for p in case_dir.glob('*.json')} if case_dir.exists() else set()
    expected={(root/ref['path']).resolve() for ref in result['cases']}
    if actual!=expected:
        raise ValueError('Orphan or missing private Case file; explicit recovery required')
    return result


def register(dataset, request_path):
    root = private_root(dataset)
    request_raw=private_file(root,request_path)[1]
    request_ref={'path':request_path,'sha256':digest(request_raw)}
    request = artifact(root, request_ref)
    registry = Registry(); method, question, review = validate_request(root, request, registry)
    catalog = load_catalog(root)
    canonical_bindings={}
    for ref in catalog['cases']:
        prior=artifact(root,artifact(root,ref)['registration_request_ref'])
        _check_canonical_binding(prior,canonical_bindings)
    for alias in catalog['aliases']:
        prior=artifact(root,alias['registration_request_ref'])
        _check_canonical_binding(prior,canonical_bindings)
    _check_canonical_binding(request,canonical_bindings)
    key = [request['canonical_question_id'], request['method_id'], request['case_type'], request['method_version']]
    for ref in catalog['cases']:
        record = artifact(root, ref)
        if record['registration_key'] == key:
            alias=request.get('source_alias')
            if not isinstance(alias,dict) or alias.get('case_id')!=record['case_id'] or \
                    alias.get('old_pdf_sha256')!=record['source']['pdf_sha256'] or \
                    alias.get('new_pdf_sha256')!=request['source']['pdf_sha256'] or \
                    review.get('source_alias_reconciled') is not True:
                raise ValueError('Same question/method/type/version already registered; explicit source alias reconciliation required')
            if request['source']['pdf_sha256']==record['source']['pdf_sha256'] or any(
                    a['registration_key']==key and a['source_pdf_sha256']==request['source']['pdf_sha256']
                    for a in catalog['aliases']):
                raise ValueError('Duplicate source alias')
            next_revision=catalog['revision']+1
            revision={'revision':next_revision,'previous_sha256':catalog['sha256'],
                      'cases':catalog['cases'],'aliases':catalog['aliases']+[
                          {'case_id':record['case_id'],'registration_key':key,
                           'source_pdf_sha256':request['source']['pdf_sha256'],
                           'registration_request_ref':request_ref}]}
            target=root/CATALOG/f'catalog-{next_revision:06d}.json'
            with target.open('xb') as stream:
                stream.write((json.dumps(revision,ensure_ascii=False,indent=2)+'\n').encode('utf-8'))
            return {'case_id':record['case_id'],'status':'source_alias_reconciled',
                    'catalog_revision':next_revision,'new_case_count':0}
    case_id=expected_case_id(request,review,registry)
    if any(artifact(root, ref)['case_id'] == case_id for ref in catalog['cases']):
        raise ValueError('Case ID already registered')
    record=expected_record(request,request_ref,method,question,review,case_id)
    validate_schema('case', record)
    target = f'{CATALOG}/cases/{case_id}.json'
    if not (root/target).resolve().is_relative_to((root/CATALOG/'cases').resolve()):
        raise ValueError('Private Case target escaped catalog')
    if (root/target).exists():
        raise ValueError('Case file exists; explicit new revision required')
    raw = (json.dumps(record, ensure_ascii=False, indent=2)+'\n').encode('utf-8')
    ref = {'path': target, 'sha256': digest(raw)}
    next_revision = catalog['revision'] + 1
    revision = {'revision': next_revision, 'previous_sha256': catalog['sha256'],
                'cases': catalog['cases'] + [ref], 'aliases':catalog['aliases']}
    catalog_target = root/CATALOG/f'catalog-{next_revision:06d}.json'
    if catalog_target.exists():
        raise ValueError('Catalog revision already exists')
    (root/target).parent.mkdir(parents=True, exist_ok=True)
    with (root/target).open('xb') as stream: stream.write(raw)
    with catalog_target.open('xb') as stream:
        stream.write((json.dumps(revision, ensure_ascii=False, indent=2)+'\n').encode('utf-8'))
    return {'case_id': case_id, 'registration_key': key, 'status': STATUS,
            'review_scope': record['review_scope'], 'catalog_revision': next_revision,
            'source_authority': request['source']['answer_authority'],
            'learner_validation': record['learner_validation']}


def coverage_overlay(coverage, dataset):
    root = private_root(dataset); catalog = load_catalog(root)
    records = [artifact(root, ref) for ref in catalog['cases']]
    seen = set(); pairs = set(); questions = set()
    for case in records:
        key = tuple(case['registration_key'])
        if key in seen: raise ValueError('Duplicate private Case registration key')
        seen.add(key); pairs.add((case['method_id'], case['case_type']))
        questions.add(case['registration_key'][0])
    for method in coverage['methods']:
        for slot in method['slots']:
            own = [c for c in records if c['method_id'] == method['method_id']
                   and c['case_type'] == slot['case_type']]
            slot['private_registered_case_count'] = len(own)
            slot['private_case_ids'] = [c['case_id'] for c in own]
            slot['private_review_status'] = STATUS if own else None
    coverage['private_catalog'] = {'revision': catalog['revision'],
                                   'private_reviewed_case_count': len(records),
                                   'unique_question_count': len(questions),
                                   'covered_method_type_pairs': len(pairs),
                                   'release_gate': 'not_satisfied_by_private_case_registration'}
    return coverage
