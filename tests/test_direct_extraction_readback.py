"""Counterfactuals for native keyword selectors and complete selected inventory."""
from copy import deepcopy
import json
import shutil
import subprocess
import unittest

from ae_production.direct_extraction import direct_extraction_readback, validate_direct_extraction
from tests import test_direct_extraction as fixtures


class DirectExtractionReadback(unittest.TestCase):
    def fixture(self, two_blocks=False):
        p,n,rows=fixtures.DirectExtractionTests().fixture()
        if two_blocks:
            p['excerpts']['e']['block_ids'].append('b2')
            p['worlds']['w']['blocks'].append({'id':'b2','text':'Other original.','start':5,'end':20})
            p['scenes'][0]['source_refs'][0]['end']=20
            n['audit']['sources'].append({'id':'b2','text':'Other original.','layer_id':14,'position':[2,54,100]})
            n['audit']['extractions'][0]['selected_block_ids'].append('b2')
            n['audit']['direct_extractions'][0]['clone_ids'].append(15)
            for row in rows:
                b=deepcopy(row['blocks'][0]);extra=100*(row['comp_id']-1)
                b.update(block_id='b2',source_name='b2',source_id=14+extra,
                    source_text='Other original.',source_position=[2,54,100],
                    clone_name='EXTRACT_s_b2',clone_id=15+extra,clone_text='Other original.',
                    clone_position=[0,50,0])
                row['blocks'].append(b);row['clone_names'].append('EXTRACT_s_b2')
        return p,n,rows

    def test_master_uses_own_layer_ids_and_proxy_build_inventory_stays_bound(self):
        p,n,rows=self.fixture(True)
        self.assertNotEqual(rows[0]['blocks'][0]['clone_id'],rows[1]['blocks'][0]['clone_id'])
        self.assertEqual(validate_direct_extraction(p,n,rows)['status'],'PASS')
        rows[0]['blocks'][0]['source_id']=111
        with self.assertRaises(ValueError):validate_direct_extraction(p,n,rows)

    def test_each_selected_block_handoff_is_checked_without_a_keyword(self):
        for field,value in [('source_opacity',100),('clone_opacity',0),('clone_enabled',False),
                            ('clone_guide',True),('clone_parent',999),('clone_out',6.5),
                            ('clone_position',[0,0,0]),('clone_text','Different original.')]:
            with self.subTest(field=field):
                p,n,rows=self.fixture(True)
                # The legacy scalar still says PASS, and this block has no hit.
                rows[0]['blocks'][1][field]=value
                with self.assertRaises(ValueError):validate_direct_extraction(p,n,rows)

    def test_incomplete_extra_duplicate_and_wrong_clone_inventory_are_rejected(self):
        for kind in ('missing','extra','duplicate','wrong','identity'):
            with self.subTest(kind=kind):
                p,n,rows=self.fixture(True)
                if kind=='missing':rows[0]['blocks'].pop()
                elif kind=='extra':rows[0]['clone_names'].append('EXTRACT_s_unselected')
                elif kind=='duplicate':rows[0]['blocks'].append(deepcopy(rows[0]['blocks'][0]))
                elif kind=='wrong':rows[0]['blocks'][1]['block_id']='another'
                else:rows[0]['blocks'][1]['clone_id']=rows[0]['blocks'][0]['clone_id']
                with self.assertRaises(ValueError):validate_direct_extraction(p,n,rows)

    def test_both_keyword_selector_ranges_and_colors_are_actual_requirements(self):
        changes=[('start',1),('end',3),('clone_start',1),('clone_end',3),
                 ('source_units',1),('clone_units',1),('source_smoothness',100),
                 ('source_fill',[.09,.13,.16]),('clone_fill',[.09,.13,.16]),
                 ('clone_fill',[.69,.27]),('clone_fill',[float('nan'),.27,.06]),
                 ('source_opacity',100),('clone_opacity',0),('clone_id',999)]
        for field,value in changes:
            with self.subTest(field=field,value=value):
                p,n,rows=self.fixture()
                rows[1]['hits'][0][field]=value
                with self.assertRaises(ValueError):validate_direct_extraction(p,n,rows)

    def test_keyword_ramp_errors_and_disappearance_cannot_be_hidden_by_a_peak(self):
        for field,value in [('source_samples',[100,100,100,100]),
                            ('clone_samples',[0,50,100,0]),
                            ('source_samples',[0,0,100,100]),
                            ('clone_expression_error','Invalid expression'),
                            ('source_fill_error','Invalid expression')]:
            with self.subTest(field=field):
                p,n,rows=self.fixture();rows[0]['hits'][0][field]=value
                with self.assertRaises(ValueError):validate_direct_extraction(p,n,rows)

    def test_wrong_words_cannot_pass_by_changing_both_readback_copies(self):
        p,n,rows=self.fixture()
        b=rows[0]['blocks'][0];h=rows[0]['hits'][0]
        b['source_text']=b['clone_text']='fake'
        h['source_text']=h['clone_text']=h['phrase']='fake'
        with self.assertRaises(ValueError):validate_direct_extraction(p,n,rows)

    def test_manifest_source_range_and_group_binding_are_not_self_authenticating(self):
        for field in ('source','hits','clock','origin','clones'):
            with self.subTest(field=field):
                p,n,rows=self.fixture();a=n['audit']
                if field=='source':a['sources'][0]['text']='different'
                elif field=='hits':a['direct_extractions'][0]['hits'][0]['source_block_id']='other'
                elif field=='clock':a['direct_extractions'][0]['reading_end']+=.25
                elif field=='origin':
                    a['extractions'][0]['origin']=[0,0,0]
                    rows[0]['position']=rows[0]['expected_origin']=[0,0,0]
                else:a['direct_extractions'][0]['clone_ids']=[999]
                with self.assertRaises(ValueError):validate_direct_extraction(p,n,rows)

    def test_finite_times_positions_and_distinct_compositions_required(self):
        for kind in ('time','position','opacity','comp'):
            with self.subTest(kind=kind):
                p,n,rows=self.fixture()
                if kind=='time':rows[0]['in_point']=float('nan')
                elif kind=='position':rows[0]['position']=[float('nan'),4,100]
                elif kind=='opacity':rows[0]['blocks'][0]['clone_opacity']=float('inf')
                else:n['master_comp_id']=n['comp_id']
                with self.assertRaises(ValueError):validate_direct_extraction(p,n,rows)

    def test_no_policy_keeps_historical_native_path_inert(self):
        class NoHost:
            def js(self,code):raise AssertionError('Historical film must not call a new native audit')
        self.assertIsNone(direct_extraction_readback(NoHost(),{'scenes':[]},{}))

    @unittest.skipUnless(shutil.which('node'),'Node is only a synthetic reader harness, never Adobe')
    def test_generated_reader_observes_every_block_and_both_selector_properties(self):
        p,n,expected=self.fixture(True)
        class Capture:
            code=None
            def js(self,code):self.code=code;return deepcopy(expected)
        host=Capture();direct_extraction_readback(host,p,n)
        # A small mocked native object graph runs the actual generated reader.
        # It checks property paths/loops; it is not an ExtendScript engine test.
        code=r'''
const model=MODEL, calls=[];
function property(value){return {value,expressionError:'',valueAtTime(){return value;}};}
function layer(c,r,isSource){
 const b=r,hit=model[c].hits.find(h=>h.source_block_id===b.block_id),prefix=isSource?'source':'clone';
 const sel={property(k){if(k==='ADBE Text Index Start')return property(hit[prefix==='source'?'start':'clone_start']);if(k==='ADBE Text Index End')return property(hit[prefix==='source'?'end':'clone_end']);if(k==='ADBE Text Range Advanced')return {property(k){if(k==='ADBE Text Range Units')return property(2);if(k==='ADBE Text Selector Smoothness')return property(0);if(k==='ADBE Text Selector Max Amount')return {expressionError:'',valueAtTime(t){return t===2.75?0:t===2.875?50:100;}};throw Error(k);}};throw Error(k);}};
 const an={property(k){if(k==='ADBE Text Selectors')return {property(){return sel;}};if(k==='ADBE Text Animator Properties')return {property(k){if(k==='ADBE Text Fill Color')return property([.69,.27,.06]);throw Error(k);}};throw Error(k);}};
 return {name:b[prefix+'_name'],id:b[prefix+'_id'],enabled:true,guideLayer:false,threeDLayer:true,inPoint:3,outPoint:7,parent:{id:model[c].group_id},property(k){calls.push([this.name,k]);if(k==='Source Text')return {valueAtTime(){return {text:b[prefix+'_text']};}};if(k==='ADBE Text Properties')return {property(){return {property(){if(!hit)throw Error('No keyword animator on this block');return an;}};}};if(k==='ADBE Transform Group')return {property(k){if(k==='ADBE Opacity')return property(isSource?0:100);if(k==='ADBE Position')return property(b[prefix+'_position']);throw Error(k);}};throw Error(k);}};
}
const comps={};for(let ci=0;ci<model.length;ci++){
 const r=model[ci],layers=[];for(const b of r.blocks){layers.push(layer(ci,b,true),layer(ci,b,false));}
 layers.push({name:'SOURCE_LIFT_s',id:r.group_id,inPoint:3,outPoint:7,enabled:true,guideLayer:false,threeDLayer:true,property(){return {property(){return property([2,4,100]);}};}});
 comps[r.comp_id]={id:r.comp_id,numLayers:layers.length,layer(i){return layers[i-1];}};
}
const app={project:{itemByID(id){return comps[id];}}};
const result=(function(){READER})();process.stdout.write(JSON.stringify({result,calls}));
'''.replace('MODEL',json.dumps(expected)).replace('READER',host.code)
        result=json.loads(subprocess.check_output(['node','-e',code],text=True,encoding='utf-8'))
        self.assertEqual(validate_direct_extraction(p,n,result['result'])['status'],'PASS')
        self.assertTrue(any(name=='EXTRACT_s_b2' for name,prop in result['calls']))


if __name__=='__main__':unittest.main()
