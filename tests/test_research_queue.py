from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "research_queue.py"


class ResearchQueueCLITest(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.state = self.root / ".codex" / "research-paper-workflow.json"

    def tearDown(self) -> None:
        self.temp.cleanup()

    def run_cli(self, *args: str, ok: bool = True) -> subprocess.CompletedProcess[str]:
        result = subprocess.run(
            [sys.executable, "-X", "utf8", str(SCRIPT), *map(str, args)],
            cwd=self.root,
            text=True,
            capture_output=True,
            encoding="utf-8",
        )
        if ok and result.returncode != 0:
            self.fail(f"CLI failed ({result.returncode}): {result.stderr}\n{result.stdout}")
        if not ok and result.returncode == 0:
            self.fail(f"CLI unexpectedly passed: {result.stdout}")
        return result

    def init_exploration(self) -> None:
        self.run_cli(
            "init",
            self.state,
            "--project",
            "demo",
            "--phase",
            "exploration",
            "--venue-or-window",
            "ICASSP",
            "--domain",
            "structural MRI",
            "--pi-decision",
            "Use ICASSP and structural MRI",
            "--pi-outcome",
            "select",
        )

    @property
    def l1(self) -> Path:
        return self.root / ".codex" / "research" / "L1-directions.md"

    @property
    def l2(self) -> Path:
        return self.root / ".codex" / "research" / "L2" / "D001.md"

    def managed_text(self, path: Path, name: str) -> str:
        text = path.read_text(encoding="utf-8")
        start = f"<!-- RPW:{name}:START -->"
        end = f"<!-- RPW:{name}:END -->"
        return text.split(start, 1)[1].split(end, 1)[0]

    def add_answer(
        self,
        layer: str,
        text: str,
        outcome: str = "approve",
        decision: str = "approved",
        target: str | None = None,
        revisit_condition: str | None = None,
    ) -> str:
        if target is None:
            defaults = {
                "compass": "compass:C001",
                "direction": "direction:D001",
                "science": "science:S001",
                "paper": "paper:P001",
            }
            target = defaults.get(layer, f"{layer}:decision")
        added = self.run_cli(
            "question",
            self.state,
            "--layer",
            layer,
            "--target",
            target,
            "--text",
            text,
        )
        question_id = json.loads(added.stdout)["added"]["id"]
        answer_args = [
            "answer",
            self.state,
            "--id",
            question_id,
            "--decision",
            decision,
            "--outcome",
            outcome,
        ]
        if revisit_condition is not None:
            answer_args.extend(["--revisit-condition", revisit_condition])
        self.run_cli(*answer_args)
        return question_id

    def confirm_direction(self, decision_id: str) -> None:
        self.run_cli(
            "confirm",
            self.state,
            "--layer",
            "direction",
            "--id",
            "D001",
            "--record",
            self.l1,
            "--decision-id",
            decision_id,
            "--task-type",
            "cross-site classification",
            "--dataset",
            "Dataset-A+Dataset-B",
            "--competitive-bar",
            "beat the strongest matched baseline",
            "--novelty-sufficiency",
            "a distinct problem-linked mechanism",
            "--generalization-requirement",
            "second dataset required",
            "--paper-ready-threshold",
            "stable gain and matched external comparison",
        )

    def confirm_science(self, decision_id: str) -> None:
        self.run_cli(
            "confirm",
            self.state,
            "--layer",
            "science",
            "--id",
            "S001",
            "--record",
            self.l2,
            "--decision-id",
            decision_id,
            "--direction-id",
            "D001",
            "--problem",
            "site-specific shortcuts",
            "--core-mechanism",
            "source-identifiable residual representation",
            "--innovation-claim",
            "remove shortcut information without target labels",
            "--external-baseline-status",
            "key matched comparison complete",
            "--ceiling-summary",
            "promising stable gain across held sites",
            "--nearest-work-record",
            self.l2,
            "--baseline-record",
            self.l2,
            "--result-record",
            self.l2,
        )

    def enter_paper_ready(self, assessment: Path, ok: bool = True) -> subprocess.CompletedProcess[str]:
        return self.run_cli(
            "phase",
            self.state,
            "--set",
            "paper_ready_pending_pi",
            "--assessment",
            assessment,
            "--competitive-bar-assessment",
            "met with a protocol-matched gain",
            "--novelty-assessment",
            "nearest-work difference verified",
            "--generalization-assessment",
            "required held-site evidence complete",
            "--paper-ready-threshold-assessment",
            "threshold met",
            "--narrowest-supported-claim",
            "a narrow supported claim",
            "--strongest-matched-comparison",
            "matched baseline B",
            "--remaining-objection",
            "limited sample size",
            "--necessary-work",
            "none",
            "--optional-work",
            "one sensitivity analysis",
            ok=ok,
        )

    def test_init_creates_scaffold_and_cannot_start_late(self) -> None:
        output = self.run_cli("init", self.state, "--project", "demo")
        self.assertEqual(json.loads(output.stdout)["phase"], "discussion")
        self.assertTrue(self.l1.is_file())
        self.assertTrue(self.l1.parent.joinpath("L2").is_dir())
        state = json.loads(self.state.read_text(encoding="utf-8"))
        root_audit = next(
            iter(state["instruction_maintenance"]["audits_by_scope"].values())
        )
        self.assertEqual(
            root_audit["status"],
            "NO_PROJECT_INSTRUCTIONS",
        )

        late = self.root / "late.json"
        result = self.run_cli(
            "init",
            late,
            "--project",
            "late",
            "--phase",
            "paper_ready_pending_pi",
            ok=False,
        )
        self.assertNotEqual(result.returncode, 0)

    def test_exploration_init_requires_confirmed_compass(self) -> None:
        result = self.run_cli(
            "init",
            self.state,
            "--project",
            "demo",
            "--phase",
            "exploration",
            ok=False,
        )
        self.assertIn("requires --venue-or-window", result.stderr)
        self.assertFalse(self.l1.exists())

    def test_direction_requires_confirmed_compass(self) -> None:
        self.run_cli("init", self.state, "--project", "demo")
        question_id = self.add_answer(
            "direction", "Choose D001?", outcome="select", decision="Select D001"
        )
        result = self.run_cli(
            "confirm",
            self.state,
            "--layer",
            "direction",
            "--id",
            "D001",
            "--record",
            self.l1,
            "--decision-id",
            question_id,
            "--task-type",
            "task",
            "--dataset",
            "data",
            "--competitive-bar",
            "bar",
            "--novelty-sufficiency",
            "novel",
            "--generalization-requirement",
            "none",
            "--paper-ready-threshold",
            "threshold",
            ok=False,
        )
        self.assertIn("complete research compass", result.stderr)

    def test_rejected_answer_cannot_confirm_direction(self) -> None:
        self.init_exploration()
        l1_text = self.l1.read_text(encoding="utf-8")
        self.assertIn("Venue or submission window: ICASSP", l1_text)
        self.assertIn("Domain: structural MRI", l1_text)
        question_id = self.add_answer(
            "direction", "Choose D001?", outcome="reject", decision="Reject D001"
        )
        result = self.run_cli(
            "confirm",
            self.state,
            "--layer",
            "direction",
            "--id",
            "D001",
            "--record",
            self.l1,
            "--decision-id",
            question_id,
            "--task-type",
            "task",
            "--dataset",
            "data",
            "--competitive-bar",
            "bar",
            "--novelty-sufficiency",
            "novel",
            "--generalization-requirement",
            "none",
            "--paper-ready-threshold",
            "threshold",
            ok=False,
        )
        self.assertIn("cannot authorize", result.stderr)

    def test_full_typed_flow_reaches_paper_handoff(self) -> None:
        self.init_exploration()
        direction_q = self.add_answer(
            "direction", "Choose D001?", outcome="select", decision="Select D001"
        )
        self.confirm_direction(direction_q)
        self.assertTrue(self.l2.is_file())
        l1_text = self.l1.read_text(encoding="utf-8")
        self.assertIn("Confirmed direction checkpoint", l1_text)
        self.assertIn("Competitive bar: beat the strongest matched baseline", l1_text)

        science_q = self.add_answer("science", "Promote S001?")
        self.confirm_science(science_q)
        l2_text = self.l2.read_text(encoding="utf-8")
        self.assertIn("Confirmed science checkpoint", l2_text)
        self.assertIn("L2 status: `ACTIVE_PI_CONFIRMED`", l2_text)

        assessment = self.root / "paper-ready.md"
        assessment.write_text("# Paper ready\n\nPASS\n", encoding="utf-8")
        self.enter_paper_ready(assessment)
        paper_q = self.add_answer("paper", "Enter writing and use this claim?")
        final = self.run_cli(
            "confirm",
            self.state,
            "--layer",
            "paper",
            "--id",
            "P001",
            "--record",
            assessment,
            "--decision-id",
            paper_q,
            "--science-id",
            "S001",
            "--headline-claim",
            "A narrow supported claim",
            "--handoff-target",
            "paper-submission-orchestrator",
        )
        summary = json.loads(final.stdout)
        self.assertEqual(summary["phase"], "paper_handoff_approved")
        self.assertEqual(summary["control_issues"], [])
        self.assertIn("Confirmed paper checkpoint", assessment.read_text(encoding="utf-8"))
        self.run_cli("audit", self.state)

    def test_five_questions_pause_blocks_phase_advance(self) -> None:
        self.init_exploration()
        for index in range(5):
            self.run_cli(
                "question",
                self.state,
                "--layer",
                "other",
                "--target",
                f"other:q{index}",
                "--text",
                f"q{index}",
            )
        result = self.run_cli(
            "phase", self.state, "--set", "confirmed_project", ok=False
        )
        self.assertIn("PAUSED_FOR_PI", result.stderr)
        self.run_cli(
            "answer",
            self.state,
            "--id",
            "Q001",
            "--decision",
            "noted",
            "--outcome",
            "informational",
        )
        status = json.loads(self.run_cli("status", self.state).stdout)
        self.assertTrue(status["paused_for_pi"])
        self.assertEqual(status["pending_macro_count"], 5)
        self.run_cli(
            "answer",
            self.state,
            "--id",
            "Q001",
            "--decision",
            "ask after the baseline finishes",
            "--outcome",
            "defer",
            "--revisit-condition",
            "baseline job reaches completed or failed",
        )
        status = json.loads(self.run_cli("status", self.state).stdout)
        self.assertFalse(status["paused_for_pi"])
        self.assertEqual(status["pending_macro_count"], 4)
        self.assertEqual(status["deferred_pi_count"], 1)

    def test_missing_l2_record_blocks_paper_ready_transition(self) -> None:
        self.init_exploration()
        self.confirm_direction(
            self.add_answer("direction", "Choose D001?", outcome="select")
        )
        self.confirm_science(self.add_answer("science", "Promote S001?"))
        self.l2.unlink()
        assessment = self.root / "paper-ready.md"
        assessment.write_text("# Paper ready\n", encoding="utf-8")
        result = self.enter_paper_ready(assessment, ok=False)
        self.assertIn("complete L1 and L2", result.stderr)

    def test_legacy_v3_state_is_flagged_for_reconfirmation(self) -> None:
        self.state.parent.mkdir(parents=True)
        legacy = {
            "schema_version": 3,
            "project": "legacy",
            "phase": "confirmed_project",
            "status": "ACTIVE",
            "paused_for_pi": False,
            "frozen_by_pi": {},
            "frozen_history": [],
            "layer_checkpoints": {
                "direction": {
                    "status": "CONFIRMED_BY_PI",
                    "id": "D001",
                    "summary": "task=x; dataset=y",
                    "confirmed_at": "2026-01-01T00:00:00+00:00",
                    "decision_source": {"type": "answered_question", "decision": "yes"},
                },
                "science": {
                    "status": "UNSET",
                    "id": None,
                    "summary": None,
                    "confirmed_at": None,
                    "decision_source": None,
                },
            },
            "checkpoint_history": [],
            "macro_questions": [],
            "notifications": [],
            "created_at": "2026-01-01T00:00:00+00:00",
            "updated_at": "2026-01-01T00:00:00+00:00",
        }
        self.state.write_text(json.dumps(legacy), encoding="utf-8")
        result = self.run_cli("audit", self.state, ok=False)
        summary = json.loads(result.stdout)
        codes = {issue["code"] for issue in summary["control_issues"]}
        self.assertIn("LEGACY_DIRECTION_NEEDS_RECONFIRMATION", codes)
        self.assertIn("COMPASS_CHECKPOINT_INCOMPLETE", codes)

    def test_schema_v4_science_without_evidence_refs_needs_audit(self) -> None:
        self.init_exploration()
        self.confirm_direction(
            self.add_answer("direction", "Choose D001?", outcome="select")
        )
        self.confirm_science(self.add_answer("science", "Promote S001?"))
        state = json.loads(self.state.read_text(encoding="utf-8"))
        state["schema_version"] = 4
        del state["layer_checkpoints"]["science"]["payload"]["evidence_refs"]
        for question in state["macro_questions"]:
            for field in (
                "decision_target",
                "consumed_by",
                "responses",
                "revisit_condition",
                "deferred_at",
                "reopened_at",
            ):
                question.pop(field, None)
        self.state.write_text(json.dumps(state), encoding="utf-8")
        result = self.run_cli("audit", self.state, ok=False)
        summary = json.loads(result.stdout)
        codes = {issue["code"] for issue in summary["control_issues"]}
        self.assertIn("LEGACY_SCIENCE_NEEDS_RECONFIRMATION", codes)

    def test_schema_v5_migrates_without_changing_scientific_state(self) -> None:
        self.init_exploration()
        state = json.loads(self.state.read_text(encoding="utf-8"))
        original_compass = state["layer_checkpoints"]["compass"]
        state["schema_version"] = 5
        state.pop("instruction_maintenance")
        self.state.write_text(json.dumps(state), encoding="utf-8")

        summary = json.loads(self.run_cli("status", self.state).stdout)
        self.assertEqual(summary["schema_version"], 7)
        self.assertEqual(summary["layer_checkpoints"]["compass"], original_compass)
        self.assertEqual(
            summary["instruction_maintenance"]["recent_updates"], []
        )

    def test_direction_change_invalidates_science(self) -> None:
        self.init_exploration()
        self.confirm_direction(
            self.add_answer("direction", "Choose D001?", outcome="select")
        )
        self.confirm_science(self.add_answer("science", "Promote S001?"))
        result = self.run_cli(
            "confirm",
            self.state,
            "--layer",
            "direction",
            "--id",
            "D002",
            "--record",
            self.l1,
            "--pi-decision",
            "Switch to D002",
            "--pi-outcome",
            "select",
            "--task-type",
            "new task",
            "--dataset",
            "new data",
            "--competitive-bar",
            "new bar",
            "--novelty-sufficiency",
            "new novelty rule",
            "--generalization-requirement",
            "not required",
            "--paper-ready-threshold",
            "new threshold",
        )
        summary = json.loads(result.stdout)
        self.assertTrue(
            summary["layer_checkpoints"]["science"]["status"].startswith("STALE_AFTER")
        )
        self.assertEqual(summary["phase"], "confirmed_project")

    def test_scoped_approval_cannot_be_reused_for_another_checkpoint(self) -> None:
        self.init_exploration()
        direction_q = self.add_answer(
            "direction",
            "Choose D001?",
            outcome="select",
            decision="Select D001",
        )
        self.confirm_direction(direction_q)
        result = self.run_cli(
            "confirm",
            self.state,
            "--layer",
            "science",
            "--id",
            "S001",
            "--record",
            self.l2,
            "--decision-id",
            direction_q,
            "--direction-id",
            "D001",
            "--problem",
            "problem",
            "--core-mechanism",
            "mechanism",
            "--innovation-claim",
            "claim",
            "--external-baseline-status",
            "matched",
            "--ceiling-summary",
            "summary",
            "--nearest-work-record",
            self.l2,
            "--baseline-record",
            self.l2,
            "--result-record",
            self.l2,
            ok=False,
        )
        self.assertTrue(
            "belongs to layer" in result.stderr
            or "already consumed" in result.stderr
            or "targets" in result.stderr
        )

    def test_older_approval_is_invalid_after_a_newer_decision_for_same_target(self) -> None:
        self.init_exploration()
        old_approval = self.add_answer(
            "direction", "Approve D001?", outcome="approve", decision="approve old D001"
        )
        newer_reject = self.add_answer(
            "direction", "Reconsider D001?", outcome="reject", decision="reject D001"
        )
        result = self.run_cli(
            "confirm",
            self.state,
            "--layer",
            "direction",
            "--id",
            "D001",
            "--record",
            self.l1,
            "--decision-id",
            old_approval,
            "--task-type",
            "task",
            "--dataset",
            "data",
            "--competitive-bar",
            "bar",
            "--novelty-sufficiency",
            "novel",
            "--generalization-requirement",
            "none",
            "--paper-ready-threshold",
            "threshold",
            ok=False,
        )
        self.assertIn("superseded", result.stderr)
        state = json.loads(self.state.read_text(encoding="utf-8"))
        questions = {q["id"]: q for q in state["macro_questions"]}
        self.assertEqual(questions[old_approval]["superseded_by"], newer_reject)
        self.assertEqual(state["layer_checkpoints"]["direction"]["status"], "UNSET")

    def test_latest_approval_for_reasked_target_can_confirm(self) -> None:
        self.init_exploration()
        self.add_answer(
            "direction", "Reject D001 first?", outcome="reject", decision="reject first"
        )
        latest = self.add_answer(
            "direction", "Approve revised D001?", outcome="select", decision="select revised D001"
        )
        self.confirm_direction(latest)
        state = json.loads(self.state.read_text(encoding="utf-8"))
        self.assertEqual(state["layer_checkpoints"]["direction"]["id"], "D001")

    def test_managed_current_blocks_replace_stale_compass_direction_and_science(self) -> None:
        self.init_exploration()
        self.run_cli(
            "confirm",
            self.state,
            "--layer",
            "compass",
            "--id",
            "C002",
            "--record",
            self.l1,
            "--pi-decision",
            "Switch to KDD recommender systems",
            "--pi-outcome",
            "select",
            "--venue-or-window",
            "KDD",
            "--domain",
            "recommender systems",
        )
        compass = self.managed_text(self.l1, "COMPASS_CURRENT")
        self.assertIn("KDD", compass)
        self.assertNotIn("ICASSP", compass)

        self.confirm_direction(
            self.add_answer("direction", "Choose D001?", outcome="select")
        )
        self.run_cli(
            "confirm",
            self.state,
            "--layer",
            "direction",
            "--id",
            "D002",
            "--record",
            self.l1,
            "--pi-decision",
            "Switch to D002",
            "--pi-outcome",
            "select",
            "--task-type",
            "sequential recommendation",
            "--dataset",
            "Dataset-C",
            "--competitive-bar",
            "new-bar",
            "--novelty-sufficiency",
            "new novelty",
            "--generalization-requirement",
            "not required",
            "--paper-ready-threshold",
            "new threshold",
        )
        direction = self.managed_text(self.l1, "DIRECTION_DECISION_CURRENT")
        standard = self.managed_text(self.l1, "DIRECTION_STANDARD_CURRENT")
        self.assertIn("D002", direction)
        self.assertIn("Dataset-C", direction)
        self.assertIn("new-bar", standard)
        self.assertNotIn("beat the strongest matched baseline", standard)

        l2_d2 = self.root / ".codex" / "research" / "L2" / "D002.md"
        for science_id, problem in (("S001", "old problem"), ("S002", "new problem")):
            self.run_cli(
                "confirm",
                self.state,
                "--layer",
                "science",
                "--id",
                science_id,
                "--record",
                l2_d2,
                "--pi-decision",
                f"Promote {science_id}",
                "--pi-outcome",
                "approve",
                "--direction-id",
                "D002",
                "--problem",
                problem,
                "--core-mechanism",
                f"mechanism {science_id}",
                "--innovation-claim",
                f"claim {science_id}",
                "--external-baseline-status",
                "matched",
                "--ceiling-summary",
                "competitive",
                "--nearest-work-record",
                l2_d2,
                "--baseline-record",
                l2_d2,
                "--result-record",
                l2_d2,
            )
        science = self.managed_text(l2_d2, "SCIENCE_CURRENT")
        self.assertIn("S002", science)
        self.assertIn("new problem", science)
        self.assertNotIn("old problem", science)

    def test_checkpoint_history_does_not_duplicate_stale_science(self) -> None:
        self.init_exploration()
        self.confirm_direction(self.add_answer("direction", "Choose D001?", outcome="select"))
        self.confirm_science(self.add_answer("science", "Promote S001?"))
        self.run_cli(
            "confirm",
            self.state,
            "--layer",
            "direction",
            "--id",
            "D002",
            "--record",
            self.l1,
            "--pi-decision",
            "Switch direction",
            "--pi-outcome",
            "select",
            "--task-type",
            "new task",
            "--dataset",
            "new data",
            "--competitive-bar",
            "new bar",
            "--novelty-sufficiency",
            "new novelty",
            "--generalization-requirement",
            "none",
            "--paper-ready-threshold",
            "new threshold",
        )
        l2_d2 = self.root / ".codex" / "research" / "L2" / "D002.md"
        self.run_cli(
            "confirm",
            self.state,
            "--layer",
            "science",
            "--id",
            "S002",
            "--record",
            l2_d2,
            "--pi-decision",
            "Promote replacement science",
            "--pi-outcome",
            "approve",
            "--direction-id",
            "D002",
            "--problem",
            "p2",
            "--core-mechanism",
            "m2",
            "--innovation-claim",
            "i2",
            "--external-baseline-status",
            "matched",
            "--ceiling-summary",
            "good",
            "--nearest-work-record",
            l2_d2,
            "--baseline-record",
            l2_d2,
            "--result-record",
            l2_d2,
        )
        state = json.loads(self.state.read_text(encoding="utf-8"))
        science_history = [h for h in state["checkpoint_history"] if h["layer"] == "science"]
        self.assertEqual(len(science_history), 1)

    def test_deferred_question_requires_condition_and_can_reopen(self) -> None:
        self.init_exploration()
        added = self.run_cli(
            "question",
            self.state,
            "--layer",
            "resource",
            "--target",
            "resource:gpu-rental",
            "--text",
            "Rent a GPU?",
        )
        question_id = json.loads(added.stdout)["added"]["id"]
        missing = self.run_cli(
            "answer",
            self.state,
            "--id",
            question_id,
            "--decision",
            "decide later",
            "--outcome",
            "defer",
            ok=False,
        )
        self.assertIn("requires --revisit-condition", missing.stderr)
        self.run_cli(
            "answer",
            self.state,
            "--id",
            question_id,
            "--decision",
            "decide after local screening",
            "--outcome",
            "defer",
            "--revisit-condition",
            "local screen completes",
        )
        deferred = json.loads(self.run_cli("status", self.state).stdout)
        self.assertEqual(deferred["pending_macro_count"], 0)
        self.assertEqual(deferred["deferred_pi_count"], 1)
        self.assertEqual(
            deferred["deferred_pi_questions"][0]["revisit_condition"],
            "local screen completes",
        )
        self.run_cli("audit", self.state)
        self.run_cli(
            "reopen",
            self.state,
            "--id",
            question_id,
            "--reason",
            "local screen completed",
        )
        reopened = json.loads(self.run_cli("status", self.state).stdout)
        self.assertEqual(reopened["pending_macro_count"], 1)
        self.assertEqual(reopened["deferred_pi_count"], 0)

    def test_reserved_core_field_cannot_be_duplicated_as_frozen(self) -> None:
        self.init_exploration()
        result = self.run_cli(
            "freeze",
            self.state,
            "--key",
            "domain",
            "--value",
            "NLP",
            "--pi-decision",
            "Change the domain",
            "--pi-outcome",
            "approve",
            ok=False,
        )
        self.assertIn("cannot be duplicated", result.stderr)

        state = json.loads(self.state.read_text(encoding="utf-8"))
        state["frozen_by_pi"]["domain"] = {
            "value": "NLP",
            "frozen_at": "2026-01-01T00:00:00+00:00",
            "decision_source": {
                "type": "direct_pi_instruction",
                "decision": "legacy duplicate",
                "outcome": "approve",
            },
        }
        self.state.write_text(json.dumps(state), encoding="utf-8")
        audit = self.run_cli("audit", self.state, ok=False)
        codes = {
            issue["code"]
            for issue in json.loads(audit.stdout)["control_issues"]
        }
        self.assertIn("RESERVED_FIELD_DUPLICATED_IN_FROZEN_BY_PI", codes)

    def test_paper_ready_requires_structured_assessment(self) -> None:
        self.init_exploration()
        self.confirm_direction(
            self.add_answer("direction", "Choose D001?", outcome="select")
        )
        self.confirm_science(self.add_answer("science", "Promote S001?"))
        assessment = self.root / "paper-ready.md"
        assessment.write_text("# Paper ready\n", encoding="utf-8")
        result = self.run_cli(
            "phase",
            self.state,
            "--set",
            "paper_ready_pending_pi",
            "--assessment",
            assessment,
            ok=False,
        )
        self.assertIn("missing structured fields", result.stderr)

    def test_recent_notifications_are_bounded(self) -> None:
        self.init_exploration()
        for index in range(55):
            self.run_cli("notify", self.state, "--text", f"notice-{index}")
        summary = json.loads(self.run_cli("status", self.state).stdout)
        self.assertEqual(summary["notification_count"], 50)
        self.assertEqual(summary["notification_compacted_count"], 5)

    def test_active_job_is_resumable_and_removable(self) -> None:
        self.init_exploration()
        added = self.run_cli(
            "job-add",
            self.state,
            "--id",
            "J001",
            "--description",
            "baseline run",
            "--command",
            "python run.py",
            "--status",
            "running",
            "--next-action",
            "poll result",
        )
        self.assertEqual(len(json.loads(added.stdout)["state"]["active_jobs"]), 1)
        self.run_cli(
            "job-update",
            self.state,
            "--id",
            "J001",
            "--status",
            "completed",
            "--result",
            "results.json",
        )
        self.run_cli("job-remove", self.state, "--id", "J001")
        summary = json.loads(self.run_cli("status", self.state).stdout)
        self.assertEqual(summary["active_jobs"], [])

    def test_agents_audit_discovers_effective_chain_and_size_review(self) -> None:
        root_agents = self.root / "AGENTS.md"
        nested = self.root / "src" / "service"
        nested.mkdir(parents=True)
        nested_agents = nested / "AGENTS.md"
        root_agents.write_text("r" * (12 * 1024 + 1), encoding="utf-8")
        nested_agents.write_text("nested rules", encoding="utf-8")
        self.run_cli("init", self.state, "--project", "demo")

        result = self.run_cli("agents-audit", self.state, "--cwd", nested)
        audit = json.loads(result.stdout)["instruction_audit"]
        self.assertEqual(audit["status"], "REVIEW")
        self.assertEqual(
            [item["path"] for item in audit["effective_files"]],
            ["AGENTS.md", "src/service/AGENTS.md"],
        )
        codes = {issue["code"] for issue in audit["issues"]}
        self.assertIn("ROOT_AGENTS_REVIEW_REQUIRED", codes)
        stored = json.loads(self.state.read_text(encoding="utf-8"))
        scopes = {
            audit["scope_cwd"]
            for audit in stored["instruction_maintenance"]["audits_by_scope"].values()
        }
        self.assertEqual(scopes, {".", "src/service"})

    def test_unrecorded_agents_change_is_a_control_issue(self) -> None:
        agents = self.root / "AGENTS.md"
        agents.write_text("stable rules", encoding="utf-8")
        self.run_cli("init", self.state, "--project", "demo")
        agents.write_text("changed rules", encoding="utf-8")

        result = self.run_cli("audit", self.state, ok=False)
        codes = {
            issue["code"]
            for issue in json.loads(result.stdout)["control_issues"]
        }
        self.assertIn("PROJECT_INSTRUCTIONS_CHANGED_SINCE_AUDIT", codes)

    def test_agents_compaction_records_bounded_receipt_and_notification(self) -> None:
        agents = self.root / "AGENTS.md"
        canonical = self.root / "docs" / "instruction-details.md"
        canonical.parent.mkdir()
        canonical.write_text("old detail retained here\n", encoding="utf-8")
        agents.write_text("stable rule\n" + "old detail\n" * 20, encoding="utf-8")
        self.run_cli("init", self.state, "--project", "demo")
        agents.write_text("stable rule\n", encoding="utf-8")

        missing_source = self.run_cli(
            "agents-record",
            self.state,
            "--path",
            agents,
            "--kind",
            "compaction",
            "--reason",
            "Moved detail",
            "--summary",
            "压缩项目说明。",
            ok=False,
        )
        self.assertIn("--canonical-source", missing_source.stderr)

        result = self.run_cli(
            "agents-record",
            self.state,
            "--path",
            agents,
            "--kind",
            "compaction",
            "--reason",
            "Moved duplicated detail to its canonical project record",
            "--summary",
            "删去重复历史，只保留稳定规则；研究结论和权限没有变化。",
            "--canonical-source",
            canonical,
        )
        payload = json.loads(result.stdout)
        receipt = payload["recorded"]
        self.assertLess(receipt["after_bytes"], receipt["before_bytes"])
        self.assertEqual(
            receipt["decision_source"]["type"], "autonomous_maintenance"
        )
        self.assertIn("项目说明维护", payload["notification"]["text"])
        self.run_cli("audit", self.state)
        canonical.unlink()
        missing = self.run_cli("audit", self.state, ok=False)
        codes = {
            issue["code"]
            for issue in json.loads(missing.stdout)["control_issues"]
        }
        self.assertIn("INSTRUCTION_COMPACTION_SOURCE_UNAVAILABLE", codes)

    def test_agents_audit_cannot_accept_an_unrecorded_change(self) -> None:
        agents = self.root / "AGENTS.md"
        agents.write_text("stable\n", encoding="utf-8")
        self.run_cli("init", self.state, "--project", "demo")
        state_before = json.loads(self.state.read_text(encoding="utf-8"))
        baseline = next(
            iter(state_before["instruction_maintenance"]["audits_by_scope"].values())
        )["observed_files"][0]["sha256"]
        agents.write_text("changed without receipt\n", encoding="utf-8")

        first = self.run_cli("agents-audit", self.state, ok=False)
        second = self.run_cli("agents-audit", self.state, ok=False)
        self.assertFalse(json.loads(first.stdout)["snapshot_updated"])
        self.assertFalse(json.loads(second.stdout)["snapshot_updated"])
        state_after = json.loads(self.state.read_text(encoding="utf-8"))
        still_baseline = next(
            iter(state_after["instruction_maintenance"]["audits_by_scope"].values())
        )["observed_files"][0]["sha256"]
        self.assertEqual(still_baseline, baseline)
        self.run_cli("audit", self.state, ok=False)

    def test_multiple_instruction_scopes_remain_independently_audited(self) -> None:
        (self.root / "AGENTS.md").write_text("root\n", encoding="utf-8")
        src = self.root / "src"
        docs = self.root / "docs"
        src.mkdir()
        docs.mkdir()
        src_agents = src / "AGENTS.md"
        src_agents.write_text("src stable\n", encoding="utf-8")
        (docs / "AGENTS.md").write_text("docs stable\n", encoding="utf-8")
        self.run_cli("init", self.state, "--project", "demo")
        self.run_cli("agents-audit", self.state, "--cwd", src)
        self.run_cli("agents-audit", self.state, "--cwd", docs)

        src_agents.write_text("src changed\n", encoding="utf-8")
        result = self.run_cli("agents-audit", self.state, "--cwd", docs, ok=False)
        self.assertIn("src", json.loads(result.stdout)["changed_scopes"])
        audit = self.run_cli("audit", self.state, ok=False)
        messages = "\n".join(
            issue["message"]
            for issue in json.loads(audit.stdout)["control_issues"]
        )
        self.assertIn("src", messages)
        self.run_cli(
            "agents-record",
            self.state,
            "--path",
            src_agents,
            "--kind",
            "mechanical",
            "--reason",
            "Update verified src command",
            "--summary",
            "更新 src 目录的已验证命令。",
        )
        self.run_cli("audit", self.state)

        root_agents = self.root / "AGENTS.md"
        root_agents.write_text("root changed\n", encoding="utf-8")
        self.run_cli(
            "agents-record",
            self.state,
            "--path",
            root_agents,
            "--kind",
            "mechanical",
            "--reason",
            "Update verified root command",
            "--summary",
            "更新根目录的已验证命令。",
        )
        self.run_cli("audit", self.state)

    def test_instruction_file_deletion_can_be_recorded(self) -> None:
        agents = self.root / "AGENTS.md"
        agents.write_text("obsolete scoped rules\n", encoding="utf-8")
        self.run_cli("init", self.state, "--project", "demo")
        agents.unlink()
        result = self.run_cli(
            "agents-record",
            self.state,
            "--path",
            agents,
            "--after-absent",
            "--kind",
            "mechanical",
            "--reason",
            "Remove obsolete instruction file",
            "--summary",
            "删除已经失效的项目说明文件。",
        )
        receipt = json.loads(result.stdout)["recorded"]
        self.assertTrue(receipt["after_absent"])
        self.assertIsNone(receipt["after_sha256"])
        self.run_cli("audit", self.state)

    def test_semantic_agents_update_consumes_scoped_pi_decision(self) -> None:
        agents = self.root / "AGENTS.md"
        agents.write_text("ask before external sends\n", encoding="utf-8")
        self.run_cli("init", self.state, "--project", "demo")
        agents.write_text("external sends are allowed\n", encoding="utf-8")

        missing = self.run_cli(
            "agents-record",
            self.state,
            "--path",
            agents,
            "--kind",
            "semantic",
            "--reason",
            "Change external-send authority",
            "--summary",
            "修改外发权限。",
            ok=False,
        )
        self.assertIn("requires --decision-id", missing.stderr)

        added = self.run_cli(
            "question",
            self.state,
            "--layer",
            "instructions",
            "--target",
            "instructions:AGENTS.md",
            "--text",
            "Change the external-send authority?",
        )
        question_id = json.loads(added.stdout)["added"]["id"]
        self.run_cli(
            "answer",
            self.state,
            "--id",
            question_id,
            "--decision",
            "Approve this exact instruction change",
            "--outcome",
            "approve",
        )
        result = self.run_cli(
            "agents-record",
            self.state,
            "--path",
            agents,
            "--kind",
            "semantic",
            "--reason",
            "Change external-send authority",
            "--summary",
            "按已确认决定修改外发权限。",
            "--decision-id",
            question_id,
        )
        payload = json.loads(result.stdout)
        self.assertEqual(
            payload["recorded"]["decision_source"]["question_id"], question_id
        )
        state = json.loads(self.state.read_text(encoding="utf-8"))
        question = next(q for q in state["macro_questions"] if q["id"] == question_id)
        self.assertEqual(question["consumed_by"]["type"], "instruction_update")
        self.run_cli("audit", self.state)

    def test_agents_audit_flags_project_chain_above_default_budget(self) -> None:
        (self.root / "AGENTS.md").write_text("x" * (32 * 1024 + 1), encoding="utf-8")
        self.run_cli("init", self.state, "--project", "demo")
        result = self.run_cli("agents-audit", self.state, ok=False)
        audit = json.loads(result.stdout)["instruction_audit"]
        self.assertEqual(audit["status"], "OVER_DEFAULT_LIMIT")
        codes = {issue["code"] for issue in audit["issues"]}
        self.assertIn("PROJECT_INSTRUCTION_CHAIN_DEFAULT_LIMIT_EXCEEDED", codes)

    def test_checkpoint_record_outside_project_is_rejected(self) -> None:
        self.init_exploration()
        question = self.add_answer("direction", "Choose D001?", outcome="select")
        with tempfile.TemporaryDirectory() as outside_raw:
            outside = Path(outside_raw) / "direction.md"
            outside.write_text("# outside\n", encoding="utf-8")
            result = self.run_cli(
                "confirm",
                self.state,
                "--layer",
                "direction",
                "--id",
                "D001",
                "--record",
                outside,
                "--decision-id",
                question,
                "--task-type",
                "task",
                "--dataset",
                "data",
                "--competitive-bar",
                "bar",
                "--novelty-sufficiency",
                "novel",
                "--generalization-requirement",
                "none",
                "--paper-ready-threshold",
                "threshold",
                ok=False,
            )
        self.assertIn("must stay inside", result.stderr)

    def test_external_science_evidence_is_read_only_and_allowed(self) -> None:
        self.init_exploration()
        self.confirm_direction(self.add_answer("direction", "Choose D001?", outcome="select"))
        with tempfile.TemporaryDirectory() as outside_raw:
            evidence = Path(outside_raw) / "evidence.md"
            original = "# external evidence\nimmutable source\n"
            evidence.write_text(original, encoding="utf-8")
            self.run_cli(
                "confirm",
                self.state,
                "--layer",
                "science",
                "--id",
                "S001",
                "--record",
                self.l2,
                "--pi-decision",
                "Promote S001",
                "--pi-outcome",
                "approve",
                "--direction-id",
                "D001",
                "--problem",
                "p",
                "--core-mechanism",
                "m",
                "--innovation-claim",
                "i",
                "--external-baseline-status",
                "matched",
                "--ceiling-summary",
                "good",
                "--nearest-work-record",
                evidence,
                "--baseline-record",
                evidence,
                "--result-record",
                evidence,
            )
            self.assertEqual(evidence.read_text(encoding="utf-8"), original)
        state = json.loads(self.state.read_text(encoding="utf-8"))
        ref = state["layer_checkpoints"]["science"]["payload"]["evidence_refs"]["results"]
        self.assertTrue(Path(ref["path"]).is_absolute())

    def test_schema_v6_migrates_target_revisions_and_instruction_scopes(self) -> None:
        self.init_exploration()
        first = self.add_answer("direction", "Approve once?", outcome="approve")
        second = self.add_answer("direction", "Reject later?", outcome="reject")
        state = json.loads(self.state.read_text(encoding="utf-8"))
        root_audit = next(
            iter(state["instruction_maintenance"]["audits_by_scope"].values())
        )
        state["schema_version"] = 6
        state.pop("decision_target_revisions")
        state["instruction_maintenance"].pop("audits_by_scope")
        state["instruction_maintenance"]["last_audit"] = root_audit
        for question in state["macro_questions"]:
            question.pop("target_revision")
            question.pop("superseded_by")
        self.state.write_text(json.dumps(state), encoding="utf-8")

        self.run_cli("notify", self.state, "--text", "save migration")
        migrated = json.loads(self.state.read_text(encoding="utf-8"))
        questions = {q["id"]: q for q in migrated["macro_questions"]}
        self.assertEqual(migrated["schema_version"], 7)
        self.assertEqual(questions[first]["superseded_by"], second)
        self.assertEqual(
            migrated["decision_target_revisions"]["direction:D001"], 2
        )
        self.assertEqual(
            len(migrated["instruction_maintenance"]["audits_by_scope"]), 1
        )


if __name__ == "__main__":
    unittest.main()
