"""Run the unchanged engine on a paper's source-only structural projection.

This is an initial mechanical smoke pass, not an English solver, an independent
unseen-paper blind evaluation or proof that an entire paper was segmented.
Every paper still requires its own actual subagent source/semantic review.
"""
import argparse
from collections import Counter
from copy import deepcopy
import json
from pathlib import Path
import re

from core.analyzer import QuestionAnalyzer, PaperAnalyzer
from core.registry import Registry, ROOT, validate_schema
from core.real_cases import MATERIAL_FIELDS, text_leaves
from scripts.ingest_exam_sources import freeze_json, sha

KINDS={'single_choice':'未知','cloze':'完形填空','seven_five':'七选五','grammar_fill':'语法填空'}
TRANSCRIPTION_KINDS = dict(KINDS, reading='阅读理解', application_writing='应用文',
                           continuation_writing='读后续写', unknown='未知')

def projection(value):
    # The parser records any removed printed pagination lines separately.
    return value['text']

def admission_issue(entry, document_text):
    marker=entry.get('blank_location')
    if not marker: return None
    start=marker['start']; end=marker['end']
    a=document_text.rfind('\n',0,start)+1
    b=document_text.find('\n',end)
    line=document_text[a:b if b>=0 else len(document_text)]
    if re.search(r'阅读下面|空白处填入|每小题|满分|共\s*\d+\s*小题|第\s*\d+\s*页.*共\s*\d+\s*页',line):
        return 'number_in_instruction_or_pagination_not_a_verified_blank'
    if not re.search(r'[_＿]',marker['quote']) and not re.fullmatch(r'[（(]\s*\d+[）)]',marker['quote'].strip()):
        # Space-delimited digits can be a price, count or damaged printed gap.
        # Retain them in the original dossier for the paper agent, not in the
        # supposedly unambiguous initial analyzer subset.
        return 'space_delimited_number_requires_independent_blank_confirmation'
    return None

def convert(entry, document_text):
    kind=entry['question_type']
    if kind not in KINDS: raise ValueError('Unsupported structural projection')
    q={'question_id':entry['question_id'],'question_type':KINDS[kind],
       'stem':projection(entry['question']), 'passage':projection(entry['shared_context']),
       'task_type':'source_intake_projection_'+kind}
    if entry.get('blank_location'):
        q['stem']=entry['blank_location']['quote']
        if kind=='grammar_fill':
            # Copy an immediately printed prompt word; never infer one from
            # grammar, an answer, or the original part of speech.
            end=entry['blank_location']['end']
            hint=re.match(r'[_＿]*\s*[（(]([A-Za-z]+(?:[ -][A-Za-z]+){0,2})[）)]',document_text[end:])
            if hint: q['given_word']=hint[1]
    if entry['options']:
        q['options']={}
        for opt in entry['options']:
            raw=projection(opt['projection'])
            prefix=opt['label']+opt['printed_delimiter']
            if not raw.startswith(prefix): raise ValueError('Unbound option delimiter')
            body=raw[len(prefix):].strip()
            if not body: raise ValueError('Empty printed option')
            q['options'][opt['label']]=body
    # Single-choice legacy grammar questions remain UNKNOWN: they are not
    # grammar-fill questions simply because both can involve grammar.
    return q

def runtime_hashes():
    result={}
    for folder in ('core','schemas','method-registry'):
        for path in sorted((ROOT/folder).rglob('*')):
            if path.is_file() and path.suffix in {'.py','.json','.yaml'}:
                result[path.relative_to(ROOT).as_posix()]=sha(path.read_bytes())
    return result


def check_visual_reference(row, dataset_root):
    """Bind an actual private render file; this does not authenticate its meaning."""
    if dataset_root is None or not isinstance(row, dict) or type(row.get('page_number')) is not int or row['page_number']<1:
        raise ValueError('Visual source check requires a private dataset and actual page number')
    if not isinstance(row.get('rendered_path'),str) or not isinstance(row.get('rendered_sha256'),str):
        raise ValueError('Visual source check requires an explicit render and fingerprint')
    root=Path(dataset_root).resolve(); path=Path(row['rendered_path'])
    path=(path if path.is_absolute() else root/path).resolve()
    if not path.is_relative_to(root) or not path.is_file() or path.suffix.lower()!='.png':
        raise ValueError('Visual source render is missing or outside private dataset')
    raw=path.read_bytes()
    if sha(raw)!=row['rendered_sha256'] or not raw.startswith(b'\x89PNG\r\n\x1a\n'):
        raise ValueError('Visual source render fingerprint or PNG signature differs')


