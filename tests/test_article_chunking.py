from copy import deepcopy
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from ae_production.article_chunking import (SCHEMA, compile_chunks, text_sha,
    bind_worlds, chunk_stage, current_chunks)
from video_contracts import write


def fixture():
    text='Each day, they take part in writing sessions.\nHigh school writers sign up for a summer camp.'
    bundles={'camp':{'source_snapshot':{'question_id':'Q1','passage':text}}}
    draft={'schema':SCHEMA,'editor':'Test language author','articles':{'camp':{
        'passage_sha256':text_sha(text),
        'chunks':['Each day,','they take part in','writing sessions.','High school writers','sign up for','a summer camp.'],
        'keep_together':['take part in','High school writers','sign up for']}}}
    return draft,bundles


class ArticleChunking(unittest.TestCase):
    def test_source_coverage_does_not_rewrite_whitespace_or_punctuation(self):
        d,b=fixture();r=compile_chunks(d,b)
        self.assertEqual(len(r['articles']['camp']['chunks']),6)
        for c in r['articles']['camp']['chunks']:
            self.assertEqual(b['camp']['source_snapshot']['passage'][c['start']:c['end']],c['text'])
        self.assertEqual(r['human_visual_review'],'PENDING')

    def test_reported_take_part_in_and_high_school_defects_are_blocked(self):
        for pieces in (['Each day,','they take','part in','writing sessions.','High school writers','sign up for','a summer camp.'],
                       ['Each day,','they take part in','writing sessions.','High','school writers','sign up for','a summer camp.']):
            d,b=fixture();d['articles']['camp']['chunks']=pieces
            with self.assertRaisesRegex(ValueError,'protected phrase was split'):compile_chunks(d,b)

    def test_missing_reordered_modified_or_partial_words_are_rejected(self):
        for index,value in [(1,'they take part'),(2,'writing workshops.'),(3,'High school'),(0,'Each')]:
            d,b=fixture();d['articles']['camp']['chunks'][index]=value
            with self.assertRaises(ValueError):compile_chunks(d,b)
        d,b=fixture();d['articles']['camp']['chunks'].pop()
        with self.assertRaisesRegex(ValueError,'unread words'):compile_chunks(d,b)

    def test_stale_source_and_unannotated_article_rejected(self):
        d,b=fixture();b['camp']['source_snapshot']['passage']+=' New facts.'
        with self.assertRaisesRegex(ValueError,'another source'):compile_chunks(d,b)
        d,b=fixture();b['second']=deepcopy(b['camp'])
        with self.assertRaisesRegex(ValueError,'every frozen article'):compile_chunks(d,b)

    def test_no_fixed_word_count_can_split_a_legitimate_group(self):
        text='the Center for the Study of Creative Writing'
        b={'w':{'source_snapshot':{'question_id':'q','passage':text}}}
        d={'schema':SCHEMA,'editor':'test','articles':{'w':{'passage_sha256':text_sha(text),'chunks':[text]}}}
        self.assertEqual(compile_chunks(d,b)['articles']['w']['chunks'][0]['text'],text)

    def test_excerpt_boundary_cannot_be_a_hidden_chunker(self):
        d,b=fixture();r=compile_chunks(d,b);text=b['camp']['source_snapshot']['passage']
        worlds={'camp':{'blocks':[{'id':'b','start':0,'end':len(text)}]}}
        bind_worlds(worlds,r)
        self.assertEqual(len(worlds['camp']['blocks'][0]['reading_chunks']),6)
        worlds={'camp':{'blocks':[{'id':'bad','start':0,'end':20},{'id':'tail','start':20,'end':len(text)}]}}
        with self.assertRaisesRegex(ValueError,'excerpt boundary'):bind_worlds(worlds,r)

    def test_source_packet_is_not_an_automatic_approval_or_word_count_fallback(self):
        d,b=fixture()
        with TemporaryDirectory() as temp:
            folder=Path(temp)
            self.assertFalse(chunk_stage(folder,b)['production_ready'])
            self.assertFalse((folder/'READING_CHUNKS.json').exists())
            write(folder/'ARTICLE_CHUNKS.json',d)
            self.assertEqual(chunk_stage(folder,b)['status'],'COMPILED')
            current_chunks(folder,b)
            d['articles']['camp']['chunks'][0:2]=['Each day, they take part in']
            write(folder/'ARTICLE_CHUNKS.json',d)
            with self.assertRaisesRegex(ValueError,'changed'):current_chunks(folder,b)
            write(folder/'native-identity.json',{'existing_aep':True})
            with self.assertRaisesRegex(ValueError,'new revision'):chunk_stage(folder,b)


if __name__=='__main__':unittest.main()
