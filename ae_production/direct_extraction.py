"""Read actual native handoffs for the optional highlight-then-extract edit."""
import json
import math


ORANGE = [.69, .27, .06]


def _close(actual, expected, tolerance=.001):
    return (isinstance(actual, (int, float)) and not isinstance(actual, bool)
            and math.isfinite(actual) and abs(actual-expected)<=tolerance)


def _vector(actual, expected, tolerance=.01):
    return (isinstance(actual, list) and len(actual)==len(expected)
            and all(_close(x,y,tolerance) for x,y in zip(actual,expected)))


def _identity(value):
    return isinstance(value,int) and not isinstance(value,bool) and value>0


def _scope(plan, native):
    scenes=[s for s in plan['scenes'] if s.get('extraction_policy')=='highlight_then_extract'
            and s.get('motion_treatment')!='in_place_check']
    if not scenes:return []
    audit=native['audit'];manifest=audit.get('direct_extractions',[])
    if len(manifest)!=len(scenes) or {x['scene'] for x in manifest}!={s['id'] for s in scenes}:
        raise ValueError('Native build omitted the direct extraction policy')
    scope=[]
    for s in scenes:
        end=s['reading_events'][-1]['end_time']
        if (not _close(s['extract_start'],end,1e-6) or not _close(s['source_arrive'],end,1e-6)
                or not _close(s['extraction_highlight_at'],end-.25,1/24+1e-6)):
            raise ValueError('Direct extraction has an extra hold after reading')
        if not 0<end-s['extraction_highlight_at']<=.3:
            raise ValueError('Highlight must lead immediately into extraction')
        m=next(x for x in manifest if x['scene']==s['id'])
        if any(not _close(m[k],v,1e-6) for k,v in (
                ('extract_start',end),('settled',s['settled']),
                ('highlight_at',s['extraction_highlight_at']),('reading_end',end))):
            raise ValueError('Native direct extraction clock differs from plan')
        excerpt=plan['excerpts'][s['excerpt']]
        blocks={b['id']:b for b in plan['worlds'][excerpt['world']]['blocks']}
        refs=[r for r in s['source_refs'] if r['world']==excerpt['world'] and r['pointer']=='/passage']
        selected=[blocks[bid] for bid in excerpt['block_ids'] if any(
            r['start']<blocks[bid]['end'] and r['end']>blocks[bid]['start'] for r in refs)]
        if not selected:raise ValueError('Direct extraction has no explicitly selected original blocks')
        sources=[]
        for block in selected:
            bound=[r for r in audit['sources'] if r['id']==block['id']]
            if len(bound)!=1 or bound[0]['text']!=block['text'] or not _identity(bound[0]['layer_id']):
                raise ValueError('Direct extraction original inventory differs from the frozen plan')
            sources.append({'block_id':block['id'],'text':block['text'],
                            'source_layer_id':bound[0]['layer_id'],'position':bound[0]['position']})
        hits=[]
        for hi,phrase in enumerate(s['extraction_highlights']):
            matches=[b for b in selected if phrase and phrase in b['text']]
            if not matches:raise ValueError('Direct extraction keyword is not in its selected original')
            for block in matches:
                source=next(x for x in sources if x['block_id']==block['id'])
                hits.append({'phrase':phrase,'name':'DIRECT_EXTRACTION_HIT_'+s['id']+'_'+str(hi),
                             'source_layer_id':source['source_layer_id'],'source_block_id':block['id']})
        if not hits or m['hits']!=hits:
            raise ValueError('Native source highlights do not match authored keywords and originals')
        extractions=[x for x in audit['extractions'] if x['scene']==s['id']]
        if len(extractions)!=1:raise ValueError('Direct extraction group inventory changed')
        ex=extractions[0]
        if (ex['selected_block_ids']!=[b['id'] for b in selected]
                or not _vector(ex['origin'],sources[0]['position'])
                or len(m['clone_ids'])!=len(selected) or len(set(m['clone_ids']))!=len(selected)
                or any(not _identity(x) for x in m['clone_ids'])):
            raise ValueError('Native extraction inventory is not the selected original inventory')
        scope.append({'scene':s['id'],'time':end,'highlight_at':s['extraction_highlight_at'],
                      'settled':s['settled'],'end':s['end'],'origin':ex['origin'],
                      'group_id':ex['group_id'],'clone_ids':m['clone_ids'],
                      'blocks':sources,'hits':hits})
    return scope


