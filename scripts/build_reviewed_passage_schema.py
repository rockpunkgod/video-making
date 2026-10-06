"""Schema for explicit upstream host lesson packets, without real question data."""
from video_contracts import ROOT,write

S={'type':'string','minLength':1}
def arr(item,minimum=0):return {'type':'array','items':item,'minItems':minimum}
def obj(properties,optional=()):return {'type':'object','properties':properties,'required':[k for k in properties if k not in optional],'additionalProperties':False}
span=obj({'field':S,'start':{'type':'integer','minimum':0},'end':{'type':'integer','minimum':1},'quote':S})
question=obj({'question_id':S,'number':{'type':'integer','minimum':1},'stem':S,'options':{'type':'object','minProperties':2,'additionalProperties':S}})
decision=obj({'question_id':S,'candidate':S,'effect':{'enum':['retain','eliminate']},'basis':{'const':'direct_text_review'},'method_id':{'type':'null'},'rationale':S,'evidence':arr(span,1)})
action=obj({'action_id':S,'question_id':S,'method_id':S,'method_version':S,'role':{'enum':['locator','interpreter','framework']},'output':S,'evidence':arr(span,1),'stop_rule':S,'answer':{'type':'null'}})
indices=arr({'type':'integer','minimum':0})
segment=obj({'segment_id':S,'question_id':S,'kind':{'enum':['action','evidence','comparison','closure','boundary']},'text':S,'screen_text':S,'evidence':arr(span,1),'decision_refs':indices,'action_refs':arr(S),'fidelity_reviewed':{'const':True},'summary_refs':indices},('summary_refs',))
review=obj({'reviewer':S,'reviewer_kind':{'enum':['AI','ai_host','human']},'status':{'const':'reviewed'},'evaluation_phase':{'const':'post_reveal'},'independent_human_certified':{'type':'boolean'},'independent_human_review':S,'order':arr(S,1),'order_rationale':S,'decisions':arr(decision,2),'method_actions':arr(action),'segments':arr(segment,1),'material_sha':S},('independent_human_certified','independent_human_review'))
packet=obj({'lesson_id':S,'passage':S,'questions':arr(question,1),'methods':arr({'type':'object'}),'review':review,'source':{'type':'object','required':['usage_status','redistribution_status'],'properties':{'usage_status':S,'redistribution_status':S}}})
packet.update({'$schema':'https://json-schema.org/draft/2020-12/schema','$id':'https://answer.local/schemas/reviewed-passage-export.json'})
if __name__=='__main__':write(ROOT/'schemas/reviewed-passage-export.json',packet)
