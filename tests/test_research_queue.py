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
        self.assertIn("cannot confirm", result.stderr)

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


if __name__ == "__main__":
    unittest.main()
