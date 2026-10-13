"""Private, append-only research Case registration over frozen exam artifacts.

This module makes no claim about answer authority, English semantics, reviewers'
identity, redistribution rights, or learner outcomes. It never writes public cases.
"""
from __future__ import annotations

import hashlib
import io
import json
from pathlib import Path
import re
import unicodedata
from zipfile import BadZipFile, ZipFile
import xml.etree.ElementTree as ET

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


def frozen_question(blind, request, root=None):
    phases = {
            'agent_before_reference_read_source_only_freeze',
            'source_only_before_reference_read',
            'agent_before_reference_read'}
    if ('phase' in blind and blind['phase'] not in phases) or \
            ('pass' in blind and blind['pass'] not in {'blind', 'host_reviewed_blind'}) or \
            ('phase' not in blind and 'pass' not in blind):
        raise ValueError('Prediction is not a frozen pre-reveal pass')
    document = blind
    if 'blind_question_ref' in request:
        # A real historical prediction may hash-bind full source material in a
        # separate file. Never copy current answers into a new "blind" wrapper.
        if root is None:
            raise ValueError('External frozen question requires a private dataset root')
        ref = request['blind_question_ref']
        document = artifact(root, ref)
        bindings = blind.get('input_sha256')
        if not isinstance(bindings, dict) or bindings.get(Path(ref['path']).name) != ref['sha256']:
            raise ValueError('Original prediction does not hash-bind this external source')
        if (document.get('phase') != 'low_model_source_transcription_no_answers'
                or document.get('reference_read') is not False
                or document.get('paper_id') != blind.get('paper_id')
                or not isinstance(blind.get('source_sha256'), str)
                or document.get('source_sha256') != blind['source_sha256']):
            raise ValueError('External source phase, paper or original identity differs')
        if not isinstance(blind.get('reviewer_agent'), str) or not blind['reviewer_agent'].strip():
            raise ValueError('Original prediction author required for external material')
        predictions = blind.get('objective_predictions')
        if not isinstance(predictions, list) or len([
                row for row in predictions if isinstance(row, dict)
                and row.get('question_id') == request.get('question_id')]) != 1:
            raise ValueError('One actual original question prediction required')
    question = pointer(document, request.get('blind_question_pointer'))
    if not isinstance(question, dict) or question.get('question_id') != request['question_id']:
        raise ValueError('Frozen blind question identity mismatch')
    if json_digest(material(question)) != request.get('question_input_sha256'):
        raise ValueError('Frozen core question material fingerprint mismatch')
    return question


def check_external_reveal(root, request, blind, reveal, reference_row):
    """Bind a post-reveal adapter to actual old same-question records.

    This checks preserved assertions, not time authenticity or answer authority.
    Old incorrect/unresolved predictions remain incorrect/unresolved; no current
    answer or method credit can be substituted into the historical record.
    """
    if (reveal.get('phase') != 'post_reveal_adapter_not_new_prediction'
            or 'original_comparison_ref' not in reveal
            or 'source_only_checkpoint_ref' not in reveal):
        raise ValueError('External reveal needs an explicit adapter, original comparison and source-only checkpoint')
    checkpoint = artifact(root, reveal['source_only_checkpoint_ref'])
    if (checkpoint.get('blind_sha256') != request['blind']['sha256']
            or checkpoint.get('reference_read') is not False
            or checkpoint.get('paper_id') != blind.get('paper_id')
            or checkpoint.get('source_sha256') != blind.get('source_sha256')
            or checkpoint.get('reviewer_agent') != blind.get('reviewer_agent')):
        raise ValueError('Source-only checkpoint does not bind the actual old prediction')
    comparison = artifact(root, reveal['original_comparison_ref'])
    if (comparison.get('phase') != 'after_source_only_freeze_reference_read'
            or comparison.get('paper_id') != blind.get('paper_id')
            or comparison.get('source_sha256') != blind.get('source_sha256')
            or comparison.get('reviewer_agent') != blind.get('reviewer_agent')):
        raise ValueError('Original comparison phase, paper, source or old author differs')
    if 'reference_pdf_ref' in reveal:
        if comparison.get('reference_sha256') != reveal['reference_pdf_ref']['sha256']:
            raise ValueError('Original comparison does not bind this reference PDF')
    elif ('reference_original_ref' not in reveal
          or comparison.get('reference_original_ref') != reveal['reference_original_ref']):
        raise ValueError('Original comparison does not bind this reference original')
    row_keys = [key for key in ('rows', 'questions') if key in comparison]
    if len(row_keys) != 1 or not isinstance(comparison[row_keys[0]], list):
        raise ValueError('One unambiguous original comparison row collection required')
    rows = [row for row in comparison[row_keys[0]] if isinstance(row, dict)
            and row.get('question_id') == request['question_id']]
    predictions = [row for row in blind['objective_predictions'] if isinstance(row, dict)
                   and row.get('question_id') == request['question_id']]
    if len(rows) != 1 or len(predictions) != 1:
        raise ValueError('One original prediction and comparison for this question required')
    original, compared = predictions[0], rows[0]
    for before, after in (('predicted_answer', 'agent_before_reference_read'),
                          ('candidate_if_unresolved', 'agent_unresolved_candidate'),
                          ('decisive_evidence', 'source_evidence_retained_in_blind')):
        if before not in original or after not in compared or original[before] != compared[after]:
            raise ValueError('Original same-question prediction field differs: '+before)
    if ('third_party_reference' not in compared
            or compared['third_party_reference'] != reference_row['reference_answer']):
        raise ValueError('Adapter reference answer differs from original same-question comparison')