def validate_transcription(value, dossier, dataset_root=None):
    """Check source fidelity, not completeness, English semantics or answers.

    Low-model transcription is deliberately not a Case or blind prediction.
    Every displayed text field must be copied from exact source spans. Only
    explicitly recorded pagination deletions may separate those spans.
    """
    if value.get('phase') != 'low_model_source_transcription_no_answers' or \
            value.get('reference_read') is not False:
        raise ValueError('Expected source-only transcription, not answer-aware annotations')
    if value.get('paper_id') != dossier.get('paper_id') or \
            value.get('source_sha256') != dossier.get('source_sha256'):
        raise ValueError('Transcription and frozen source identity differ')
    if not isinstance(value.get('source_sha256'), str) or not re.fullmatch(r'[0-9a-f]{64}', value['source_sha256']):
        raise ValueError('Frozen original source fingerprint required')
    if not isinstance(value.get('reviewer_agent'), str) or not value['reviewer_agent'].startswith('/root/'):
        raise ValueError('Actual transcription agent label required')
    inputs = value.get('inputs')
    if not isinstance(inputs, dict) or inputs.get('paper_id') != value['paper_id'] or \
            not isinstance(inputs.get('questions'), list) or not inputs['questions']:
        raise ValueError('Explicit nonempty paper inputs required')
    questions = inputs['questions']
    ids = [q.get('question_id') for q in questions if isinstance(q, dict)]
    if len(ids) != len(questions) or any(not isinstance(x, str) or not x for x in ids) or len(set(ids)) != len(ids):
        raise ValueError('Transcription question IDs are absent or duplicated')
    bindings = value.get('source_bindings')
    if not isinstance(bindings, list) or any(not isinstance(x, dict) for x in bindings) or \
            len(bindings) != len(ids) or {x.get('question_id') for x in bindings} != set(ids):
        raise ValueError('One exact source binding required per question')
    by_id = {x['question_id']: x for x in bindings}
    content = dossier['document_text']
    layout = re.compile(
        r'\s*(?:英语试[题卷]\s*)?第\s*\d+\s*页\s*'
        r'(?:(?:[|/｜，,]\s*)?共\s*\d+\s*页|'
        r'[（(]\s*共\s*\d+\s*页\s*[）)])\s*')
    # An answer printed inside a response box is not an unseen student's draft.
    allowed = set(MATERIAL_FIELDS) - {'student_symptoms', 'original_images', 'student_text', 'student_draft'} | {'task_type', 'printed_number'}
    def span(row):
        if not isinstance(row, dict) or type(row.get('start')) is not int or type(row.get('end')) is not int:
            raise ValueError('Integer source span required')
        a, b = row['start'], row['end']
        if not 0 <= a < b <= len(content) or row.get('quote') != content[a:b]:
            raise ValueError('Source span does not reproduce original bytes as text')
        return a, b
    normalized = deepcopy(inputs)
    for index, q in enumerate(questions):
        if set(q) - allowed:
            raise ValueError('Transcription cannot contain answers, semantic actions or unbound image claims')
        if 'printed_number' in q and not re.fullmatch(r'[1-9][0-9]*',str(q['printed_number'])):
            raise ValueError('Printed question number metadata must be a positive number')
        normalized['questions'][index].pop('printed_number', None)
        normalized['questions'][index]['question_type'] = TRANSCRIPTION_KINDS.get(q.get('question_type'),q.get('question_type'))
        validate_schema('question-input', normalized['questions'][index])
        binding = by_id[q['question_id']]
        fields = binding.get('fields')
        leaves = text_leaves(q)
        if not leaves or not isinstance(fields, dict) or set(fields) != set(leaves):
            raise ValueError('Every nonempty core text field must have an exact binding')
        excluded = binding.get('display_exclusions', [])
        if not isinstance(excluded, list):
            raise ValueError('Explicit display exclusion list required')
        exclusions = set()
        for row in excluded:
            a, b = span(row)
            if not layout.fullmatch(content[a:b]):
                if row.get('kind')!='printed_pagination' or not re.fullmatch(r'\s*\d+\s*',content[a:b]) or \
                        int(content[a:b])!=row.get('printed_page_number',row.get('page_number')):
                    raise ValueError('Only recorded printed pagination may be deleted')
                # Physical and printed page numbers can differ (e.g. a cover),
                # but that mapping needs an explicit visual confirmation.
                if row.get('printed_page_number',row.get('page_number')) != row.get('page_number') and row.get('confirmed') is not True:
                    raise ValueError('Different printed pagination and render page needs visual confirmation')
                check_visual_reference(row,dataset_root)
            exclusions.add((a, b))
        for field, text in leaves.items():
            rows = fields[field]
            if not isinstance(rows, list) or not rows:
                raise ValueError('Field source spans required')
            previous = None
            copied = []
            for row in rows:
                a, b = span(row)
                if previous is not None:
                    if a < previous:
                        raise ValueError('Source spans overlap or reorder text')
                    if a > previous and (previous, a) not in exclusions:
                        raise ValueError('Unrecorded non-pagination source deletion')
                copied.append(row['quote'])
                previous = b
            if ''.join(copied) != text:
                raise ValueError('Transcribed field is not an exact source projection')
        if normalized['questions'][index]['question_type'] == '语法填空':
            stem_spans = fields.get('/stem', [])
            marker=re.fullmatch(r'[_＿]*\s*(\d+)\s*[_＿]*',q.get('stem','').strip())
            if len(stem_spans) != 1 or not marker:
                raise ValueError('Grammar input must bind its particular printed blank marker')
            if not re.search(r'[_＿]',q['stem']):
                visual=binding.get('blank_marker_visual_check')
                if not isinstance(visual,dict) or visual.get('confirmed') is not True or \
                        visual.get('printed_number')!=int(marker[1]) or visual.get('source_sha256')!=value['source_sha256']:
                    raise ValueError('Space-delimited digit needs explicit source-PDF blank confirmation')
                check_visual_reference(visual,dataset_root)
            tail = content[stem_spans[0]['end']:]
            hint = re.match(r'[_＿]*\s*[（(]\s*([A-Za-z]+(?:[ -][A-Za-z]+){0,2})\s*[）)]',tail)
            supplied = q.get('given_word','').strip('()（） \t\r\n')
            if (hint and supplied != hint[1].strip()) or (not hint and supplied):
                raise ValueError('Grammar prompt word missing or different from the target blank')
    return normalized


