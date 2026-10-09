"""Synthetic contract counterexamples, not Adobe execution or semantic review."""
from copy import deepcopy
import unittest
import math
import importlib.util
import sys
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import Mock,patch
from video_contracts import sha,write
from tests import test_method_relay_dual_pass as base
from tests.test_reviewed_passage import fixture as passage_fixture
from video_contracts.passage import material,export_bundle,status_manifest
relay=base.relay
with patch.dict(sys.modules,{'run':relay}):
    spec=importlib.util.spec_from_file_location('fulltext_acquisition',base.HERE/'fulltext.py')
    fulltext=importlib.util.module_from_spec(spec);spec.loader.exec_module(fulltext)


class SourceAcquisitionTests(unittest.TestCase):
    def setUp(self):
        self.helper=base.MethodRelayTests();self.helper.setUp()
        self.r=self.helper.request('full')
        self.r['source_acquisition']=relay.acquisition_plan(self.r)
        self.r['spec_sha']=sha({k:v for k,v in self.r.items() if k not in ('spec_sha','project')})

    def native(self):
        n=self.helper.native_fixture(self.r)
        def context(font=40,opacity=100,depth=False):
            return [{'name':name,'text':text,'font_size':font,'opacity':opacity,'z':z if depth else 0,
                     'key_texts':[text]*4,'native_layer_id':i+100}
                    for i,(name,text,z) in enumerate(zip(('CONTEXT_BEFORE','CONTEXT_AFTER'),self.r['fixture']['context'],(130,180)))]
        def marks(source=0,scope=0,guide=0,retired=False):
            return {'source_mark':source,'sentence_scope':scope,'reader_guide':guide,
                    'contexts':context(32,15,True) if retired else context()}
        center=self.r['locate_geometry']['source_x']+self.r['locate_geometry']['source_width']/2
        end=self.r['layout'][-1]['x']+self.r['layout'][-1]['width']
        n['source_acquisition']={'version':'0.2.0','passes':[
            {'kind':p['kind'],'pre_hit':marks(guide=42),'hit':marks(source=24),
             'confirm':marks(source=24,scope=45,retired=True),'peel':marks(retired=True),
             'scope_start':[[center,472],[center,472]],'scope_end':[[190,472],[end,472]]}
            for p in self.r['source_acquisition']['passes']],
            'rewind_restore':context(),'rewind_marks':marks(),
            'focus_restore':[{'name':name,'initial':[960,540,0],'restored':[960,540,0]}
                             for name in ('FOCUS_TARGET','GUIDED_CAMERA')]}
        return n

    def test_old_request_remains_compatible(self):
        old=self.helper.request('full');relay.validate_acquisition(old)
        relay.validate_native(old,self.helper.native_fixture(old))

    def test_literal_span_and_stage_order_cannot_be_changed(self):
        for mutate in (lambda r:r['source_acquisition']['cue_refs']['stem'].update(text='invented keyword'),
                       lambda r:r['source_acquisition']['passes'][0].update(hit=[2.5,2.6]),
                       lambda r:r['source_acquisition'].update(complete_fast_action=[2.65,12.5]),
                       lambda r:r['source_acquisition'].update(transcript_changed=True)):
            bad=deepcopy(self.r);mutate(bad)
            with self.subTest(mutation=mutate),self.assertRaises(ValueError):relay.validate_acquisition(bad)

    def test_plan_preserves_voice_duration_and_every_later_beat(self):
        old=self.helper.request('full')
        self.assertEqual(old['duration'],self.r['duration'])
        self.assertEqual(old['passes'],self.r['passes'])
        self.assertEqual(relay.voice_slots(old),relay.voice_slots(self.r))
        self.assertEqual(old['fixture'],self.r['fixture'])
        self.assertEqual(self.r['source_acquisition']['complete_fast_action'],[1.5,12.5])

    def test_current_native_states_pass(self):
        relay.validate_native(self.r,self.native())

    def test_preselected_context_and_early_result_are_rejected(self):
        for mutate in (lambda a:a['pre_hit'].update(source_mark=1),
                       lambda a:a['pre_hit'].update(sentence_scope=1),
                       lambda a:a['pre_hit']['contexts'][0].update(font_size=32),
                       lambda a:a['pre_hit']['contexts'][1].update(opacity=65),
                       lambda a:a['pre_hit']['contexts'][0].update(z=130)):
            bad=self.native();mutate(bad['source_acquisition']['passes'][0])
            with self.subTest(mutation=mutate),self.assertRaises(ValueError):relay.validate_native(self.r,bad)

    def test_word_hit_must_precede_sentence_confirmation(self):
        bad=self.native();bad['source_acquisition']['passes'][1]['hit']['sentence_scope']=45
        with self.assertRaises(ValueError):relay.validate_native(self.r,bad)

    def test_scope_expands_from_exact_hit_to_whole_original(self):
        for prop in ('scope_start','scope_end'):
            bad=self.native();bad['source_acquisition']['passes'][0][prop][0][0]+=12
            with self.subTest(prop=prop),self.assertRaises(ValueError):relay.validate_native(self.r,bad)

    def test_reader_guide_hands_off_and_cannot_compete_with_peel(self):
        for phase,prop in (('confirm','reader_guide'),('peel','reader_guide'),('peel','source_mark'),('peel','sentence_scope')):
            bad=self.native();bad['source_acquisition']['passes'][1][phase][prop]=42
            with self.subTest(phase=phase,prop=prop),self.assertRaises(ValueError):relay.validate_native(self.r,bad)

    def test_new_context_style_restores_before_guided(self):
        bad=self.native();bad['source_acquisition']['rewind_restore'][0]['font_size']=32
        with self.assertRaises(ValueError):relay.validate_native(self.r,bad)

    def test_focus_and_camera_restoration_cannot_be_omitted(self):
        for mutate in (lambda a:a.update(focus_restore=[]),
                       lambda a:a['focus_restore'][1].update(restored=[800,460,0]),
                       lambda a:a['rewind_marks'].update(source_mark=24)):
            bad=self.native();mutate(bad['source_acquisition'])
            with self.subTest(mutation=mutate),self.assertRaises(ValueError):relay.validate_native(self.r,bad)

    def test_context_cannot_be_rewritten_as_style(self):
        bad=self.native();bad['source_acquisition']['passes'][0]['confirm']['contexts'][0]['key_texts'][1]='new sentence'
        with self.assertRaises(ValueError):relay.validate_native(self.r,bad)

    def test_no_self_reported_pass_without_native_acquisition(self):
        bad=self.native();bad.pop('source_acquisition')
        with self.assertRaises(ValueError):relay.validate_native(self.r,bad)


