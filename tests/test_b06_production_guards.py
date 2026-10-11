"""Bounded consumer drift checks with synthetic data; no Adobe calls."""
from copy import deepcopy
import importlib.util
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import Mock, patch

HERE = Path(__file__).resolve().parents[1]/'ae/experiments/r06-b06-judgement'
sys.path.insert(0, str(HERE))
from produce import validate_visual_operations
from delivery import validate_export_binding, sha
import produce
import premiere
spec = importlib.util.spec_from_file_location('b06_native_render', HERE/'render.py')
render = importlib.util.module_from_spec(spec)
spec.loader.exec_module(render)


class ProductionGuardTests(unittest.TestCase):
    def test_wrong_initial_ae_project_never_acquires_or_mutates(self):
        with TemporaryDirectory() as tmp:
            folder=Path(tmp);production={'project':str(folder/'intended.aep'),'revision_id':'synthetic'}
            observed={'process_id':123,'project_path':str(folder/'unrelated.aep'),'target_id':'comp:1','rendering':False}
            mutation=Mock()
            with patch.object(produce,'current',return_value=(production,{})), \
                    patch.object(produce,'JunkdogeClient'),patch.object(produce,'process_identity',return_value=(123,0)), \
                    patch.object(produce.OwnedAE,'reader',return_value=observed), \
                    patch.object(produce,'HostOwnership') as ownership:
                with self.assertRaisesRegex(ValueError,'intended AE production project'):
                    owner=produce.OwnedAE(folder)
                    owner.lease.mutate(lambda:observed,mutation)
                ownership.assert_not_called();mutation.assert_not_called()

    def test_wrong_initial_pr_project_never_acquires_or_mutates(self):
        with TemporaryDirectory() as tmp:
            folder=Path(tmp);token=folder/'local-data/v9.1/mcp-token.txt'
            token.parent.mkdir(parents=True);token.write_text('synthetic-token',encoding='utf-8')
            workspace={'project':str(folder/'intended.prproj')}
            observed={'process_id':123,'project_path':str(folder/'unrelated.prproj'),'target_id':'sequence:1'}
            mutation=Mock()
            with patch.object(premiere,'inputs',return_value=({}, {}, None, workspace)),patch.object(premiere,'ROOT',folder), \
                    patch.object(premiere,'PremiereMcpClient'),patch.object(premiere,'process_identity',return_value=(123,0)), \
                    patch.object(premiere.OwnedPR,'reader',return_value=observed), \
                    patch.object(premiere,'HostOwnership') as ownership:
                with self.assertRaisesRegex(ValueError,'intended PR workspace project'):
                    owner=premiere.OwnedPR(folder)
                    owner.lease.mutate(lambda:observed,mutation)
                ownership.assert_not_called();mutation.assert_not_called()

    def test_same_length_variant_cannot_reuse_other_native_export_binding(self):
        name='NEW_CONTEXT_FULL'
        production={'production_sha':'current'}
        plan={'av_plan_sha':'plan','variants':{name:{'frames':1516,'source_frames':[6374,7890]}}}
        workspace={'sequences':{name:{'id':'full-sequence'}}}
        audit={'status':'PASS_NATIVE_TIMELINE','production_sha':'current','av_plan_sha':'plan',
            'sequence':{'id':'full-sequence','name':name}}
        receipt={'production_sha':'current','av_plan_sha':'plan','sequence_id':'full-sequence',
            **plan['variants'][name],'native_audit_sha':sha(audit)}
        validate_export_binding(name,receipt,audit,production,plan,workspace)
        for key,value in [('av_plan_sha','other-plan'),('sequence_id','visual-sequence')]:
            with self.subTest(key=key),self.assertRaises(ValueError):
                validate_export_binding(name,{**receipt,key:value},audit,production,plan,workspace)
        for key,value in [('id','visual-sequence'),('name','NEW_CONTEXT_VISUAL')]:
            foreign=deepcopy(audit);foreign['sequence'][key]=value
            with self.subTest(key=key),self.assertRaises(ValueError):
                validate_export_binding(name,{**receipt,'native_audit_sha':sha(foreign)},foreign,production,plan,workspace)

    def test_context_may_remain_but_may_not_become_reviewed_emphasis(self):
        review = {'decisions':[{'operation_id':'phrase', 'selection':{'start':5,'end':10},
            'execution':{'primitives':['focus_in_context','move_as_group','compare_bound_relation']}}]}
        visual = {'groups':[{'operation_id':'phrase','lines':[
            {'range':[0,5],'emphasize':False}, {'range':[5,10],'emphasize':True}]}]}
        validate_visual_operations(visual,review)
        drift = deepcopy(visual); drift['groups'][0]['lines'][0]['emphasize']=True
        with self.assertRaises(ValueError): validate_visual_operations(drift,review)
        review['decisions'][0]['execution']['primitives'].remove('move_as_group')
        with self.assertRaises(ValueError): validate_visual_operations(visual,review)

    def test_self_consistent_foreign_receipt_cannot_bind_current_native_composition(self):
        production={'production_sha':'current-production','spec_sha':'current-spec','project':'current.aep'}
        composition={'comp_id':42,'source_frames':[120,240],'frames':120}
        identity={'spec_sha':'current-spec','project':'current.aep','compositions':{'NEW_CONTEXT_FULL':composition}}
        audit={'status':'PASS','spec_sha':'current-spec','compositions':6,'errors':[]}
        receipt={**production,'native_project':production['project'],'composition':'NEW_CONTEXT_FULL',
            **composition,'duration':5.0,'canvas':[3840,2160,24]}
        render.validate_render_binding('NEW_CONTEXT_FULL',receipt,production,identity,audit)
        for field,value in [('production_sha','other'),('spec_sha','other'),('composition','OLD_CONTEXT_FULL'),
                            ('comp_id',43),('source_frames',[240,360]),('frames',121),('canvas',[1920,1080,24])]:
            with self.subTest(field=field), self.assertRaises(ValueError):
                render.validate_render_binding('NEW_CONTEXT_FULL',{**receipt,field:value},production,identity,audit)
        with self.assertRaises(ValueError):
            render.validate_render_binding('NEW_CONTEXT_FULL',receipt,production,identity,{**audit,'status':'HOLD'})


if __name__ == '__main__': unittest.main()