def validate_direct_extraction(plan, native, rows):
    scope=_scope(plan,native)
    comps=(native['comp_id'],native['master_comp_id'])
    if any(not _identity(c) for c in comps) or comps[0]==comps[1]:
        raise ValueError('Direct extraction requires two distinct native compositions')
    expected={(comp,s['scene']) for comp in comps for s in scope}
    if {(r['comp_id'],r['scene']) for r in rows}!=expected or len(rows)!=len(expected):
        raise ValueError('Incomplete native direct extraction coverage')
    source_identities={}
    for row in rows:
        s=next(s for s in scope if s['scene']==row['scene'])
        if (not _close(row['in_point'],s['time']) or not _close(row['out_point'],s['end'])
                or row['enabled'] is not True or row['guide'] is not False
                or row['three_d'] is not True or not _identity(row['group_id'])
                or not _vector(row['position'],s['origin'])
                or not _vector(row['expected_origin'],s['origin'])):
            raise ValueError('Extraction must start visibly at its original position')
        if row['comp_id']==comps[0] and row['group_id']!=s['group_id']:
            raise ValueError('Native proxy extraction group identity changed')
        expected_names=['EXTRACT_'+s['scene']+'_'+b['block_id'] for b in s['blocks']]
        inventory=row['blocks']
        if (len(inventory)!=len(s['blocks']) or row['clone_names']!=expected_names
                or [b['block_id'] for b in inventory]!=[b['block_id'] for b in s['blocks']]):
            raise ValueError('Native selected clone inventory is incomplete or gained unrelated text')
        clone_ids=[]
        for actual,bound,name in zip(inventory,s['blocks'],expected_names):
            if (actual['source_name']!=bound['block_id'] or actual['clone_name']!=name
                    or actual['source_text']!=bound['text'] or actual['clone_text']!=bound['text']
                    or actual['source_enabled'] is not True or actual['clone_enabled'] is not True
                    or actual['source_guide'] is not False or actual['clone_guide'] is not False
                    or actual['clone_three_d'] is not True or actual['clone_parent']!=row['group_id']
                    or not _close(actual['clone_in'],s['time']) or not _close(actual['clone_out'],s['end'])
                    or not _close(actual['source_opacity'],0,.01)
                    or not _close(actual['clone_opacity'],100,.01)
                    or not _vector(actual['source_position'],bound['position'])
                    or not _vector(actual['clone_position'],[0,bound['position'][1]-s['origin'][1],0])):
                raise ValueError('Selected source/clone text, origin, lifetime or visibility changed')
            ids=(actual['source_id'],actual['clone_id'],row['group_id'])
            if any(not _identity(x) for x in ids) or len(set(ids))!=3:
                raise ValueError('Direct extraction native layer identity changed')
            if row['comp_id']==comps[0] and actual['source_id']!=bound['source_layer_id']:
                raise ValueError('Direct extraction proxy original identity changed')
            key=(row['comp_id'],bound['block_id'])
            if key in source_identities and source_identities[key]!=actual['source_id']:
                raise ValueError('One original acquired inconsistent native identities')
            source_identities[key]=actual['source_id'];clone_ids.append(actual['clone_id'])
        if len(set(clone_ids))!=len(clone_ids) or (row['comp_id']==comps[0] and clone_ids!=s['clone_ids']):
            raise ValueError('Direct extraction clone identities changed')
        # The final keyword's block cannot stand in for the other selected originals.
        if not _close(row['source_opacity'],0,.01) or not _close(row['clone_opacity'],100,.01):
            raise ValueError('Source-to-clone handoff is not at the reading boundary')
        if len(row['hits'])!=len(s['hits']):raise ValueError('Native keyword coverage changed')
        for hit,bound in zip(row['hits'],s['hits']):
            block=next(b for b in inventory if b['block_id']==bound['source_block_id'])
            start=block['source_text'].index(bound['phrase']);end=start+len(bound['phrase'])
            if (hit['phrase']!=bound['phrase'] or hit['source_block_id']!=bound['source_block_id']
                    or hit['name']!=bound['name'] or hit['source_id']!=block['source_id']
                    or hit['clone_id']!=block['clone_id']
                    or hit['source_text']!=block['source_text'] or hit['clone_text']!=block['clone_text']):
                raise ValueError('Highlight/extraction lost the selected original words or identity')
            for prefix in ('source','clone'):
                lo=hit['start'] if prefix=='source' else hit['clone_start']
                hi=hit['end'] if prefix=='source' else hit['clone_end']
                if (lo!=start or hi!=end or hit[prefix+'_units']!=2
                        or hit[prefix+'_smoothness']!=0
                        or not _close(hit[prefix+'_peak'],100,.01)
                        or not _vector(hit[prefix+'_samples'],[0,50,100,100],.01)
                        or hit[prefix+'_expression_error'] or hit[prefix+'_fill_error']
                        or not _vector(hit[prefix+'_fill'],ORANGE,.002)
                        or not _close(hit[prefix+'_opacity'],0 if prefix=='source' else 100,.01)):
                    raise ValueError('Native keyword range, highlight color or visible handoff changed')
    return {'status':'PASS','policy':'highlight_then_extract','readbacks':rows,
            'normal_speed_review':'UNOBSERVED'}


