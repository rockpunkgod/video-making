"""Native state PASS requires full real comp, layer and time coverage."""
from copy import deepcopy
import unittest

from ae_production.authored_native import validate_visual_state_readback


class NativeVisualStates(unittest.TestCase):
    def fixture(self):
        p={'duration':5,'scenes':[{'id':'SC01','reading_events':[{'arrival':0,'end_time':2}]}],
           'visual_states':{'thinking_windows':[{'scene_id':'SC01','settled':2,'release':4}]}}
        spec={'reality_layers':['paper','words'],'foreground_layers':['EXTRACT_SC01_words']}
        n={'comp_id':1,'master_comp_id':2,'audit':{'visual_states':spec}}
        samples=[]
        for thinking,time in [(False,1),(True,3)]:
            target=100 if thinking else 0
            samples.append({'state':'thinking' if thinking else 'reading','time':time,'scene':'SC01',
                'environment':target,'reality':[{'name':name,'dim':target,'blur':12 if thinking else 0,
                    'errors':['','']} for name in spec['reality_layers']],
                'foreground':[{'name':'EXTRACT_SC01_words','amount':target,'error':'','blur_effect':False}]})
        rows=[{'comp_id':cid,'rows':deepcopy(samples),'paper':[242/255,240/255,234/255],
               'environment_color':[23/255,24/255,26/255],
               'foreground_inventory':[{'name':'EXTRACT_SC01_words','inPoint':0,'outPoint':5}]}
              for cid in (1,2)]
        return p,n,rows

    def test_complete_readbacks_pass_only_with_explicit_perceptual_limit(self):
        p,n,rows=self.fixture()
        self.assertEqual(validate_visual_state_readback(p,n,rows)['normal_speed_review'],'UNOBSERVED')

    def test_empty_or_duplicate_comp_readbacks_cannot_pass(self):
        p,n,rows=self.fixture()
        for altered in ([],rows[:1],[rows[0],rows[0]]):
            with self.subTest(altered=altered),self.assertRaisesRegex(ValueError,'proxy/master'):
                validate_visual_state_readback(p,n,altered)

    def test_missing_time_reality_or_foreground_cannot_pass(self):
        for scope in ('time','reality','foreground','foreground_inventory'):
            p,n,rows=self.fixture()
            if scope=='time':rows[0]['rows'].pop()
            elif scope=='foreground_inventory':rows[0][scope]=[]
            else:rows[0]['rows'][0][scope]=[]
            with self.subTest(scope=scope),self.assertRaises(ValueError):
                validate_visual_state_readback(p,n,rows)

    def test_missing_palette_and_thinking_ink_are_rejected(self):
        p,n,rows=self.fixture();rows[0]['paper']=[]
        with self.assertRaisesRegex(ValueError,'palette'):validate_visual_state_readback(p,n,rows)
        p,n,rows=self.fixture();rows[0]['rows'][1]['foreground'][0]['amount']=0
        with self.assertRaisesRegex(ValueError,'foreground'):validate_visual_state_readback(p,n,rows)

    def test_preserved_reading_mode_requires_original_background(self):
        p,n,rows=self.fixture()
        p['visual_states']['definition']={'reading':{'mode':'preserve_existing'}}
        for row in rows:
            row['paper']=[.955,.946,.92];row['background']=[.91,.905,.88]
        self.assertEqual(validate_visual_state_readback(p,n,rows)['normal_speed_review'],'UNOBSERVED')
        rows[1]['paper']=[242/255,240/255,234/255]
        with self.assertRaisesRegex(ValueError,'palette'):
            validate_visual_state_readback(p,n,rows)