class NativeGeometryTests(unittest.TestCase):
    def setUp(self):
        helper=SourceAcquisitionTests();helper.setUp();self.r=helper.r;self.n=helper.native()
        self.r['native_acquisition_geometry']=True
        self.r['spec_sha']=sha({k:v for k,v in self.r.items() if k not in ('spec_sha','project')})
        self.n['spec_sha']=self.r['spec_sha'];a=self.n['source_acquisition']
        handles={x['id']:x['native_layer_id'] for x in self.n['objects']}
        def transform(point):
            return {'name':'synthetic-initial-pose','position':point,'anchor':[0,0,0],
                    'scale':[100,100,100],'rotation':0,'x_rotation':0,'y_rotation':0}
        rows=[];boxes=[]
        for o in self.r['layout']:
            z=-1 if o['role']=='supplied_modifier' else 0
            rows.append({'name':o['id'],'layer_id':handles[o['id']],
                'rect':{'left':1,'top':-29,'width':o['width']-2,'height':36},'parents':[transform([o['x'],460,z])]})
            boxes.append({'name':o['id'],'layer_id':handles[o['id']],
                          'min':[o['x']+1,431,z],'max':[o['x']+o['width']-1,467,z]})
        # Deliberately simple, portable synthetic native metrics, not an AE receipt.
        hit={'min':[451,431,0],'max':[609,467,0],'center':[530,449,0]}
        sentence={'min':[191,431,-1],'max':[869,467,0],'center':[530,449,-.5]}
        marker={'name':'EVIDENCE_LOCATION_CUE','layer_id':200,'min':[447,427,1],'max':[613,471,1]}
        rows += [{'name':marker['name'],'layer_id':200,'rect':{'left':-83,'top':-22,'width':166,'height':44},
                  'parents':[transform([530,449,1])]},
                 {'name':'CONTEXT_BEFORE','layer_id':100,'rect':{'left':1,'top':-29,'width':600,'height':36},
                  'parents':[transform([190,365,0])]}]
        a.update(native_source_rects=rows,temporary_probes=[],geometry={'space':'native_toWorld','sample_time':0,
            'cue_refs':self.r['source_acquisition']['cue_refs'],'probe_retained':False,
            'keyword_layers':boxes[2:4],'sentence_layers':boxes,'keyword':hit,'sentence':sentence,'marker_after':marker,'projections':[]})
        for actual,plan,p in zip(a['passes'],self.r['source_acquisition']['passes'],self.r['passes']):
            def camera(time,point,look):
                return {'time':time,'position':point,'look':look,'focus':look,'focus_distance':math.dist(point,look),
                        'focus_error':'','dof':1,'zoom':1950,'aperture':40}
            depth=-2000 if p['kind']=='fast' else -1940
            actual['lock_camera']=camera(plan['hit'][1],[560,464,depth],hit['center'])
            actual['settled_camera']=camera(plan['settle'][1],[560,464,depth],hit['center'])
            actual['lift_camera']=camera(p['lift'][1],[820,410,-1960 if p['kind']=='fast' else -1880],[800,420,-140])
            times=[plan['enter'][0],plan['enter'][1],plan['browse'][1],plan['hit'][1]]
            actual['curves']=[[{'time':t,'in_speed':s,'out_speed':s,'in_influence':70 if i==3 else 35,
                'out_influence':25 if i==1 else 55} for i,(t,s) in enumerate(zip(times,[0,10,3,0]))] for _ in range(3)]
            actual.update(scope_start=[[530,476],[530,476]],scope_end=[[191,476],[869,476]])
            a['geometry']['projections'].append({'kind':p['kind'],'samples':[{'time':t,'source':
                {'min':[300,500,0],'max':[1500,540,0]}} for t in (plan['enter'][1],plan['hit'][1],plan['confirm'][1],p['lift'][1])]})

    def test_geometry_bound_native_states_pass(self):
        relay.validate_native(self.r,self.n)

    def test_independent_glyph_and_shape_binding_rejects_false_camera_geometry(self):
        for mutate in (lambda a:a['geometry']['keyword_layers'][0].update(layer_id=999),
                       lambda a:a['geometry']['keyword']['center'].__setitem__(0,700),
                       lambda a:a['geometry']['marker_after']['max'].__setitem__(0,900),
                       lambda a:a['native_source_rects'][2]['rect'].update(width=120),
                       lambda a:a.update(temporary_probes=[456])):
            bad=deepcopy(self.n);mutate(bad['source_acquisition'])
            with self.subTest(mutation=mutate),self.assertRaises(ValueError):relay.validate_native(self.r,bad)

    def test_focus_dof_and_existing_peel_camera_cannot_diverge(self):
        for mutate in (lambda p:p['lock_camera'].update(look=[800,460,0]),
                       lambda p:p['settled_camera'].update(dof=0),
                       lambda p:p['lift_camera'].update(position=[820,410,-1700]),
                       lambda p:p['lock_camera'].update(focus_distance=500)):
            bad=deepcopy(self.n);mutate(bad['source_acquisition']['passes'][0])
            with self.subTest(mutation=mutate),self.assertRaises(ValueError):relay.validate_native(self.r,bad)

    def test_native_projection_cannot_clip_source(self):
        bad=deepcopy(self.n);bad['source_acquisition']['geometry']['projections'][1]['samples'][1]['source']['max'][0]=2000
        with self.assertRaises(ValueError):relay.validate_native(self.r,bad)

    def test_one_uniform_ease_and_abrupt_browse_stop_are_rejected(self):
        for change in ({'out_speed':0},{'out_influence':32}):
            bad=deepcopy(self.n);bad['source_acquisition']['passes'][0]['curves'][0][1].update(change)
            with self.subTest(change=change),self.assertRaises(ValueError):relay.validate_native(self.r,bad)

    def test_p0_ranges_are_exact_frames_and_cover_both_unchanged_peels(self):
        for label,expected in (('FAST_ACQUISITION',[36,150]),('GUIDED_ACQUISITION',[384,625])):
            span=relay.render_span(self.r,label);self.assertEqual(span['frame_range'],expected)
            p=self.r['passes'][0 if label.startswith('FAST') else 1]
            self.assertGreaterEqual(span['start']+span['duration'],p['peel_b'][4]+.15)
        with self.assertRaises(ValueError):relay.render_span(self.r,'arbitrary-range')
        old=self.r.copy();old.pop('native_acquisition_geometry')
        with self.assertRaises(ValueError):relay.render_span(old,'GUIDED_ACQUISITION')

    def test_full_integration_requires_new_bound_human_review(self):
        with TemporaryDirectory() as tmp:
            out=Path(tmp)
            with self.assertRaises(FileNotFoundError):relay.require_acquisition_review(out,self.r,'DUAL')
            shas={}
            for label in relay.ACQUISITION_RANGES:
                movie=out/(label+'.mp4');movie.write_bytes(b'synthetic-test-only')
                shas[label]=relay.file_sha(movie)
                write(out/('render-receipt-'+label+'.json'),{'spec_sha':self.r['spec_sha'],
                      'output':str(movie),'output_sha':shas[label]})
            review={'spec_sha':self.r['spec_sha'],'reviewer_type':'human','status':'PASS',
                    'feedback':'synthetic unit test, never used for acceptance','p0_clip_shas':shas}
            for change in ({'reviewer_type':'agent'},{'spec_sha':'old-approved-picture'},
                           {'p0_clip_shas':{}},{'status':'PENDING'}):
                write(out/'acquisition-human-review.json',dict(review,**change))
                with self.subTest(change=change),self.assertRaises(ValueError):relay.require_acquisition_review(out,self.r,'DUAL')
            relay.require_acquisition_review(out,self.r,'GUIDED_ACQUISITION')


