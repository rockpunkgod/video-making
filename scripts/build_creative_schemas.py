"""V9 additive schemas; does not rewrite frozen ANSWER or V0–V8 contracts."""
import argparse
import json
from video_contracts import ROOT

S={'type':'string'}; N={'type':'number','minimum':0}; B={'type':'boolean'}
SHA={'type':'string','pattern':'^[a-f0-9]{64}$'}
def obj(props,required=None):return {'type':'object','properties':props,'required':list(props) if required is None else required,'additionalProperties':False}
def arr(item):return {'type':'array','items':item}
REF=obj({'asset_id':S,'pointer':S})
EXCERPT=obj({'ref':REF,'start':{'type':'integer','minimum':0},'end':{'type':'integer','minimum':1},'text':S,'candidate':S},['ref','start','end','text'])
REVIEW={'type':['object','null']}
UNIT=obj({'unit_id':S,'scene_id':S,'source_claim_refs':{'type':'array','minItems':1,'items':S},'evidence_refs':arr(REF),
    'action_artifact_refs':arr(REF),'review_refs':arr(REF),'method_id':S,'asset_id':S,'role':S,
    'intent':{'enum':['hook','evidence','core','regroup','routing','rewire','boundary','stop','method','cta']},
    'source_meaning':arr(obj({'claim_id':S,'text':S})),'spoken_copy':S,'on_screen_copy':S,'protected_terms':arr(S),
    'prohibited_implications':arr(S),'tone':S,'pause_after':N,'breath':S,'emphasis':arr(S),'visual_excerpts':arr(EXCERPT),'fidelity_review':REVIEW,
    'sentence_bindings':arr(obj({'text':S,'source_claim_refs':arr(S),'evidence_refs':arr(REF)}))})
DELIVERY=obj({'schema_version':{'const':'0.1.0'},'version':{'const':'0.1.0'},'delivery_id':S,'package_id':S,
    'package_sha':SHA,'manifest_sha':SHA,'teaching_semantic_sha':SHA,'provider':{'const':'agent_authored_internal'},
    'units':{'type':'array','minItems':1,'items':UNIT},'delivery_copy_sha':SHA,'screen_copy_sha':SHA,
    'editorial_review_sha':{'type':'null'},'public_render_ready':{'const':False}})
TRACK=obj({'version':{'const':'0.1.0'},'delivery_copy_sha':SHA,'fps':{'const':24},'provider':S,
    'usage':{'const':'INTERNAL_SCRATCH_VOICE'},'duration':N,'audio_timing_sha':SHA,
    'units':arr(obj({'unit_id':S,'start':N,'voice_end':N,'end':N,'estimated_or_recorded_duration':N,'duration_kind':S,
        'pause':N,'breath':S,'emphasis':arr(S),'audio_path':{'type':['string','null']},'audio':{'type':'object'},'spoken_copy_sha':SHA,'sentence_boundaries':arr({'type':'object'})}))})
PLAN=obj({'version':{'const':'0.1.0'},'profile':{'const':'CINEMATIC_LANDSCAPE'},'design':{'type':'object'},'design_sha':SHA,
    'delivery_copy_sha':SHA,'screen_copy_sha':SHA,'teaching_semantic_sha':SHA,'audio_timing_sha':SHA,'duration':N,
    'shots':arr({'type':'object','required':['shot_id','unit_id','scene_id','start','end','phases','hold_start','components','structure','source_claim_refs','evidence_refs']}),
    'captions':arr({'type':'object','required':['cue_id','unit_id','start','end','lines','text','source_claim_refs','evidence_refs']}),
    'source_display':{'type':'object'},'public_render_ready':{'const':False}})
LANDSCAPE=obj({'schema_version':{'const':'0.1.0'},'version':{'const':'0.3.0'},'render_id':S,'package_id':S,'package_sha':SHA,
    'manifest_sha':SHA,'delivery_id':S,'delivery_sha':SHA,'shot_plan':PLAN,'shot_plan_sha':SHA,'narration_track':TRACK,
    'audio':{'type':'object'},'audio_cue_sheet':{'type':'object'},'copy_lock':obj({'teaching_semantic_sha':SHA,'delivery_copy_sha':SHA,'screen_copy_sha':SHA,'audio_timing_sha':SHA,'editorial_review_sha':{'type':'null'}}),
    'canvas':obj({'width':{'const':1920},'height':{'const':1080},'fps':{'const':24},'duration':N}),
    'template_family':{'const':'CINEMATIC_LANDSCAPE_MASTER'},'template_version':{'const':'0.3.0'},'template_sha':SHA,
    'usage':{'const':'INTERNAL_CREATIVE_PREVIEW'},'public_render_ready':{'const':False},'status_input_shas':{'type':'object'},
    'upstream_bindings':{'type':'object'},'schema_shas':{'type':'object'},'revision':{'type':'integer','minimum':1},
    'method_tags':S,'review_status':obj({'teaching':{'const':'PENDING'},'source':{'const':'PENDING'},'editorial':{'const':'PENDING'},'human_taste':{'const':'PENDING'}})})
SCHEMAS={'delivery-copy':DELIVERY,'narration-track':TRACK,'shot-plan':PLAN,'landscape-render-contract':LANDSCAPE}
def main():
    ap=argparse.ArgumentParser();ap.add_argument('--check',action='store_true');a=ap.parse_args()
    for name,schema in SCHEMAS.items():
        path=ROOT/'creative/schemas'/f'{name}.json';text=json.dumps({'$schema':'https://json-schema.org/draft/2020-12/schema',**schema},ensure_ascii=False,indent=2)+'\n'
        if a.check:
            if not path.exists() or path.read_text(encoding='utf-8')!=text:raise SystemExit('V9 schema drift: '+name)
        else:path.parent.mkdir(parents=True,exist_ok=True);path.write_text(text,encoding='utf-8',newline='\n')
    print('V9 schemas PASS')
if __name__=='__main__':main()
