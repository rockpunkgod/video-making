"""Synthetic engineering controls; never real learner/semantic validation."""
from copy import deepcopy
import ast
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from core.registry import Registry
from core.analyzer import QuestionAnalyzer
from core.review_withdrawal import withdraw_review
from tests.test_execution import fixture
from answer_engine.frozen_export import FrozenAssetExporter, load_request
from video_contracts import ROOT, sha, seal, write, verify_bundle
from content_os.candidates import make_candidate
from content_os.scoring import score, rate, rank, DIMENSIONS, FEASIBILITY
from content_os.director import build_draft, finalize_copy, copy_payload, claim_guard
from content_os.polisher import IdentityPolisher, polish
from content_os.release import validate_package, ae_contract, apply_reviews, publication_check, display_payload
from content_os.lifecycle import refresh, refresh_catalog


def ratings(dimensions=DIMENSIONS):
    return {k: {'value': 8, 'status': 'known', 'rationale': 'Synthetic editor input', 'evidence': ['synthetic:observation']}
            for k in dimensions}


class VideoOSTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.registry = Registry()
        cls.engine = QuestionAnalyzer(cls.registry)
        q = fixture(); a = cls.engine.analyze(q)
        cls.base = {'question': q, 'analysis': a, 'methods': [deepcopy(cls.registry.methods[mid]) for mid in a['method_versions']],
            'reviews': [{'question_id': q['question_id'], 'input_sha256': sha(q), 'analysis_sha256': sha(a),
                         'reviewer_kind': 'AI', 'reviewer': 'SYNTHETIC ONLY', 'evaluation_phase': 'post_reveal'}],
            'withdrawals': [], 'evaluation_phase': 'post_reveal',
            'source': {'usage_status': 'internal_only', 'redistribution_status': 'redistribution_not_verified',
                       'source_reference': 'synthetic-program-fixture', 'attribution_text': 'SYNTHETIC'}}

    def setUp(self):
        self.req = deepcopy(self.base)
        self.exporter = FrozenAssetExporter()

    def assets(self):
        b = self.exporter.export(self.req)
        st = self.exporter.status(self.req)
        return b, {b['asset_id']: st}

    def candidate(self):
        b, statuses = self.assets()
        c = make_candidate([b], [{'asset_id': b['asset_id'], 'method_id': 'R12', 'action_ids': ['loc']}], statuses)
        return c, statuses

    def package(self):
        c, statuses = self.candidate()
        p = finalize_copy(polish(build_draft(c, statuses), IdentityPolisher()))
        return p, statuses

    def finding(self):
        return {'question_id': self.req['question']['question_id'], 'input_sha256': sha(self.req['question']),
            'analysis_sha256': sha(self.req['analysis']), 'review_stage': 'post_reveal',
            'reviewer': 'SYNTHETIC CONTROL', 'reviewer_kind': 'AI', 'reason': 'Synthetic invalidation',
            'withdrawn_relation_indexes': [], 'withdrawn_execution_ids': ['loc'], 'failure_categories': ['semantic_review_problem']}

    def test_canonical_hash_order_missing_null_arrays_newlines(self):
        self.assertEqual(sha({'a': 1, 'b': '中'}), sha({'b': '中', 'a': 1}))
        self.assertNotEqual(sha({}), sha({'a': None}))
        self.assertNotEqual(sha([1, 2]), sha([2, 1]))
        self.assertNotEqual(sha('a\nb'), sha('a\r\nb'))

    def test_repeat_export_semantics_stable_timestamp_distinct(self):
        a = self.exporter.export(self.req, 'one'); b = self.exporter.export(self.req, 'two')
        self.assertEqual(a['semantic_binding_sha'], b['semantic_binding_sha'])
        self.assertEqual(a['content_sha'], b['content_sha'])
        self.assertNotEqual(a['envelope_sha'], b['envelope_sha'])

    def test_review_diagnostic_timestamp_not_semantic(self):
        a = self.exporter.export(self.req)
        self.req['reviews'][0]['generated_at'] = 'new diagnostic time'
        self.req['reviews'][0]['provenance'] = {'path': 'moved'}
        b = self.exporter.export(self.req)
        self.assertEqual(a['semantic_binding_sha'], b['semantic_binding_sha'])

    def test_export_readonly_and_never_calls_analyzer(self):
        before = deepcopy(self.req)
        with patch.object(QuestionAnalyzer, 'analyze', side_effect=AssertionError('must not solve')):
            self.exporter.export(self.req)
        self.assertEqual(self.req, before)

    def test_current_epoch_status_supersedes_without_rewriting_frozen_input(self):
        before=deepcopy(self.req)
        current=Registry()
        current.methods['R12']['version']='99.0.0'  # synthetic future version only
        current.index['methods']['R12']['version']='99.0.0'
        with patch.object(QuestionAnalyzer,'analyze',side_effect=AssertionError('must not re-solve')):
            status=self.exporter.status_current_epoch(self.req,current)
        self.assertEqual(status['effective_status'],'SUPERSEDED')
        self.assertEqual(self.req,before)
        self.assertEqual(status['method_versions']['R12'],before['analysis']['method_versions']['R12'])
        bundle=self.exporter.export(self.req)
        candidate=make_candidate([bundle],[{'asset_id':bundle['asset_id'],'method_id':'R12','action_ids':['loc']}],
                                 {bundle['asset_id']:self.exporter.status(self.req)})
        updated=refresh(candidate,{bundle['asset_id']:status})
        self.assertTrue(updated['invalidation']['teaching_stale'])
        self.assertTrue(updated['invalidation']['editorial_stale'])
        self.assertFalse(updated['engineering_pilot_eligible'])

    def test_archived_registry_cannot_claim_current_epoch(self):
        history=Registry(snapshot_commit='b04ebc26d7fa096404111a0bb12f6c77cc8525b9')
        with self.assertRaisesRegex(ValueError,'Historical replay'):
            self.exporter.status_current_epoch(self.req,history)

    def test_same_version_cannot_hide_changed_teaching_facts(self):
        current=Registry(); current.methods['R12']['core_action']='Synthetic changed facts only'
        current.methods['R12']['full']['summary']=current.methods['R12']['core_action']+' '+current.methods['R12']['decision_rule']
        status=self.exporter.status_current_epoch(self.req,current)
        self.assertEqual(status['effective_status'],'SUPERSEDED')
        self.assertTrue(any('teaching facts differ' in reason for reason in status['invalidation_reasons']))

    def test_same_version_student_task_or_visual_change_invalidates_current_export(self):
        for key in ('challenge_prompt','visual_formula','entry_copy'):
            with self.subTest(key=key):
                current=Registry()
                current.methods[self.req['methods'][0]['method_id']][key]='changed student instruction'
                status=self.exporter.status_current_epoch(self.req,current)
                self.assertEqual(status['effective_status'],'SUPERSEDED')
        self.assertTrue(any('teaching facts differ' in reason for reason in status['invalidation_reasons']))

    def test_ai_not_human(self):
        b, _ = self.assets()
        self.assertEqual(b['semantic_review']['level'], 'ai_reviewed')
        self.assertFalse(b['semantic_review']['independent_human_certified'])

    def test_wrong_exact_review_binding_rejected(self):
        self.req['reviews'][0]['analysis_sha256'] = '0' * 64
        with self.assertRaises(ValueError): self.exporter.export(self.req)

    def test_blind_cannot_read_post_reveal_or_answer(self):
        self.req['evaluation_phase'] = 'blind'
        with self.assertRaises(ValueError): self.exporter.export(self.req)
        self.req['reviews'][0]['evaluation_phase'] = 'blind'
        with self.assertRaises(ValueError): self.exporter.export(self.req)

    def test_history_cannot_leak_later_review_into_blind_or_host_review(self):
        q = fixture(); q['relations'] = []; q['requested_chain'] = ['R12']
        q['observations'] = [q['observations'][0]]; q['action_executions'] = [q['action_executions'][0]]
        a = self.engine.analyze(q)
        self.req.update(question=q, analysis=a, methods=[self.registry.methods[m] for m in a['method_versions']])
        self.req['reviews'][0].update(input_sha256=sha(q), analysis_sha256=sha(a))
        later = self.exporter.export(self.req)
        for phase in ('blind', 'host_review'):
            with self.subTest(phase=phase):
                self.req['evaluation_phase'] = phase
                self.req['reviews'][0]['evaluation_phase'] = phase
                self.req.pop('history', None)
                self.exporter.export(self.req)  # Earlier unclosed snapshot itself is legitimate.
                self.req['history'] = [later]
                with self.assertRaisesRegex(ValueError, 'Historical artifact crosses'):
                    self.exporter.export(self.req)

    def test_resealed_review_summary_cannot_promote_ai_to_human(self):
        b, _ = self.assets()
        b['semantic_review'].update(level='human_certified', independent_human_certified=True, reviewer_type='human')
        b = seal(b)
        with self.assertRaisesRegex(ValueError, 'summary'):
            verify_bundle(b)

    def test_resealed_presentation_or_fingerprint_disagreement_rejected(self):
        b, _ = self.assets()
        for field in ('presentation_sha', 'binding_fingerprint'):
            altered = deepcopy(b)
            if field == 'presentation_sha': altered[field] = '0' * 64
            else: altered[field]['analysis_sha'] = '0' * 64
            altered = seal(altered)
            with self.subTest(field=field), self.assertRaises(ValueError): verify_bundle(altered)
    def test_withdrawal_transitive_and_historical_record_retained(self):
        upstream = withdraw_review(self.req['question'], self.req['analysis'], self.finding(), self.engine)
        self.req['withdrawals'] = [upstream]
        b, _ = self.assets()
        self.assertEqual(b['state']['effective_status'], 'WITHDRAWN')
        self.assertTrue(all(x['status'] == 'blocked' for x in b['lifecycle']['actions']))
        self.assertTrue(all(x['cause']['withdrawal_sha'] for x in b['lifecycle']['actions']))
        self.assertEqual(b['lifecycle']['reviews'][0]['status'], 'withdrawn')
        self.assertEqual(b['analysis'], self.req['analysis'])  # Historical truth retained, not rewritten.

    def test_history_retains_withdrawn_review_next_to_new_review(self):
        self.req['withdrawals'] = [self.finding()]
        old = self.exporter.export(self.req)
        self.req['withdrawals'] = []; self.req['history'] = [old]
        self.req['reviews'][0]['reviewer'] = 'NEW SYNTHETIC REVIEW'
        b = self.exporter.export(self.req)
        self.assertEqual(b['history'][0]['lifecycle']['reviews'][0]['status'], 'withdrawn')
        self.assertEqual(b['lifecycle']['reviews'][0]['status'], 'active')

    def test_method_upgrade_supersedes_historical_asset(self):
        self.req['current'] = {'method_versions': {'R12': '99.0.0'}}
        self.assertEqual(self.exporter.export(self.req)['state']['effective_status'], 'SUPERSEDED')

    def test_metadata_path_change_not_teaching_stale(self):
        p, _ = self.package()
        self.req['provenance'] = {'path': 'moved/to/another/location'}
        self.req['methods'][0]['change_reason'] = 'Typo in diagnostic description'
        b, statuses = self.assets()
        self.assertFalse(refresh(p, statuses)['invalidation']['teaching_stale'])

    def test_rights_change_only_invalidates_source(self):
        p, _ = self.package()
        self.req['source']['redistribution_status'] = 'withdrawn'
        _, statuses = self.assets()
        inv = refresh(p, statuses)['invalidation']
        self.assertFalse(inv['teaching_stale']); self.assertTrue(inv['source_release_stale'])

    def test_presentation_change_only_invalidates_editorial(self):
        p, _ = self.package()
        self.req['methods'][0]['brand_name'] += ' corrected display name'
        _, statuses = self.assets()
        inv = refresh(p, statuses)['invalidation']
        self.assertFalse(inv['teaching_stale']); self.assertTrue(inv['editorial_stale'])

    def test_stop_change_stales_teaching(self):
        p, statuses = self.package()
        self.req['methods'][0]['stop_rule'] += ' extra boundary'
        # An unmatched edited method is rejected, never silently reinterpreted.
        with self.assertRaises(ValueError): self.exporter.export(self.req)
        st = next(iter(statuses.values()))
        st['semantic_binding_sha'] = 'a' * 64
        statuses[st['asset_id']] = seal(st)
        self.assertTrue(refresh(p, statuses)['invalidation']['teaching_stale'])

    def test_unknown_not_zero_and_scores_have_evidence(self):
        r = ratings(); r['TS'] = {'value': None, 'status': 'unknown', 'rationale': 'Radar absent'}
        scored = score(r)
        self.assertEqual(scored['raw_score'], 8); self.assertEqual(scored['known_dimension_count'], 6)
        r['HP'].pop('evidence')
        with self.assertRaises(ValueError): score(r)

    def test_rank_does_not_accept_inflated_totals_or_false_gate_flags(self):
        c, _ = self.candidate(); c = rate(c, ratings(), ratings(FEASIBILITY))
        c['content_score']['raw_score'] = 10
        with self.assertRaises(ValueError): rank([c])
        c['content_score']['raw_score'] = 8
        c['selections'][0]['action_ids'] = ['nonexistent']
        self.assertEqual(rank([c])['rows'][0]['engineering_priority'], 'HOLD')

    def test_empty_boundary_credential_cannot_pass_scope_gate(self):
        self.req['reviews'][0]['reviewed_claims'] = {'boundary': None}
        b, statuses = self.assets()
        selections = [{'asset_id': b['asset_id'], 'method_id': 'R12', 'action_ids': ['loc']}]
        self.assertFalse(make_candidate([b], selections, statuses, 'boundary_demo')['engineering_pilot_eligible'])

    def test_all_unknown_returns_null(self):
        self.assertIsNone(score({k: {'value': None, 'status': 'unknown', 'rationale': 'Unknown'} for k in DIMENSIONS})['raw_score'])

    def test_engineering_p0_public_hold_portfolio_separate(self):
        c, _ = self.candidate(); r = rank([rate(c, ratings(), ratings(FEASIBILITY))])
        self.assertEqual(r['rows'][0]['engineering_priority'], 'P0')
        self.assertEqual(r['rows'][0]['public_priority'], 'HOLD')
        self.assertEqual(r['rows'][0]['raw_rank'], r['rows'][0]['portfolio_rank'])
        self.assertEqual(r['ranking_policy']['status'], 'provisional')

    def test_unreviewed_cannot_score(self):
        self.req['reviews'] = []
        c, _ = self.candidate()
        self.assertFalse(c['engineering_pilot_eligible'])
        with self.assertRaises(ValueError): rate(c, ratings(), ratings(FEASIBILITY))

    def test_wrong_method_action_cannot_pass_gate(self):
        b, statuses = self.assets()
        c = make_candidate([b], [{'asset_id': b['asset_id'], 'method_id': 'R01', 'action_ids': ['loc']}], statuses)
        self.assertFalse(c['engineering_pilot_eligible'])

    def test_review_for_one_method_cannot_support_another(self):
        self.req['reviews'][0]['method_id'] = 'R01'
        c, _ = self.candidate()
        self.assertFalse(c['engineering_pilot_eligible'])
        self.assertEqual(c['semantic_review']['level'], 'unreviewed')

    def test_multi_method_claims_bind_only_their_own_review(self):
        one = self.req['reviews'][0]
        one['method_id'] = 'R12'
        two = deepcopy(one); two['method_id'] = 'R11'; two['reviewer'] = 'SECOND SYNTHETIC REVIEW'
        self.req['reviews'].append(two)
        b, statuses = self.assets()
        selections = [{'asset_id': b['asset_id'], 'method_id': 'R12', 'action_ids': ['loc']},
                      {'asset_id': b['asset_id'], 'method_id': 'R11', 'action_ids': ['meaning']}]
        c = make_candidate([b], selections, statuses, 'method_comparison')
        self.assertTrue(c['engineering_pilot_eligible'])
        from video_contracts import pointer
        for claim in c['claims']:
            for ref in claim['review_refs']:
                self.assertEqual(pointer(b, ref['pointer'])['record']['method_id'], claim['method_id'])
        finalize_copy(build_draft(c, statuses, 'P05'))

    def test_missing_current_status_blocks_generation(self):
        c, _ = self.candidate()
        with self.assertRaises((ValueError, KeyError)): build_draft(c, {})

    def test_empty_package_cannot_use_vacuous_release_checks(self):
        from jsonschema.exceptions import ValidationError
        p, _ = self.package()
        p['source_items'] = []; p['selections'] = []; p['claims'] = []
        with self.assertRaises(ValidationError): validate_package(p)

    def test_cross_method_claim_text_rejected(self):
        c, statuses = self.candidate()
        other = next(i for i, m in enumerate(c['source_items'][0]['methods']) if m['method_id'] == 'R01')
        c['claims'][0]['source_ref']['pointer'] = f'/methods/{other}/core_action'
        c['claims'][0]['text'] = c['source_items'][0]['methods'][other]['core_action']
        with self.assertRaises(ValueError): build_draft(c, statuses)

    def test_package_replay_and_internal_handoff(self):
        p, statuses = self.package(); q, _ = self.package()
        # Bundle transport timestamps vary; semantic copy and timeline remain identical.
        self.assertEqual(p['copy_lock'], q['copy_lock']); self.assertEqual(p['semantic_scenes'], q['semantic_scenes'])
        self.assertEqual(p['package_id'], q['package_id'])
        validate_package(p)
        handoff = ae_contract(p, statuses, internal=True)
        self.assertEqual(handoff['usage'], 'internal_engineering_only')
        self.assertTrue(handoff['evidence']); self.assertTrue(handoff['claims']); self.assertTrue(handoff['methods'])
        with self.assertRaises(ValueError): ae_contract(p, statuses)

    def test_scene_claim_tamper_stop_omission_and_evidence_drift(self):
        p, _ = self.package()
        for mutation in ('claim', 'stop', 'quote'):
            q = deepcopy(p)
            if mutation == 'claim': next(s for s in q['semantic_scenes'] if s['claim_refs'])['spoken_text'] = '答案必定是B'
            elif mutation == 'stop': q['semantic_scenes'] = [s for s in q['semantic_scenes'] if s['scene_type'] != 'STOP_RULE']
            else: q['source_display']['excerpts'][0]['text'] = 'made up quote'
            with self.subTest(mutation=mutation), self.assertRaises(ValueError): validate_package(q)

    def test_claim_guard_is_only_lint(self):
        self.assertEqual(claim_guard('99%的学生都会错')['status'], 'FAIL')
        self.assertEqual(claim_guard('最近爆火，今年必考')['status'], 'FAIL')
        self.assertIn('not_semantic_truth', claim_guard('只看这一步。')['scope'])

    def test_polisher_rejects_teaching_change(self):
        c, statuses = self.candidate(); p = build_draft(c, statuses)
        class Bad:
            def polish(self, q):
                next(s for s in q['semantic_scenes'] if s['claim_refs'])['spoken_text'] = '另一个答案'
                return q
        with self.assertRaises(ValueError): polish(p, Bad())

    def test_polisher_precedes_lock_and_invalidates_editorial(self):
        p, _ = self.package()
        q = polish(p, IdentityPolisher())
        self.assertIsNone(q['copy_lock']['final_copy_sha'])
        self.assertIsNone(q['copy_lock']['editorial_review_sha'])
        self.assertFalse(q['render_ready_for_publication'])
        self.assertIsNotNone(finalize_copy(q)['copy_lock']['final_copy_sha'])

    def test_allowed_non_teaching_polish_requires_new_display_and_editorial_reviews(self):
        p, statuses = self.package()
        class ConnectivePolisher:
            def polish(self, q):
                text = '一起核对这个动作。'
                q['semantic_scenes'][-1]['spoken_text'] = text
                q['semantic_scenes'][-1]['on_screen']['primary_text'] = text
                q['voiceover'][-1]['text'] = text
                q['content']['cta'] = text
                return q
        q = finalize_copy(polish(p, ConnectivePolisher()))
        validate_package(q)
        self.assertNotEqual(p['copy_lock']['final_copy_sha'], q['copy_lock']['final_copy_sha'])
        self.assertTrue(q['invalidation']['editorial_stale'])
        self.assertTrue(q['invalidation']['source_release_stale'])
        self.assertFalse(publication_check(q, statuses)['render_ready_for_publication'])

    def test_three_keys_no_ai_shortcut(self):
        p, statuses = self.package()
        source = {'reviewer_kind': 'human', 'reviewer': 'SYNTHETIC', 'review_id': 's1', 'status': 'pass',
                  'display_sha': sha(display_payload(p)), 'source_bindings': {b['asset_id']: statuses[b['asset_id']]['source_sha'] for b in p['source_items']}}
        editorial = {'reviewer_kind': 'human', 'reviewer': 'SYNTHETIC', 'review_id': 'e1', 'status': 'pass',
            'final_copy_sha': p['copy_lock']['final_copy_sha'], 'display_sha': sha(display_payload(p)),
            'teaching_bindings': {b['asset_id']: b['semantic_binding_sha'] for b in p['source_items']},
            'checks': {k: 'pass' for k in ('teaching_consistency', 'role', 'evidence', 'stop_rule', 'hook', 'subtitle', 'source_display', 'challenge_no_leak')}}
        q = apply_reviews(p, statuses, source, editorial)
        self.assertEqual(q['pilot_status']['source_release'], 'PASS')
        self.assertEqual(q['pilot_status']['editorial_release'], 'PASS')
        self.assertEqual(q['pilot_status']['semantic_release'], 'PENDING')
        self.assertFalse(q['render_ready_for_publication'])

    def test_final_copy_edit_invalidates_editorial(self):
        p, statuses = self.package()
        p['semantic_scenes'][0]['spoken_text'] = '一起核对这个动作。'
        q = publication_check(p, statuses)
        self.assertFalse(q['render_ready_for_publication'])
        self.assertEqual(q['pilot_status']['editorial_release'], 'PENDING')
        self.assertTrue(q['invalidation']['editorial_stale'])

    def test_human_three_key_positive_and_each_missing_key_blocks(self):
        review = self.req['reviews'][0]
        review.update(reviewer_kind='human', independent_human_review='pass', independent_human_certified=False,
                      release_review={'status': 'pass', 'content_scope': 'method_action_demo', 'method_id': 'R12',
                                      'action_ids': ['loc'], 'checks': {k: 'pass' for k in ('trigger', 'action', 'output', 'role', 'stop_rule')}})
        p, statuses = self.package()
        source = {'reviewer_kind': 'human', 'reviewer': 'SYNTHETIC ONLY', 'review_id': 's1', 'status': 'pass',
                  'display_sha': sha(display_payload(p)), 'source_bindings': {b['asset_id']: statuses[b['asset_id']]['source_sha'] for b in p['source_items']}}
        editorial = {'reviewer_kind': 'human', 'reviewer': 'SYNTHETIC ONLY', 'review_id': 'e1', 'status': 'pass',
            'final_copy_sha': p['copy_lock']['final_copy_sha'], 'display_sha': sha(display_payload(p)),
            'teaching_bindings': {b['asset_id']: b['semantic_binding_sha'] for b in p['source_items']},
            'checks': {k: 'pass' for k in ('teaching_consistency', 'role', 'evidence', 'stop_rule', 'hook', 'subtitle', 'source_display', 'challenge_no_leak')}}
        approved = apply_reviews(p, statuses, source, editorial)
        self.assertTrue(approved['render_ready_for_publication'])
        self.assertTrue(ae_contract(approved, statuses)['public_render_ready'])
        self.assertFalse(apply_reviews(p, statuses, source=source)['render_ready_for_publication'])
        self.assertFalse(apply_reviews(p, statuses, editorial=editorial)['render_ready_for_publication'])
        self.assertFalse(publication_check(approved, {})['render_ready_for_publication'])
        changed = deepcopy(approved); changed['source_display']['attribution_text'] = 'different attribution'
        self.assertFalse(publication_check(changed, statuses)['render_ready_for_publication'])
        self.assertTrue(publication_check(changed, statuses)['invalidation']['source_release_stale'])

    def test_helper_without_answer_exports_and_full_solution_holds(self):
        q = fixture(); q['relations'] = []; q['requested_chain'] = ['R12']
        q['observations'] = [q['observations'][0]]; q['action_executions'] = [q['action_executions'][0]]
        a = self.engine.analyze(q)
        self.req.update(question=q, analysis=a, methods=[self.registry.methods[m] for m in a['method_versions']])
        self.req['reviews'][0].update(input_sha256=sha(q), analysis_sha256=sha(a))
        b, statuses = self.assets()
        self.assertIsNone(b['analysis']['answer'])
        self.assertFalse(b['analysis']['answer_verification']['closed'])
        selections = [{'asset_id': b['asset_id'], 'method_id': 'R12', 'action_ids': ['loc']}]
        self.assertTrue(make_candidate([b], selections, statuses)['engineering_pilot_eligible'])
        self.assertFalse(make_candidate([b], selections, statuses, 'full_solution')['engineering_pilot_eligible'])

    def test_unknown_pattern_requirements_and_short_format_reject(self):
        c, statuses = self.candidate()
        with self.assertRaises(ValueError): build_draft(c, statuses, 'P04')
        p = build_draft(c, statuses)
        p['semantic_scenes'][0]['spoken_text'] *= 100
        self.assertEqual(finalize_copy(p)['pilot_status']['engineering'], 'FAIL')

    def test_tampered_frozen_bytes_rejected(self):
        b, _ = self.assets(); b['analysis']['answer'] = 'B'
        with self.assertRaises(ValueError): verify_bundle(b)

    def test_omitting_stop_claims_and_scenes_cannot_bypass_guard(self):
        p, _ = self.package()
        p['claims'] = [c for c in p['claims'] if c['kind'] not in ('stop_rule', 'action_stop')]
        p['semantic_scenes'] = [s for s in p['semantic_scenes'] if s['scene_type'] != 'STOP_RULE']
        p = finalize_copy(p)
        with self.assertRaises(ValueError): validate_package(p)

    def test_omitting_actual_action_scene_or_output_rejects_engineering_pass(self):
        p, _ = self.package()
        actual = next(c['claim_id'] for c in p['claims'] if c['kind'] == 'actual_action')
        missing = deepcopy(p)
        missing['semantic_scenes'] = [s for s in missing['semantic_scenes'] if actual not in s['claim_refs']]
        for i, s in enumerate(missing['semantic_scenes']): s['order'] = i
        missing['voiceover'] = [{'scene_id': s['scene_id'], 'text': s['spoken_text']} for s in missing['semantic_scenes']]
        missing = finalize_copy(missing)
        with self.assertRaisesRegex(ValueError, 'omitted'): validate_package(missing)
        invisible = deepcopy(p)
        s = next(s for s in invisible['semantic_scenes'] if actual in s['claim_refs'])
        s['method_visual'] = None; s['on_screen']['primary_text'] = s['spoken_text']
        invisible = finalize_copy(invisible)
        with self.assertRaisesRegex(ValueError, 'output omitted'): validate_package(invisible)

    def test_multi_method_claims_and_visuals_keep_own_bindings(self):
        b, statuses = self.assets()
        selections = [{'asset_id': b['asset_id'], 'method_id': 'R12', 'action_ids': ['loc']},
                      {'asset_id': b['asset_id'], 'method_id': 'R11', 'action_ids': ['meaning']}]
        c = make_candidate([b], selections, statuses, 'method_comparison')
        p = finalize_copy(build_draft(c, statuses, 'P05'))
        validate_package(p)
        for claim in p['claims']:
            for r in claim['action_artifact_refs']:
                from video_contracts import pointer
                self.assertEqual(pointer(b, r['pointer'])['method_id'], claim['method_id'])

    def test_challenge_uses_independent_question_without_answer_copy(self):
        b, statuses = self.assets()
        req2 = deepcopy(self.req); req2['question']['question_id'] = 'synthetic-second-question'
        req2['analysis'] = self.engine.analyze(req2['question'])
        req2['reviews'][0].update(question_id=req2['question']['question_id'], input_sha256=sha(req2['question']), analysis_sha256=sha(req2['analysis']))
        b2 = self.exporter.export(req2); statuses[b2['asset_id']] = self.exporter.status(req2)
        selections = [{'asset_id': b['asset_id'], 'method_id': 'R12', 'action_ids': ['loc'], 'purpose': 'teaching'},
                      {'asset_id': b2['asset_id'], 'method_id': 'R12', 'action_ids': ['loc'], 'purpose': 'challenge'}]
        c = make_candidate([b, b2], selections, statuses, 'challenge')
        p = finalize_copy(build_draft(c, statuses, 'P04'))
        validate_package(p)
        hidden = {c['claim_id'] for c in p['claims'] if c['purpose'] == 'challenge'}
        self.assertFalse(hidden & {r for s in p['semantic_scenes'] for r in s['claim_refs']})
        self.assertTrue(any(s['scene_type'] == 'QUESTION' for s in p['semantic_scenes']))
        self.assertFalse(any(s['scene_type'] == 'VERDICT' for s in p['semantic_scenes']))

    def test_resealed_candidate_gate_flag_cannot_bypass_unreviewed_actions(self):
        c, statuses = self.candidate()
        c['selections'][0]['action_ids'] = ['nonexistent']
        with self.assertRaises(ValueError): build_draft(c, statuses)

    def test_refresh_propagates_to_registered_render_and_never_revives(self):
        p, statuses = self.package()
        self.req['withdrawals'] = [self.finding()]
        b, withdrawn = self.assets()
        catalog = {'entries': [{'id': 'p', 'parent_ids': [], 'artifact': p},
                               {'id': 'render', 'parent_ids': ['p'], 'artifact': {'status': 'pending_publish'}}]}
        result = refresh_catalog(catalog, withdrawn)
        self.assertTrue(result['entries'][1]['artifact']['invalidation']['teaching_stale'])
        self.assertTrue(refresh_catalog(result, statuses)['entries'][0]['artifact']['invalidation']['teaching_stale'])

    def test_explicit_file_loader_hash_binding(self):
        with tempfile.TemporaryDirectory() as directory:
            d = Path(directory); write(d / 'q.json', self.req['question'])
            req = deepcopy(self.req); req['question'] = {'file': 'q.json', 'sha256': sha(self.req['question'])}
            write(d / 'request.json', req)
            self.assertEqual(load_request(d / 'request.json')['question'], self.req['question'])

    def test_content_os_does_not_import_teaching_engine(self):
        for path in (ROOT / 'content_os').glob('*.py'):
            tree = ast.parse(path.read_text(encoding='utf-8'))
            for node in ast.walk(tree):
                if isinstance(node, ast.ImportFrom):
                    self.assertFalse((node.module or '').split('.')[0] in {'answer_engine', 'core', 'renderers'})


if __name__ == '__main__': unittest.main()