def source_identity(source):
    """Keep legacy PDF requests intact; new requests name the actual original."""
    generic = any(k in source for k in ('original_path', 'original_sha256', 'source_format'))
    if generic:
        if any(k in source for k in ('pdf_path', 'pdf_sha256')):
            raise ValueError('Ambiguous original/PDF source identity')
        fmt = source.get('source_format')
        if fmt not in {'pdf', 'docx', 'doc'}:
            raise ValueError('Explicit supported original source format required')
        path, fingerprint = source.get('original_path'), source.get('original_sha256')
    else:
        fmt, path, fingerprint = 'pdf', source.get('pdf_path'), source.get('pdf_sha256')
    if not isinstance(fingerprint, str) or not HEX64.fullmatch(fingerprint):
        raise ValueError('Source original sha256 required')
    if not isinstance(path, str) or Path(path).suffix.lower() != '.'+fmt:
        raise ValueError('Original source extension differs from declared format')
    return path, fingerprint, fmt, generic


def check_original(root, path, fingerprint, fmt):
    """Reject renamed derivatives; format checks do not certify source meaning."""
    _, raw = private_file(root, path, fingerprint)
    if fmt == 'pdf' and not raw.startswith(b'%PDF'):
        raise ValueError('Original source is not PDF bytes')
    if fmt == 'doc' and not raw.startswith(bytes.fromhex('d0cf11e0a1b11ae1')):
        raise ValueError('Original source is not legacy Word bytes')
    if fmt == 'doc':
        try:
            import olefile
        except ImportError as exc:
            raise ValueError('Legacy Word validation requires the organized-exams optional dependencies') from exc
        try:
            with olefile.OleFileIO(io.BytesIO(raw), raise_defects=olefile.DEFECT_FATAL) as container:
                if not container.exists('WordDocument') or not any(container.exists(name) for name in ('0Table','1Table')):
                    raise ValueError('Legacy Word container lacks document/table streams')
                if container.openstream('WordDocument').read(2) != b'\xec\xa5':
                    raise ValueError('Legacy Word document stream lacks Word FIB signature')
        except OSError as exc:
            raise ValueError('Original source is not a readable legacy Word container') from exc
    if fmt == 'docx':
        try:
            with ZipFile(io.BytesIO(raw)) as archive:
                document = ET.fromstring(archive.read('word/document.xml'))
                if document.tag != '{http://schemas.openxmlformats.org/wordprocessingml/2006/main}document':
                    raise ValueError('Original DOCX lacks a Word document root')
                types=ET.fromstring(archive.read('[Content_Types].xml'))
                rels=ET.fromstring(archive.read('_rels/.rels'))
                ct='{http://schemas.openxmlformats.org/package/2006/content-types}'
                rel='{http://schemas.openxmlformats.org/package/2006/relationships}'
                main_type='application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml'
                office_rel='http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument'
                if types.tag!=ct+'Types' or not any(
                        n.get('PartName')=='/word/document.xml' and n.get('ContentType')==main_type
                        for n in types.findall(ct+'Override')):
                    raise ValueError('Original DOCX lacks a Word main-part content type')
                if rels.tag!=rel+'Relationships' or not any(
                        n.get('Type')==office_rel and n.get('Target') in {'word/document.xml','/word/document.xml'}
                        and n.get('TargetMode','Internal')=='Internal' for n in rels.findall(rel+'Relationship')):
                    raise ValueError('Original DOCX lacks an internal office-document relationship')
        except (BadZipFile, KeyError, ET.ParseError) as exc:
            raise ValueError('Original source is not DOCX Word bytes') from exc


