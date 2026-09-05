from __future__ import annotations

import importlib.util
import json
import unittest
from pathlib import Path

import test_research_queue as fixtures


class ResearchIterationTest(unittest.TestCase):
    def setUp(self) -> None:
        self.t = fixtures.ResearchQueueCLITest()
        self.t.setUp()
        self.t.init_exploration()
        self.t.confirm_direction(self.t.add_answer("direction", "Choose this task and data", outcome="select"))

    def tearDown(self) -> None:
        self.t.tearDown()

    def state(self) -> dict:
        return json.loads(self.t.state.read_text(encoding="utf-8"))

    def update(self, subject="M-ONE", status="SCREENING", extra=(), ok=True):
        return self.t.run_cli(
            "research-update", self.t.state, "--layer", "L2", "--kind", "method_cluster",
            "--subject-id", subject, "--title", "Representation mechanism", "--status", status,
            "--observation", "Held-domain diagnostic improved; see results/diagnostic.json",
            "--interpretation", "Supports the nuisance hypothesis, not yet a competitive claim",
            "--next-action", "Compare the relevant simpler alternative", *extra, ok=ok,
        )

    def focus_flags(self):
        return ("--set-current", "--hypothesis", "Removing nuisance reduces held-domain errors",
                "--current-action", "Discriminate nuisance removal from capacity increase")

    def test_one_update_persists_research_and_view_without_new_approval(self):
        before = self.state()["layer_checkpoints"]
        self.update(extra=self.focus_flags())
        content = self.t.l2.read_text(encoding="utf-8")
        self.assertIn("results/diagnostic.json", content)
        self.assertEqual(content.count("### Representation mechanism (M-ONE)"), 1)
        self.update(status="PROMISING", extra=("--best-result", "0.79", *self.focus_flags()))
        self.assertEqual(self.t.l2.read_text(encoding="utf-8").count("### Representation mechanism (M-ONE)"), 1)
        report = json.loads(self.t.run_cli("status", self.t.state, "--window").stdout)
        cards = [c for c in report["research_window"]["l2_cards"] if c["subject_id"] == "M-ONE"]
        self.assertEqual(len(cards), 1)
        self.assertEqual(cards[0]["best_result"], "0.79")
        self.assertEqual(self.state()["layer_checkpoints"], before)
        self.assertEqual(report["pending_pi_questions"], [])

    def test_notification_update_does_not_overwrite_evidence_or_create_a_question(self):
        self.update(extra=("--notify-kind", "method_cluster_switch", "--from-id", "M-OLD", *self.focus_flags()))
        state = self.state()
        self.assertEqual(len(state["notifications"]), 1)
        card = next(c for c in state["research_window"]["cards"] if c["subject_id"] == "M-ONE")
        self.assertIn("Held-domain diagnostic", card["verified_observation"])
        self.assertEqual(state["notifications"][0]["transition"], {"from_id": "M-OLD", "to_id": "M-ONE"})

    def test_boundary_preserves_focus_but_not_old_delta_and_retains_closed_alternative(self):
        self.update(status="CLOSED")
        self.update("M-TWO", extra=self.focus_flags())
        self.t.run_cli("window-start", self.t.state, "--instruction", "继续当前研究")
        report = json.loads(self.t.run_cli("status", self.t.state, "--window").stdout)
        self.assertEqual(report["research_window"]["l2_cards"], [])
        self.assertEqual(report["research_window"]["current_focus"]["subject_id"], "M-TWO")
        self.assertEqual(report["research_window"]["current_focus"]["context_origin"], "carried_forward_not_new_progress")
        content = self.t.l2.read_text(encoding="utf-8")
        self.assertIn("M-ONE", content)
        self.assertIn("Status: CLOSED", content)
        self.assertIn("M-TWO", content)

    def test_closing_carried_focus_clears_it(self):
        self.update(extra=self.focus_flags())
        self.t.run_cli("window-start", self.t.state, "--instruction", "继续")
        self.update(status="EXHAUSTED")
        report = json.loads(self.t.run_cli("status", self.t.state, "--window").stdout)
        self.assertIsNone(report["research_window"]["current_focus"])

    def test_baseline_evidence_refresh_preserves_current_and_carried_focus(self):
        self.t.set_evaluation_anchor()
        self.update(extra=self.focus_flags())
        self.t.set_baseline_roster(status="MATCHED", our_score=0.806)
        self.t.run_cli("window-start", self.t.state, "--instruction", "继续，任务数据不变")
        report = json.loads(self.t.run_cli("status", self.t.state, "--window").stdout)
        self.assertEqual(report["research_window"]["current_focus"]["subject_id"], "M-ONE")
        self.assertEqual(report["research_window"]["l2_cards"], [])
        self.t.set_baseline_roster(status="MATCHED", our_score=0.808)
        report = json.loads(self.t.run_cli("status", self.t.state, "--window").stdout)
        self.assertEqual(report["research_window"]["current_focus"]["context_origin"], "carried_forward_not_new_progress")
        self.t.run_cli("window-start", self.t.state, "--instruction", "继续")
        report = json.loads(self.t.run_cli("status", self.t.state, "--window").stdout)
        self.assertEqual(report["research_window"]["current_focus"]["subject_id"], "M-ONE")

    def test_changed_scientific_scope_does_not_report_or_carry_stale_focus(self):
        self.t.set_evaluation_anchor()
        self.update(extra=self.focus_flags())
        self.t.set_evaluation_anchor(method_cluster_id="M-NEW", reason="New exploratory mechanism")
        report = json.loads(self.t.run_cli("status", self.t.state, "--window").stdout)
        self.assertIsNone(report["research_window"]["current_focus"])
        self.t.run_cli("window-start", self.t.state, "--instruction", "继续新机制")
        report = json.loads(self.t.run_cli("status", self.t.state, "--window").stdout)
        self.assertIsNone(report["research_window"]["current_focus"])
        self.update("M-NEW", extra=self.focus_flags())
        self.t.run_cli("window-start", self.t.state, "--instruction", "继续")
        self.t.set_evaluation_anchor(method_cluster_id="M-NEW", primary_metric="accuracy", reason="Metric correction")
        report = json.loads(self.t.run_cli("status", self.t.state, "--window").stdout)
        self.assertIsNone(report["research_window"]["current_focus"])

    def test_update_uses_selected_custom_record_and_returns_small_receipt(self):
        custom = self.t.root / "custom-research.md"
        custom.write_text("# Existing project research\n", encoding="utf-8")
        original_l2 = self.t.l2
        run_cli = self.t.run_cli

        def custom_record(*args, **kwargs):
            values = list(args)
            if values[0] == "confirm":
                values[values.index("--record") + 1] = custom
            return run_cli(*values, **kwargs)

        self.t.run_cli = custom_record
        self.t.confirm_science(self.t.add_answer("science", "Adopt this scoped mechanism"))
        self.t.run_cli = run_cli
        original_content = original_l2.read_bytes()
        receipt = json.loads(self.update(extra=self.focus_flags()).stdout)
        self.assertIn("### Representation mechanism", custom.read_text(encoding="utf-8"))
        self.assertEqual(original_l2.read_bytes(), original_content)
        self.assertEqual(Path(receipt["record_path"]), custom)
        self.assertNotIn("window", receipt)
        self.t.run_cli("audit", self.t.state)

    def test_switch_without_new_focus_does_not_reuse_old_hypothesis(self):
        self.update(extra=self.focus_flags())
        self.t.run_cli("window-start", self.t.state, "--instruction", "继续")
        self.update("M-TWO", extra=("--notify-kind", "method_cluster_switch", "--from-id", "M-ONE"))
        report = json.loads(self.t.run_cli("status", self.t.state, "--window").stdout)
        self.assertIsNone(report["research_window"]["current_focus"])
        self.update("M-TWO", extra=self.focus_flags())
        self.update("M-THREE", extra=("--notify-kind", "method_cluster_switch", "--from-id", "M-TWO"))
        report = json.loads(self.t.run_cli("status", self.t.state, "--window").stdout)
        self.assertIsNone(report["research_window"]["current_focus"])

    def test_paused_update_and_invalid_switch_leave_all_artifacts_unchanged(self):
        original = self.t.l2.read_bytes()
        before = self.t.state.read_bytes()
        self.update(extra=("--notify-kind", "problem_switch", "--from-id", "P-OLD"), ok=False)
        self.assertEqual(self.t.l2.read_bytes(), original)
        self.assertEqual(self.t.state.read_bytes(), before)
        self.t.run_cli("pause", self.t.state, "--pi-decision", "暂停", "--reason", "User paused")
        self.update(ok=False)
        self.assertEqual(self.t.l2.read_bytes(), original)

    def test_closed_candidate_cannot_be_current(self):
        self.update(status="CLOSED", extra=self.focus_flags(), ok=False)
        self.assertNotIn("### Representation mechanism", self.t.l2.read_text(encoding="utf-8"))

    def test_local_evidence_updates_preserve_selection_but_lock_paper_evidence(self):
        self.t.confirm_science(self.t.add_answer("science", "Adopt the mechanism"))
        before = self.state()["layer_checkpoints"]["science"]
        self.update(extra=self.focus_flags())
        self.t.run_cli("audit", self.t.state)
        self.assertEqual(self.state()["layer_checkpoints"]["science"], before)
        report = self.t.root / "paper.md"
        report.write_text("# Evidence-based report\n", encoding="utf-8")
        self.t.enter_paper_ready(report)
        self.t.run_cli("audit", self.t.state)
        self.t.l2.write_text(self.t.l2.read_text(encoding="utf-8") + "\nA new diagnostic contradicts the result.\n", encoding="utf-8")
        failed = self.t.run_cli("audit", self.t.state, ok=False)
        self.assertIn("PAPER_EVIDENCE_REVIEW_REQUIRED", failed.stdout)
        self.assertEqual(self.state()["layer_checkpoints"]["science"]["status"], "CONFIRMED_BY_PI")

    def test_v15_upgrade_preserves_choices_without_creating_questions(self):
        self.t.confirm_science(self.t.add_answer("science", "Adopt the mechanism"))
        state = self.state()
        state["schema_version"] = 15
        self.t.state.write_text(json.dumps(state), encoding="utf-8")
        report = json.loads(self.t.run_cli("status", self.t.state).stdout)
        self.assertEqual(report["schema_version"], 16)
        self.assertEqual(report["layer_checkpoints"], state["layer_checkpoints"])
        self.assertEqual(self.state()["macro_questions"], state["macro_questions"])

    def test_documented_baseline_shape_parses(self):
        spec = importlib.util.spec_from_file_location("iteration_controller", fixtures.SCRIPT)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        doc = (fixtures.ROOT / "references" / "research-state.md").read_text(encoding="utf-8")
        row = json.loads(doc.split("```json\n", 1)[1].split("```", 1)[0])
        parsed = module.parse_dataset_baseline_matrix(json.dumps([row]), require_matched=False)
        self.assertEqual(parsed[0]["dataset"], "Dataset-A")

    def test_unconfirmed_update_cannot_claim_selection_or_fake_a_comparison(self):
        before = self.t.l2.read_bytes()
        self.update(status="SELECTED", ok=False)
        self.update(extra=("--notification", "message without a notification kind"), ok=False)
        self.update(extra=("--notify-kind", "method_cluster_switch", "--from-id", "M-OLD", "--notification", " "), ok=False)
        self.assertEqual(self.t.l2.read_bytes(), before)

    def test_approved_refinement_can_keep_method_identity(self):
        self.t.confirm_science(self.t.add_answer("science", "Adopt the mechanism"))
        new_decision = self.t.add_answer("science", "Narrow the innovation claim while retaining this mechanism")
        run_cli = self.t.run_cli

        def scoped_refinement(*args, **kwargs):
            values = list(args)
            if values[0] == "confirm":
                i = values.index("--innovation-claim")
                values[i + 1] = "remove identifiable nuisance in the scoped source setting"
                values.extend(("--change-notification", "The user narrowed the claim; task and mechanism remain the same"))
            return run_cli(*values, **kwargs)

        self.t.run_cli = scoped_refinement
        self.t.confirm_science(new_decision)
        self.t.run_cli = run_cli
        self.t.run_cli("audit", self.t.state)
        self.assertEqual(self.state()["layer_checkpoints"]["science"]["payload"]["method_cluster_id"], "M-RESIDUAL")

    def current_card(self, subject="M-ONE"):
        report = json.loads(self.t.run_cli("status", self.t.state, "--window").stdout)
        return next(c for c in report["research_window"]["l2_cards"] if c["subject_id"] == subject), report

    def test_partial_update_preserves_hypothesis_and_refreshes_current_summary(self):
        self.update(extra=("--best-result", "0.820", "--latest-result", "0.820", *self.focus_flags()))
        self.update(extra=("--latest-result", "0.815", "--next-action", "Frequency-stratified diagnostic"))
        card, report = self.current_card()
        self.assertEqual(card["best_result"], "0.820")
        self.assertEqual(report["research_window"]["current_focus"]["latest_result"], "0.815")
        self.assertEqual(report["research_window"]["current_focus"]["next_action"], "Frequency-stratified diagnostic")
        note = self.t.l2.read_text(encoding="utf-8")
        self.assertIn("Hypothesis: Removing nuisance", note)
        self.assertIn("Current test: Discriminate nuisance", note)

    def test_durable_best_and_start_survive_multiple_reporting_boundaries(self):
        self.update(extra=("--starting-result", "0.801", "--best-result", "0.820", *self.focus_flags()))
        for latest in ("0.815", "0.816"):
            self.t.run_cli("window-start", self.t.state, "--instruction", "Continue this same mechanism")
            self.update(extra=("--latest-result", latest))
            card, report = self.current_card()
            self.assertEqual(card["starting_result"], "0.801")
            self.assertEqual(card["best_result"], "0.820")
            self.assertEqual(report["research_window"]["current_focus"]["latest_result"], latest)
        self.assertIn("best_result: 0.820", self.t.l2.read_text(encoding="utf-8"))

    def test_optional_results_are_not_inherited_across_changed_scope(self):
        self.t.set_evaluation_anchor()
        self.update(extra=("--best-result", "0.820", *self.focus_flags()))
        self.t.set_evaluation_anchor(primary_metric="accuracy", reason="Different metric")
        self.update(extra=("--latest-result", "0.71"))
        card, report = self.current_card()
        self.assertNotIn("best_result", card)
        self.assertNotIn("hypothesis", card)
        self.assertIsNone(report["research_window"]["current_focus"])
        self.update("M-OTHER", extra=("--latest-result", "0.72"))
        self.assertNotIn("best_result", self.current_card("M-OTHER")[0])

    def test_explicit_clear_does_not_resurrect_invalid_result_after_restart(self):
        self.update(extra=("--best-result", "0.820", *self.focus_flags()))
        self.update(extra=("--clear-field", "best_result", "--latest-result", "0.79"))
        self.t.run_cli("window-start", self.t.state, "--instruction", "Continue after the metric repair")
        self.update(extra=("--latest-result", "0.80"))
        self.assertNotIn("best_result", self.current_card()[0])
        self.assertNotIn("best_result: 0.820", self.t.l2.read_text(encoding="utf-8"))
        before = self.t.l2.read_bytes()
        self.update(extra=("--clear-field", "best_result", "--best-result", "0.82"), ok=False)
        self.assertEqual(self.t.l2.read_bytes(), before)

    def test_inactive_method_update_preserves_reasoning_without_stealing_focus(self):
        self.update(extra=self.focus_flags())
        self.update("M-TWO", extra=self.focus_flags())
        self.update(extra=("--latest-result", "0.815"))
        card, report = self.current_card()
        self.assertIn("Removing nuisance", card["hypothesis"])
        self.assertEqual(report["research_window"]["current_focus"]["subject_id"], "M-TWO")

    def test_external_reference_survives_internal_gains_and_window_changes(self):
        self.t.set_baseline_roster(status="MATCHED", baseline_score=0.85, our_score=0.81)
        selection = self.state()["layer_checkpoints"]
        for score in (0.82, 0.83):
            self.update(extra=("--latest-result", str(score), "--external-baseline-gap", "Our old variant was only 0.81", *self.focus_flags()))
            self.t.set_baseline_roster(status="MATCHED", baseline_score=0.85, our_score=score)
            self.t.run_cli("window-start", self.t.state, "--instruction", "Continue toward the external baseline")
            self.update(extra=("--latest-result", str(score)))
            card, report = self.current_card()
            primary = next(row for row in report["current_external_baselines"] if row["role"] == "primary")
            self.assertEqual(primary["baseline_score"], 0.85)
            self.assertEqual(primary["our_score"], score)
            self.assertIn("ours-baseline=-", primary["gap"])
            self.assertIn("Baseline B", card["external_baseline_gap"])
            self.assertIn("0.85", card["external_baseline_gap"])
            self.assertNotIn("Our old variant", card["external_baseline_gap"])
            self.assertIn("source", primary)
            self.assertEqual(self.state()["layer_checkpoints"], selection)
        self.t.set_baseline_roster(status="MATCHED", baseline_score=0.86, our_score=0.83)
        before = self.t.state.read_bytes()
        card, report = self.current_card()
        self.assertIn("0.86", card["external_baseline_gap"])
        self.assertEqual(self.t.state.read_bytes(), before)
        self.assertIsNone(self.state()["paper_ready_assessment"])

    def test_missing_external_reference_does_not_fall_back_to_our_variant(self):
        self.update(extra=("--latest-result", "0.99", "--external-baseline-gap", "Much higher than our previous model", *self.focus_flags()))
        card, report = self.current_card()
        self.assertIn("score unresolved", card["external_baseline_gap"])
        self.assertIn("internal variant gains do not replace", card["external_baseline_gap"])
        self.assertNotIn("Much higher", card["external_baseline_gap"])
        self.assertIsNone(report["current_external_baselines"][0]["baseline_score"])

    def test_changed_anchor_keeps_external_target_but_clears_old_method_scores(self):
        self.t.set_evaluation_anchor()
        self.t.set_baseline_roster(status="MATCHED", baseline_score=0.85, our_score=0.83)
        original_rows = self.state()["dataset_baseline_roster"]["rows"]
        self.t.set_evaluation_anchor(method_cluster_id="M-NEW", reason="Different mechanism")
        report = json.loads(self.t.run_cli("status", self.t.state, "--window").stdout)
        for old, row in zip(original_rows, report["current_external_baselines"]):
            self.assertEqual(row["baseline"], old["baseline"])
            self.assertEqual(row["source"], old["source"])
            self.assertEqual(row["baseline_score"], 0.85)
            self.assertIsNone(row["our_score"])
            self.assertEqual(row["status"], "IDENTIFIED")
            self.assertNotIn("ours-baseline=", row["gap"])
        for card in report["research_window"]["l2_cards"]:
            if card["kind"] == "baseline_comparison":
                self.assertNotIn("latest_result", card)
        self.assertEqual(self.state()["dataset_baseline_roster_history"][-1]["rows"], original_rows)
        self.t.run_cli("audit", self.t.state)
        self.t.set_baseline_roster(status="MATCHED", baseline_score=0.85, our_score=0.828)
        report = json.loads(self.t.run_cli("status", self.t.state, "--window").stdout)
        self.assertEqual(report["current_external_baselines"][0]["our_score"], 0.828)
        self.assertEqual(report["pending_pi_questions"], [])
        self.t.set_evaluation_anchor(method_cluster_id="M-NEW", primary_metric="accuracy", reason="Different metric")
        self.assertIsNone(self.state()["dataset_baseline_roster"]["rows"][0]["our_score"])

    def test_meaning_preserving_legacy_anchor_relock_keeps_matched_scores(self):
        self.t.set_evaluation_anchor()
        self.t.set_baseline_roster(status="MATCHED", baseline_score=0.85, our_score=0.83)
        state = self.state()
        state["evaluation_anchor"]["legacy_derived"] = True
        self.t.state.write_text(json.dumps(state), encoding="utf-8")
        self.t.run_cli(
            "evaluation-anchor", self.t.state, "--problem-path", "P-DOMAIN",
            "--problem-path", "P-SHORTCUT", "--problem-id", "P-SHORTCUT",
            "--method-cluster-id", "M-RESIDUAL", "--falsifiable-prediction",
            state["evaluation_anchor"]["falsifiable_prediction"], "--primary-metric",
            "balanced accuracy", "--metric-scale", "unit_interval",
            "--metric-direction", "higher_is_better", "--reason", "Explicitly relock identical legacy scope",
        )
        self.assertEqual(self.state()["dataset_baseline_roster"]["rows"], state["dataset_baseline_roster"]["rows"])
        self.t.run_cli("audit", self.t.state)

    def test_legacy_note_is_preserved_without_inventing_validity(self):
        import re
        self.update(extra=("--best-result", "0.820", *self.focus_flags()))
        note = re.sub(r"^<!-- RPW:RESEARCH_DATA .+ -->\n", "", self.t.l2.read_text(encoding="utf-8"), flags=re.MULTILINE)
        self.t.l2.write_text(note, encoding="utf-8")
        self.t.run_cli("window-start", self.t.state, "--instruction", "Continue legacy research")
        self.update(extra=("--latest-result", "0.81"))
        self.assertIn("best_result: 0.820", self.t.l2.read_text(encoding="utf-8"))
        self.assertIn("Legacy research", self.t.l2.read_text(encoding="utf-8"))
        self.assertNotIn("best_result", self.current_card()[0])

    def test_multiline_scientific_context_round_trips_in_one_record(self):
        hypothesis = "First explanation\nSecond explanation with --> and <tokens>"
        self.update(extra=("--set-current", "--hypothesis", hypothesis, "--current-action", "Distinguish both explanations"))
        self.t.run_cli("window-start", self.t.state, "--instruction", "Continue")
        self.update(extra=("--latest-result", "0.81"))
        self.assertEqual(self.current_card()[0]["hypothesis"], hypothesis)


if __name__ == "__main__":
    unittest.main()