def run_transcription_batch(paths, output_root, bank_root=None, analyzer=None):
    """Preflight the entire explicit batch before running its source-only replay."""
    bank_root = Path(bank_root or ROOT/'local-data/organized-pdfs/case-bank-v4')
    dataset = bank_root.parent.resolve()
    output_root = Path(output_root).resolve()
    if not output_root.is_relative_to(dataset):
        raise ValueError('Keep exam output inside its explicitly selected private dataset')
    prepared = []
    for path in paths:
        path = Path(path).resolve()
        if not path.is_relative_to(dataset):
            raise ValueError('Transcription must stay inside its private dataset')
        raw = path.read_bytes(); value = json.loads(raw)
        pid = value.get('paper_id')
        if not isinstance(pid, str) or not re.fullmatch(r'[A-Za-z0-9_-]+', pid):
            raise ValueError('Safe explicit paper ID required')
        original_path = bank_root/'papers'/(pid+'.json')
        original_raw = original_path.read_bytes(); original = json.loads(original_raw)
        document_ref=value.get('source_document_ref')
        if document_ref is not None:
            if not isinstance(document_ref,dict) or not isinstance(document_ref.get('path'),str) or Path(document_ref['path']).is_absolute():
                raise ValueError('Visual source document needs a private relative reference')
            dossier_path=(dataset/document_ref['path']).resolve()
            if not dossier_path.is_relative_to(dataset):
                raise ValueError('Visual source document escaped private dataset')
            dossier_raw=dossier_path.read_bytes(); dossier=json.loads(dossier_raw)
            if document_ref.get('sha256')!=sha(dossier_raw) or dossier.get('origin')!='visual_transcription_sidecar' or \
                    dossier.get('original_dossier_ref')!={'path':original_path.resolve().relative_to(dataset).as_posix(),'sha256':sha(original_raw)}:
                raise ValueError('Visual sidecar must bind preserved original text-layer dossier')
            pages=dossier.get('pages')
            if not isinstance(pages,list) or not pages or any(not isinstance(p,dict) or not isinstance(p.get('text'),str) for p in pages):
                raise ValueError('Visual sidecar requires explicit transcribed pages')
            for page in pages: check_visual_reference(page,dataset)
            numbers=[p['page_number'] for p in pages]
            if numbers!=sorted(set(numbers)) or dossier.get('document_text')!='\n'.join(p['text'] for p in pages):
                raise ValueError('Visual source page order or joined text differs')
            if dossier.get('source_sha256')!=original['source_sha256'] or dossier.get('paper_id')!=original['paper_id']:
                raise ValueError('Visual sidecar has a different original PDF identity')
        else:
            dossier_path=original_path; dossier_raw=original_raw; dossier=original
        if value.get('source_document_sha256') != sha(dossier_raw):
            raise ValueError('Frozen source dossier fingerprint differs')
        inputs = validate_transcription(value, dossier, dataset)
        pdf = dataset/'originals/files'/(value['source_sha256']+'.pdf')
        if sha(pdf.read_bytes()) != value['source_sha256']:
            raise ValueError('Frozen original PDF fingerprint differs')
        prepared.append((path, raw, value, inputs))
    if not prepared or len({x[2]['paper_id'] for x in prepared}) != len(prepared):
        raise ValueError('Batch papers are empty or duplicated')
    analyzer = analyzer or QuestionAnalyzer(Registry())
    fingerprints = runtime_hashes()
    results = []
    for path, raw, value, inputs in prepared:
        predictions = [analyzer.analyze(deepcopy(q)) for q in inputs['questions']]
        paper = PaperAnalyzer(analyzer).analyze(deepcopy(inputs))
        if predictions != paper['questions'] or any(p['answer'] is not None for p in predictions):
            raise ValueError('Source-only replay disagrees or unexpectedly declares an answer')
        report = {'paper_id':value['paper_id'], 'source_sha256':value['source_sha256'],
                  'phase':'source_transcription_engine_replay_not_semantic_acceptance',
                  'transcription_path':path.relative_to(dataset).as_posix(),
                  'transcription_sha256':sha(raw), 'reviewer_agent':value['reviewer_agent'],
                  'source_document_sha256':value['source_document_sha256'],
                  'source_document_ref':value.get('source_document_ref'),
                  'source_answer_exposure':deepcopy(value.get('source_answer_exposure')),
                  'visual_fidelity_certified':False,
                  'printed_number_metadata_retained_in_transcription_not_engine':True,
                  'source_type_mapping':[
                      {'question_id':q['question_id'], 'source_type':q['question_type'],
                       'engine_type':mapped['question_type']}
                      for q,mapped in zip(value['inputs']['questions'],inputs['questions'])
                      if q['question_type'] != mapped['question_type']],
                  'inputs':inputs, 'predictions':predictions, 'paper_analysis':paper,
                  'runtime_sha256':fingerprints,
                  'limits':{'source_authenticity':'unverified', 'source_completeness_certified':False,
                            'whole_paper_semantic_review':False, 'whole_paper_acceptance':False,
                            'safe_abstention':None, 'new_blind_sample':False,
                            'clean_blind_certified':False,
                            'formal_method_cases_registered':0, 'human_participants':0}}
        dest = output_root/value['paper_id']/'transcription-engine-replay.json'
        freeze_json(dest, report)
        results.append({'paper_id':value['paper_id'], 'input_count':len(predictions),
                        'engine_answer_count':0, 'formal_case_count':0,
                        'report':dest.relative_to(dataset).as_posix(), 'report_sha256':sha(dest.read_bytes())})
    summary = {'phase':'source_transcription_batch_replay', 'papers':results,
               'source_completeness_certified':False, 'whole_paper_acceptance':False,
               'new_question_count':None, 'new_blind_samples':0, 'human_participants':0}
    freeze_json(output_root/'transcription-batch-summary.json', summary)
    return summary

