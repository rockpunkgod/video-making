from pathlib import Path
import hashlib
import json
import yaml
from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[1]

def load(path):
    return yaml.safe_load((ROOT/path).read_text(encoding='utf-8'))

def validate_schema(name, value):
    schema = json.loads((ROOT/'schemas'/f'{name}.json').read_text(encoding='utf-8'))
    Draft202012Validator.check_schema(schema)
    Draft202012Validator(schema).validate(value)

class Registry:
    def __init__(self):
        self.index = load('method-registry/registry.yaml')
        self.sources = load(self.index['source_sections'])
        self.risks = load('method-registry/source-risks.yaml')['risks']
        self.symptom_cues = load('method-registry/symptom-cues.yaml')['routes']
        self.grammar_tree = load('method-registry/grammar-tree.yaml')
        self.methods = {}
        for path in self.index['method_files']:
            for method in load(path)['methods']:
                mid = method['method_id']
                if mid in self.methods:
                    raise ValueError('Duplicate method id: '+mid)
                self.methods[mid] = method

    def full(self, mid):
        warnings = ['源资料审阅提醒：'+x['action'] for x in self.risks if mid in x['affected_methods']]
        return '\n'.join(warnings+[self.sources['sections'][sid]['content'] for sid in self.methods[mid]['section_ids']])

    def document(self, path):
        doc = next(d for d in self.sources['documents'] if d['path']==path)
        return ''.join(self.sources['sections'][sid]['content'] for sid in doc['sections'])

    def validate(self):
        risk_ids=set()
        for risk in self.risks:
            if risk['risk_id'] in risk_ids: raise ValueError('Duplicate source risk')
            risk_ids.add(risk['risk_id'])
            if not risk['affected_methods'] or any(mid not in self.methods for mid in risk['affected_methods']):
                raise ValueError('Invalid risk method dependency')
            if 'section_id' in risk:
                sid=risk['section_id']
                if sid not in self.sources['sections'] or not risk.get('source_quote') or risk['source_quote'] not in self.sources['sections'][sid]['content']:
                    raise ValueError('Source risk quote mismatch')
            elif not any(d['path']==risk.get('source_path') for d in self.sources['documents']):
                raise ValueError('Missing risk source document')
        tree=self.grammar_tree; nodes=tree['nodes']; visited=set()
        def check_node(nid,ancestors):
            if nid not in nodes: raise ValueError('Unknown grammar tree node')
            if nid in ancestors: raise ValueError('Circular grammar tree')
            visited.add(nid)
            for mid in nodes[nid]['methods']:
                if mid not in self.methods or self.methods[mid]['question_type']!='语法填空': raise ValueError('Invalid grammar method dependency')
            for child in nodes[nid]['children']: check_node(child,ancestors|{nid})
        check_node(tree['root'],set())
        if visited!=set(nodes): raise ValueError('Unreachable grammar tree node')
        covered={mid for n in nodes.values() for mid in n['methods']}|set(tree['preparatory_methods'])|set(tree['postcheck_methods'])
        if covered!={mid for mid,m in self.methods.items() if m['question_type']=='语法填空'}: raise ValueError('Grammar dependency coverage gap')
        for sid in tree['source_sections']:
            if sid not in self.sources['sections']: raise ValueError('Missing grammar tree source')
        cue_ids=set()
        for route in self.symptom_cues:
            if set(route) != {'method_id','phrases'} or route['method_id'] not in self.methods:
                raise ValueError('Invalid symptom route')
            if route['method_id'] in cue_ids or not isinstance(route['phrases'],list) or not route['phrases'] or any(not isinstance(p,str) or not p.strip() for p in route['phrases']):
                raise ValueError('Invalid or duplicated symptom cue')
            cue_ids.add(route['method_id'])
        for mid, m in self.methods.items():
            validate_schema('method-card',m)
            if m.get('student_ready'):
                if not m.get('entry_copy') or not m['counterexamples']:
                    raise ValueError('Student entry lacks first-use copy or boundary: '+mid)
                copies=[m['decision_rule'],m['stop_rule'],*m['compact'].values(),*m['four_step_card'].values()]
                placeholders=['逐条核源章节判据','具体边界见源章节','完整规则必须读取对应源章节']
                if any(marker in text for text in copies for marker in placeholders):
                    raise ValueError('Student-ready copy still delegates concrete action to source: '+mid)
            if m.get('static_design_review') and m['static_design_review']['source_section_ids']!=m['section_ids']:
                raise ValueError('Editorial review source mismatch: '+mid)
            if m['role'] != m['primary_role'] or m['status'] != m['maturity_status'] or m['practical_value'] != m['usefulness_level']:
                raise ValueError('Legacy alias mismatch: '+mid)
            if m['primary_role'] in {'locator','reducer'} and m['output_type']=='decide':
                raise ValueError('method_overreach: '+mid)
            if self.index['methods'][mid]['version'] != m['version']:
                raise ValueError('Version index mismatch')
            for sid in m['section_ids']:
                s = self.sources['sections'][sid]
                p = ROOT/'provenance/ANSWER'/s['path']
                original = p.read_text(encoding='utf-8').splitlines(keepends=True)
                if ''.join(original[s['line_start']-1:s['line_end']]) != s['content']:
                    raise ValueError('Source drift: '+sid)
            for ref in m['source_references']:
                if ref['commit'] != self.index['source_baseline']['commit']:
                    raise ValueError('Source version mismatch')
                if not (ROOT/'provenance/ANSWER'/ref['path']).is_file():
                    raise ValueError('Unresolved source path: '+ref['path'])
            for path in m['cases'].values():
                case = load(path)
                validate_schema('case',case)
                if case['method_id'] != mid or case['method_role'] != m['primary_role']:
                    raise ValueError('Case mismatch: '+path)
                if case['status']=='verified_course_example' and not case['question']:
                    raise ValueError('Verified case without question')
            if m['maturity_status'] in {'validated','stable'} or m['practical_value'] != 'Useful':
                # Mechanical validation cannot authenticate people or validate teaching semantics.
                raise ValueError('Human promotion requires separately reviewed release artifact: '+mid)
        for item in load('provenance/manifest.yaml')['files']:
            if hashlib.sha256((ROOT/'provenance/ANSWER'/item['path']).read_bytes()).hexdigest() != item['sha256']:
                raise ValueError('Frozen snapshot changed')
        for d in self.sources['documents']:
            content = self.document(d['path'])
            original = (ROOT/'provenance/ANSWER'/d['path']).read_text(encoding='utf-8')
            if content != original:
                raise ValueError('Document coverage gap')
        return {'methods':len(self.methods),'source_documents':len(self.sources['documents']),'status':'PASS'}