def source_digest(source):
    return source_identity(source)[1]


def alias_digest(alias):
    keys = [key for key in ('source_pdf_sha256', 'source_original_sha256') if key in alias]
    if len(keys) != 1:
        raise ValueError('Ambiguous or missing source alias fingerprint')
    return alias[keys[0]]


def alias_reconciles(alias, original, request):
    if not isinstance(alias, dict):
        return False
    generic = source_identity(request['source'])[3]
    old_key, new_key = ('old_original_sha256', 'new_original_sha256') if generic else ('old_pdf_sha256', 'new_pdf_sha256')
    other = ('old_pdf_sha256', 'new_pdf_sha256') if generic else ('old_original_sha256', 'new_original_sha256')
    return not any(k in alias for k in other) and alias.get('case_id') == original['case_id'] and \
        alias.get(old_key) == source_digest(original['source']) and \
        alias.get(new_key) == source_digest(request['source'])


def check_alias_material(root, original, request):
    """New aliases must match all core fields, not just a claimed canonical ID."""
    if not source_identity(request['source'])[3]:
        return  # Preserve legacy alias requests byte-for-byte and their contract.
    previous=artifact(root,original['registration_request_ref'])
    old=frozen_question(artifact(root,previous['blind']),previous,root)
    new=frozen_question(artifact(root,request['blind']),request,root)
    def normalized(value):
        if isinstance(value,str):
            return re.sub(r'\s+','',unicodedata.normalize('NFKC',value))
        if isinstance(value,dict): return {k:normalized(v) for k,v in value.items()}
        if isinstance(value,list): return [normalized(v) for v in value]
        return value
    def identity(q):
        core=material(q); core.pop('question_id',None)
        return normalized(core)
    if identity(old)!=identity(new):
        raise ValueError('Source alias full question material differs; explicit separate review required')


def source_check(root, source, question, blind):
    if not isinstance(source, dict):
        raise ValueError('Source binding required')
    path, fingerprint, fmt, generic = source_identity(source)
    check_original(root, path, fingerprint, fmt)
    binding = source.get('question_binding')
    if not isinstance(binding, dict):
        raise ValueError('Exact source question binding required')
    document = artifact(root, {'path': binding.get('document_path'),
                               'sha256': binding.get('document_sha256')})
    pointer_key = 'original_sha256_pointer' if generic else 'pdf_sha256_pointer'
    other_key = 'pdf_sha256_pointer' if generic else 'original_sha256_pointer'
    if other_key in binding or pointer(document,binding.get(pointer_key)) != fingerprint:
        raise ValueError('Frozen source text is not bound to original source fingerprint')
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
            if type(start) is not int or type(end) is not int or start<0 or end<=start or end>len(content) or \
                    content[start:end]!=quote or not quote:
                raise ValueError('Exact source span replay failed: '+field)
            pieces.append(quote)
        if ''.join(pieces)!=expected:
            raise ValueError('Source spans do not reproduce frozen question field: '+field)
    exam_id=blind.get('exam_id',blind.get('paper_id'))
    if source.get('exam_id') != exam_id or source.get('question_id') != question['question_id']:
        raise ValueError('Source exam/question identity mismatch')
    top_source = blind.get('source_sha256')
    if 'source_sha256' in blind and top_source != fingerprint:
        raise ValueError('Frozen blind top-level source '+('original' if generic else 'PDF')+' fingerprint mismatch')
    bindings = blind.get('source_bindings', {})
    if not isinstance(bindings, dict):
        raise ValueError('Frozen blind source bindings must be keyed by question ID')
    existing = bindings.get(question['question_id'], {})
    if not isinstance(existing, dict):
        raise ValueError('Frozen blind question source binding must be an object')
    if 'source_sha256' in existing and existing['source_sha256'] != fingerprint:
        raise ValueError('Frozen blind source original fingerprint mismatch')
    if top_source is None and existing.get('source_sha256') != fingerprint:
        raise ValueError('Frozen blind source '+('original' if generic else 'PDF')+' fingerprint required')
    if source.get('usage_status') != 'local_research_only' or source.get('answer_authority') not in {
            'third_party_unverified','user_supplied_unverified'}:
        raise ValueError('Private rights and unverified reference authority required')


