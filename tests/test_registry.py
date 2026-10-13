from __future__ import annotations

import unittest
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]


def load_yaml(relative_path: str):
    return yaml.safe_load((ROOT / relative_path).read_text(encoding="utf-8"))


class RegistryTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.schema = load_yaml("method-registry/schema.yaml")
        cls.registry = load_yaml("method-registry/registry.yaml")
        cls.methods = {}
        for relative_path in cls.registry["method_files"]:
            payload = load_yaml(relative_path)
            for method in payload["methods"]:
                cls.methods[method["method_id"]] = method
        # Preserve the six-card baseline; full-registry coverage is tested separately.
        cls.methods = {mid: cls.methods[mid] for mid in cls.registry['golden_methods']}

    def test_exact_six_sample_methods_exist(self):
        self.assertEqual(set(self.methods), {"R01", "R02", "R06", "R09", "F01", "G01"})

    def test_every_card_has_required_fields(self):
        required = set(self.schema["required_fields"])
        for method_id, method in self.methods.items():
            with self.subTest(method_id=method_id):
                self.assertFalse(required - set(method), required - set(method))

    def test_registry_index_matches_cards(self):
        self.assertTrue(set(self.methods).issubset(self.registry["methods"]))
        for method_id in self.methods:
            index = self.registry["methods"][method_id]
            card = self.methods[method_id]
            self.assertEqual(index["brand_name"], card["brand_name"])
            self.assertEqual(index["status"], card["status"])
            self.assertEqual(index["version"], card["version"])

    def test_roles_and_outputs_are_explicit(self):
        allowed_roles = set(self.schema["allowed_roles"])
        allowed_outputs = set(self.schema["allowed_output_types"])
        for method_id, method in self.methods.items():
            with self.subTest(method_id=method_id):
                self.assertIn(method["role"], allowed_roles)
                self.assertEqual(method["primary_role"], method["role"])
                self.assertIsInstance(method["secondary_roles"], list)
                self.assertIn(method["output_type"], allowed_outputs)
        self.assertEqual(self.methods["F01"]["output_type"], "reduce")
        self.assertEqual(self.methods["R09"]["primary_role"], "framework")

    def test_source_references_are_frozen_and_complete(self):
        baseline = self.registry["source_baseline"]
        for method_id, method in self.methods.items():
            with self.subTest(method_id=method_id):
                self.assertTrue(method["source_name"])
                self.assertTrue(method["source_references"])
                for source in method["source_references"]:
                    self.assertEqual(source["repository"], baseline["repository"])
                    self.assertEqual(source["commit"], baseline["commit"])
                    self.assertTrue(source["path"])
                    self.assertTrue(source["heading"])

    def test_four_step_cards_are_concrete(self):
        for method_id, method in self.methods.items():
            card = method["four_step_card"]
            with self.subTest(method_id=method_id):
                self.assertEqual(set(card), {"start", "first_cut", "judge", "stop"})
                for value in card.values():
                    self.assertGreaterEqual(len(value), 10)

    def test_practicality_gate_is_complete_but_not_falsely_claimed(self):
        required = {"status", "trigger", "action", "output", "stop", "transfer", "efficiency", "misuse_cost"}
        for method_id, method in self.methods.items():
            gate = method["practicality_gate"]
            with self.subTest(method_id=method_id):
                self.assertFalse(required - set(gate), required - set(gate))
                self.assertEqual(gate["status"], "design_complete_empirical_pending")
                self.assertTrue(gate["output"].startswith(method["output_type"]))

    def test_first_use_results_are_not_fabricated(self):
        metrics = {
            "trigger_success",
            "action_success",
            "evidence_success",
            "stop_rule_success",
            "no_answer_backfit",
        }
        for method_id, method in self.methods.items():
            first_use = method["first_use_test"]
            with self.subTest(method_id=method_id):
                self.assertEqual(first_use["status"], "designed_not_run")
                self.assertTrue(all(first_use[name] is None for name in metrics))
                self.assertEqual(first_use["final_result"], "pending_real_student_test")

    def test_blind_metrics_have_baseline_and_remain_pending(self):
        metrics = {
            "trigger_precision",
            "trigger_recall",
            "resolution_rate",
            "standalone_rate",
            "assist_rate",
            "false_trigger_rate",
            "transfer_rate",
            "time_complexity_gain",
        }
        for method_id, method in self.methods.items():
            evaluation = method["evaluation"]
            with self.subTest(method_id=method_id):
                self.assertTrue(evaluation["baseline"])
                self.assertTrue(all(evaluation[name] is None for name in metrics))
                self.assertTrue(evaluation["primary_benefit_hypothesis"])
                self.assertEqual(method["usefulness_level"], "Useful")

    def test_candidate_status_does_not_overclaim_stability(self):
        for method in self.methods.values():
            self.assertEqual(method["status"], "candidate")
            self.assertNotEqual(method["usefulness_level"], "Signature")

    def test_all_four_case_types_exist_and_match(self):
        case_types = set(self.schema["case_types"])
        for method_id, method in self.methods.items():
            with self.subTest(method_id=method_id):
                self.assertEqual(set(method["cases"]), case_types)
                for case_type, relative_path in method["cases"].items():
                    path = ROOT / relative_path
                    self.assertTrue(path.is_file(), path)
                    case = yaml.safe_load(path.read_text(encoding="utf-8"))
                    self.assertEqual(case["method_id"], method_id)
                    self.assertEqual(case["case_type"], case_type)
                    self.assertIn(case["status"], {"verified_course_example", "source_pattern_only", "evidence_gap"})
                    self.assertTrue(case["source_reference"])

    def test_stable_gate_rejects_case_gaps(self):
        for method_id, method in self.methods.items():
            statuses = {
                yaml.safe_load((ROOT / path).read_text(encoding="utf-8"))["status"]
                for path in method["cases"].values()
            }
            if method["status"] in {"validated", "stable"}:
                self.assertEqual(statuses, {"verified_course_example"}, method_id)

    def test_student_first_contact_guides_exist(self):
        guides = list((ROOT / "student-guides").glob("*.md"))
        self.assertGreaterEqual(len(guides), 6)
        for method_id, method in self.methods.items():
            matches = [path for path in guides if path.name.startswith(method_id + "-")]
            self.assertEqual(len(matches), 1, method_id)
            text = matches[0].read_text(encoding="utf-8")
            for marker in ("## 四步实战卡", "## 10 秒版", "## 30 秒版", "## 90 秒版", "挑战：", "## 一屏视觉式", "反口诀："):
                self.assertIn(marker, text, f"{method_id}: {marker}")
            first_body_line = next(line for line in text.splitlines()[1:] if line.strip())
            self.assertNotIn("是指", first_body_line)
            self.assertNotIn("是一种", first_body_line)

    def test_anti_rule_registry_has_first_batch(self):
        text = (ROOT / "references/anti-rules.md").read_text(encoding="utf-8")
        self.assertGreaterEqual(text.count("## AR"), 8)
        for phrase in ("同词 ≠ 答案", "绝对词 ≠ 必错", "转折后 ≠ 必选", "段首 ≠ 中心句", "范围最大 ≠ 主旨", "分组 ≠ 定案", "定位 ≠ 答案", "只剩一个 ≠ 自动正确"):
            self.assertIn(phrase, text)

    def test_regression_boundaries_remain_explicit(self):
        self.assertIn("直接或间接", self.methods["R01"]["decision_rule"])
        self.assertIn("一致只通过", self.methods["R02"]["decision_rule"])
        self.assertIn("不能据剩余项定案", self.methods["R02"]["four_step_card"]["stop"])
        self.assertIn("主旨、标题或目的", self.methods["R06"]["four_step_card"]["start"])
        self.assertIn("全文骨架卡", self.methods["R09"]["decision_rule"])
        self.assertIn("先读实际题干", self.methods["R09"]["core_action"])
        self.assertIn("重复线索缺失只跳过", self.methods["R09"]["stop_rule"])
        self.assertIn("只产出优先候选组", self.methods["F01"]["decision_rule"])
        self.assertIn("不据组小、占用或剩一项选", self.methods["F01"]["stop_rule"])
        self.assertIn("只在空位已确认需要动词形式时进入", self.methods["G01"]["full"]["decision_tree"]["prompt_word"][True]["children"]["verb"]["gate"])

    def test_g01_is_a_tree_not_a_flat_list(self):
        tree = self.methods["G01"]["full"]["decision_tree"]
        self.assertIn("prompt_word", tree)
        self.assertIn(False, tree["prompt_word"])
        self.assertIn(True, tree["prompt_word"])
        self.assertIn("function_word", tree["prompt_word"][False]["node"])
        self.assertIn("verb", tree["prompt_word"][True]["children"])


if __name__ == "__main__":
    unittest.main()
