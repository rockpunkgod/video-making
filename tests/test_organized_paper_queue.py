import json
from pathlib import Path
import tempfile
import unittest

from scripts.organized_paper_queue import assign, connect, initialize, paper_label, record_report, snapshot

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

if __name__=='__main__': unittest.main()
