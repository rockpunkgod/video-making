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
