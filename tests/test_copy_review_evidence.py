"""Synthetic external-copy receipts; no real human review, media QA or Adobe."""
from copy import deepcopy
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from ae_production import authored_episode as episode
from ae_production import autonomous_episode as autonomous
from ae_production import authored_native as native
from scripts.voice_delivery import sha256
from video_contracts import read,sha,write


class CopyReviewEvidence(unittest.TestCase):
    def setUp(self):
        temporary=TemporaryDirectory();self.addCleanup(temporary.cleanup)
        self.root=Path(temporary.name);self.folder=self.root/'episode';self.folder.mkdir()
        self.source=self.root/'captured-user-copy.md';self.receipt=self.root/'external-copy-review.json'
        self.source.write_text('# Synthetic external source fixture\n\n### SC01 · Opening\n\n先别猜，\n回文章看看。\n\n'
                               '### SC09L · Relation\n\n把 those options 代入前面那两款。\n',encoding='utf-8')
        self.rows=[{'scene':'SC01','text':'先别猜，回文章看看。'},
                   {'scene':'SC09L','text':'把thoseoptions代入前面那两款。'}]
        self.evidence={'schema':'explicit-user-copy-review/v1','authority':'explicit_current_chat_user_copy_review',
            'reviewer_kind':'external_human','scope':'exact_spoken_copy_only',
            'source_markdown':str(self.source.resolve()),'source_markdown_sha256':sha256(self.source),
            'reviewed_copy_sha256':sha(self.rows),'user_reviewed':True,'film_accepted':False,
            'listening_accepted':False,'public_render_ready':False}
        self.author={'revision':'synthetic','product':'FREE_SHOWCASE','format':{'width':1920,'height':1080,'fps':24},
            'media_role':'EDITORIAL_PROXY','public_render_ready':False,'copy_review':'USER_REVIEWED_EXACT_COPY',
            'input_files':{},'sources':{},'voices':[{'id':'one','text':'先别猜，'},
                {'id':'two','text':'回文章看看。'},{'id':'relation','text':'把 those options 代入前面那两款。'}],
            'scenes':[{'id':'SC01','title':'Opening','voice_ids':['one','two']},
                      {'id':'SC09L','title':'Relation','voice_ids':['relation']}]}
        self.bind()

    def bind(self):
        write(self.receipt,self.evidence)
        self.author['copy_review_evidence']={'path':str(self.receipt.resolve()),'sha256':sha256(self.receipt)}
        self.author['input_files']={str(self.receipt.resolve()):sha256(self.receipt),
                                    str(self.source.resolve()):sha256(self.source)}

    def test_actual_source_and_complete_scene_voices_are_checked_without_upgrading_film(self):
        result=episode.validate_copy_review(self.author)
        self.assertTrue(result['user_reviewed']);self.assertEqual(result['reviewed_copy_sha256'],sha(self.rows))
        for field in ('film_accepted','listening_accepted','public_render_ready'):
            self.assertFalse(result[field])
        self.assertIn('文案状态：用户已独立审阅（仅此逐字稿）',episode.script_text(self.author))

    def test_reviewed_label_without_bound_receipt_is_rejected(self):
        self.author.pop('copy_review_evidence')
        with self.assertRaisesRegex(ValueError,'bound external'):episode.validate_copy_review(self.author)

    def test_merged_hook_copy_requires_the_opening_as_well_as_body(self):
        self.author['audience_hook']={'scene_id':'HOOK01','voice_ids':['hook']}
        self.author['voices'].insert(0,{'id':'hook','text':'为什么不能选？'})
        text=self.source.read_text('utf-8').replace('### SC','## SC')
        self.source.write_text('## HOOK01 · Opening\n\n为什么不能选？\n\n'+text,encoding='utf-8')
        self.evidence['source_markdown_sha256']=sha256(self.source)
        self.evidence['reviewed_copy_sha256']=sha([{'scene':'HOOK01','text':'为什么不能选？'}]+self.rows)
        self.bind()
        self.assertTrue(episode.validate_copy_review(self.author)['user_reviewed'])
        self.author['voices'][0]['text']='Different opening.'
        with self.assertRaisesRegex(ValueError,'exact spoken copy'):
            episode.validate_copy_review(self.author)

    def test_source_and_receipt_both_need_author_input_bindings(self):
        original=deepcopy(self.author['input_files'])
        for path in original:
            self.author['input_files']={p:d for p,d in original.items() if p!=path}
            with self.subTest(path=path),self.assertRaisesRegex(ValueError,'binding changed'):
                episode.validate_copy_review(self.author)

    def test_changed_spoken_word_punctuation_or_english_case_cannot_reuse_user_review(self):
        for text in ('别急，','先别猜。','先别猜，Air'):
            author=deepcopy(self.author);author['voices'][0]['text']=text
            with self.subTest(text=text),self.assertRaisesRegex(ValueError,'exact spoken copy'):
                episode.validate_copy_review(author)
        self.author['voices'][2]['text']='把 Those options 代入前面那两款。'
        with self.assertRaisesRegex(ValueError,'exact spoken copy'):episode.validate_copy_review(self.author)

    def test_changed_source_or_receipt_bytes_are_rejected(self):
        self.source.write_text(self.source.read_text('utf-8')+'Changed original input',encoding='utf-8')
        with self.assertRaisesRegex(ValueError,'binding changed'):episode.validate_copy_review(self.author)

    def test_rebound_source_hash_still_requires_the_actual_same_words(self):
        self.source.write_text(self.source.read_text('utf-8').replace('回文章看看','直接选答案'),encoding='utf-8')
        self.evidence['source_markdown_sha256']=sha256(self.source);self.bind()
        with self.assertRaisesRegex(ValueError,'exact spoken copy'):episode.validate_copy_review(self.author)

    def test_false_source_sha_cannot_be_hidden_by_rehashing_receipt(self):
        self.evidence['source_markdown_sha256']='0'*64;self.bind()
        with self.assertRaisesRegex(ValueError,'binding changed'):episode.validate_copy_review(self.author)

    def test_ai_reviewer_wrong_scope_or_film_and_listening_claims_are_rejected(self):
        original=deepcopy(self.evidence)
        for key,value in [('reviewer_kind','ai_host'),('authority','self_signed_pass'),('scope','entire_film'),
                          ('user_reviewed',False),('film_accepted',True),('listening_accepted',True),
                          ('public_render_ready',True)]:
            self.evidence={**original,key:value};self.bind()
            with self.subTest(key=key),self.assertRaisesRegex(ValueError,'exact-copy-only scope'):
                episode.validate_copy_review(self.author)

    def test_scene_identity_order_and_duplicate_placement_are_not_just_a_hash_claim(self):
        original=deepcopy(self.author)
        for edit in (lambda a:a['scenes'].reverse(),lambda a:a['scenes'][0].update(id='SC99'),
                     lambda a:a['scenes'][0]['voice_ids'].append('one'),
                     lambda a:a['voices'].append({'id':'unused','text':'unplaced'})):
            author=deepcopy(original);edit(author)
            with self.subTest(edit=edit),self.assertRaises(ValueError):episode.validate_copy_review(author)

    def test_reviewed_digest_is_verified_against_both_source_and_author(self):
        self.evidence['reviewed_copy_sha256']='0'*64;self.bind()
        with self.assertRaisesRegex(ValueError,'complete copy digest'):episode.validate_copy_review(self.author)

    def test_checked_author_revalidates_the_evidence_on_every_read(self):
        write(self.folder/'AV_AUTHOR.json',self.author)
        # The remaining complete-film source checks are outside this fixture.
        with self.assertRaisesRegex(ValueError,'distinct, source-bound questions'):episode.checked_author(self.folder)
        self.receipt.write_text(self.receipt.read_text('utf-8')+'\n',encoding='utf-8')
        with self.assertRaisesRegex(ValueError,'binding changed'):episode.checked_author(self.folder)

    def test_pending_labels_and_missing_historical_label_do_not_gain_approval(self):
        for label in ('PENDING','PENDING independent user review'):
            author=deepcopy(self.author);author['copy_review']=label;author.pop('copy_review_evidence')
            self.assertFalse(episode.validate_copy_review(author)['user_reviewed'])
            self.assertIn('文案状态：'+label+'\n',episode.script_text(author))
        self.author.pop('copy_review');self.author.pop('copy_review_evidence')
        self.assertFalse(episode.validate_copy_review(self.author)['user_reviewed'])

    def response(self):
        return {'human_approved':False,'author':deepcopy(self.author),'editorial_manifest':{'synthetic':True},
                'authoring_notes':'SYNTHETIC copy-only consumption test'}

    def test_autonomous_consumer_accepts_exact_user_copy_and_keeps_ai_authority_false(self):
        with patch.object(autonomous,'checked_author',return_value=(self.author,{})), \
                patch.object(autonomous,'complete_chunks',return_value={'status':'COMPILED'}):
            result=autonomous.consume_author_response(self.folder,self.response())
        self.assertEqual(result['status'],'AUTHORED')
        saved=read(self.folder/'AUTHORING_RECEIPT.json')
        self.assertFalse(saved['human_approved']);self.assertFalse(saved['public_render_ready'])
        self.assertEqual(read(self.folder/'AV_AUTHOR.json')['copy_review'],'USER_REVIEWED_EXACT_COPY')

    def test_copy_evidence_cannot_approve_ai_or_publication(self):
        response=self.response();response['human_approved']=True
        with self.assertRaisesRegex(ValueError,'does not approve'):autonomous.consume_author_response(self.folder,response)
        response=self.response();response['author']['public_render_ready']=True
        with self.assertRaisesRegex(ValueError,'does not approve'):autonomous.consume_author_response(self.folder,response)
        self.assertFalse((self.folder/'AV_AUTHOR.json').exists())

    def test_review_page_separates_reviewed_copy_from_pending_film_and_listening(self):
        plan={'revision':'synthetic','duration':1,'copy_review':'USER_REVIEWED_EXACT_COPY',
              'scenes':[{'id':'SC01','start':0,'title':'Synthetic scene'}]}
        write(self.folder/'AV_PLAN.json',plan)
        media=self.folder/'synthetic.bin';media.write_bytes(b'not media')
        autonomous.review_page(self.folder,{'media':str(media)})
        text=(self.folder/'REVIEW.html').read_text('utf-8')
        self.assertIn('此逐字稿已由用户独立审阅',text);self.assertIn('观感、听感和整片仍待你验收',text)
        plan['copy_review']='PENDING';write(self.folder/'AV_PLAN.json',plan)
        autonomous.review_page(self.folder,{'media':str(media)})
        self.assertIn('文案、观感和听感仍待确认',(self.folder/'REVIEW.html').read_text('utf-8'))

    def test_package_metadata_propagates_copy_scope_only(self):
        media=self.folder/'media';media.mkdir()
        for name in ('MAIN_FILM.aep','MAIN_FILM.prproj','PR_NATIVE_EXPORT.mp4','MAIN_FILM_4K24.mp4','picture.bin'):
            (media/name).write_bytes(b'SYNTHETIC package metadata boundary only')
        plan={'frames':24,'duration':1,'segments':[],'copy_review':self.author['copy_review'],
              'voice_delivery_sha256':'synthetic voice binding','complete_copy_sha256':'synthetic copy binding'}
        write(self.folder/'AV_PLAN.json',plan)
        write(self.folder/'MASTER_PICTURE_RECEIPT.json',{'plan_sha256':sha256(self.folder/'AV_PLAN.json'),
            'frames':24,'comp_id':2,'formal_4k_rendered':True,'output':str(media/'picture.bin'),
            'sha256':sha256(media/'picture.bin')})
        streams={'streams':[{'codec_type':'video','width':3840,'height':2160,'r_frame_rate':'24/1','nb_read_frames':'24'},
                             {'codec_type':'audio','codec_name':'aac','sample_rate':'48000','time_base':'1/48000'}]}
        # Engineering media routines are mocked: this tests only authority field
        # propagation and explicitly makes no synthetic decode/listening claim.
        with patch.object(native,'current_native',return_value=(self.author,plan,{'master_comp_id':2})), \
                patch.object(native,'probe',return_value=streams), \
                patch.object(native,'measured_audio_delay',return_value=(0,[])), \
                patch.object(native,'packet_binding',return_value='SYNTHETIC packets'), \
                patch.object(native,'audio_packet_rows',return_value=[]), \
                patch.object(native,'verify_prior_production',return_value={'scope':'SYNTHETIC'}), \
                patch.object(native.subprocess,'check_output',return_value=b'\0\0'*64), \
                patch.object(native.subprocess,'run'):
            native.package(self.folder,master=True)
        qa=read(self.folder/'MASTER_DELIVERY_QA.json')
        self.assertEqual(qa['independent_new_copy_review'],'USER_REVIEWED_EXACT_COPY')
        self.assertEqual(qa['human_creative_review'],'PENDING');self.assertEqual(qa['human_listening_review'],'PENDING')
        self.assertFalse(qa['public_render_ready']);self.assertEqual(qa['student_count'],0)


if __name__=='__main__':unittest.main()
