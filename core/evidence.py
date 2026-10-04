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

def validate_graph(graph):
    validate_schema('evidence-graph',graph)
    nodes = {n['id']:n for n in graph['nodes']}
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
    for nid, node in nodes.items():
        if node['type'] in {'decision','verification'}:
            upstream = ancestors(nid)
            if not any(n['type']=='source_evidence' and n.get('span') for n in upstream):
                raise ValueError('Conclusion without source evidence path')
            if not any(n['type']=='relation' and n.get('reviewed') for n in upstream):
                raise ValueError('Conclusion without reviewed semantic relation')
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
    def result(self): return validate_graph(self.graph)
