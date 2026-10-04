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
        for mid, m in self.methods.items():
            validate_schema('method-card',m)
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
