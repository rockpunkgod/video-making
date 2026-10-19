"""Exact footer repair reuses only proved unaffected complete encoded parts."""
from pathlib import Path
import json
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from ae_production import native_parts_reuse as reuse
from ae_production.authored_native import validate_material_identity_scope
from scripts.voice_delivery import sha256
from tests.test_native_parts_reuse import NativePartsReuseTests
from video_contracts import read,write


class NativeMaterialScopeReuse(unittest.TestCase):
    make_revision=NativePartsReuseTests.make_revision
    make_part=NativePartsReuseTests.make_part
    alter_child_plan=NativePartsReuseTests.alter_child_plan
    change_snapshot=NativePartsReuseTests.change_snapshot

    def setUp(self):
        temporary=TemporaryDirectory();self.addCleanup(temporary.cleanup)
        self.root=Path(temporary.name);self.parent=self.root/'parent';self.child=self.root/'child'
        template=(Path(__file__).parent/'fixtures/authored-episode-hook-r06.jsx').read_bytes()
        for folder,offset,data in [(self.parent,1,template),(self.child,7,template.replace(reuse.MATERIAL_OLD,reuse.MATERIAL_NEW))]:
            self.make_revision(folder,data,offset)
            plan=read(folder/'AV_PLAN.json');plan['audience_hook']={'end':1};write(folder/'AV_PLAN.json',plan)
            native=read(folder/'native-identity.json');native['plan_sha256']=sha256(folder/'AV_PLAN.json');write(folder/'native-identity.json',native)
            audit=read(folder/'native-audit.json');audit['layers'][1]['future_color_fixed']=False
            audit['layers'][2]['outPoint']=5
            audit['layers'].append({'id':offset+99,'name':'MATERIAL_IDENTITY','text':'Synthetic identity',
                'font':'ArialMT','parent':None,'threeD':False,'inPoint':1,'outPoint':3 if folder==self.parent else 2})
            write(folder/'native-audit.json',audit)
            if folder==self.child:
                write(folder/'MATERIAL_IDENTITY_NATIVE_READBACK.json',{'rows':[
                    {'comp_id':i,'inPoint':1,'outPoint':2} for i in (offset,offset+1)]})
        probe=patch.object(reuse,'_probe_master',return_value={'synthetic':'only ffprobe mocked'})
        probe.start();self.addCleanup(probe.stop)
        for i in range(5):self.make_part(i,i*24,(i+1)*24)

    def test_partial_parent_prefix_and_guarded_whole_parts(self):
        result=reuse.reuse_unchanged_parts(self.parent,self.child)
        self.assertEqual(result['operation'],reuse.MATERIAL_OPERATION)
        self.assertEqual([(r['start'],r['end']) for r in result['reused_parts']],[(0,24),(96,120)])
        for path in (self.child/'native-master-parts').glob('*.json'):
            row=read(path);self.assertFalse(row['new_native_render'])
            self.assertEqual(reuse.validate_reused_part(self.child,row,row['path'])['status'],'VERIFIED_PARENT_NATIVE_BYTES')

    def test_unknown_template_audio_or_native_changes_cannot_reuse(self):
        audit=read(self.child/'native-audit.json');audit['layers'][0]['text']='Changed source'
        write(self.child/'native-audit.json',audit)
        with self.assertRaisesRegex(ValueError,'Unaffected native'):reuse.reuse_unchanged_parts(self.parent,self.child)
        audit['layers'][0]['text']='source';write(self.child/'native-audit.json',audit)
        self.alter_child_plan(lambda p:p['segments'][0].update(voice_start=.2))
        with self.assertRaisesRegex(ValueError,'semantics'):reuse.reuse_unchanged_parts(self.parent,self.child)

    def test_bad_footer_range_and_extra_template_patch_are_rejected(self):
        audit=read(self.child/'native-audit.json');audit['layers'][-1]['outPoint']=2.5
        write(self.child/'native-audit.json',audit)
        with self.assertRaisesRegex(ValueError,'unproved lifetime'):reuse.reuse_unchanged_parts(self.parent,self.child)
        audit['layers'][-1]['outPoint']=2;write(self.child/'native-audit.json',audit)
        template=(self.child/'native-source/authored-episode.jsx').read_bytes()
        self.change_snapshot('template',template+b'\n// unrelated patch\n')
        with self.assertRaises(ValueError):reuse.reuse_unchanged_parts(self.parent,self.child)

    def test_missing_parent_prefix_receipt_fails_closed(self):
        for suffix in ('.json','.mp4'):(self.parent/'native-master-parts'/('part-0001'+suffix)).unlink()
        with self.assertRaisesRegex(ValueError,'gap-free'):reuse.reuse_unchanged_parts(self.parent,self.child)

    def test_native_scope_rejects_shifted_end_or_missing_comp(self):
        plan={'audience_hook':{'end':1},'scenes':[{'end':2}]}
        rows=[{'comp_id':i,'inPoint':1,'outPoint':2} for i in (1,2)]
        self.assertEqual(validate_material_identity_scope(plan,rows,[1,2])['status'],'PASS_EXACT_OPENING_SCOPE')
        rows[0]['outPoint']=3
        with self.assertRaisesRegex(ValueError,'overlaps source reading'):validate_material_identity_scope(plan,rows,[1,2])
        with self.assertRaisesRegex(ValueError,'every native'):validate_material_identity_scope(plan,rows[:1],[1,2])
        rows[0]['outPoint']=float('nan')
        with self.assertRaisesRegex(ValueError,'overlaps source reading'):validate_material_identity_scope(plan,rows,[1,2])

    def test_nonfinite_native_scope_and_missing_child_master_readback_rejected(self):
        audit=read(self.child/'native-audit.json');audit['layers'][-1]['outPoint']=float('nan')
        # Deliberately corrupt external input; the production writer rejects NaN.
        (self.child/'native-audit.json').write_text(json.dumps(audit),encoding='utf-8')
        with self.assertRaisesRegex(ValueError,'unproved lifetime'):reuse.reuse_unchanged_parts(self.parent,self.child)
        audit['layers'][-1]['outPoint']=2;write(self.child/'native-audit.json',audit)
        path=self.child/'MATERIAL_IDENTITY_NATIVE_READBACK.json';record=read(path);record['rows'].pop();write(path,record)
        with self.assertRaisesRegex(ValueError,'every native'):reuse.reuse_unchanged_parts(self.parent,self.child)

    def test_only_known_camera_key_ui_values_can_be_normalized(self):
        for folder in (self.parent,self.child):
            audit=read(folder/'native-audit.json')
            audit['layers'].append({'id':1000,'name':'READING_CAMERA','parent':None,
                'position':[[0,[0,0,0]],[10,[1,1,1]]],
                'position_value':[1,1,1] if folder==self.parent else [0,0,0]})
            write(folder/'native-audit.json',audit)
        self.assertEqual(reuse.reuse_unchanged_parts(self.parent,self.child)['operation'],reuse.MATERIAL_OPERATION)
        audit=read(self.child/'native-audit.json');audit['layers'][-1]['position_value']=[99,0,0]
        write(self.child/'native-audit.json',audit)
        with self.assertRaisesRegex(ValueError,'actual proved animation key'):
            reuse.reuse_unchanged_parts(self.parent,self.child)