def _review_checks(review, method, request, blind, frozen_question):
    if review.get('stage') != 'post_reveal_case_review' or review.get('reviewer_kind') != 'AI':
        raise ValueError('Independent post-reveal Case Review required')
    explicit = [blind[key] for key in ('reviewer_agent', 'paper_agent') if key in blind]
    if explicit:
        if any(not isinstance(agent, str) or not agent.strip() for agent in explicit) or \
                len(set(explicit)) != 1:
            raise ValueError('Frozen paper agent identity is blank or conflicting')
        paper_agent = explicit[0]
    else:
        agents = {row['reviewer'] for field in ('action_executions', 'relations')
                  for row in (frozen_question.get(field) if isinstance(frozen_question.get(field), list) else [])
                  if isinstance(row, dict) and isinstance(row.get('reviewer'), str)
                  and row['reviewer'].strip()}
        paper_agent = next(iter(agents)) if len(agents) == 1 else None
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
    question = frozen_question(blind, request, root)
    exam_id = blind.get('exam_id',blind.get('paper_id'))
    if not isinstance(exam_id,str) or not exam_id:
        raise ValueError('Frozen blind exam/paper identity required')
    if question['question_type'] != method['question_type']:
        raise ValueError('Question/method type mismatch')
    source_check(root, request['source'], question, blind)
    reveal = artifact(root, request['reveal'])
    has_comparison='original_comparison_ref' in reveal
    reference_keys=[k for k in ('reference_pdf_ref', 'reference_original_ref') if k in reveal]
    if len(reference_keys)>1 or has_comparison != bool(reference_keys):
        raise ValueError('Reveal adapter requires both original comparison and one reference original binding')
    if has_comparison:
        comparison_ref=reveal['original_comparison_ref']
        reference_ref=reveal[reference_keys[0]]
        comparison=artifact(root,comparison_ref)
        if not isinstance(reference_ref,dict) or not isinstance(reference_ref.get('sha256'),str) or \
                not HEX64.fullmatch(reference_ref['sha256']):
            raise ValueError('Reveal reference original fingerprint required')
        reference_fmt='pdf' if reference_keys[0]=='reference_pdf_ref' else reference_ref.get('format')
        if reference_fmt not in {'pdf','docx','doc'} or not isinstance(reference_ref.get('path'),str) or \
                Path(reference_ref['path']).suffix.lower()!='.'+reference_fmt:
            raise ValueError('Reveal reference original format mismatch')
        check_original(root,reference_ref['path'],reference_ref['sha256'],reference_fmt)
        if reference_keys[0]=='reference_original_ref' and comparison.get('reference_original_ref')!=reference_ref:
            raise ValueError('Original comparison does not bind the exact reference original')
    if reveal.get('exam_id',reveal.get('paper_id')) != exam_id or reveal.get('prediction_sha256') != request['blind']['sha256']:
        raise ValueError('Reveal does not bind frozen blind prediction')
    matches = [q for q in reveal.get('questions', []) if q.get('question_id') == request['question_id']]
    if len(matches) != 1 or not matches[0].get('reference_answer') or matches[0].get('official_answer') or \
            matches[0].get('answer_authority') not in {'third_party_compilation_not_official',
                                                        'third_party_unverified','user_supplied_unverified'}:
        raise ValueError('Revealed reference answer identity missing or duplicated')
    if 'blind_question_ref' in request:
        check_external_reveal(root, request, blind, reveal, matches[0])
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
    _review_checks(review, method, request, blind, question)
    if 'blind_question_ref' in request:
        # Historical prediction author and current action author are separate
        # roles. Distinctness from only the old author cannot certify a new
        # post-reveal action written by the reviewer themselves.
        authors = {row.get('reviewer') for field in ('action_executions', 'relations')
                   for row in action['question'].get(field, [])}
        for field in ('grammar_hint_review', 'question_verification_review',
                      'lesson_review', 'writing_review'):
            annotation = action['question'].get(field)
            if annotation is not None:
                authors.add(annotation.get('reviewer'))
        author = review.get('action_author')
        if (not isinstance(author, str) or not author.strip() or authors != {author}
                or author == review.get('reviewer')
                or review.get('independent_from_action_author') is not True
                or review.get('blind_question_ref') != request['blind_question_ref']):
            raise ValueError('External-source Case Review must independently bind the actual current action author and source')
    if request['case_type']=='counterexample' and not review.get('negative_trigger_confirmed'):
        raise ValueError('Counterexample needs explicit negative trigger review')
    if request['case_type']=='boundary' and not review.get('boundary_stop_confirmed'):
        raise ValueError('Boundary needs explicit Stop review')
    if review.get('action_analysis_sha256') != json_digest(analysis) or \
            review.get('evidence_graph_sha256') != json_digest(analysis['evidence_graph']) or \
            review.get('replay_analysis_sha256') != json_digest(analysis) or \
            sorted(review.get('own_execution_ids', [])) != sorted(x['execution_id'] for x in own):
        raise ValueError('Case Review does not bind typed action and graph')
    generic=source_identity(request['source'])[3]
    review_source_key='source_original_sha256' if generic else 'source_pdf_sha256'
    other_source_key='source_pdf_sha256' if generic else 'source_original_sha256'
    if other_source_key in review or review.get(review_source_key) != source_digest(request['source']) or \
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


