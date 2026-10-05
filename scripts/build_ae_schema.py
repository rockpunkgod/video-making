"""Generate the V8 schema without altering the frozen Video OS schemas."""
import argparse
import json
from video_contracts import ROOT
from ae_production.contract import COMPONENTS


def obj(properties, required=None):
    return {'type':'object','properties':properties,'required':list(properties) if required is None else required,'additionalProperties':False}
def array(item): return {'type':'array','items':item}
S={'type':'string'}; N={'type':'number','minimum':0}; I={'type':'integer','minimum':1}
REF=obj({'pointer':S,'value_sha':{'type':'string','pattern':'^[a-f0-9]{64}$'}})
LAYOUT=obj({'x':N,'y':N,'width':N,'height':N,'lines':array(S),'style_token':{'enum':['Hero','Title','Body','Metadata','Subtitle']}})
MOTION=obj({'type':{'enum':['reveal','focus','compare','eliminate','connect']},'duration_frames':I,
            'easing':{'const':'soft_out'},'delay_frames':{'type':'integer','minimum':0},'emphasis':S})
COMP=obj({'component_id':S,'component_type':{'enum':list(COMPONENTS)},'content':{'type':'object'},
          'source_refs':{'type':'array','minItems':1,'items':REF},'layout':LAYOUT,'style_token':S,'motion_primitive':MOTION})
SCENE=obj({'scene_id':S,'package_scene_id':S,'scene_type':S,'start':N,'end':N,'layout_variant':S,
           'components':{'type':'array','minItems':1,'items':COMP},'claim_refs':array(S),'evidence_refs':array({'type':'object'}),
           'semantic_payload_sha':S,'spoken_text':S,'typed_output':{'type':['object','null']}})
CUE=obj({'cue_id':S,'scene_id':S,'start':N,'end':N,'text':S,'lines':{'type':'array','minItems':1,'maxItems':2,'items':S},'source_ref':REF})
SCHEMA={'$schema':'https://json-schema.org/draft/2020-12/schema',**obj({
    'schema_version':{'const':'0.1.0'},'render_id':S,'package_id':S,'package_sha':S,'manifest_sha':S,'final_copy_sha':S,
    'usage':{'const':'INTERNAL_ENGINEERING_PREVIEW'},'public_render_ready':{'const':False},
    'canvas':obj({'width':{'const':1080},'height':{'const':1920},'fps':{'const':30},'duration':N,'safe_area':{'type':'object'}}),
    'design_system_version':S,'design_sha':S,'design':{'type':'object'},'template_family':{'const':'METHOD_DEMO_MASTER'},
    'template_version':S,'template_sha':S,'revision':I,'methods':array(obj({'method_id':S,'role':S,'brand':S,'refs':array(REF)})),
    'scenes':{'type':'array','minItems':1,'items':SCENE},'subtitles':array(CUE),'source_tags':S,'projection_refs':array(REF),
    'upstream_bindings':{'type':'object'},'status_input_shas':{'type':'object'},
    'render_profile':obj({'fps':{'const':30},'voiceover':{'const':'text_timed_no_recording'},'watermark':{'const':True},'silent_preview':{'const':True}})
})}


def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--check',action='store_true'); args=ap.parse_args()
    path=ROOT/'ae/schemas/render-contract.json'; text=json.dumps(SCHEMA,ensure_ascii=False,indent=2)+'\n'
    if args.check:
        if not path.exists() or path.read_text(encoding='utf-8')!=text: raise SystemExit('AE schema drift')
    else:
        path.parent.mkdir(parents=True,exist_ok=True); path.write_text(text,encoding='utf-8')
    print('AE schema PASS')
if __name__=='__main__': main()
