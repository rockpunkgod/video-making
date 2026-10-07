"""Synthetic ordering and no-premature-analysis checks for original-task previews."""
from copy import deepcopy
from unittest import TestCase
from unittest.mock import patch
from creative_os.passage_sequence import question_first,validate_sequence


class Font:
    def getlength(self,text):return len(text)*18


def inputs():
    questions=[dict(question_id=q,number=i,stem='Synthetic question '+q,
                    options={'A':'alpha','B':'beta','C':'gamma','D':'delta'}) for i,q in enumerate(['q1','q2'],1)]
    scenes=[dict(segment_id=str(i),question_id=q,heading='Synthetic task',segment_sha='frozen-'+str(i),start=i*5,duration=5)
            for i,q in enumerate(['q1','q1','q2'])]
    plan=dict(plan_sha='synthetic-plan',fonts=dict(english='font',chinese='font'),scenes=scenes,
              canvas=dict(width=1920,height=1080,fps=24,duration=15))
    bundle=dict(semantic_binding_sha='frozen',payload=dict(passage='Synthetic original passage.',questions=questions))
    return plan,bundle


@patch('creative_os.passage_sequence.validate_plan')
@patch('PIL.ImageFont.truetype',return_value=Font())
class QuestionFirstTests(TestCase):
    def test_full_original_and_neutral_question_precede_every_explanation_group(self,font,validate):
        p,b=inputs();s=question_first(p,b,{})
        self.assertEqual([e['kind'] for e in s['entries']],['original','original','explanation','explanation','original','explanation'])
        self.assertEqual(s['entries'][0]['card_id'],'original-passage-1')
        for card in s['cards'].values():
            self.assertTrue(all('review' not in n['origin'] for n in card['nodes']))
            self.assertFalse(any('JUDGMENT' in n['name'] or 'STATE' in n['name'] for n in card['nodes']))
            if card['kind']=='original_question':self.assertEqual(sum(n['name'].startswith('OPTION_') for n in card['nodes']),4)
        self.assertEqual(s['canvas']['duration'],43)
        self.assertFalse(s['preview_is_full_reading_time']);self.assertFalse(s['public_render_ready'])

    def test_inserted_answer_or_skipped_original_invalidates_sequence(self,font,validate):
        p,b=inputs();s=question_first(p,b,{})
        changed=deepcopy(s);changed['entries'].pop(1)
        with self.assertRaises(ValueError):validate_sequence(changed,p,b,{})
        changed=deepcopy(s);changed['cards']['original-question-1']['nodes'][-1]['text']='Correct answer: A'
        with self.assertRaises(ValueError):validate_sequence(changed,p,b,{})

    def test_silent_cross_question_reordering_is_rejected(self,font,validate):
        p,b=inputs();p['scenes'].append(dict(p['scenes'][0],segment_id='later',start=15))
        with self.assertRaises(ValueError):question_first(p,b,{})
