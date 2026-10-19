from copy import deepcopy
import unittest

from ae_production.authored_episode import compile_clock, shift_body_clock
from ae_production.direct_extraction import validate_direct_extraction
from tests import test_authored_episode as fixtures


class DirectExtractionTests(unittest.TestCase):
    def test_reading_boundary_replaces_hold_and_shifts_complete_voice(self):
        a,c,l=fixtures.ClockConsumption().motion_input()
        before=compile_clock(a,c,l)
        shot=a['scenes'][0]
        shot['extraction_policy']='highlight_then_extract'
        shot['attention']=[{'anchor':'Inspect','phrase':'Source','target':'source'}]
        after=compile_clock(a,c,l)
        s=after['scenes'][0]
        self.assertEqual(s['extract_start'],s['reading_events'][-1]['end_time'])
        self.assertEqual(s['source_arrive'],s['extract_start'])
        self.assertAlmostEqual(s['extract_start']-s['extraction_highlight_at'],.25)
        self.assertEqual(s['extraction_highlights'],['Source'])
        self.assertAlmostEqual(before['segments'][0]['voice_start']-after['segments'][0]['voice_start'],before['scenes'][0]['extract_start']-s['extract_start'])
        self.assertAlmostEqual(before['segments'][0]['voice_start']-after['segments'][0]['voice_start'],4,delta=1/24+.0001)
        self.assertEqual(after['segments'][0]['voice'],before['segments'][0]['voice'])
        self.assertEqual(after['candidate_events'][0]['refs'],before['candidate_events'][0]['refs'])
        shifted=shift_body_clock(after,7.5)
        self.assertEqual(shifted['scenes'][0]['extraction_highlight_at'],s['extraction_highlight_at']+7.5)

    def fixture(self):
        s={'id':'s','extraction_policy':'highlight_then_extract','extract_start':3,
           'source_arrive':3,'extraction_highlight_at':2.75,'extraction_highlights':['word'],
           'reading_events':[{'end_time':3}],'settled':4,'end':7,'excerpt':'e',
           'source_refs':[{'world':'w','pointer':'/passage','start':0,'end':4}]}
        p={'scenes':[s],'excerpts':{'e':{'world':'w','block_ids':['b']}},
           'worlds':{'w':{'blocks':[{'id':'b','start':0,'end':4,'text':'word'}]}}}
        n={'comp_id':1,'master_comp_id':2,'audit':{
            'sources':[{'id':'b','text':'word','layer_id':11,'position':[2,4,100]}],
            'extractions':[{'scene':'s','selected_block_ids':['b'],'origin':[2,4,100],'group_id':12}],
            'direct_extractions':[{'scene':'s','extract_start':3,'settled':4,
                'highlight_at':2.75,'reading_end':3,'clone_ids':[13],
                'hits':[{'phrase':'word','name':'DIRECT_EXTRACTION_HIT_s_0',
                         'source_layer_id':11,'source_block_id':'b'}]}]}}
        rows=[{'comp_id':i,'scene':'s','in_point':3,'out_point':7,
               'group_id':12+(i-1)*100,'enabled':True,'guide':False,'three_d':True,
               'source_opacity':0,'clone_opacity':100,
               'position':[2,4,100],'expected_origin':[2,4,100],
               'clone_names':['EXTRACT_s_b'],
               'blocks':[{'block_id':'b','source_name':'b','source_id':11+(i-1)*100,
                    'source_text':'word','source_enabled':True,'source_guide':False,
                    'source_opacity':0,'source_position':[2,4,100],
                    'clone_name':'EXTRACT_s_b','clone_id':13+(i-1)*100,'clone_text':'word',
                    'clone_enabled':True,'clone_guide':False,'clone_three_d':True,
                    'clone_opacity':100,'clone_in':3,'clone_out':7,
                    'clone_parent':12+(i-1)*100,'clone_position':[0,0,0]}],
               'hits':[{'phrase':'word','source_text':'word','clone_text':'word','start':0,'end':4,
                        'name':'DIRECT_EXTRACTION_HIT_s_0','source_block_id':'b',
                        'source_id':11+(i-1)*100,'clone_id':13+(i-1)*100,
                        'clone_start':0,'clone_end':4,'source_units':2,'clone_units':2,
                        'source_smoothness':0,'clone_smoothness':0,
                        'source_peak':100,'clone_peak':100,
                        'source_samples':[0,50,100,100],'clone_samples':[0,50,100,100],
                        'source_expression_error':'','clone_expression_error':'',
                        'source_fill':[.69,.27,.06],'clone_fill':[.69,.27,.06],
                        'source_fill_error':'','clone_fill_error':'',
                        'source_opacity':0,'clone_opacity':100}]} for i in [1,2]]
        return p,n,rows

    def test_complete_native_handoff(self):
        self.assertEqual(validate_direct_extraction(*self.fixture())['status'],'PASS')

    def test_rejects_extra_hold_missing_comp_and_highlight_loss(self):
        for change in ['hold','missing','lost','origin','text']:
            with self.subTest(change=change):
                p,n,rows=self.fixture()
                if change=='hold':p['scenes'][0]['extract_start']+=1
                elif change=='missing':rows.pop()
                elif change=='lost':rows[0]['hits'][0]['clone_peak']=0
                elif change=='origin':rows[0]['position']=[0,0,0]
                else:rows[0]['hits'][0]['clone_text']='other'
                with self.assertRaises(ValueError):validate_direct_extraction(p,n,rows)


if __name__=='__main__':unittest.main()
