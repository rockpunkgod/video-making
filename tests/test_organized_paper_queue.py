import json
from pathlib import Path
import tempfile
import unittest

from scripts.organized_paper_queue import assign, advance_semantic, connect, initialize, paper_label, record_report, snapshot
from scripts.ingest_exam_sources import freeze_json, sha

class PaperQueueTests(unittest.TestCase):
    def test_human_labels_preserve_region_volume_season(self):
        self.assertEqual(paper_label('x/2021年高考英语试卷（新高考Ⅱ卷）（空白卷）.pdf'), 'gaokao-2021-new-gaokao-ii')
        self.assertEqual(paper_label('x/2020年高考英语试卷（浙江）（1月）（空白卷）.pdf'), 'gaokao-2020-zhejiang-m01')
        self.assertEqual(paper_label('02_2026真题/二卷/英语Ⅱ卷试题.pdf'), 'gaokao-2026-national-ii')

    def test_distinct_agents_required_and_report_source_binding(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp); db=connect(root/'queue.sqlite')
            rows=[{'relative_path':f'{i}/2020年高考英语试卷（北京）（空白卷）.pdf', 'extension':'.pdf',
                   'sha256':str(i)*64,'filename_claim':'questions_only'} for i in (1,2)]
            self.assertEqual(initialize(db,{'files':rows}),2)
            assign(db,'gaokao-2020-beijing-v01','/root/paper_one','gpt-6-sol','high',str(root/'one'))
            with self.assertRaises(Exception):
                assign(db,'gaokao-2020-beijing-v02','/root/paper_one','gpt-6-sol','high',str(root/'two'))
            db.rollback()
            self.assertEqual(snapshot(db)['counts'],{'pending':1,'running':1})
            (root/'one').mkdir()
            (root/'one/review.json').write_text(json.dumps({'source_sha256':'2'*64}),encoding='utf-8')
            with self.assertRaises(ValueError): record_report(db,'gaokao-2020-beijing-v01','PARTIAL')
            (root/'one/review.json').write_text(json.dumps({'source_sha256':'1'*64,
                'paper_id':'gaokao-2020-beijing-v01','reviewer_agent':'/root/paper_one'}),encoding='utf-8')
            record_report(db,'gaokao-2020-beijing-v01','PARTIAL')
            self.assertEqual(snapshot(db)['counts'],{'pending':1,'reviewed':1})
            db.close()

    def test_explicit_revision_preserves_original_and_checks_reviewer(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp); db=connect(root/'queue.sqlite')
            row={'relative_path':'2021年高考英语试卷（北京）（空白卷）.pdf','extension':'.pdf',
                 'sha256':'a'*64,'filename_claim':'questions_only'}
            initialize(db,{'files':[row]})
            pid='gaokao-2021-beijing-v01'
            assign(db,pid,'/root/revision_worker','gpt-6-sol','high',str(root/'paper'))
            (root/'paper').mkdir()
            original=b'{"superseded":true}'
            (root/'paper/review.json').write_bytes(original)
            revision={'paper_id':pid,'source_sha256':'a'*64,'reviewer_agent':'/root/wrong_worker'}
            (root/'paper/review-v2.json').write_text(json.dumps(revision),encoding='utf-8')
            with self.assertRaises(ValueError): record_report(db,pid,'PARTIAL','review-v2.json')
            with self.assertRaises(ValueError): record_report(db,pid,'PARTIAL','../review.json')
            revision['reviewer_agent']='/root/revision_worker'
            (root/'paper/review-v2.json').write_text(json.dumps(revision),encoding='utf-8')
            record_report(db,pid,'PARTIAL','review-v2.json')
            stored=db.execute('SELECT * FROM papers WHERE paper_id=?',(pid,)).fetchone()
            self.assertEqual(stored['report_file'],'review-v2.json')
            self.assertEqual((root/'paper/review.json').read_bytes(),original)
            db.close()

    def test_manifest_drift_cannot_rewrite_ids(self):
        with tempfile.TemporaryDirectory() as tmp:
            db=connect(Path(tmp)/'q.sqlite')
            row={'relative_path':'2021年高考英语试卷（北京）（空白卷）.pdf','extension':'.pdf',
                 'sha256':'a'*64,'filename_claim':'questions_only'}
            initialize(db,{'files':[row]})
            with self.assertRaises(ValueError): initialize(db,{'files':[{**row,'sha256':'b'*64}]})
            db.close()

    def test_semantic_stage_binds_preflighted_bytes_and_preserves_low_agent_history(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp); db=connect(root/'q.sqlite')
            row={'relative_path':'2021年高考英语试卷（北京）（空白卷）.pdf','extension':'.pdf',
                 'sha256':'a'*64,'filename_claim':'questions_only'}
            initialize(db,{'files':[row]}); pid='gaokao-2021-beijing-v01'
            assign(db,pid,'/root/transcribe','gpt-6-luna','low',str(root/'paper'))
            source=root/'paper/transcription.json'
            freeze_json(source,{'paper_id':pid,'source_sha256':'a'*64,'reviewer_agent':'/root/transcribe',
                                'reference_read':False,'phase':'low_model_source_transcription_no_answers'})
            replay=root/'replay.json'
            result={'paper_id':pid,'source_sha256':'a'*64,'transcription_sha256':'0'*64,
                    'phase':'source_transcription_engine_replay_not_semantic_acceptance'}
            freeze_json(replay,result)
            with self.assertRaisesRegex(ValueError,'exact transcription'):
                advance_semantic(db,pid,'/root/semantic','gpt-6-sol','medium',source,replay)
            self.assertEqual(db.execute('SELECT agent_task FROM papers').fetchone()[0],'/root/transcribe')
            result['transcription_sha256']=sha(source.read_bytes()); good=root/'replay-v2.json'; freeze_json(good,result)
            advance_semantic(db,pid,'/root/semantic','gpt-6-sol','medium',source,good)
            self.assertEqual(db.execute('SELECT agent_task FROM papers').fetchone()[0],'/root/semantic')
            self.assertEqual(snapshot(db)['counts'],{'running':1})
            events=list(db.execute('SELECT event,detail FROM events ORDER BY sequence'))
            self.assertEqual([e[0] for e in events],['agent_assigned','semantic_agent_assigned'])
            self.assertEqual(json.loads(events[-1][1])['previous_transcription_assignment']['agent_task'],'/root/transcribe')
            db.close()

if __name__=='__main__': unittest.main()
