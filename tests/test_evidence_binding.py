"""Evidence path integrity, not verification of external English assertions."""
from copy import deepcopy
import unittest
from core.analyzer import QuestionAnalyzer
from core.evidence import validate_graph
from core.registry import Registry
from renderers import render
from tests.test_engine import grammar_review
from tests.test_execution import fixture as execution_fixture
from tests.test_writing_feedback import fixture as writing_fixture


class EvidenceBindingTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.registry=Registry(); cls.analyzer=QuestionAnalyzer(cls.registry)

    def assert_rejected(self,out):
        with self.assertRaisesRegex(ValueError,'own candidate relation path'):
            validate_graph(out['evidence_graph'])
        for kind in ('structured','student','legacy-wechat','content-export'):
            with self.subTest(renderer=kind),self.assertRaisesRegex(ValueError,'own candidate relation path'):
                render(out,kind,self.registry)

    def test_valid_objective_and_writing_candidate_paths_remain_usable(self):
        for q in (grammar_review(),writing_fixture()):
            out=self.analyzer.analyze(q); validate_graph(out['evidence_graph'],q)
            for kind in ('structured','student','legacy-wechat','content-export'):
                self.assertTrue(render(out,kind,self.registry))
        writing=self.analyzer.analyze(writing_fixture())
        self.assertTrue(all(n.get('candidate')=='student_draft' for n in writing['evidence_graph']['nodes'] if n['type']=='relation'))

    def test_objective_cannot_borrow_another_candidate_relation(self):
        out=self.analyzer.analyze(grammar_review())
        for node in out['evidence_graph']['nodes']:
            if node['type']=='relation': node['candidate']='different-candidate'
        self.assert_rejected(out)

    def test_writing_verification_cannot_borrow_another_draft_relation(self):
        out=self.analyzer.analyze(writing_fixture())
        for node in out['evidence_graph']['nodes']:
            if node['type']=='relation': node['candidate']='different-draft'
        self.assert_rejected(out)

    def test_candidate_claim_grafted_onto_conclusion_is_not_relation_proof(self):
        out=self.analyzer.analyze(grammar_review()); g=out['evidence_graph']
        claim=next(n['id'] for n in g['nodes'] if n['type']=='candidate_claim')
        relation=next(n['id'] for n in g['nodes'] if n['type']=='relation')
        decision=next(n['id'] for n in g['nodes'] if n['type']=='decision')
        g['edges']=[e for e in g['edges'] if not(e['from']==claim and e['to']==relation)]
        g['edges'].append({'from':claim,'to':decision,'type':'supports'})
        self.assert_rejected(out)

    def test_trigger_grafted_onto_conclusion_is_not_relation_proof(self):
        out=self.analyzer.analyze(grammar_review()); g=out['evidence_graph']
        signal=next(n['id'] for n in g['nodes'] if n['type']=='question_signal' and n.get('reviewed'))
        relation=next(n['id'] for n in g['nodes'] if n['type']=='relation')
        decision=next(n['id'] for n in g['nodes'] if n['type']=='decision')
        g['edges']=[e for e in g['edges'] if not(e['from']==signal and e['to']==relation)]
        g['edges'].append({'from':signal,'to':decision,'type':'supports'})
        self.assert_rejected(out)

    def test_trigger_quote_alone_cannot_replace_relation_source_evidence(self):
        out=self.analyzer.analyze(grammar_review()); g=out['evidence_graph']
        relation=next(n['id'] for n in g['nodes'] if n['type']=='relation')
        sources={n['id'] for n in g['nodes'] if n['type']=='source_evidence'}
        g['edges']=[e for e in g['edges'] if not(e['from'] in sources and e['to']==relation)]
        self.assert_rejected(out)

    def test_decision_artifact_needs_own_relation_even_without_conclusion_nodes(self):
        out=self.analyzer.analyze(execution_fixture()); g=deepcopy(out['evidence_graph'])
        removed={n['id'] for n in g['nodes'] if n['type'] in {'decision','verification'}}
        g['nodes']=[n for n in g['nodes'] if n['id'] not in removed]
        g['edges']=[e for e in g['edges'] if e['from'] not in removed and e['to'] not in removed]
        validate_graph(g)
        for n in g['nodes']:
            if n['type']=='relation' and n.get('candidate')=='A': n['candidate']='different'
        with self.assertRaisesRegex(ValueError,'Decision artifact without its own reviewed candidate relation'):
            validate_graph(g)


if __name__=='__main__': unittest.main()