class FullPassageTests(unittest.TestCase):
    """Invented source and portable geometry, never real-exam or native acceptance."""
    def setUp(self):
        packet=passage_fixture()
        packet['passage']='\n'.join([
            'SYNTHETIC first paragraph starts here. '+('alpha beta gamma '*8),
            'SYNTHETIC second paragraph. '+('delta epsilon zeta '*8),
            'SYNTHETIC condition relies on the sample retaining its whole boundary.',
            'SYNTHETIC fourth paragraph is retained.',
            'SYNTHETIC fifth paragraph is retained.'])
        quote='SYNTHETIC condition relies on the sample retaining its whole boundary.'
        start=packet['passage'].index(quote)
        evidence=[{'field':'passage','start':start,'end':start+len(quote),'quote':quote}]
        for row in packet['review']['decisions']+packet['review']['segments']:row['evidence']=deepcopy(evidence)
        packet['review']['segments'][0]['kind']='action'
        packet['review']['material_sha']=sha(material(packet))
        self.bundle=export_bundle(packet,'synthetic-time');self.status=status_manifest(self.bundle,'synthetic-time')
        self.temp=TemporaryDirectory();self.addCleanup(self.temp.cleanup);root=Path(self.temp.name)
        write(root/'bundle.json',self.bundle);write(root/'status.json',self.status)
        with patch.object(relay,'file_sha',return_value='a'*64),patch('PIL.ImageFont.truetype',return_value=Mock(getlength=lambda text:len(text)*12)):
            self.r=fulltext.make_request(root/'first',root/'bundle.json',root/'status.json','synthetic-1','task','relies on')

    def reseal(self,r):
        r['spec_sha']=sha({k:v for k,v in r.items() if k not in ('spec_sha','project','bundle_path','status_path')})
        return r

    def native(self):
        r=self.r;rows=[];scale=r['render_scale'];physical=lambda values:[v*scale for v in values]
        for i,w in enumerate(r['words']):
            rows.append(dict(w,layer_id=i+10,source_sha=r['source']['passage_sha'],source_text_keys=0,threeD=True,
                             position=physical(w['position']),font_size=24,
                             rect={'left':0,'top':-20,'width':len(w['text'])*12,'height':24},anchor=[0,0,0],scale=[100*scale]*3,
                             parent=None,rotation=0,x_rotation=0,y_rotation=0))
        actual={w['id']:w for w in rows}
        def box(ids,lift=False):
            low=[math.inf]*3;high=[-math.inf]*3
            for id in ids:
                w=actual[id];p=physical(r['lift_positions'][id]) if lift else w['position'];rect=w['rect'];s=(32/24 if lift else 1)*scale
                for j,(v,size) in enumerate(((0,rect['width']),(-20,24),(0,0))):
                    low[j]=min(low[j],p[j]+v*s);high[j]=max(high[j],p[j]+(v+size)*s)
            return {'min':low,'max':high,'center':[(x+y)/2 for x,y in zip(low,high)]}
        g={k:box(ids,lift) for k,ids,lift in [('whole',list(actual),False),('hit',r['hit_ids'],False),
                                             ('scope',r['target_ids'],False),('lifted',r['target_ids'],True)]}
        g['line_boxes']=[box(line['word_ids']) for line in r['lines']];column=g['whole']['center'][0]
        style={k:(v if k in ('background_max_word_scale','reader_opacity') else
                  {a:b*scale for a,b in v.items()} if k=='aperture' else v*scale) for k,v in r['camera_style'].items()}
        bg_projection=style['zoom']/(1980*scale+style['background_z'])
        bg_word_scale=min(style['background_max_word_scale'],(style['background_bottom']-style['background_top'])/
                          ((g['whole']['max'][1]-g['whole']['min'][1])*bg_projection))
        origin=g['lifted']['center'][1]+120*scale/(1950/1840)+50*scale/bg_projection
        handles={w['id']:w['layer_id'] for w in rows};passes=[]
        for p in r['director']['passes']:
            samples=[]
            for i in r['scan_line_ids']:
                b=g['line_boxes'][i]
                reader=[b['min'][0]+10*scale,b['max'][1]+6*scale,scale];camera=[column+20*scale,b['center'][1]+250*scale,-1500*scale]
                look=[column,b['center'][1]+30*scale,0];focus=[reader[0]+40*scale,b['center'][1],0]
                forward=[a-c for a,c in zip(look,camera)];norm=math.sqrt(sum(v*v for v in forward))
                samples.append({'reader':reader,'reader_opacity':0,'camera':camera,'look':look,'focus':focus,'aperture':style['aperture']['scan'],
                                'focus_distance':sum((a-c)*v/norm for a,c,v in zip(focus,camera,forward))})
            poses=[]
            for w in rows:
                id=w['id'];initial=w['position'];selected=id in r['lift_positions']
                destination=physical(r['lift_positions'][id]) if selected else [column+(initial[0]-column)*bg_word_scale,
                    origin+(initial[1]-g['whole']['min'][1])*bg_word_scale,style['background_z']]
                poses.append({'id':id,'initial':initial,'restored':initial,'at_lift':destination,
                              'pre_hit_opacity':100,'lift_opacity':100 if selected else 28,
                              'restored_scale':[100*scale]*3,'lifted_scale':[(100*32/24 if selected else 100*bg_word_scale)*scale]*3})
            passes.append({'kind':p['kind'],'visited_lines':r['scan_line_ids'],'pre_hit_mark':0,'peak_hit_mark':85,
                           'hit_mark':0,'lift_handles':handles,'positions':poses,'scan_samples':samples,
                           'camera':{'dof':1,'aperture':style['aperture']['hit'],'zoom':style['zoom'],'focus_error':'','focus_distance':1500*scale},
                           'apertures':style['aperture'],
                           'lift_focus':{'actual_sentence_center':[900,500,-70],'focus':[900,500,-70],'error':''},
                           'mark_position':[g['hit']['center'][0],g['hit']['center'][1],scale],
                           'mark_size':[g['hit']['max'][0]-g['hit']['min'][0]+8*scale,g['hit']['max'][1]-g['hit']['min'][1]+8*scale],'mark_strokes':0})
            passes[-1]['mental_state']={phase:{'question_opacity':values,
                'option_opacity':{id:100 if phase=='initial' else 0 for id in r['source']['question']['options']}}
                for phase,values in [('initial',{'QUESTION_PREFIX':100,'QUESTION_KEYWORD':100,'QUESTION_SUFFIX':100}),
                                     ('scan',{'QUESTION_PREFIX':0,'QUESTION_KEYWORD':60,'QUESTION_SUFFIX':0}),
                                     ('before_lift',{'QUESTION_PREFIX':0,'QUESTION_KEYWORD':60,'QUESTION_SUFFIX':0}),
                                     ('lifted',{'QUESTION_PREFIX':0,'QUESTION_KEYWORD':0,'QUESTION_SUFFIX':0})]}
        return {'spec_sha':r['spec_sha'],'canvas':r['canvas'],'renderer':'ADBE Advanced 3d','draft3d':False,'resolution_factor':[1,1],
                'words':rows,'handles':handles,'initial_handles':handles,
                'passes':passes,'geometry':g,'temporary_probes':[],'annotation_layers':[],'visible_attention_cursor':False,
                'question_parts':[dict(p,source_text_keys=0,font_size=34,scale=[100*scale,100*scale,100],
                                       position=physical(p['position'])+[0]) for p in r['question_parts']],
                'question_handles':{p['id']:700+i for i,p in enumerate(r['question_parts'])},
                'initial_question_handles':{p['id']:700+i for i,p in enumerate(r['question_parts'])},
                'option_texts':{id:id+'. '+text for id,text in r['source']['question']['options'].items()},
                'viewport_guards':{name:{'vertices':[[0,g['top']*scale],[r['canvas'][0],g['top']*scale],[r['canvas'][0],g['bottom']*scale],[0,g['bottom']*scale]],
                    'feather':[0,g['feather']*scale],'mask_keys':0,'feather_keys':0,'mask_count':1,'mask_add':True,'inverted':False,
                    'mask_opacity':100,'layer_opacity':100,'enabled':True,'threeD':False,'parent':None,'rotation':0,
                    'position':[r['canvas'][0]/2,r['canvas'][1]/2,0],'anchor':[r['canvas'][0]/2,r['canvas'][1]/2,0],
                    'scale':[100,100,100],'size':r['canvas'][:2],
                    'color':[.973,.969,.949]} for name,g in r['viewport_guards'].items()},
                'new_method_certification':False,'public_render_ready':False}

    def test_complete_original_and_first_line_survive(self):
        fulltext.validate(self.r);fulltext.validate_native(self.r,self.native())
        self.assertEqual(self.r['scan_line_ids'][0],0)
        self.assertEqual(len(set(line['paragraph'] for line in self.r['lines'])),5)
        self.assertFalse(self.r['director']['synthetic_handoff'])
        self.assertIsNone(self.r['source']['answer'])
        self.assertFalse(self.r['source']['method_certification'])

    def test_omitted_paragraph_or_jump_to_hit_is_rejected(self):
        for mutation in (lambda r:r['words'].pop(),lambda r:r['scan_line_ids'].pop(0),
                         lambda r:r['target_ids'].pop(),lambda r:r['words'][0].update(text='rewritten')):
            bad=deepcopy(self.r);mutation(bad)
            with self.subTest(mutation=mutation),self.assertRaises(ValueError):fulltext.validate(self.reseal(bad))

    def test_withdrawn_or_missing_current_status_blocks_projection(self):
        for status in (None,status_manifest(self.bundle,'synthetic-later','WITHDRAWN')):
            with self.subTest(status=status),self.assertRaises(ValueError):
                fulltext.project(self.bundle,status,'synthetic-1','task','relies on')

    def test_native_bad_span_source_or_swapped_word_is_rejected(self):
        for change in ({'start':1},{'source_sha':'old'},{'source_text_keys':1},{'parent':99}):
            bad=self.native();bad['words'][0].update(change)
            with self.subTest(change=change),self.assertRaises(ValueError):fulltext.validate_native(self.r,bad)

    def test_real_line_geometry_and_offset_mark_cannot_be_faked(self):
        for mutation in (lambda n:n['geometry']['hit']['center'].__setitem__(0,9000),
                         lambda n:n['passes'][0].update(mark_position=[960,540,0]),
                         lambda n:n['passes'][1]['scan_samples'][0]['reader'].__setitem__(1,1000),
                         lambda n:n['passes'][0]['scan_samples'][0]['camera'].__setitem__(0,10)):
            bad=self.native();mutation(bad)
            with self.subTest(mutation=mutation),self.assertRaises(ValueError):fulltext.validate_native(self.r,bad)

    def test_same_original_lift_and_rewind_must_be_preserved(self):
        for phase,key,change in ((0,'at_lift',[0,0,0]),(1,'restored',[0,0,0]),(0,'pre_hit_opacity',28)):
            bad=self.native();bad['passes'][phase]['positions'][0][key]=change
            with self.subTest(key=key),self.assertRaises(ValueError):fulltext.validate_native(self.r,bad)

    def test_focus_must_follow_current_reading_row_before_acquire(self):
        for key,value in (('focus',[1,1,0]),('focus_distance',5),('aperture',40)):
            bad=self.native();bad['passes'][0]['scan_samples'][0][key]=value
            with self.subTest(key=key),self.assertRaises(ValueError):fulltext.validate_native(self.r,bad)
        bad=self.native();bad['passes'][0]['lift_focus']['focus']=[900,500,-140]
        with self.assertRaises(ValueError):fulltext.validate_native(self.r,bad)

    def test_underlines_or_visible_scan_cursor_cannot_replace_attention(self):
        for mutation in (lambda n:n['annotation_layers'].append('SCOPE_1'),lambda n:n.update(visible_attention_cursor=True),
                         lambda n:n['passes'][0].update(mark_strokes=1),lambda n:n['passes'][0].update(hit_mark=85)):
            bad=self.native();mutation(bad)
            with self.subTest(mutation=mutation),self.assertRaises(ValueError):fulltext.validate_native(self.r,bad)

    def test_only_original_cue_remains_in_working_memory(self):
        for mutation in (lambda n:n['passes'][0]['mental_state']['scan']['question_opacity'].update(QUESTION_PREFIX=100),
                         lambda n:n['passes'][1]['mental_state']['scan']['option_opacity'].update(A=100),
                         lambda n:n['question_parts'][1].update(text='new cognitive summary'),
                         lambda n:n['question_handles'].update(QUESTION_KEYWORD=999)):
            bad=self.native();mutation(bad)
            with self.subTest(mutation=mutation),self.assertRaises(ValueError):fulltext.validate_native(self.r,bad)

    def test_feathered_guard_cannot_reveal_text_again_at_frame_edge(self):
        for mutation in (lambda g:g['vertices'][2].__setitem__(1,1080),
                         lambda g:g.update(layer_opacity=50),lambda g:g.update(inverted=True),
                         lambda g:g.update(position=[960,600,0])):
            bad=self.native();mutation(bad['viewport_guards']['PAPER_FOOT_GUARD'])
            with self.subTest(mutation=mutation),self.assertRaises(ValueError):fulltext.validate_native(self.r,bad)

    def test_4k_requires_native_canvas_text_camera_and_full_resolution(self):
        self.assertEqual(self.r['canvas'][:2],[3840,2160])
        for mutation in (lambda n:n.update(canvas=[1920,1080,24,20]),lambda n:n.update(resolution_factor=[2,2]),
                         lambda n:n['words'][0].update(scale=[100,100,100]),lambda n:n['words'][0].update(font_size=12),
                         lambda n:n['passes'][0]['camera'].update(zoom=1950),lambda n:n['question_parts'][0].update(scale=[100,100,100])):
            bad=self.native();mutation(bad)
            with self.subTest(mutation=mutation),self.assertRaises(ValueError):fulltext.validate_native(self.r,bad)

    def test_native_chunks_bind_done_comp_and_exact_contiguous_spans(self):
        for first in (0,120,240,360):
            paths=[Path('FRAME_'+str(i).zfill(5)+'.tif') for i in range(first,first+120)]
            native={'done':True,'comp_id':42,'start':first/24,'duration':5}
            fulltext.validate_render_chunk(native,paths,first,120,42)
            for change in ({'done':False},{'comp_id':43},{'start':first/24+.1},{'duration':4.9}):
                bad=dict(native,**change)
                with self.subTest(first=first,change=change),self.assertRaises(ValueError):
                    fulltext.validate_render_chunk(bad,paths,first,120,42)

    def test_native_chunk_rejects_missing_gapped_or_foreign_frames(self):
        native={'done':True,'comp_id':42,'start':5,'duration':5}
        paths=[Path('FRAME_'+str(i).zfill(5)+'.tif') for i in range(120,240)]
        for bad in (paths[:-1],paths[:-1]+[Path('FRAME_00241.tif')],paths[:-1]+[Path('OTHER_00239.tif')]):
            with self.subTest(last=bad[-1]),self.assertRaises(ValueError):
                fulltext.validate_render_chunk(native,bad,120,120,42)

    def test_keyword_flash_begins_only_after_camera_settle(self):
        for p in self.r['director']['passes']:
            self.assertGreater(p['hit_flash'][0],p['hit_settle_end'])
            self.assertEqual(p['hit_flash'][1],p['hit'][1])
            self.assertLess(p['source_reveal_end'],p['enter_start'])

    def test_no_teaching_or_public_promotion(self):
        for key in ('new_method_certification','public_render_ready'):
            bad=self.native();bad[key]=True
            with self.subTest(key=key),self.assertRaises(ValueError):fulltext.validate_native(self.r,bad)

    def test_transparent_sentence_rejects_a_paper_background(self):
        bad=self.native();bad['passes'][0]['sentence_occlusion']={'enabled':True}
        with self.assertRaises(ValueError):fulltext.validate_native(self.r,bad)

    def test_source_glyphs_never_acquire_editorial_masks(self):
        bad=self.native();bad['background_cutouts']=[{'id':self.r['target_ids'][0],'count':1}]
        with self.assertRaises(ValueError):fulltext.validate_native(self.r,bad)

    def test_sentence_plane_requires_bound_unadorned_temporary_occlusion(self):
        o={'position':[100,200,40],'size':[516,56],'expected_center':[100,200,0],
           'expected_bounds_size':[500,40],'opacity_before':0,'opacity_mid':100,'opacity_after':0,
           'position_error':'','size_error':'','stroke':False,'effect_count':0,'threeD':True,
           'fill':[.973,.969,.949],'enabled':True}
        fulltext.validate_sentence_plane(dict(self.r,motion_profile={'sentence_occlusion':'unadorned_bound_paper_plane','plane_depth_offset':20}),[{'sentence_occlusion':o}])
        for key,value in [('position',[101,200,40]),('size',[600,56]),('opacity_mid',50),
                          ('opacity_after',100),('enabled',False),('stroke',True),('effect_count',1),('fill',[1,0,0])]:
            bad=deepcopy(o);bad[key]=value
            with self.subTest(key=key),self.assertRaises(ValueError):
                fulltext.validate_sentence_plane(dict(self.r,motion_profile={'sentence_occlusion':'unadorned_bound_paper_plane','plane_depth_offset':20}),[{'sentence_occlusion':bad}])
        with self.assertRaises(ValueError):fulltext.validate_sentence_plane(dict(self.r,motion_profile={'sentence_occlusion':'unadorned_bound_paper_plane','plane_depth_offset':20}),[{}])

    def test_previous_motion_take_replays_without_new_occlusion(self):
        prior=deepcopy(self.r);prior['version']='0.2.9';prior['motion_profile'].pop('foreground_background');prior['motion_profile'].pop('background_clear')
        prior['spec_sha']=sha({k:v for k,v in prior.items() if k not in ('spec_sha','project','bundle_path','status_path')})
        fulltext.validate(prior)

    def test_prior_4k_request_remains_replayable_without_new_motion_profile(self):
        prior=deepcopy(self.r);prior['version']='0.2.8';prior.pop('motion_profile')
        prior['spec_sha']=sha({k:v for k,v in prior.items() if k not in ('spec_sha','project','bundle_path','status_path')})
        fulltext.validate(prior)

    def test_motion_readback_rejects_synchronous_reflow_and_row_stops(self):
        rows=[]
        for p in self.r['director']['passes']:
            rows.append({'kind':p['kind'],'departure_time':p['lift'][0]+(1 if p['kind']=='fast' else 2)/24,
                'foreground_original':[10,20,0],'foreground_departure':[10,20,-48],
                'background_original':[100,200,0],'background_departure':[100,200,0],
                'camera_carries':[{'bezier':True,'speed':90,'influence':22}],
                'sentence_plane_index':300,'last_sentence_text_index':299,
                'background_opacity_before':28,'background_opacity_departure':0,'foreground_opacity_departure':100})
        fulltext.validate_motion(self.r,rows)
        for field,value in (('foreground_departure',[11,20,-48]),('foreground_departure',[10,20,0]),
                            ('background_departure',[100,201,0]),('foreground_opacity_departure',80),('background_opacity_departure',28),('camera_carries',[]),
                            ('camera_carries',[{'bezier':True,'speed':0,'influence':22}])):
            bad=deepcopy(rows);bad[0][field]=value
            with self.subTest(field=field,value=value),self.assertRaises(ValueError):fulltext.validate_motion(self.r,bad)

    def test_output_diagnostic_path_does_not_change_spec(self):
        bad=deepcopy(self.r);bad['project']='moved/project.aep';bad['bundle_path']='moved/bundle.json';bad['status_path']='moved/status.json'
        fulltext.validate(bad);self.assertEqual(self.r['spec_sha'],bad['spec_sha'])