def direct_extraction_readback(host, plan, native):
    scope=_scope(plan,native)
    if not scope:return None
    code='var scope='+json.dumps(scope)+';var ids='+json.dumps([native['comp_id'],native['master_comp_id']])+''';var out=[];
function uniqueLayer(c,name){var found=null;for(var i=1;i<=c.numLayers;i++){if(c.layer(i).name!==name)continue;if(found)throw Error("Duplicate direct extraction layer: "+name);found=c.layer(i);}if(!found)throw Error("Missing direct extraction layer: "+name);return found;}
function transform(l,name){return l.property("ADBE Transform Group").property(name);}
function textAt(l,t){return l.property("Source Text").valueAtTime(t,false).text.replace(/\\r/g,"\\n");}
function amountAt(p,t){var v=p.valueAtTime(t,false);if(v instanceof Array)return v[0];return v;}
function hitState(layer,h,s){
 var an=layer.property("ADBE Text Properties").property("ADBE Text Animators").property(h.name);
 var sel=an.property("ADBE Text Selectors").property(1),adv=sel.property("ADBE Text Range Advanced"),amount=adv.property("ADBE Text Selector Max Amount"),fill=an.property("ADBE Text Animator Properties").property("ADBE Text Fill Color");
 var times=[s.highlight_at,(s.highlight_at+s.time)/2,s.time,s.settled],samples=[];for(var i=0;i<times.length;i++)samples.push(amountAt(amount,times[i]));
 return {start:sel.property("ADBE Text Index Start").valueAtTime(s.time,false),end:sel.property("ADBE Text Index End").valueAtTime(s.time,false),units:adv.property("ADBE Text Range Units").value,smoothness:adv.property("ADBE Text Selector Smoothness").value,peak:amountAt(amount,s.time),samples:samples,expression_error:amount.expressionError,fill:fill.valueAtTime(s.time,false),fill_error:fill.expressionError,opacity:transform(layer,"ADBE Opacity").valueAtTime(s.time,false)};
}
for(var ci=0;ci<ids.length;ci++){var c=app.project.itemByID(ids[ci]);
 for(var si=0;si<scope.length;si++){var s=scope[si],g=uniqueLayer(c,"SOURCE_LIFT_"+s.scene),hits=[],inventory=[],cloneNames=[],prefix="EXTRACT_"+s.scene+"_";
  for(var li=1;li<=c.numLayers;li++)if(c.layer(li).name.indexOf(prefix)===0)cloneNames.push(c.layer(li).name);
  for(var bi=0;bi<s.blocks.length;bi++){var b=s.blocks[bi],source=uniqueLayer(c,b.block_id),clone=uniqueLayer(c,prefix+b.block_id);
   inventory.push({block_id:b.block_id,source_name:source.name,source_id:source.id,source_text:textAt(source,s.time),source_enabled:source.enabled,source_guide:source.guideLayer,source_opacity:transform(source,"ADBE Opacity").valueAtTime(s.time,false),source_position:transform(source,"ADBE Position").valueAtTime(s.time,false),clone_name:clone.name,clone_id:clone.id,clone_text:textAt(clone,s.time),clone_enabled:clone.enabled,clone_guide:clone.guideLayer,clone_three_d:clone.threeDLayer,clone_opacity:transform(clone,"ADBE Opacity").valueAtTime(s.time,false),clone_in:clone.inPoint,clone_out:clone.outPoint,clone_parent:clone.parent.id,clone_position:transform(clone,"ADBE Position").valueAtTime(s.time,false)});
  }
  for(var hi=0;hi<s.hits.length;hi++){var h=s.hits[hi],source=uniqueLayer(c,h.source_block_id),clone=uniqueLayer(c,prefix+h.source_block_id),a=hitState(source,h,s),b=hitState(clone,h,s);
   hits.push({phrase:h.phrase,name:h.name,source_block_id:h.source_block_id,source_id:source.id,clone_id:clone.id,source_text:textAt(source,s.time),clone_text:textAt(clone,s.time),start:a.start,end:a.end,clone_start:b.start,clone_end:b.end,source_units:a.units,clone_units:b.units,source_smoothness:a.smoothness,clone_smoothness:b.smoothness,source_peak:a.peak,clone_peak:b.peak,source_samples:a.samples,clone_samples:b.samples,source_expression_error:a.expression_error,clone_expression_error:b.expression_error,source_fill:a.fill,clone_fill:b.fill,source_fill_error:a.fill_error,clone_fill_error:b.fill_error,source_opacity:a.opacity,clone_opacity:b.opacity});
  }
  cloneNames.sort();var wanted=[];for(var bi=0;bi<s.blocks.length;bi++)wanted.push(prefix+s.blocks[bi].block_id);wanted.sort();
  if(JSON.stringify(cloneNames)!==JSON.stringify(wanted))throw Error("Unexpected direct extraction clone inventory");
  var orderedNames=[];for(var bi=0;bi<s.blocks.length;bi++)orderedNames.push(prefix+s.blocks[bi].block_id);
  out.push({comp_id:c.id,scene:s.scene,group_id:g.id,in_point:g.inPoint,out_point:g.outPoint,enabled:g.enabled,guide:g.guideLayer,three_d:g.threeDLayer,position:transform(g,"ADBE Position").valueAtTime(s.time,false),expected_origin:s.origin,source_opacity:inventory[inventory.length-1].source_opacity,clone_opacity:inventory[inventory.length-1].clone_opacity,blocks:inventory,clone_names:orderedNames,hits:hits});
 }
}return out;'''
    return validate_direct_extraction(plan,native,host.js(code))
