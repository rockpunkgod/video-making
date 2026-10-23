"""Source structure contracts; synthetic geometry is not native visual approval."""
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import unittest
from copy import deepcopy

import test_first_person_challenges as challenge_fixture
from scripts.voice_delivery import sha256
from video_contracts import write
from ae_production.challenge_original import _structured_regions


class ChallengeSourceLayoutTests(unittest.TestCase):
    def setUp(self):
        self.fixture=challenge_fixture.FirstPersonChallenges();self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.a=self.fixture.a;self.path=Path(self.fixture.temp.name)/'layout.json'
        self.doc=self.path.with_suffix('.docx');self.doc.write_bytes(b'SYNTHETIC SOURCE FIXTURE')
        self.a['input_files'][str(self.doc)]=sha256(self.doc)
        self.layout={'schema':'challenge-source-layout/v1','worlds':{}}
        for world,b in self.fixture.b.items():
            text=b['source_snapshot']['passage']
            self.layout['worlds'][world]={'source_document':{'path':str(self.doc),'sha256':sha256(self.doc)},
                'passage_sha256':hashlib.sha256(text.encode()).hexdigest(),
                'blocks':[{'kind':'heading','start':0,'end':11,'quote':'First line.','alignment':'center'},
                          {'kind':'paragraph','start':12,'end':24,'quote':'Second line.'}]}
        self.bind()

    def bind(self):
        write(self.path,self.layout)
        self.a['input_files'][str(self.path)]=sha256(self.path)
        self.a['audience_challenges']['source_layout']={'path':str(self.path),'sha256':sha256(self.path)}

    def test_exact_source_structure_survives_existing_compiler(self):
        result=self.fixture.compile()
        for row in result['rows']:
            self.assertEqual(row['source_layout'],self.layout['worlds'][row['world']])
            self.assertEqual(row['source_layout_binding']['sha256'],sha256(self.path))

    def test_missing_changed_and_reordered_source_are_rejected(self):
        original=deepcopy(self.layout)
        for change in ('omit','reverse','quote','sha'):
            self.layout=deepcopy(original);w=self.layout['worlds']['first']
            if change=='omit':w['blocks'].pop()
            if change=='reverse':w['blocks'].reverse()
            if change=='quote':w['blocks'][0]['quote']='Invented heading'
            if change=='sha':w['passage_sha256']='0'*64
            self.bind()
            with self.assertRaises(ValueError):self.fixture.compile()

    def test_rectangular_table_preserves_empty_cell_and_rejects_missing_width(self):
        w=self.layout['worlds']['first'];a,b=w['blocks']
        w['blocks']=[{'kind':'table','column_widths_twips':[100,100],
                     'rows':[[{'start':None,'end':None,'quote':''},a],[b,{'start':None,'end':None,'quote':''}]]}]
        self.bind();self.fixture.compile()
        w['blocks'][0]['column_widths_twips']=[100];self.bind()
        with self.assertRaises(ValueError):self.fixture.compile()

    def test_native_readback_rejects_flattened_paragraph_and_wrong_table_column(self):
        layout={'blocks':[{'kind':'heading','start':0,'end':1},
            {'kind':'table','column_widths_twips':[100,100],
             'rows':[[{'start':2,'end':3},{'start':4,'end':5}]]}]}
        challenge={'source_layout':layout,'source_layout_binding':{'sha256':'synthetic'}}
        regions=[{'start':0,'end':1,'kind':'heading','row':None,'column':None,'left':0,'width':760,'top':17,'bottom':21},
                 {'start':2,'end':3,'kind':'table','row':0,'column':0,'left':4,'width':372,'top':47.6,'bottom':51.6},
                 {'start':4,'end':5,'kind':'table','row':0,'column':1,'left':384,'width':372,'top':47.6,'bottom':51.6}]
        for i,region in enumerate(regions):region.update(block_index=0 if i==0 else 1,alignment=None)
        built={'source_layout':{'binding':challenge['source_layout_binding'],'regions':regions}}
        chunks=[{'start':0,'end':1,'baseline':[40,149,0],'width':30},
                {'start':2,'end':3,'baseline':[44,179.6,0],'width':30},
                {'start':4,'end':5,'baseline':[424,179.6,0],'width':30}]
        _structured_regions(challenge,built,chunks,0)
        bad=deepcopy(chunks);bad[2]['baseline'][0]=80
        with self.assertRaises(ValueError):_structured_regions(challenge,built,bad,0)
        layout['blocks'][0]['alignment']='center';regions[0]['alignment']='center'
        with self.assertRaisesRegex(ValueError,'alignment'):_structured_regions(challenge,built,chunks,0)
        chunks[0]['baseline'][0]=405
        _structured_regions(challenge,built,chunks,0)

    def test_separate_tables_with_empty_cells_are_not_the_same_row(self):
        empty={'start':None,'end':None,'quote':''};a={'start':0,'end':1};b={'start':2,'end':3}
        layout={'blocks':[{'kind':'table','column_widths_twips':[100,100],'rows':[[a,empty]]},
                          {'kind':'table','column_widths_twips':[100,100],'rows':[[empty,b]]}]}
        challenge={'source_layout':layout,'source_layout_binding':{'sha256':'synthetic'}}
        regions=[{'start':0,'end':1,'kind':'table','block_index':0,'row':0,'column':0,'alignment':None,'left':4,'width':372,'top':17,'bottom':21},
                 {'start':2,'end':3,'kind':'table','block_index':1,'row':0,'column':1,'alignment':None,'left':384,'width':372,'top':45.56,'bottom':49.56}]
        chunks=[{'start':0,'end':1,'baseline':[44,149,0],'width':30},
                {'start':2,'end':3,'baseline':[424,177.56,0],'width':30}]
        built={'source_layout':{'binding':challenge['source_layout_binding'],'regions':regions}}
        _structured_regions(challenge,built,chunks,0)
        bad=deepcopy(chunks);bad[1]['baseline'][1]=149
        with self.assertRaises(ValueError):_structured_regions(challenge,built,bad,0)

    @unittest.skipUnless(shutil.which('node'),'Node unavailable for pure native-layout math test')
    def test_native_layout_keeps_paragraphs_and_table_cells_and_rejects_overflow(self):
        rig=Path(__file__).resolve().parents[1]/'ae/rigs/first-person-challenge.jsx'
        script=rig.read_text('utf-8')+r'''
var groups=[{id:'a',start:0,end:1,width:30,gap:4},{id:'b',start:2,end:3,width:40,gap:4},{id:'c',start:4,end:5,width:30,gap:4}];
var layout={blocks:[{kind:'heading',start:0,end:1,alignment:'center'},
 {kind:'table',column_widths_twips:[100,200],rows:[[{start:2,end:3},{start:4,end:5}]]}]};
var r=cmChallengeStructuredLayout(groups,layout,300,17,20.4);
if(r.positions.a.x!==135||r.positions.b.y!==r.positions.c.y||r.positions.c.x<=r.positions.b.x||r.positions.a.y>=r.positions.b.y)throw Error('source structure lost');
if(Math.abs(r.positions.b.y-r.positions.a.y-20.4)>1e-8)throw Error('invented paragraph gap');
var paragraphs={blocks:[{kind:'paragraph',start:0,end:1,font_size_half_points:20,spacing_raw:{after:'100'}},
 {kind:'paragraph',start:2,end:3,font_size_half_points:20,spacing_raw:{before:'200'}},
 {kind:'paragraph',start:4,end:5,spacing_raw:{beforeLines:'50'}}]};
var spaced=cmChallengeStructuredLayout(groups,paragraphs,300,17,20.4);
if(Math.abs(spaced.positions.b.y-spaced.positions.a.y-37.4)>1e-8||Math.abs(spaced.positions.c.y-spaced.positions.b.y-30.6)>1e-8)throw Error('source paragraph spacing lost');
paragraphs.blocks[2].spacing_raw={beforeAutospacing:'1'};var automaticRejected=false;
try{cmChallengeStructuredLayout(groups,paragraphs,300,17,20.4);}catch(e){automaticRejected=true;}
if(!automaticRejected)throw Error('unresolved source spacing guessed');
groups[1].width=400;var rejected=false;try{cmChallengeStructuredLayout(groups,layout,300,17,20.4);}catch(e){rejected=true;}if(!rejected)throw Error('cell overflow accepted');
console.log(JSON.stringify(r));
'''
        result=subprocess.run(['node','-e',script],capture_output=True,text=True)
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertEqual(len(json.loads(result.stdout)['regions']),3)