class SentenceAttentionTests(unittest.TestCase):
    def test_literal_groups_do_not_split_at_layout_wrap(self):
        words=[{'id':'a','text':'A','gap_before':''}, {'id':'b','text':'sentence.','gap_before':' '},
               {'id':'c','text':'Next','gap_before':' '}, {'id':'d','text':'one!','gap_before':' '}]
        self.assertEqual(fulltext.sentence_groups(words),[['a','b'],['c','d']])
        words[1]['text']='sentence';words[2]['gap_before']='\n'
        self.assertEqual(fulltext.sentence_groups(words),[['a','b'],['c','d']])

    def test_native_intent_alone_cannot_pass(self):
        r={'sentence_attention':{'groups':[['a','b']]}}
        row={'ids':['a','b'],'gain_cap':.02,'scale_error':'','position_error':'',
             'samples':[{'time':1,'base':[200]*3,'actual':[204]*3}]}
        fulltext.validate_attention(r,[row])
        for field,value in [('ids',['unbound']),('gain_cap',.1),('scale_error','failed')]:
            bad=deepcopy(row);bad[field]=value
            with self.subTest(field=field),self.assertRaises(ValueError):fulltext.validate_attention(r,[bad])
        for scale in ([200]*3,[220]*3,[204,203,204]):
            bad=deepcopy(row);bad['samples'][0]['actual']=scale
            with self.subTest(scale=scale),self.assertRaises(ValueError):fulltext.validate_attention(r,[bad])


if __name__=='__main__':unittest.main()