def _runtime_contexts(root):
    """Bind archived requests to a verified past Registry, never new admission."""
    paths=sorted((root/CATALOG).glob('runtime-context-*.json'))
    assignments={}; registries={}; previous=None
    for number,path in enumerate(paths,1):
        if path.name!=f'runtime-context-{number:06d}.json':
            raise ValueError('Historical runtime context revisions are missing or invalid')
        raw=path.read_bytes(); context=json.loads(raw)
        if context.get('revision')!=number or context.get('previous_sha256')!=previous or \
                context.get('scope')!='historical_revalidation_only' or \
                context.get('current_rule_acceptance') is not False or context.get('new_blind_sample') is not False or \
                context.get('past_analysis_replay_checked') is not True or context.get('learner_validation') is not None:
            raise ValueError('Historical runtime context chain mismatch')
        commit=context.get('registry_snapshot_commit')
        if not isinstance(commit,str) or not re.fullmatch(r'[0-9a-f]{40}',commit):
            raise ValueError('Historical runtime context requires a full source commit')
        if commit not in registries:
            registries[commit]=Registry(snapshot_commit=commit)
        registry=registries[commit]
        if not registry.is_historical or digest((registry.asset_root/'snapshot-manifest.json').read_bytes())!=context.get('snapshot_manifest_sha256'):
            raise ValueError('Historical runtime context snapshot differs')
        frontier=context.get('catalog_revision')
        expected_path=f'{CATALOG}/catalog-{frontier:06d}.json' if type(frontier) is int and frontier>0 else None
        catalog_ref=context.get('catalog_ref')
        if not isinstance(catalog_ref,dict) or catalog_ref.get('path')!=expected_path:
            raise ValueError('Historical runtime context must bind an actual catalog frontier')
        catalog=artifact(root,catalog_ref)
        if catalog.get('revision')!=frontier:
            raise ValueError('Historical runtime context frontier mismatch')
        expected={}
        for case_ref in catalog.get('cases',[]):
            record=artifact(root,case_ref); ref=record.get('registration_request_ref')
            if not isinstance(ref,dict): raise ValueError('Historical Case request reference missing')
            expected[(ref.get('path'),ref.get('sha256'))]=ref
        for alias in catalog.get('aliases',[]):
            ref=alias.get('registration_request_ref')
            if not isinstance(ref,dict): raise ValueError('Historical alias request reference missing')
            expected[(ref.get('path'),ref.get('sha256'))]=ref
        incoming=context.get('request_refs')
        if not isinstance(incoming,list) or any(not isinstance(ref,dict) for ref in incoming):
            raise ValueError('Historical request context references required')
        keys=[(ref.get('path'),ref.get('sha256')) for ref in incoming]
        if len(set(keys))!=len(keys) or set(keys)!=(set(expected)-set(assignments)) or not keys:
            raise ValueError('Historical runtime context request coverage differs')
        for ref in incoming:
            key=(ref['path'],ref['sha256'])
            artifact(root,ref)
            assignments[key]={'registry':registry,'source_commit':commit,
                              'context_ref':{'path':path.relative_to(root).as_posix(),'sha256':digest(raw)}}
        previous=digest(raw)
    return assignments


