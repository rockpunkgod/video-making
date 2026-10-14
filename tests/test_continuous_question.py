"""Synthetic evidence slices: preserve exact lexical/source bindings in native lifts."""
from copy import deepcopy
import unittest
from creative_os.continuous_question import validate_projection


class ProjectionTests(unittest.TestCase):
    def setUp(self):
        self.bundle={'asset_id':'synthetic','source_snapshot':{'passage':'Alpha beta gamma.',
            'action_executions':[{'evidence':[{'field':'passage','start':6,'end':10}]}]}}
        self.projection={'action_index':0,'range':[6,10],'text':'beta'}

    def test_exact_subslice_and_read_only(self):
        before=deepcopy(self.bundle)
        ref=validate_projection(self.bundle,self.projection)
        self.assertEqual(ref['pointer'],'/source_snapshot/passage')
        self.assertEqual(before,self.bundle)

    def test_evidence_cannot_back_neighbouring_words(self):
        p=dict(self.projection,range=[0,5],text='Alpha')
        with self.assertRaises(ValueError):validate_projection(self.bundle,p)

    def test_rewording_and_empty_range_rejected(self):
        for p in (dict(self.projection,text='better'),dict(self.projection,range=[6,6],text='')):
            with self.assertRaises(ValueError):validate_projection(self.bundle,p)

    def test_partial_word_cannot_disappear_in_native_glyph_copy(self):
        with self.assertRaises(ValueError):validate_projection(self.bundle,dict(self.projection,range=[7,10],text='eta'))
