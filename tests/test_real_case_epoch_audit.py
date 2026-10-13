"""Synthetic audit controls, not English or real student validation."""
from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from scripts.audit_real_case_epoch import audit


class EpochAuditTests(unittest.TestCase):
    def run_audit(self,rejected=True):
        method={'version':'1.2.0','core_action':'current action',
                'four_step_card':{'start':'cue','first_cut':'circle','judge':'compare','stop':'stop'}}
        current=SimpleNamespace(validate=lambda:None,is_historical=False,methods={'R01':method},
                                index={'source_baseline':{'commit':'current'}})
        history=deepcopy(current); history.methods['R01']['version']='1.1.0'
        history.methods['R01']['core_action']='old action'
        history.index={'source_baseline':{'commit':'old'}}
        request_ref={'path':'request.json','sha256':'request-hash'}
        case_ref={'path':'case.json','sha256':'case-hash'}
        record={'case_id':'existing-case','registration_request_ref':request_ref}
        request={'canonical_question_id':'existing-question','method_id':'R01',
                 'method_version':'1.1.0','case_type':'boundary'}
        original=deepcopy((record,request))
        catalog={'revision':0,'sha256':None,'cases':[case_ref]}
        context={('request.json','request-hash'):{'registry':history}}
        with (patch('scripts.audit_real_case_epoch.private_root',return_value=Path('/synthetic')),
             patch('scripts.audit_real_case_epoch.load_catalog',return_value=catalog),
             patch('scripts.audit_real_case_epoch._runtime_contexts',return_value=context),
             patch('scripts.audit_real_case_epoch.artifact',side_effect=lambda root,ref:record if ref==case_ref else request),
             patch('scripts.audit_real_case_epoch.validate_request',side_effect=ValueError('Method identity/version mismatch') if rejected else None)):
            report=audit('/synthetic',current)
        self.assertEqual((record,request),original)
        return report

    def test_historical_success_not_current_credit(self):
        report=self.run_audit()
        self.assertEqual(report['historical_catalog_validation'],'PASS')
        self.assertEqual(report['admission_counts'],{'current_binding_rejected':1})
        row=report['cases'][0]
        self.assertEqual(row['changed_core_fields'],['core_action'])
        self.assertEqual(row['next_review']['first_action'],'circle')
        self.assertFalse(row['new_blind_sample'])

    def test_structural_pass_still_not_semantic_or_learner_success(self):
        report=self.run_audit(False)
        self.assertEqual(report['cases'][0]['current_admission'],'current_structural_admission_passed')
        self.assertEqual(report['cases'][0]['semantic_reacceptance'],'not_established_by_this_audit')
        self.assertEqual(report['new_case_count'],0)
        self.assertFalse(report['method_promotion_applied'])


if __name__=='__main__': unittest.main()
