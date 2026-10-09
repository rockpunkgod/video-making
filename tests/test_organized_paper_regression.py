import unittest
import json
from copy import deepcopy
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
from scripts.run_organized_paper_regression import admission_issue, convert, validate_transcription, run_transcription_batch
from scripts.ingest_exam_sources import freeze_json, sha

class OrganizedRegressionTests(unittest.TestCase):
    def test_reading_option_next_passage_requires_review_not_automatic_trimming(self):
        for boundary in ('B\n', 'C\n', 'D\n', '第二节 七选五(共5小题)\n'):
            content = 'Which?\nNormal answer.\n'+boundary+'Next passage begins here.'
            q = {'question_id': 'test-Q23', 'question_type': 'reading', 'stem': 'Which?',
                 'passage': 'Normal answer.', 'options': {'D': content[7:]}}
            fields = {}
            for name, text in (('/stem', q['stem']), ('/passage', q['passage']), ('/options/D', q['options']['D'])):
                start = content.index(text)
                fields[name] = [{'start': start, 'end': start+len(text), 'quote': text}]
            value = {'paper_id': 'test-paper', 'source_sha256': sha(b'PDF'),
                     'reviewer_agent': '/root/source_worker', 'reference_read': False,
                     'phase': 'low_model_source_transcription_no_answers',
                     'inputs': {'paper_id': 'test-paper', 'questions': [q]},
                     'source_bindings': [{'question_id': q['question_id'], 'fields': fields}]}
            dossier = {'paper_id': 'test-paper', 'source_sha256': sha(b'PDF'), 'document_text': content}
            with self.subTest(boundary=boundary), self.assertRaisesRegex(ValueError, 'source review required'):
                validate_transcription(value, dossier)
            self.assertEqual(q['options']['D'], content[7:])

    def test_wrapped_long_reading_option_without_section_marker_is_not_trimmed(self):
        value, dossier = self.transcription()
        q = value['inputs']['questions'][0]
        q['question_type'] = 'reading'
        option = 'A complete candidate with detailed qualifications and conditions. '*5+'\nThe same candidate continues on another printed line.'
        start = len(dossier['document_text'])+1
        dossier['document_text'] += '\n'+option
        q['options']['D'] = option
        value['source_bindings'][0]['fields']['/options/D'] = [
            {'start': start, 'end': start+len(option), 'quote': option}]
        # Ordinary wrap/length is not enough to declare a source-boundary error.
        result = validate_transcription(value, dossier)
        self.assertEqual(result['questions'][0]['options']['D'], option)

    def source_batch(self, root, extension='.docx', transcription_extension=None, changed=False):
        value, dossier = self.transcription()
        dossier['source_extension'] = extension
        value['source_document_sha256'] = sha((json.dumps(dossier, ensure_ascii=False, indent=2)+'\n').encode('utf-8'))
        if transcription_extension is not None:
            value['source_extension'] = transcription_extension
        bank = root/'case-bank'
        freeze_json(bank/'papers/test-paper.json', dossier)
        freeze_json(root/'transcription.json', value)
        freeze_json(bank/'source-bank.json', {'sources': []})
        source = root/'originals/files'/(dossier['source_sha256']+extension)
        source.parent.mkdir(parents=True)
        source.write_bytes(b'CHANGED' if changed else b'PDF')
        return bank, root/'transcription.json'

    def test_docx_original_replays_without_derivative_pdf_or_semantic_claim(self):
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            bank, path = self.source_batch(root)
            summary = run_transcription_batch([path], root/'replay', bank)
            report = json.loads((root/summary['papers'][0]['report']).read_text(encoding='utf-8'))
            self.assertEqual(report['source_extension'], '.docx')
            self.assertEqual(report['source_sha256'], sha(b'PDF'))
            self.assertFalse(report['limits']['whole_paper_acceptance'])
            self.assertEqual(summary['papers'][0]['engine_answer_count'], 0)
            self.assertFalse((root/'originals/files'/(sha(b'PDF')+'.pdf')).exists())

    def test_source_extension_mismatch_unsupported_or_changed_fails_before_engine(self):
        for extension, claimed, changed, error in [
                ('.docx', '.pdf', False, 'extensions differ'),
                ('.exe', None, False, 'Unsupported'),
                ('.docx', None, True, 'source fingerprint')]:
            with self.subTest(extension=extension, claimed=claimed, changed=changed), TemporaryDirectory() as temporary:
                root = Path(temporary)
                bank, path = self.source_batch(root, extension, claimed, changed)
                with patch('scripts.run_organized_paper_regression.QuestionAnalyzer') as analyzer:
                    with self.assertRaisesRegex(ValueError, error):
                        run_transcription_batch([path], root/'replay', bank)
                    analyzer.assert_not_called()
                self.assertFalse((root/'replay').exists())

    def entry(self,text,quote,kind='grammar_fill'):
        start=text.index(quote)
        return {'question_id':'gaokao-2024-test-S12-Q56','question_type':kind,
                'question':{'text':quote},'shared_context':{'text':text},'options':[],
                'blank_location':{'start':start,'end':start+len(quote),'quote':quote}}

    def test_instruction_price_and_damaged_spaces_not_certified_blanks(self):
        text='阅读下面短文，在空白处填入 1 个适当的单词。\nBooks cost 99 pence.\nIt is 56 today.'
        self.assertIn('instruction',admission_issue(self.entry(text,' 1 '),text))
        self.assertIn('independent_blank',admission_issue(self.entry(text,' 99 '),text))
        self.assertIn('independent_blank',admission_issue(self.entry(text,' 56 '),text))

    def test_prompt_word_copied_after_the_printed_marker(self):
        text='In the_＿56_＿ (seven) grade, they started.'
        entry=self.entry(text,'＿56_')
        self.assertIsNone(admission_issue(entry,text))
        q=convert(entry,text)
        self.assertEqual(q['given_word'],'seven')
        self.assertEqual(q['passage'],text)
        no_hint='It changed ＿65＿ plastic to paper.'
        self.assertNotIn('given_word',convert(self.entry(no_hint,'＿65＿'),no_hint))

    def test_legacy_single_choice_does_not_become_grammar_fill(self):
        entry={'question_id':'old-Q21','question_type':'single_choice','question':{'text':'Why?'},
               'shared_context':{'text':'Why?'},'options':[{'label':'A','printed_delimiter':'.','projection':{'text':'A. Maybe'}}]}
        q=convert(entry,'Why?')
        self.assertEqual(q['question_type'],'未知')
        self.assertEqual(q['options'],{'A':'Maybe'})

    def transcription(self):
        content='Which?\nAlpha.\n第1页 | 共2页\nBeta.\nYes\nNo'
        q={'question_id':'test-Q1','question_type':'未知','stem':'Which?',
           'passage':'Alpha.\nBeta.','options':{'A':'Yes','B':'No'}}
        def span(text):
            start=content.index(text)
            return {'start':start,'end':start+len(text),'quote':text}
        dossier={'paper_id':'test-paper','source_sha256':sha(b'PDF'),'document_text':content}
        value={'paper_id':'test-paper','source_sha256':dossier['source_sha256'],
               'reviewer_agent':'/root/low_transcriber','reference_read':False,
               'phase':'low_model_source_transcription_no_answers',
               'inputs':{'paper_id':'test-paper','questions':[q]},
               'source_bindings':[{'question_id':'test-Q1','fields':{
                   '/stem':[span('Which?')],'/passage':[span('Alpha.\n'),span('Beta.')],
                   '/options/A':[span('Yes')],'/options/B':[span('No')]},
                   'display_exclusions':[span('第1页 | 共2页\n')]}]}
        return value,dossier

    def test_low_transcription_exact_source_and_recorded_pagination(self):
        value,dossier=self.transcription()
        inputs=validate_transcription(value,dossier)
        self.assertEqual(inputs,value['inputs'])
        inputs['questions'][0]['stem']='changed'
        self.assertEqual(value['inputs']['questions'][0]['stem'],'Which?')

    def test_low_transcription_normalizes_section_code_without_rewriting_frozen_material(self):
        value,dossier=self.transcription(); value['inputs']['questions'][0]['question_type']='single_choice'
        value['inputs']['questions'][0]['printed_number']='1'
        inputs=validate_transcription(value,dossier)
        self.assertEqual(inputs['questions'][0]['question_type'],'未知')
        self.assertEqual(value['inputs']['questions'][0]['question_type'],'single_choice')
        self.assertNotIn('printed_number',inputs['questions'][0])
        self.assertEqual(value['inputs']['questions'][0]['printed_number'],'1')
        for field in ('stem','passage','options'):
            self.assertEqual(inputs['questions'][0][field],value['inputs']['questions'][0][field])

    def test_low_transcription_rejects_answer_actions_and_reference_read(self):
        for field,content in [('answer','A'),('observations',[]),('relations',[]),('original_images',[])]:
            value,dossier=self.transcription(); value['inputs']['questions'][0][field]=content
            with self.subTest(field=field),self.assertRaisesRegex(ValueError,'cannot contain'):
                validate_transcription(value,dossier)
        value,dossier=self.transcription(); value['reference_read']=True
        with self.assertRaisesRegex(ValueError,'source-only'):
            validate_transcription(value,dossier)

    def test_low_transcription_rejects_missing_duplicate_reordered_or_changed_binding(self):
        value,dossier=self.transcription()
        variants=[]
        missing=deepcopy(value); del missing['source_bindings'][0]['fields']['/options/B']; variants.append(missing)
        duplicate=deepcopy(value); duplicate['inputs']['questions']*=2; variants.append(duplicate)
        reordered=deepcopy(value); reordered['source_bindings'][0]['fields']['/passage'].reverse(); variants.append(reordered)
        changed=deepcopy(value); changed['source_bindings'][0]['fields']['/stem'][0]['quote']='Which!'; variants.append(changed)
        for item in variants:
            with self.subTest(item=item),self.assertRaises(ValueError): validate_transcription(item,dossier)

    def test_low_transcription_cannot_delete_article_or_unrecorded_layout(self):
        value,dossier=self.transcription(); value['source_bindings'][0]['display_exclusions']=[]
        with self.assertRaisesRegex(ValueError,'Unrecorded'):
            validate_transcription(value,dossier)
        value,dossier=self.transcription()
        # Even an accurately quoted deletion cannot remove arbitrary article text.
        row=value['source_bindings'][0]['display_exclusions'][0]
        dossier['document_text']=dossier['document_text'].replace(row['quote'],'Important evidence.\n')
        # Rebuild accurate spans to show the rejection is about deletion type.
        content=dossier['document_text']
        for rows in value['source_bindings'][0]['fields'].values():
            for s in rows:
                s['start']=content.index(s['quote']); s['end']=s['start']+len(s['quote'])
        row.update(start=content.index('Important'),end=content.index('Beta.'),quote='Important evidence.\n')
        with self.assertRaisesRegex(ValueError,'pagination'):
            validate_transcription(value,dossier)

    def test_low_transcription_requires_prompt_from_its_own_grammar_blank(self):
        value,dossier=self.transcription(); content='___61___ (poor) studied'
        dossier['document_text']=content
        q={'question_id':'test-Q1','question_type':'grammar_fill','stem':'___61___','passage':content}
        value['inputs']['questions']=[q]
        fields={'/stem':[{'start':0,'end':8,'quote':'___61___'}],
                '/passage':[{'start':0,'end':len(content),'quote':content}]}
        value['source_bindings']=[{'question_id':'test-Q1','fields':fields,'display_exclusions':[]}]
        with self.assertRaisesRegex(ValueError,'prompt word missing'):
            validate_transcription(value,dossier)
        q['given_word']='poor'; fields['/given_word']=[{'start':10,'end':14,'quote':'poor'}]
        self.assertEqual(validate_transcription(value,dossier)['questions'][0]['given_word'],'poor')

    def test_low_batch_preflights_all_sources_before_analyzer_or_writes(self):
        with TemporaryDirectory() as temp:
            root=Path(temp); bank=root/'case-bank-v4'; paths=[]
            for n in (1,2):
                value,dossier=self.transcription(); pid='paper-'+str(n)
                value['paper_id']=dossier['paper_id']=value['inputs']['paper_id']=pid
                doc=bank/'papers'/(pid+'.json'); freeze_json(doc,dossier)
                value['source_document_sha256']=sha(doc.read_bytes())
                if n==2: value['source_document_sha256']='0'*64
                path=root/(pid+'.json'); freeze_json(path,value); paths.append(path)
            pdf=root/'originals/files'/(sha(b'PDF')+'.pdf'); pdf.parent.mkdir(parents=True); pdf.write_bytes(b'PDF')
            with patch('scripts.run_organized_paper_regression.QuestionAnalyzer') as analyzer:
                with self.assertRaisesRegex(ValueError,'dossier fingerprint'):
                    run_transcription_batch(paths,root/'replay',bank)
                analyzer.assert_not_called()
            self.assertFalse((root/'replay').exists())

    def test_low_batch_runs_real_question_and_paper_analyzers_without_answer_claim(self):
        with TemporaryDirectory() as temp:
            root=Path(temp); bank=root/'case-bank-v4'; value,dossier=self.transcription()
            doc=bank/'papers/test-paper.json'; freeze_json(doc,dossier)
            value['source_document_sha256']=sha(doc.read_bytes())
            path=root/'transcription.json'; freeze_json(path,value)
            pdf=root/'originals/files'/(sha(b'PDF')+'.pdf'); pdf.parent.mkdir(parents=True); pdf.write_bytes(b'PDF')
            summary=run_transcription_batch([path],root/'replay',bank)
            self.assertEqual(summary['papers'][0]['input_count'],1)
            self.assertEqual(summary['papers'][0]['engine_answer_count'],0)
            self.assertFalse(summary['whole_paper_acceptance'])
            self.assertEqual(summary['new_blind_samples'],0)
            self.assertIsNone(summary['new_question_count'])

if __name__=='__main__': unittest.main()
