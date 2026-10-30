from .registry import validate_schema

def field_text(question, field):
    if field.startswith('option:'):
        return question.get('options',{}).get(field.split(':',1)[1])
    if field.startswith('continuation_starters:'):
        try: return question.get('continuation_starters',[])[int(field.split(':',1)[1])]
        except (ValueError, IndexError): return None
    if field not in {'passage','stem','student_text'}:
        return None
    return question.get(field)

def check_span(question, span):
    raw = field_text(question,span['field'])
    if raw is None or not 0 <= span['start'] < span['end'] <= len(raw) or raw[span['start']:span['end']] != span['quote']:
        raise ValueError('Invalid evidence span or fabricated quote')
    return span

def validate_graph(graph, question=None):
    validate_schema('evidence-graph',graph)
    nodes = {n['id']:n for n in graph['nodes']}
    manifest=None
    if question is not None and any(n['type']=='image_evidence' for n in nodes.values()):
        from .image_evidence import image_manifest
        manifest=image_manifest(question)
    if len(nodes) != len(graph['nodes']):
        raise ValueError('Duplicate evidence node')
    if question is not None and graph['nodes']:
        root = graph['nodes'][0]
        if root['type'] == 'question_signal' and 'material_sha256' in root:
            from .question_verification import material_fingerprint
            candidates = sorted(set(question.get('options',{}))
                                | {r['candidate'] for r in question.get('relations',[])})
            if (root['material_sha256'] != material_fingerprint(question)
                    or root.get('candidate_ids',[]) != candidates
                    or ('required_image_evidence' in root)!=('required_image_evidence' in question)
                    or root.get('required_image_evidence')!=question.get('required_image_evidence')):
                raise ValueError('Question signal scope differs from original material/candidates')
    adjacency = {i:[] for i in nodes}
    incoming = {i:[] for i in nodes}
    for e in graph['edges']:
        if e['from'] not in nodes or e['to'] not in nodes:
            raise ValueError('Dangling evidence edge')
        adjacency[e['from']].append(e['to'])
        incoming[e['to']].append(e['from'])
    colors = {}
    def visit(nid):
        if colors.get(nid)==1: raise ValueError('Circular evidence proof')
        if colors.get(nid)==2: return
        colors[nid]=1
        for child in adjacency[nid]: visit(child)
        colors[nid]=2
    for nid in nodes: visit(nid)
    def ancestors(nid):
        found = set()
        work = list(incoming[nid])
        while work:
            x = work.pop()
            if x not in found:
                found.add(x)
                work.extend(incoming[x])
        return [nodes[x] for x in found]
    def own_candidate_relation(relation,method_id,candidate):
        if relation['type']!='relation' or not relation.get('reviewed') or relation.get('method_id')!=method_id or relation.get('candidate')!=candidate:
            return False
        proof=ancestors(relation['id'])
        return (any(n['type']=='candidate_claim' and n.get('candidate')==candidate for n in proof)
                and any(n['type']=='question_signal' and n.get('reviewed') and n.get('method_id')==method_id for n in proof)
                and any(nodes[parent]['type']=='source_evidence' and nodes[parent].get('span') for parent in incoming[relation['id']]))
    for nid, node in nodes.items():
        if node['type']=='question_scope':
            if (node.get('method_id') or not node.get('review_id') or not node.get('candidate_ids')
                    or not node.get('material_sha256') or not node.get('artifact_fingerprint')):
                raise ValueError('Whole-question scope requires original material and review payload binding')
            if question is not None:
                from .question_verification import material_fingerprint
                if node['material_sha256']!=material_fingerprint(question) or node['candidate_ids']!=sorted(question.get('options',{})):
                    raise ValueError('Whole-question scope differs from original material')
        if node['type'] in {'question_review','question_decision','question_verification'}:
            if node.get('method_id') or not node.get('candidate') or not node.get('review_id'):
                raise ValueError('Whole-question proof is not a branded method decision')
            if node['type']=='question_review':
                parents=[nodes[x] for x in incoming[nid]]
                scopes=[n for n in parents if n['type']=='question_scope' and n.get('review_id')==node['review_id']]
                if len(scopes)!=1 or node['candidate'] not in scopes[0]['candidate_ids']:
                    raise ValueError('Whole-question review requires its own complete question scope')
                if not (any(n['type']=='candidate_claim' and n.get('candidate')==node['candidate'] for n in parents)
                        and any(n['type']=='source_evidence' and n.get('span',{}).get('field')=='passage' for n in parents)
                        and any(n['type']=='source_evidence' and n.get('span',{}).get('field')=='stem' for n in parents)
                        and any(n['type']=='action_artifact' and n.get('reviewed') and
                            (n.get('artifact_kind') in {'interpretation','framework_card'} or
                             (n.get('artifact_kind')=='verification_result' and n.get('verification_scope')=='candidate_relation_check' and n.get('candidate')==node['candidate'])) for n in parents)):
                    raise ValueError('Whole-question review needs own claim, passage, task and produced interpretation')
                if node.get('effect')!='undetermined' and not node.get('reviewed'):
                    raise ValueError('Unreviewed whole-question proof cannot decide')
            else:
                required='question_review' if node['type']=='question_decision' else 'question_decision'
                parents=[nodes[x] for x in incoming[nid]]
                if (not node.get('reviewed') or node.get('effect') not in {'retain','eliminate'}
                        or len(parents)!=1 or parents[0]['type']!=required
                        or not parents[0].get('reviewed') or
                        any(parents[0].get(k)!=node.get(k) for k in ('candidate','review_id','effect'))):
                    raise ValueError('Whole-question conclusion requires its own reviewed candidate path')
        if node['type']=='image_evidence':
            if not node.get('image_ref') or not node.get('artifact_fingerprint'):
                raise ValueError('Image evidence requires original payload reference and review binding')
            if manifest is not None:
                from .image_evidence import check_image_region
                check_image_region(node['image_ref'],manifest)
        if node['type']=='source_evidence':
            if not node.get('span') or node['label'] != node['span']['quote']:
                raise ValueError('Source evidence must carry its exact quoted span')
            if question is not None:
                check_span(question,node['span'])
        if node['type']=='question_signal' and node.get('reviewed'):
            if not node.get('method_id') or not any(n['type']=='source_evidence' and n.get('span') for n in ancestors(nid)):
                raise ValueError('Reviewed trigger without its own source evidence')
        if node['type']=='action_artifact':
            upstream=ancestors(nid)
            if not node.get('reviewed') or not node.get('execution_id') or not node.get('method_id') or not node.get('artifact_fingerprint') or node.get('artifact_kind')!=node['label']:
                raise ValueError('Action artifact must identify its reviewed typed execution')
            actions=[n for n in upstream if n['type']=='method_action' and n.get('execution_id')==node['execution_id'] and n.get('method_id')==node['method_id'] and n.get('reviewed')]
            if not actions: raise ValueError('Action artifact without its own reviewed action')
            own_upstream=ancestors(actions[0]['id'])
            if not any(n['type']=='question_signal' and n.get('reviewed') and n.get('method_id')==node['method_id'] for n in own_upstream):
                raise ValueError('Action artifact without independently reviewed method trigger')
            if not any(n['type']=='source_evidence' and n.get('span') for n in own_upstream):
                raise ValueError('Action artifact without source evidence')
            if node['artifact_kind']=='candidate_decision' and (not node.get('candidate') or not any(own_candidate_relation(n,node['method_id'],node['candidate']) for n in own_upstream)):
                raise ValueError('Decision artifact without its own reviewed candidate relation')
        if node['type'] in {'decision','verification'}:
            if not node.get('method_id') or not node.get('candidate'):
                raise ValueError('Conclusion must identify method and candidate')
            upstream = ancestors(nid)
            if not any(n['type']=='source_evidence' and n.get('span') for n in upstream):
                raise ValueError('Conclusion without source evidence path')
            if not any(n['type']=='relation' and n.get('reviewed') and n.get('method_id')==node.get('method_id') for n in upstream):
                raise ValueError('Conclusion without reviewed semantic relation')
            if not any(n['type']=='question_signal' and n.get('reviewed') and n.get('method_id')==node.get('method_id') for n in upstream):
                raise ValueError('Conclusion without independently reviewed method trigger')
            if not any(n['type']=='candidate_claim' and n.get('candidate')==node.get('candidate') for n in upstream):
                raise ValueError('Conclusion without its own candidate claim')
            if not any(own_candidate_relation(n,node['method_id'],node['candidate']) for n in upstream):
                raise ValueError('Conclusion without its own candidate relation path: claim, trigger and direct source must bind the same reviewed relation')
    return graph

class EvidenceGraph:
    def __init__(self):
        self.graph = {'nodes':[],'edges':[]}
    def node(self,kind,label,**kwargs):
        nid = 'n'+str(len(self.graph['nodes'])+1)
        self.graph['nodes'].append({'id':nid,'type':kind,'label':label,**kwargs})
        return nid
    def edge(self,left,right,kind):
        self.graph['edges'].append({'from':left,'to':right,'type':kind})
    def result(self,question=None): return validate_graph(self.graph,question)
