"""Read-only adapters for existing frozen transports, never QuestionAnalyzer."""
from copy import deepcopy

from content_os.candidates import engineering_gate, matching_reviews, source_gate
from video_contracts import (sha, pointer, status_matches, verify_bundle,
                             review_semantics, REVIEW_LEVELS)
from video_contracts import passage
from .policy import CAVEAT_FIELDS


def _span_valid(question, span):
    field = span['field']
    if field.startswith('option:'):
        text = question.get('options', {}).get(field.split(':', 1)[1])
    elif field.startswith('options.'):
        text = question.get('options', {}).get(field.split('.', 1)[1])
    else:
        text = question.get(field)
    return (isinstance(text, str) and type(span['start']) is int
            and type(span['end']) is int and 0 <= span['start'] < span['end'] <= len(text)
            and text[span['start']:span['end']] == span['quote'])


class FrozenSource:
    def __init__(self, bundle, status, selection):
        self.bundle = bundle
        self.status = deepcopy(status)
        if not isinstance(selection, dict) or set(selection) != {'method_id', 'action_ids'}:
            raise ValueError('Explicit method_id and action_ids selection required')
        self.selection = deepcopy(selection)
        mid, ids = selection['method_id'], selection['action_ids']
        if not ids or len(set(ids)) != len(ids):
            raise ValueError('Unique selected actual actions required')
        if bundle.get('kind') == 'frozen_reviewed_passage':
            passage.require_current(bundle, status)
            self.transport = 'reviewed_passage'
            payload = bundle['payload']
            self.method_index = next((i for i, m in enumerate(payload['methods'])
                                      if m['method_id'] == mid), None)
            if self.method_index is None:
                raise ValueError('Selected method missing from frozen passage')
            self.method_path = '/payload/methods/' + str(self.method_index)
            self.method = payload['methods'][self.method_index]
            all_actions = payload['review']['method_actions']
            self.action_paths = ['/payload/review/method_actions/' + str(i)
                for i, a in enumerate(all_actions) if a['action_id'] in ids]
            self.actions = [pointer(bundle, p) for p in self.action_paths]
            if len(self.actions) != len(ids) or any(a['method_id'] != mid for a in self.actions):
                raise ValueError('Cross-method or dangling selected action')
            if len({a['question_id'] for a in self.actions}) != 1:
                raise ValueError('One method application must bind one actual question')
            qid = self.actions[0]['question_id']
            self.question_index = next(i for i, q in enumerate(payload['questions']) if q['question_id'] == qid)
            self.question_path = '/payload/questions/' + str(self.question_index)
            self.question = {**deepcopy(payload['questions'][self.question_index]), 'passage': payload['passage']}
            self.review_paths = ['/payload/review']
            self.review_records = [payload['review']]
            self.review_level = bundle['semantic_review']['level']
            own_decisions = [d for d in payload['review']['decisions'] if d['question_id'] == qid]
            self.upstream_answer = next(d['candidate'] for d in own_decisions if d['effect'] == 'retain')
            self.upstream_closed = True
            self.analysis_sha = sha(review_semantics(payload['review']))
            self.source = payload['source']
            self.stop_key = 'stop_rule'
            self.action_key = 'output'
        else:
            verify_bundle(bundle)
            if status is None or not status_matches(bundle, status):
                raise ValueError('Current ACTIVE upstream status source required')
            if status['method_versions'].get(mid) != bundle['binding_fingerprint']['method_versions'].get(mid):
                raise ValueError('Current method version differs from the selected frozen version')
            if source_gate([bundle])['internal_use'] != 'PASS':
                raise ValueError('Source does not allow internal production')
            self.transport = 'frozen_asset'
            sel = {'asset_id': bundle['asset_id'], **selection}
            gate = engineering_gate(bundle, sel, 'method_action_demo', status)
            if gate['status'] != 'PASS':
                raise ValueError('Frozen teaching engineering gate failed: ' + ', '.join(gate['blockers']))
            self.method_index = next(i for i, m in enumerate(bundle['methods']) if m['method_id'] == mid)
            self.method_path = '/methods/' + str(self.method_index)
            self.method = bundle['methods'][self.method_index]
            self.action_paths = ['/analysis/execution_trace/' + str(i)
                for i, a in enumerate(bundle['analysis']['execution_trace']) if a['execution_id'] in ids]
            self.actions = [pointer(bundle, p) for p in self.action_paths]
            if any(a['state'] != 'produced' or a['review_status'] != 'reviewed'
                   or a.get('stop_applied') or not a.get('output') for a in self.actions):
                raise ValueError('Selected actual action is stopped or not produced/reviewed')
            own_reviews = matching_reviews(bundle, sel)
            self.review_paths = ['/reviews/' + str(i) for i, _ in own_reviews]
            self.review_records = [r['record'] for _, r in own_reviews]
            self.review_level = max((r['level'] for _, r in own_reviews), key=REVIEW_LEVELS.index)
            current_actions = {x['artifact_id'] for x in status['lifecycle']['actions'] if x['status'] == 'active'}
            current_reviews = {x['artifact_id'] for x in status['lifecycle']['reviews'] if x['status'] == 'active'}
            if not set(ids) <= current_actions or any(r['artifact_id'] not in current_reviews for _, r in own_reviews):
                raise ValueError('Current status withdraws a selected action or Review dependency')
            self.question_path = '/source_snapshot'
            self.question = bundle['source_snapshot']
            self.upstream_answer = bundle['analysis']['answer']
            self.upstream_closed = bundle['analysis']['answer_verification']['closed']
            self.analysis_sha = bundle['binding_fingerprint']['analysis_sha']
            self.source = bundle['source']
            self.stop_key = 'stop_rule_check'
            self.action_key = 'concrete_action'
        if any(a['method_version'] != self.method['version']
               or a['role'] != self.method['primary_role'] for a in self.actions):
            raise ValueError('Selected action role or version changed')
        if not self.method.get('stop_rule') or any(not a.get(self.stop_key) for a in self.actions):
            raise ValueError('Method and current action Stop must be preserved')
        if any(not a.get('evidence') or not all(_span_valid(self.question, s) for s in a['evidence'])
               for a in self.actions):
            raise ValueError('Selected evidence does not exactly match frozen question')
        self.evidence_paths = [p + '/evidence/' + str(i)
                               for p, a in zip(self.action_paths, self.actions)
                               for i, _ in enumerate(a['evidence'])]

    def ref(self, path):
        try:
            value = pointer(self.bundle, path)
        except (KeyError, IndexError, ValueError, TypeError) as error:
            raise ValueError('Dangling frozen source pointer: ' + path) from error
        return {'asset_id': self.bundle['asset_id'], 'pointer': path,
                'sha': sha(review_semantics(value))}

    def field_path(self, candidates):
        for suffix in candidates:
            path = self.method_path + suffix
            try:
                value = pointer(self.bundle, path)
            except (KeyError, IndexError, ValueError, TypeError):
                continue
            if isinstance(value, str) and value.strip():
                return path
        return None

    def caveat_paths(self):
        """Enumerate frozen semantic caveats, without inventing relevance/risk.

        The supported fields are existing text assertions or ordered arrays of
        text assertions. A structured/empty malformed assertion fails closed;
        it must not disappear inside the undifferentiated backend guard.
        """
        result = []
        for field in CAVEAT_FIELDS:
            if field not in self.method:
                continue
            value = self.method[field]
            path = self.method_path + '/' + field
            if isinstance(value, str) and value.strip():
                result.append(path)
            elif isinstance(value, list) and all(isinstance(v, str) and v.strip() for v in value):
                result += [path + '/' + str(i) for i in range(len(value))]
            else:
                raise ValueError('Frozen caveat needs existing nonempty text assertions: ' + path)
        card = self.method.get('four_step_card')
        if isinstance(card, dict) and 'stop' in card:
            if not isinstance(card['stop'], str) or not card['stop'].strip():
                raise ValueError('Frozen four-step Stop needs an existing text assertion')
            result.append(self.method_path + '/four_step_card/stop')
        for review_path, record in zip(self.review_paths, self.review_records):
            claims = record.get('reviewed_claims', {})
            if isinstance(claims, dict) and 'boundary' in claims:
                value = claims['boundary']
                if not isinstance(value, str) or not value.strip():
                    raise ValueError('Reviewed boundary needs an existing text assertion')
                prefix = review_path + ('/record' if self.transport == 'frozen_asset' else '')
                result.append(prefix + '/reviewed_claims/boundary')
        return result

    def cases(self):
        """Case content must exist in the own frozen Review, not just its label.

        The question, actual actions and evidence remain those of this selected
        frozen application. These assertions do not create another question or
        prove that a learner has completed transfer. Conflicting active content
        cannot be resolved by silently picking the last Review.
        """
        result = {}
        for path, record in zip(self.review_paths, self.review_records):
            prefix = path + ('/record' if self.transport == 'frozen_asset' else '')
            claims = record.get('reviewed_claims', {})
            if not isinstance(claims, dict):
                raise ValueError('Frozen reviewed case content must be a claims object')
            for key in ('canonical', 'counterexample', 'boundary', 'transfer', 'hard', 'hard_case'):
                if key not in claims:
                    continue
                value = claims[key]
                if not isinstance(value, str) or not value.strip():
                    raise ValueError('Frozen reviewed case content needs an existing nonempty assertion: ' + key)
                kind = 'hard' if key == 'hard_case' else key
                ref = self.ref(prefix + '/reviewed_claims/' + key)
                if kind in result:
                    previous = pointer(self.bundle, result[kind]['pointer'])
                    if previous != value:
                        raise ValueError('Conflicting frozen reviewed case content: ' + kind)
                else:
                    result[kind] = ref
        return result

    def risk(self, item_path):
        """No downstream free-form risk labels can hide upstream caveats."""
        for path, record in zip(self.review_paths, self.review_records):
            prefix = path + ('/record' if self.transport == 'frozen_asset' else '')
            for i, annotation in enumerate(record.get('pedagogy_risk_annotations', [])):
                if annotation.get('source_pointer') == item_path:
                    if annotation.get('item_sha') != sha(pointer(self.bundle, item_path)):
                        raise ValueError('Disclosure risk assessment targets a different caveat')
                    risk = annotation.get('risk')
                    if not isinstance(annotation.get('rationale'), str) or not annotation['rationale'].strip():
                        raise ValueError('Explicit risk assessment rationale required')
                    return deepcopy(risk), [self.ref(prefix + '/pedagogy_risk_annotations/' + str(i))]
        return {'frequency': 'unknown', 'severity': 'unknown', 'current_relevance': 'unknown'}, []

    def guard(self):
        return {'method_ref': self.ref(self.method_path),
                'action_refs': [self.ref(p) for p in self.action_paths],
                'evidence_refs': [self.ref(p) for p in self.evidence_paths],
                'review_refs': [self.ref(p) for p in self.review_paths],
                'method_stop_ref': self.ref(self.method_path + '/stop_rule'),
                'action_stop_refs': [self.ref(p + '/' + self.stop_key) for p in self.action_paths],
                'upstream_answer': deepcopy(self.upstream_answer),
                'upstream_closed': self.upstream_closed,
                'method_maturity': self.method.get('status', self.method.get('maturity', 'unknown')),
                'method_utility': self.method.get('utility_level', self.method.get('value_level', 'unknown'))}

    def payoff_support(self):
        """Prefer explicit credentials, otherwise project a frozen local decision.

        A mechanical candidate-state baseline is not a measured learner path.
        Partitions, unknown decision ordering and later work cannot create it.
        """
        for path, record in zip(self.review_paths, self.review_records):
            support = record.get('reviewed_payoff')
            if support is None:
                continue
            if not isinstance(support, dict):
                raise ValueError('Existing reviewed payoff must be structured')
            scope = support.get('scope', {})
            if (scope.get('question_id') != self.question['question_id']
                    or scope.get('method_id') != self.selection['method_id']
                    or scope.get('method_version') != self.method['version']
                    or set(scope.get('action_ids', [])) != set(self.selection['action_ids'])):
                raise ValueError('Reviewed payoff belongs to another question/action/method')
            evidence = support.get('evidence_pointers', [])
            if not evidence or not set(evidence) <= set(self.evidence_paths):
                raise ValueError('Reviewed payoff needs this action\'s own existing evidence')
            prefix = path + ('/record' if self.transport == 'frozen_asset' else '')
            measured = support.get('baseline_measured', False)
            return {'record': deepcopy(support),
                    'origin': 'explicit_reviewed_payoff', 'baseline_kind': 'reviewed_path',
                    'baseline_measured': measured if isinstance(measured, bool) else False,
                    'source_refs': [self.ref(prefix + '/reviewed_payoff')],
                    'action_artifact_refs': [self.ref(p) for p in self.action_paths],
                    'evidence_refs': [self.ref(p) for p in evidence],
                    'review_refs': [self.ref(p) for p in self.review_paths]}
        from .mechanical_payoff import frozen_candidate_transition
        return frozen_candidate_transition(self.bundle, self.status, self.selection)
