"""Reject partial/early-reveal native challenge proofs before media rendering."""
from copy import deepcopy
import unittest
from ae_production.authored_native import validate_challenge_native


class ChallengeNativeTests(unittest.TestCase):
    def fixture(self):
        q={'question_id':'q','passage':'Full original.\nNecessary context.',
           'stem':'What can students do?', 'options':{c:'Whole option '+c for c in 'ABCD'}}
        ch={'scene':'SC01','world':'w','question_id':'q','start_frame':24,'end_frame':96,'start':1,'end':4}
        source={'bundle':'frozen.json','status':'status.json'}
        p={'world_order':['w'],'worlds':{'w':{'question':q,'source':source}},'audience_challenges':{'rows':[ch]}}
        texts=[q['stem']]+[c+'   '+q['options'][c] for c in 'ABCD']
        glyphs=[{'text':text,'opacity':100,'position':[830 if i else 820,300+(i-1)*58 if i else 192,0],
                 'scale':[38,38,38],'animators':0,'colors':[[.09,.13,.16] for _ in text],
                 'enabled':True,'guide':False} for i,text in enumerate(texts)]
        row={'scene':'SC01','article_text':q['passage'].replace('\n',' '),
             'article_comment':{'exact_text':q['passage'],'question_id':'q','source':source},
             'badge_text':'想先自己做？可暂停','badge_in':1,'badge_out':4,'badge_spoken':False,'badge_enabled':True,'badge_guide':False,
             'article_enabled':True,'article_guide':False,'article_in':1,'article_out':4.8,'article_threeD':True,'article_height':400,'article_width':760,
             'samples':[{'frame':f,'article_opacity':100,'badge_opacity':100,'article_position':[40,132,0],'article_scale':[100,100,100],'camera_position':[640,320,-1550],'camera_target':[640,320,0],'aperture':0,'glyphs':deepcopy(glyphs)} for f in range(24,96)]}
        rows=[dict(deepcopy(row),comp_id=cid) for cid in [1,9]]
        return p,rows

    def test_both_compositions_all_frames_do_not_claim_perception(self):
        p,rows=self.fixture();r=validate_challenge_native(p,rows,[1,9])
        self.assertEqual(r['normal_speed_review'],'UNOBSERVED')
        self.assertEqual(r['mobile_legibility'],'UNOBSERVED')

    def test_missing_duplicate_or_wrong_composition_cannot_pass(self):
        for kind in ['missing','duplicate','wrong']:
            p,rows=self.fixture()
            if kind=='missing':rows.pop()
            elif kind=='duplicate':rows[1]=deepcopy(rows[0])
            else:rows[1]['comp_id']=8
            with self.subTest(kind=kind),self.assertRaises(ValueError):validate_challenge_native(p,rows,[1,9])

    def test_single_bad_frame_or_71_frames_fails(self):
        for kind in ['missing','wrong_frame','source_hidden','hint_hidden','nan','option_hidden']:
            p,rows=self.fixture();sample=rows[1]['samples'][35]
            if kind=='missing':rows[1]['samples'].pop()
            elif kind=='wrong_frame':sample['frame']=999
            elif kind=='source_hidden':sample['article_opacity']=0
            elif kind=='hint_hidden':sample['badge_opacity']=0
            elif kind=='nan':sample['article_opacity']=float('nan')
            else:sample['glyphs'][2]['opacity']=0
            with self.subTest(kind=kind),self.assertRaises(ValueError):validate_challenge_native(p,rows,[1,9])

    def test_complete_content_identity_and_exact_badge_scope(self):
        for field,value in [('article_text','Only the answer block'),('badge_text','Choose A'),
                            ('badge_out',4+1/24),('badge_in',1+1/24),('badge_spoken',True),('badge_enabled',False),('badge_guide',True),
                            ('article_in',1.01),('article_out',3.9),('article_threeD',False),('article_height',449),('article_width',800),('article_enabled',False),('article_guide',True)]:
            p,rows=self.fixture();rows[1][field]=value
            with self.subTest(field=field),self.assertRaises(ValueError):validate_challenge_native(p,rows,[1,9])
        p,rows=self.fixture();rows[1]['article_comment']['source']={'bundle':'another question'}
        with self.assertRaises(ValueError):validate_challenge_native(p,rows,[1,9])

    def test_any_option_rewrite_judgment_highlight_or_incomplete_color_readback_fails(self):
        for kind in ['rewrite','color','empty_color','nan_color','animator','position','scale']:
            p,rows=self.fixture();g=rows[0]['samples'][0]['glyphs'][1]
            if kind=='rewrite':g['text']='A   Correct answer'
            elif kind=='color':g['colors'][0]=[.69,.27,.06]
            elif kind=='empty_color':g['colors']=[]
            elif kind=='nan_color':g['colors'][0]=[float('nan'),.13,.16]
            elif kind=='animator':g['animators']=1
            elif kind=='position':g['position'][1]+=10
            else:g['scale']=[0,0,0]
            with self.subTest(kind=kind),self.assertRaises(ValueError):validate_challenge_native(p,rows,[1,9])

if __name__=='__main__':unittest.main()