def load_catalog(dataset, *, registry=None, use_runtime_contexts=True):
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
    seen_keys=set(); seen_ids=set(); registry=registry or Registry()
    contexts=_runtime_contexts(root) if use_runtime_contexts else {}
    canonical_bindings={}
    validated_records={}
    validated_requests={}

    def checked_request(ref):
        if not isinstance(ref,dict):
            raise ValueError('Case request binding missing')
        identity=(ref.get('path'),ref.get('sha256'))
        if identity not in validated_requests:
            request=artifact(root,ref)
            request_registry=contexts.get(identity,{}).get('registry',registry)
            validated_requests[identity]=(request,*validate_request(root,request,request_registry),request_registry)
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
            request,method,question,review,request_registry=checked_request(request_ref)
            _check_canonical_binding(request, canonical_bindings)
            case_id=expected_case_id(request,review,request_registry)
            if record != expected_record(request,request_ref,method,question,review,case_id):
                raise ValueError('Private Case differs from validated request')
            key=tuple(record['registration_key'])
            if key in seen_keys or record['case_id'] in seen_ids:
                raise ValueError('Duplicate private Case key or ID')
            seen_keys.add(key); seen_ids.add(record['case_id'])
            validated_records[(case_ref['path'],case_ref['sha256'])]=record
        else:
            alias=aliases[-1]
            request,_,_,review,_=checked_request(alias.get('registration_request_ref'))
            _check_canonical_binding(request, canonical_bindings)
            original=next((record for record in validated_records.values() if
                           record['case_id']==alias.get('case_id') and
                           record['registration_key']==alias.get('registration_key')),None)
            source_alias=request.get('source_alias')
            if alias.get('registration_key') != [request['canonical_question_id'],request['method_id'],
                                                  request['case_type'],request['method_version']] or \
                    tuple(alias['registration_key']) not in seen_keys or \
                    alias_digest(alias) != source_digest(request['source']) or \
                    original is None or not isinstance(source_alias,dict) or \
                    not alias_reconciles(source_alias,original,request) or \
                    review.get('source_alias_reconciled') is not True or \
                    source_digest(request['source'])==source_digest(original['source']):
                raise ValueError('Source alias reconciliation mismatch')
            check_alias_material(root,original,request)
            if any(a['registration_key']==alias['registration_key'] and
                   alias_digest(a)==alias_digest(alias) for a in preceding_aliases):
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
    if contexts:
        result['historical_runtime_contexts']=[{'request_ref':{'path':key[0],'sha256':key[1]},
                                              'source_commit':value['source_commit'],
                                              'context_ref':value['context_ref']}
                                             for key,value in sorted(contexts.items())]
    return result


