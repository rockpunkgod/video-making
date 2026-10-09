import unittest
from scripts.run_organized_paper_regression import admission_issue, convert

class OrganizedRegressionTests(unittest.TestCase):
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

if __name__=='__main__': unittest.main()
