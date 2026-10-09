from pathlib import Path
import hashlib
import json
import yaml
from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[1]
CASE_TYPES = ('canonical','counterexample','boundary','transfer','hard')
PRIMARY_OUTPUTS = {'locator':{'locate'},'interpreter':{'interpret'},'reducer':{'reduce'},'decider':{'decide'},'verifier':{'verify'},'framework':{'interpret','reduce'}}

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

    def case_inventory(self):
        """Bind the case index, method slots and actual case identities once."""
        indexed=load('cases/registry.yaml')['case_files']
        if not isinstance(indexed,list) or any(not isinstance(p,str) or not p.strip() for p in indexed) or len(indexed)!=len(set(indexed)):
            raise ValueError('Duplicate or invalid case index')
        records={}; ids=set()
        for mid,m in self.methods.items():
            if set(m['cases'])-set(CASE_TYPES): raise ValueError('Unknown case type slot: '+mid)
            for kind,path in m['cases'].items():
                if path in records: raise ValueError('Case path reused by method slots: '+path)
                try: case=load(path)
                except OSError as exc: raise ValueError('Missing or unreadable case: '+path) from exc
                validate_schema('case',case)
                if case['status']=='reviewed_real_exam_case':
                    raise ValueError('Private real exam Case cannot enter public case inventory')
                if case['case_id'] in ids: raise ValueError('Duplicate case ID: '+case['case_id'])
                ids.add(case['case_id'])
                if (case['method_id'],case['case_type'],case['question_type'],case['method_role'],case['expected_output'])!=(mid,kind,m['question_type'],m['primary_role'],m['output_type']):
                    raise ValueError('Case slot identity/type/role/output mismatch: '+path)
                if case['status']=='verified_course_example' and not case['question']:
                    raise ValueError('Verified case without question')
                records[path]=case
        if set(indexed)!=set(records):
            raise ValueError('Case index and method slots disagree')
        return records

    def case_coverage(self, private_catalog=None):
        """Report missing slots as gaps, never manufacture case records."""
        records=self.case_inventory(); methods=[]
        for mid,m in self.methods.items():
            slots=[]
            for kind in CASE_TYPES:
                path=m['cases'].get(kind); case=records.get(path)
                slots.append({'case_type':kind,'registration':'registered' if case else 'unregistered',
                              'evidence_status':case['status'] if case else 'evidence_gap',
                              'path':path,'case_id':case['case_id'] if case else None,
                              'reason':case['notes'] if case else '没有已登记、可合法使用并核验的该类题目；登记缺口不计作案例或通过。'})
            methods.append({'method_id':mid,'method_version':m['version'],'question_type':m['question_type'],
                            'method_type':m['method_type'],'core_required':m['method_type'] in {'method','framework'},
                            'source_section_ids':list(m['section_ids']),'slots':slots,
                            'registration_complete':all(s['registration']=='registered' for s in slots),
                            'registered_examples_complete':all(s['registration']=='registered' and s['evidence_status']=='verified_course_example' for s in slots)})
        core=[m for m in methods if m['core_required']]
        formal=[m for m in methods if m['method_type']=='method']
        missing=lambda subset:sum(s['registration']=='unregistered' for m in subset for s in m['slots'])
        result={'scope':'registration and recorded provenance status only; no full-question, semantic or learner validation certification',
                'required_case_types':list(CASE_TYPES),'method_count':len(methods),'registered_case_count':len(records),
                'unregistered_slot_count':missing(methods),'core_method_count':len(core),'core_unregistered_slot_count':missing(core),
                'formal_method_count':len(formal),'formal_unregistered_slot_count':missing(formal),
                'formal_methods_with_missing_slots':sum(not m['registration_complete'] for m in formal),
                'registration_complete':all(m['registration_complete'] for m in core),'methods':methods}
        if private_catalog is not None:
            from .real_cases import coverage_overlay
            return coverage_overlay(result,private_catalog)
        return result

    def validate(self):
        self.case_inventory()
        releases=self.index.get('release_reviews',{})
        if not isinstance(releases,dict) or any(mid not in self.methods or not isinstance(path,str) or not path.strip() for mid,path in releases.items()):
            raise ValueError('Invalid human release review index')
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
            if m['output_type'] not in PRIMARY_OUTPUTS[m['primary_role']]:
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
            if m['maturity_status'] in {'validated','stable'} or m['practical_value'] != 'Useful':
                from .release import check_release,read_json
                if not releases.get(mid):
                    raise ValueError('Human promotion requires separately reviewed release artifact: '+mid)
                review=read_json(releases[mid])
                if review.get('method_id')!=mid: raise ValueError('Human release review method mismatch: '+mid)
                audit=check_release(self,review,applied=True)
                if not audit['ready_for_manual_release']:
                    raise ValueError('Human release review blocked for '+mid+': '+', '.join(audit['blocking_reasons']))
        for item in load('provenance/manifest.yaml')['files']:
            if hashlib.sha256((ROOT/'provenance/ANSWER'/item['path']).read_bytes()).hexdigest() != item['sha256']:
                raise ValueError('Frozen snapshot changed')
        for d in self.sources['documents']:
            content = self.document(d['path'])
            original = (ROOT/'provenance/ANSWER'/d['path']).read_text(encoding='utf-8')
            if content != original:
                raise ValueError('Document coverage gap')
        return {'methods':len(self.methods),'source_documents':len(self.sources['documents']),'status':'PASS'}
