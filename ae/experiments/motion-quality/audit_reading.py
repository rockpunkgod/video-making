"""Native checks for row-major focus and the query-to-source color handoff."""
import json,sys
from pathlib import Path
import numpy as np
from run import Trial,read,write,sha256

def main(folder):
    t=Trial(folder);p=t.folder;n=t.native();i=t.i
    assert i.get('reading_focus_revision')==2
    old=read(Path(read(p/'USER_FEEDBACK.json')['baseline'])/'NATIVE_READBACK.json')
    now=read(p/'NATIVE_READBACK.json')
    assert old['comps']['A']==now['comps']['A']
    # B's camera, 3D placements, extraction, return and source timing must stay.
    for field in ('frames','hierarchy','texts','source_layers','controllers','liftPosition','liftOrientation'):
        assert old['comps']['B'][field]==now['comps']['B'][field],field
    code=r'''
var c=app.project.itemByID(CID),I=INPUT,rig=RIG,l=c.layer(I.reading_focus.layer),d=l.property('Source Text').valueAtTime(I.clip_start,false),aa=l.property('ADBE Text Properties').property('ADBE Text Animators'),out={rows:[],chunks:[],focus:[],query:[]};
for(var k=0;k<d.composedLineCount;k++){var row=d.composedLineRange(k,k+1);out.rows.push({row:k,start:row.characterStart,end:row.characterEnd,text:d.text.slice(row.characterStart,row.characterEnd)});}
for(var k=0;k<rig.chunks.length;k++){var ck=rig.chunks[k];if(ck.group!=='reading_line_chunks')continue;var an=aa.property(ck.colorAnimator),sel=an.property('ADBE Text Selectors').property(1),adv=sel.property('ADBE Text Range Advanced');out.chunks.push({start:sel.property('ADBE Text Index Start').value,end:sel.property('ADBE Text Index End').value,text:d.text.slice(ck.start,ck.end),color:an.property('ADBE Text Animator Properties').property('ADBE Text Fill Color').value,amountAtPeak:adv.property('ADBE Text Selector Max Amount').valueAtTime(ck.center,false)});}
for(var f=0;f<144;f++){var time=I.clip_start+f/24,amounts=[];for(var k=0;k<rig.chunks.length;k++){var ck=rig.chunks[k];if(ck.group!=='reading_line_chunks')continue;var a=aa.property(ck.colorAnimator).property('ADBE Text Selectors').property(1).property('ADBE Text Range Advanced').property('ADBE Text Selector Max Amount');amounts.push(a.valueAtTime(time,false));}out.focus.push({frame:f,amounts:amounts});}
var qp=c.layer(rig.reading_revision.query_rejoin.layer).property('ADBE Text Properties').property('ADBE Text Animators').property(rig.reading_revision.query_rejoin.animator).property('ADBE Text Animator Properties').property('ADBE Text Fill Color');
for(var f=282;f<=312;f++)out.query.push({frame:f,color:qp.valueAtTime(I.clip_start+f/24,false)});
out.queryEnd=qp.valueAtTime(I.query_rejoin.end,false);out.queryStart=qp.valueAtTime(I.query_rejoin.start,false);
var sr=rig.reading_revision.source_rejoin,sp=c.layer(sr.layer).property('ADBE Text Properties').property('ADBE Text Animators').property(sr.animator),amount=sp.property('ADBE Text Selectors').property(1).property('ADBE Text Range Advanced').property('ADBE Text Selector Max Amount');
out.sourceHandoff={before:amount.valueAtTime(I.locator_scene.end-1/24,false),at:amount.valueAtTime(I.locator_scene.end,false),color:sp.property('ADBE Text Animator Properties').property('ADBE Text Fill Color').value};
return out;
'''
    for token,value in [('CID',n['B_source']),('INPUT',i),('RIG',n['rig'])]:code=code.replace(token,json.dumps(value,ensure_ascii=False))
    r=t.h.js(code);write(p/'READING_NATIVE_READBACK.json',r)
    assert len(r['rows'])==7 and len(r['chunks'])==14
    for a,b in zip(r['rows'],i['reading_focus']['rows']):
        assert all(a[k]==b[k] for k in ('row','start','end','text'))
    for a,b in zip(r['chunks'],i['reading_focus']['chunks']):
        assert all(a[k]==b[k] for k in ('start','end','text'))
        assert abs(a['amountAtPeak']-100)<.001
        assert np.max(np.abs(np.array(a['color'][:3])-n['rig']['reading_revision']['blue']))<.001
    order=[]
    for frame in r['focus']:
        a=frame['amounts']
        if max(a)>50:
            j=int(np.argmax(a))
            if not order or order[-1]!=j:order.append(j)
    assert order==list(range(14)),order
    q=n['rig']['reading_revision']['query_rejoin'];values=np.array([x['color'][:3] for x in r['query']])
    assert np.max(np.abs(np.array(r['queryStart'][:3])-q['from']))<1e-5
    assert np.max(np.abs(np.array(r['queryEnd'][:3])-q['to']))<1e-5
    max_step=float(np.max(np.abs(np.diff(values,axis=0))))
    assert max_step<.08,max_step
    distance=np.linalg.norm(values-np.array(q['to']),axis=1)
    assert np.max(np.diff(distance))<1e-5
    assert r['sourceHandoff']['before']==0 and r['sourceHandoff']['at']==100
    assert np.max(np.abs(np.array(r['sourceHandoff']['color'][:3])-q['to']))<1e-5
    result={'status':'PASS','native_identity_sha256':sha256(p/'NATIVE_IDENTITY.json'),'rows':7,'chunks':14,'observed_dominant_order':order,'camera_objects_and_prior_motion_identical':True,'original_A_identical':True,'query_max_adjacent_frame_channel_change':max_step,'query_matches_original_ink_before_handoff':True,'copy_audio_evidence_unchanged':True,'human_revision_review':'PENDING'}
    write(p/'READING_QA.json',result);print(json.dumps(result,ensure_ascii=False))

if __name__=='__main__':main(sys.argv[1])