def freeze_runtime_context(dataset, snapshot_commit):
    """Preflight the existing prefix against its old rules before a source upgrade."""
    root=private_root(dataset); registry=Registry(snapshot_commit=snapshot_commit)
    contexts=_runtime_contexts(root)
    catalog=load_catalog(root,registry=registry,use_runtime_contexts=True)
    if catalog['revision']==0:
        raise ValueError('No registered historical Case prefix to bind')
    refs={}
    for case_ref in catalog['cases']:
        ref=artifact(root,case_ref)['registration_request_ref']
        refs[(ref['path'],ref['sha256'])]=ref
    for alias in catalog['aliases']:
        ref=alias['registration_request_ref']; refs[(ref['path'],ref['sha256'])]=ref
    incoming=[refs[key] for key in sorted(set(refs)-set(contexts))]
    if not incoming:
        return {'status':'existing_runtime_context_reused','new_context_count':0,
                'catalog_revision':catalog['revision'],
                'source_commits':sorted({value['source_commit'] for value in contexts.values()}),
                'current_rule_acceptance':False}
    prior=sorted((root/CATALOG).glob('runtime-context-*.json'))
    revision=len(prior)+1
    catalog_path=root/CATALOG/f"catalog-{catalog['revision']:06d}.json"
    value={'revision':revision,'previous_sha256':digest(prior[-1].read_bytes()) if prior else None,
           'scope':'historical_revalidation_only','registry_snapshot_commit':snapshot_commit,
           'snapshot_manifest_sha256':digest((registry.asset_root/'snapshot-manifest.json').read_bytes()),
           'catalog_revision':catalog['revision'],
           'catalog_ref':{'path':catalog_path.relative_to(root).as_posix(),'sha256':digest(catalog_path.read_bytes())},
           'request_refs':incoming,'past_analysis_replay_checked':True,
           'current_rule_acceptance':False,'new_blind_sample':False,'learner_validation':None}
    target=root/CATALOG/f'runtime-context-{revision:06d}.json'
    with target.open('xb') as stream:
        stream.write((json.dumps(value,ensure_ascii=False,indent=2)+'\n').encode('utf-8'))
    _runtime_contexts(root)
    return {'status':'historical_runtime_context_frozen','new_context_count':1,
            'context_ref':{'path':target.relative_to(root).as_posix(),'sha256':digest(target.read_bytes())},
            'catalog_revision':catalog['revision'],'historical_request_count':len(incoming),
            'source_commit':snapshot_commit,'current_rule_acceptance':False}


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
            if not alias_reconciles(alias,record,request) or \
                    review.get('source_alias_reconciled') is not True:
                raise ValueError('Same question/method/type/version already registered; explicit source alias reconciliation required')
            check_alias_material(root,record,request)
            if source_digest(request['source'])==source_digest(record['source']) or any(
                    a['registration_key']==key and alias_digest(a)==source_digest(request['source'])
                    for a in catalog['aliases']):
                raise ValueError('Duplicate source alias')
            next_revision=catalog['revision']+1
            revision={'revision':next_revision,'previous_sha256':catalog['sha256'],
                      'cases':catalog['cases'],'aliases':catalog['aliases']+[
                          {'case_id':record['case_id'],'registration_key':key,
                           ('source_original_sha256' if source_identity(request['source'])[3] else 'source_pdf_sha256'):
                               source_digest(request['source']),
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
                   and c['case_type'] == slot['case_type']
                   and c['registration_key'][3] == method['method_version']]
            slot['private_registered_case_count'] = len(own)
            slot['private_case_ids'] = [c['case_id'] for c in own]
            slot['private_review_status'] = STATUS if own else None
    coverage['private_catalog'] = {'revision': catalog['revision'],
                                   'private_reviewed_case_count': len(records),
                                   'historical_version_case_count':sum(
                                       c['registration_key'][3]!=next((m['method_version'] for m in coverage['methods']
                                                                       if m['method_id']==c['method_id']),None)
                                       for c in records),
                                   'unique_question_count': len(questions),
                                   'covered_method_type_pairs': len(pairs),
                                   'release_gate': 'not_satisfied_by_private_case_registration'}
    return coverage
