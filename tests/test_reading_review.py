"""Deliberately reintroduce the user's defects; each must fail the gate."""
from copy import deepcopy
import json
import subprocess
import unittest
from ae_production.reading_review import validate_reading
from ae_production.authored_native import READING_RIG,template_source


def fixture():
    scenes=[{'id':'loc','kind':'locate','reading_events':[{'start':0,'end':22,'arrival':1,'end_time':2}]}]
    chunks=[{'source_start':0,'source_end':10,'center':1.25,'start':0,'end':10,'text':'first part'},
            {'source_start':11,'source_end':22,'center':1.75,'start':11,'end':22,'text':'second part'}]
    audit={'reading_windows':[{'id':'w','scene':'loc','source_start':0,'source_end':22,'arrival':1,'end_time':2,'chunks':chunks}], 'query_handoffs':[{'scene':'loc'}]}
    checks=[{'text':c['text'],'range':[c['start'],c['end']],'inside_measured_line':True,'expression_error':'','threeD':True,'rest_error':[0,0],'peak':104,'color_peak':100,'coverage_complete':True} for c in chunks]
    observed={'windows':[{'id':'w','chunks':checks,'all_rows_covered':True,'frames':[{'amounts':[100,0]},{'amounts':[0,100]}]}],
              'handoffs':[{'margin_before_exit':0,'source_join':100,'landed_error':0,'ink_error':0,'frames':[{'opacity':0,'color':[.1,.1,.1],'screen':[100,60,1400]},{'opacity':0,'color':[.1,.1,.1],'screen':[105,60,1400]}]}]}
    return scenes,audit,observed


class KnownReadingDefects(unittest.TestCase):
    def test_valid_sequence_keeps_human_review_pending(self):
        self.assertEqual(validate_reading(*fixture())['human_visual_review'],'PENDING')

    def test_missing_paragraph_is_rejected(self):
        s,a,o=fixture();s[0]['reading_events'].append({'start':30,'end':60,'arrival':3,'end_time':4})
        with self.assertRaisesRegex(ValueError,'Every authored'):validate_reading(s,a,o)

    def test_reverse_or_simultaneous_focus_is_rejected(self):
        for frames in ([{'amounts':[0,100]},{'amounts':[100,0]}],[{'amounts':[100,100]}]):
            s,a,o=fixture();o['windows'][0]['frames']=frames
            with self.assertRaisesRegex(ValueError,'never visibly'):validate_reading(s,a,o)

    def test_cross_line_or_skipped_words_are_rejected(self):
        for field in ['inside_measured_line','coverage_complete','threeD']:
            s,a,o=fixture();o['windows'][0]['chunks'][0][field]=False
            with self.assertRaises(ValueError):validate_reading(s,a,o)

    def test_full_stem_mask_pop_is_rejected(self):
        s,a,o=fixture();o['handoffs'][0]['margin_before_exit']=100
        with self.assertRaisesRegex(ValueError,'one frame'):validate_reading(s,a,o)

    def test_entire_skipped_row_is_rejected(self):
        s,a,o=fixture();o['windows'][0]['all_rows_covered']=False
        with self.assertRaisesRegex(ValueError,'row was skipped'):validate_reading(s,a,o)

    def test_query_color_flash_is_rejected(self):
        s,a,o=fixture();o['handoffs'][0]['frames'][0]['color']=[.7,.3,.1]
        with self.assertRaisesRegex(ValueError,'color flashes'):validate_reading(s,a,o)

    def test_missing_word_or_offscreen_return_is_rejected(self):
        s,a,o=fixture();o['handoffs'][0]['source_join']=0
        with self.assertRaisesRegex(ValueError,'Missing-word'):validate_reading(s,a,o)
        s,a,o=fixture();o['handoffs'][0]['frames'][0]['screen'][1]=-5
        with self.assertRaisesRegex(ValueError,'viewport'):validate_reading(s,a,o)

    def test_default_template_consumes_the_real_shared_rig(self):
        source=template_source()
        self.assertIn(READING_RIG.read_text('utf-8'),source)
        self.assertEqual(source.count('function cmReadingSequence('),1)
        self.assertNotIn('function wordFocus(',source)
        self.assertIn('cmReadingSequence(rows,e,s.id,audit',source)
        self.assertIn('cmQueryHandoff(C,carried',source)

    def test_native_layout_must_consume_exact_authored_phrases(self):
        text='Each day, they take part in writing sessions.'
        pieces=['Each day,','they take part in','writing sessions.'];at=0;chunks=[]
        for piece in pieces:
            at=text.index(piece,at);chunks.append({'id':str(at),'start':at,'end':at+len(piece),'text':piece});at+=len(piece)
        code=READING_RIG.read_text('utf-8')+'\nvar text='+json.dumps(text)+';var block='+json.dumps({'start':0,'reading_chunks':chunks})+';'
        result=json.loads(subprocess.check_output(['node','-e',code+'process.stdout.write(JSON.stringify(cmMappedChunks(text,0,text.length,block)));']))
        self.assertEqual([c['text'] for c in result],pieces)
        # The former native line ended after "take". It must now request a
        # layout correction, not silently manufacture two animation phases.
        result=subprocess.run(['node','-e',code+'cmMappedChunks(text,0,20,block);'],capture_output=True)
        self.assertNotEqual(result.returncode,0)
        self.assertIn(b'Native line split a semantic chunk',result.stderr)

    def test_readback_rejects_split_or_stale_phrase_identity(self):
        s,a,o=fixture();authored={'articles':{'test':{'chunks':[]}}}
        for i,c in enumerate(a['reading_windows'][0]['chunks']):
            c['chunk_id']=str(i);authored['articles']['test']['chunks'].append({'id':str(i),'start':c['source_start'],'end':c['source_end'],'text':c['text']})
            o['windows'][0]['chunks'][i]['no_break']=True
        self.assertTrue(validate_reading(s,a,o,authored)['article_chunking_checked'])
        a['reading_windows'][0]['chunks'][0]['source_end']-=1
        with self.assertRaisesRegex(ValueError,'authored sense group'):validate_reading(s,a,o,authored)


if __name__=='__main__':unittest.main()