def run_paper(bank_root, source, output_root, analyzer=None, fingerprints=None):
    bank_root=Path(bank_root); output_root=Path(output_root)
    input_path=bank_root/source['question_input_file']
    raw=input_path.read_bytes(); record=json.loads(raw)
    if record['source_sha256'] != source['source_sha256'] or record['paper_id'] != source['paper_id']:
        raise ValueError('Wrong paper projection/source binding')
    dossier_path=bank_root/source['case_file']
    dossier=json.loads(dossier_path.read_text(encoding='utf-8'))
    if dossier['source_sha256'] != source['source_sha256']:
        raise ValueError('Wrong original-text dossier')
    admitted=[]; excluded=[]
    for entry in record['question_inputs']:
        issue=admission_issue(entry,dossier['document_text'])
        if issue: excluded.append({'question_id':entry['question_id'],'reason':issue,'source':entry['blank_location']})
        else: admitted.append(entry)
    inputs={'paper_id':source['paper_id'],'questions':[convert(e,dossier['document_text']) for e in admitted]}
    analyzer=analyzer or QuestionAnalyzer()
    predictions=[analyzer.analyze(deepcopy(q)) for q in inputs['questions']]
    paper=PaperAnalyzer(analyzer).analyze(deepcopy(inputs))
    if predictions != paper['questions']: raise ValueError('Question/Paper Analyzer disagree')
    if any(p['answer'] is not None for p in predictions):
        raise ValueError('Unreviewed structural projection unexpectedly declares an answer')
    value={'schema_version':'1.0.0','paper_id':source['paper_id'],'source_sha256':source['source_sha256'],
           'phase':'mechanical_source_only_intake','projection_sha256':sha(raw),
           'dossier_sha256':sha(dossier_path.read_bytes()),
           'intake_script_sha256':sha(Path(__file__).read_bytes()),
           'excluded_structural_candidates':excluded,
           'inputs':inputs,'predictions':predictions,'paper_analysis':paper,
           'runtime_sha256':fingerprints or runtime_hashes(),
           'limits':{'whole_paper_semantic_review':False,'novel_heldout_blind_evaluation':False,
                     'reference_answer_provided_to_engine':False,'source_authenticity':'unverified',
                     'safe_abstention':None,'formal_method_cases_registered':0,
                     'source_coverage':'structural_subset_only; independent paper agent must verify omitted tasks'}}
    dest=output_root/source['paper_id']/'mechanical-intake.json'
    freeze_json(dest,value)
    return {'paper_id':source['paper_id'],'source_sha256':source['source_sha256'],
            'structural_input_count':len(predictions),'question_type_counts':dict(Counter(q['question_type'] for q in inputs['questions'])),
            'engine_answer_count':0,'unresolved_count':len(predictions),'safe_abstention':None,
            'excluded_ambiguous_number_candidates':len(excluded),
            'formal_method_case_count':0,'report':str(dest),'report_sha256':sha(dest.read_bytes()),
            'status':'PARTIAL_STRUCTURAL_SUBSET_NOT_WHOLE_PAPER_ACCEPTANCE'}

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('paper_id',help='Human paper ID, or all for an initial corpus smoke pass')
    parser.add_argument('--bank-root',type=Path,default=ROOT/'local-data/organized-pdfs/case-bank-v4')
    parser.add_argument('--output-root',type=Path,default=ROOT/'local-data/organized-pdfs/mechanical-intake-v4-2')
    parser.add_argument('--transcriptions',type=Path,nargs='+',help='Explicit low-model source-only files; verify the whole batch before replay')
    args=parser.parse_args(); index=json.loads((args.bank_root/'source-bank.json').read_text(encoding='utf-8'))
    if args.transcriptions:
        if args.paper_id != 'all':
            parser.error('Use all with the explicit --transcriptions batch, not a conflicting paper selector')
        print(json.dumps(run_transcription_batch(args.transcriptions,args.output_root,args.bank_root),ensure_ascii=False,indent=2))
        return
    sources=[s for s in index['sources'] if args.paper_id=='all' or s['paper_id']==args.paper_id]
    if not sources: raise ValueError('Unknown paper ID')
    analyzer=QuestionAnalyzer(Registry()); fingerprints=runtime_hashes(); summaries=[]
    for source in sources:
        summary=run_paper(args.bank_root,source,args.output_root,analyzer,fingerprints)
        summaries.append(summary); print(json.dumps(summary,ensure_ascii=False),flush=True)
    if args.paper_id=='all': freeze_json(args.output_root/'summary.json',{'paper_count':len(summaries),'papers':summaries})

if __name__=='__main__': main()
