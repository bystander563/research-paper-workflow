from __future__ import annotations

import importlib.util
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

    def comparison_roles(self, dataset: str) -> dict[str, dict[str, str]]:
        return {
            "dataset_origin": {
                "status": "COVERED",
                "evidence": f"{dataset} paper reference result recorded in L2",
            },
            "recent_top_conference": {
                "status": "COVERED",
                "evidence": f"recent top-conference comparator for {dataset}",
            },
            "different_published_mechanism": {
                "status": "COVERED",
                "evidence": f"different published mechanism for {dataset}",
            },
            "strong_simple": {
                "status": "COVERED",
                "evidence": f"strong simple comparator for {dataset}",
            },
        }

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

    def confirm_direction(
        self,
        decision_id: str,
        minimum_gain: float | None = None,
        paper_ready_threshold: str = "stable gain and matched external comparison",
        ok: bool = True,
    ) -> subprocess.CompletedProcess[str]:
        args = [
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
            "--primary-dataset",
            "Dataset-A",
            "--supporting-dataset",
            "Dataset-B",
            "--unexposed-dataset-search",
            "Dataset-C found as an unexposed transfer candidate",
            "--competitive-bar",
            "beat the strongest matched baseline",
            "--novelty-sufficiency",
            "a distinct problem-linked mechanism",
            "--generalization-requirement",
            "second dataset required",
            "--paper-ready-threshold",
            paper_ready_threshold,
        ]
        if minimum_gain is not None:
            args.extend(["--minimum-paper-gain-points", str(minimum_gain)])
        result = self.run_cli(*args, ok=ok)
        if ok:
            self.set_baseline_roster(status="IDENTIFIED")
        return result

    def set_baseline_roster(
        self,
        status: str,
        primary_metric: str = "balanced accuracy",
        metric_scale: str = "unit_interval",
        baseline_score: float = 0.80,
        our_score: float = 0.82,
    ) -> subprocess.CompletedProcess[str] | None:
        baseline_search_scope = "SIGIR/KDD/WWW/RecSys 2022-2026; searched 2026-08-28"
        baseline_source = "baseline citation and result table recorded in L2"
        state = json.loads(self.state.read_text(encoding="utf-8"))
        direction = state["layer_checkpoints"]["direction"]
        rows = []
        for index, adopted in enumerate(direction["payload"]["adopted_datasets"]):
            primary = adopted["role"] == "primary"
            rows.append(
                {
                    "dataset": adopted["dataset"],
                    "role": adopted["role"],
                    "baseline": (
                        "Baseline B, recent top-conference paper"
                        if primary
                        else "Baseline C, recent top-conference paper"
                    ),
                    "venue_year": "SIGIR 2025" if primary else "KDD 2024",
                    "source": (
                        baseline_source
                        if primary
                        else "supporting baseline citation recorded in L2"
                    ),
                    "search_scope": baseline_search_scope,
                    "protocol_match": (
                        "same task and protocol"
                        if primary
                        else "same task and dataset-specific protocol"
                    ),
                    "protocol_status": {
                        "MATCHED": "VERIFIED_MATCH",
                        "BLOCKED": "BLOCKED",
                        "IDENTIFIED": "PENDING_MATCH",
                    }[status],
                    "comparison_roles": self.comparison_roles(adopted["dataset"]),
                    "metric": primary_metric,
                    "metric_scale": metric_scale,
                    "baseline_score": baseline_score if status == "MATCHED" else None,
                    "our_score": our_score if status == "MATCHED" else None,
                    "status": status,
                }
            )
        current_rows = (state.get("dataset_baseline_roster") or {}).get("rows")
        if current_rows == rows:
            return None
        return self.run_cli(
            "baseline-roster",
            self.state,
            "--rows-json",
            json.dumps(rows),
            "--record",
            self.root
            / ".codex"
            / "research"
            / "L2"
            / f"{direction['id']}.md",
            "--reason",
            f"test fixture roster status {status}",
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
            "--problem-id",
            "P-SHORTCUT",
            "--method-cluster-id",
            "M-RESIDUAL",
            "--problem",
            "site-specific shortcuts",
            "--nearest-work-gap",
            "recent methods suppress domains but do not isolate shortcut information",
            "--paper-grade-rationale",
            "the unresolved shortcut mechanism changes the scientific estimand",
            "--core-mechanism",
            "source-identifiable residual representation",
            "--falsifiable-prediction",
            "removing source-identifiable residuals improves unseen-site accuracy",
            "--contribution-type",
            "mechanism",
            "--innovation-claim",
            "remove shortcut information without target labels",
            "--external-baseline-status",
            "key matched comparison complete",
            "--ceiling-summary",
            "promising stable gain across held sites",
            "--problem-portfolio-record",
            self.l2,
            "--nearest-work-record",
            self.l2,
            "--baseline-record",
            self.l2,
            "--result-record",
            self.l2,
        )

    def set_evaluation_anchor(
        self,
        primary_metric: str = "balanced accuracy",
        metric_scale: str = "unit_interval",
        reason: str = "official task metric selected before broad tuning",
        ok: bool = True,
    ) -> subprocess.CompletedProcess[str]:
        return self.run_cli(
            "evaluation-anchor",
            self.state,
            "--primary-metric",
            primary_metric,
            "--metric-scale",
            metric_scale,
            "--metric-direction",
            "higher_is_better",
            "--reason",
            reason,
            ok=ok,
        )

    def enter_paper_ready(
        self,
        assessment: Path,
        ok: bool = True,
        metric_scale: str = "unit_interval",
        baseline_score: float = 0.80,
        our_score: float = 0.82,
        primary_metric: str = "balanced accuracy",
        favorable_seed_selection: bool = False,
        seed_risk_decision_id: str | None = None,
        seed_risk_pi_decision: str | None = None,
        seed_risk_pi_outcome: str | None = None,
        set_anchor: bool = True,
        set_roster: bool = True,
    ) -> subprocess.CompletedProcess[str]:
        state = json.loads(self.state.read_text(encoding="utf-8"))
        if set_roster:
            self.set_baseline_roster(
                status="MATCHED",
                primary_metric=primary_metric,
                metric_scale=metric_scale,
                baseline_score=baseline_score,
                our_score=our_score,
            )
        state = json.loads(self.state.read_text(encoding="utf-8"))
        if set_anchor and state.get("evaluation_anchor") is None:
            self.set_evaluation_anchor(primary_metric, metric_scale)
        baseline_search_scope = "SIGIR/KDD/WWW/RecSys 2022-2026; searched 2026-08-28"
        baseline_source = "baseline citation and result table recorded in L2"
        dataset_baseline_matrix = json.dumps(
            [
                {
                    "dataset": "Dataset-A",
                    "role": "primary",
                    "baseline": "Baseline B, recent top-conference paper",
                    "venue_year": "SIGIR 2025",
                    "source": baseline_source,
                    "search_scope": baseline_search_scope,
                    "protocol_match": "same task and protocol",
                    "protocol_status": "VERIFIED_MATCH",
                    "comparison_roles": self.comparison_roles("Dataset-A"),
                    "metric": primary_metric,
                    "metric_scale": metric_scale,
                    "baseline_score": baseline_score,
                    "our_score": our_score,
                    "status": "MATCHED",
                },
                {
                    "dataset": "Dataset-B",
                    "role": "supporting",
                    "baseline": "Baseline C, recent top-conference paper",
                    "venue_year": "KDD 2024",
                    "source": "supporting baseline citation recorded in L2",
                    "search_scope": baseline_search_scope,
                    "protocol_match": "same task and dataset-specific protocol",
                    "protocol_status": "VERIFIED_MATCH",
                    "comparison_roles": self.comparison_roles("Dataset-B"),
                    "metric": primary_metric,
                    "metric_scale": metric_scale,
                    "baseline_score": baseline_score,
                    "our_score": our_score,
                    "status": "MATCHED",
                },
            ]
        )
        args = [
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
            "--specific-method",
            "residual removal with a source-identifiability penalty",
            "--final-results",
            f"{our_score} versus {baseline_score} on the primary matched evaluation",
            "--primary-comparison-dataset",
            "Dataset-A",
            "--dataset-baseline-matrix",
            dataset_baseline_matrix,
            "--recent-top-conference-baseline",
            "Baseline B, recent top-conference paper",
            "--baseline-venue-year",
            "SIGIR 2025",
            "--baseline-search-scope",
            baseline_search_scope,
            "--baseline-source",
            baseline_source,
            "--protocol-match-evidence",
            "same dataset, split, labels, metric, and evaluation procedure",
            "--evaluation-anchor-evidence",
            "the decision result was produced under the current metric anchor",
            "--stability-evidence",
            "project-appropriate repeat and uncertainty checks support the result",
            "--primary-metric",
            primary_metric,
            "--metric-scale",
            metric_scale,
            "--baseline-score",
            str(baseline_score),
            "--our-score",
            str(our_score),
        ]
        if favorable_seed_selection:
            args.append("--favorable-seed-selection")
        if seed_risk_decision_id is not None:
            args.extend(["--seed-risk-decision-id", seed_risk_decision_id])
        if seed_risk_pi_decision is not None:
            args.extend(["--seed-risk-pi-decision", seed_risk_pi_decision])
        if seed_risk_pi_outcome is not None:
            args.extend(["--seed-risk-pi-outcome", seed_risk_pi_outcome])
        return self.run_cli(*args, ok=ok)

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

        ignored = self.root / "ignored-compass.json"
        result = self.run_cli(
            "init",
            ignored,
            "--project",
            "ignored",
            "--venue-or-window",
            "ICASSP",
            ok=False,
        )
        self.assertIn("require --phase exploration", result.stderr)
        self.assertFalse(ignored.exists())

    def test_whitespace_cannot_create_scientific_authority_or_active_job(self) -> None:
        blank = self.root / "blank.json"
        result = self.run_cli(
            "init",
            blank,
            "--project",
            "demo",
            "--phase",
            "exploration",
            "--venue-or-window",
            " ",
            "--domain",
            " ",
            "--pi-decision",
            " ",
            "--pi-outcome",
            "select",
            ok=False,
        )
        self.assertIn("Starting in exploration requires", result.stderr)
        self.assertFalse(blank.exists())

        self.init_exploration()
        active = self.run_cli(
            "job-add",
            self.state,
            "--id",
            "J001",
            "--description",
            "candidate run",
            "--command",
            " ",
            "--status",
            "running",
            "--next-poll",
            "later",
            "--next-action",
            "inspect",
            ok=False,
        )
        self.assertIn("must contain non-whitespace text", active.stderr)

    def test_discussion_cannot_register_active_execution(self) -> None:
        self.run_cli("init", self.state, "--project", "demo")
        result = self.run_cli(
            "job-add",
            self.state,
            "--id",
            "J001",
            "--description",
            "premature run",
            "--command",
            "python run.py",
            "--status",
            "running",
            "--next-poll",
            "later",
            "--next-action",
            "inspect",
            ok=False,
        )
        self.assertIn("discussion", result.stderr)

    def test_checkpoint_rejects_fields_from_another_layer(self) -> None:
        self.init_exploration()
        question = self.add_answer("direction", "Choose D001?", outcome="select")
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
            question,
            "--science-id",
            "S001",
            ok=False,
        )
        self.assertIn("does not use: --science-id", result.stderr)

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
            "--primary-dataset",
            "data",
            "--unexposed-dataset-search",
            "searched registry; candidate data-2 found",
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
            "--primary-dataset",
            "data",
            "--unexposed-dataset-search",
            "searched registry; candidate data-2 found",
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

    def test_confirmed_checkpoint_requires_complete_authority_metadata(self) -> None:
        self.init_exploration()
        state = json.loads(self.state.read_text(encoding="utf-8"))
        state["layer_checkpoints"]["compass"]["decision_source"]["decision"] = ""
        state["layer_checkpoints"]["compass"]["record_sha256_at_confirmation"] = None
        self.state.write_text(json.dumps(state), encoding="utf-8")
        result = self.run_cli("audit", self.state, ok=False)
        codes = {
            issue["code"] for issue in json.loads(result.stdout)["control_issues"]
        }
        self.assertIn("COMPASS_CHECKPOINT_INCOMPLETE", codes)
        self.assertIn("COMPASS_CONFIRMED_PAYLOAD_INCOMPLETE", codes)

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
        stored = json.loads(self.state.read_text(encoding="utf-8"))
        self.assertIn("sha256_after_handoff", stored["paper_ready_assessment"])
        paper_source = stored["layer_checkpoints"]["paper"]["decision_source"]
        self.assertEqual(
            paper_source["paper_assessment_payload_sha256"],
            stored["paper_ready_assessment"]["payload_sha256_at_gate"],
        )
        self.assertEqual(
            paper_source["paper_assessment_recorded_at"],
            stored["paper_ready_assessment"]["recorded_at"],
        )
        self.run_cli("audit", self.state)
        paper_question = next(
            question
            for question in stored["macro_questions"]
            if question.get("id") == paper_source.get("question_id")
        )
        paper_question["created_at"] = "2020-01-01T00:00:00+00:00"
        self.state.write_text(json.dumps(stored), encoding="utf-8")
        receipt_audit = json.loads(
            self.run_cli("audit", self.state, ok=False).stdout
        )
        self.assertIn(
            "PAPER_DECISION_RECEIPT_NOT_BOUND",
            {issue["code"] for issue in receipt_audit["control_issues"]},
        )
        paper_source["paper_assessment_payload_sha256"] = "tampered-binding"
        self.state.write_text(json.dumps(stored), encoding="utf-8")
        audit = json.loads(self.run_cli("audit", self.state, ok=False).stdout)
        self.assertIn(
            "PAPER_DECISION_ASSESSMENT_NOT_BOUND",
            {issue["code"] for issue in audit["control_issues"]},
        )

    def test_pre_report_paper_approval_cannot_authorize_current_report(self) -> None:
        self.init_exploration()
        self.confirm_direction(
            self.add_answer("direction", "Choose D001?", outcome="select")
        )
        self.confirm_science(self.add_answer("science", "Promote S001?"))
        stale_paper_q = self.add_answer(
            "paper", "Enter writing before a report exists?", outcome="approve"
        )
        assessment = self.root / "paper-ready-after-old-approval.md"
        assessment.write_text("# Paper ready\n", encoding="utf-8")
        self.enter_paper_ready(assessment)

        blocked = self.run_cli(
            "confirm",
            self.state,
            "--layer",
            "paper",
            "--id",
            "P001",
            "--record",
            assessment,
            "--decision-id",
            stale_paper_q,
            "--science-id",
            "S001",
            "--headline-claim",
            "A narrow supported claim",
            "--handoff-target",
            "paper-submission-orchestrator",
            ok=False,
        )
        self.assertIn("created and answered after", blocked.stderr)

        current_paper_q = self.add_answer(
            "paper", "Enter writing for the current report?", outcome="approve"
        )
        self.run_cli(
            "confirm",
            self.state,
            "--layer",
            "paper",
            "--id",
            "P001",
            "--record",
            assessment,
            "--decision-id",
            current_paper_q,
            "--science-id",
            "S001",
            "--headline-claim",
            "A narrow supported claim",
            "--handoff-target",
            "paper-submission-orchestrator",
        )
        self.run_cli("audit", self.state)

    def test_paper_handoff_can_be_revoked_without_erasing_l1_l2(self) -> None:
        self.init_exploration()
        self.confirm_direction(
            self.add_answer("direction", "Choose D001?", outcome="select")
        )
        self.confirm_science(self.add_answer("science", "Promote S001?"))
        assessment = self.root / "paper-revoke.md"
        assessment.write_text("# Candidate paper\n", encoding="utf-8")
        self.enter_paper_ready(assessment)
        paper_q = self.add_answer("paper", "Approve this paper handoff?")
        self.run_cli(
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
        revoked = json.loads(
            self.run_cli(
                "paper-revoke",
                self.state,
                "--pi-decision",
                "撤销这次写作授权",
                "--reason",
                "需要重新评估论文定位",
            ).stdout
        )
        self.assertEqual(revoked["phase"], "confirmed_project")
        self.assertEqual(revoked["layer_checkpoints"]["direction"]["id"], "D001")
        self.assertEqual(revoked["layer_checkpoints"]["science"]["id"], "S001")
        self.assertEqual(revoked["layer_checkpoints"]["paper"]["status"], "UNSET")
        self.assertIsNone(revoked["paper_ready_assessment_usable"])
        self.assertIn("Paper handoff revoked by PI", assessment.read_text(encoding="utf-8"))
        self.run_cli("audit", self.state)

    def test_paper_gate_requires_pre_tuning_metric_anchor(self) -> None:
        self.init_exploration()
        self.confirm_direction(
            self.add_answer("direction", "Choose D001?", outcome="select")
        )
        self.confirm_science(self.add_answer("science", "Promote S001?"))
        assessment = self.root / "paper-ready-no-anchor.md"
        assessment.write_text("# Paper ready\n", encoding="utf-8")

        blocked = self.enter_paper_ready(
            assessment,
            set_anchor=False,
            ok=False,
        )
        self.assertIn("evaluation anchor locked before broad tuning", blocked.stderr)

    def test_replacing_metric_anchor_blocks_old_metric_at_paper_gate(self) -> None:
        self.init_exploration()
        self.confirm_direction(
            self.add_answer("direction", "Choose D001?", outcome="select")
        )
        self.set_evaluation_anchor("balanced accuracy")
        self.confirm_science(self.add_answer("science", "Promote S001?"))
        self.set_evaluation_anchor(
            "macro F1",
            reason="the official matched comparator uses macro F1",
        )
        state = json.loads(self.state.read_text(encoding="utf-8"))
        self.assertEqual(state["evaluation_anchor"]["revision"], 2)
        self.assertNotIn("aggregation", state["evaluation_anchor"])
        self.assertEqual(len(state["evaluation_anchor_history"]), 1)

        assessment = self.root / "paper-ready-anchor-replaced.md"
        assessment.write_text("# Paper ready\n", encoding="utf-8")
        blocked = self.enter_paper_ready(
            assessment,
            primary_metric="balanced accuracy",
            set_anchor=False,
            ok=False,
        )
        self.assertIn("must match the current evaluation anchor", blocked.stderr)

        self.enter_paper_ready(
            assessment,
            primary_metric="macro F1",
            set_anchor=False,
        )
        stored = json.loads(self.state.read_text(encoding="utf-8"))
        self.assertEqual(
            stored["paper_ready_assessment"]["evaluation_anchor_revision"], 2
        )

    def test_favorable_seed_selection_requires_private_scoped_pi_acceptance(self) -> None:
        self.init_exploration()
        self.confirm_direction(
            self.add_answer("direction", "Choose D001?", outcome="select")
        )
        self.set_evaluation_anchor()
        self.confirm_science(self.add_answer("science", "Promote S001?"))
        assessment = self.root / "paper-ready-selected-seeds.md"
        assessment.write_text("# Paper ready\n", encoding="utf-8")

        blocked = self.enter_paper_ready(
            assessment,
            favorable_seed_selection=True,
            set_anchor=False,
            ok=False,
        )
        self.assertIn("Favorable-seed selection requires", blocked.stderr)

        private_queue_marker = "PRIVATE_QUEUED_SEED_POOL_RULE_AND_RISK_DETAIL"
        risk_question = self.add_answer(
            "paper",
            private_queue_marker,
            outcome="approve",
            decision=private_queue_marker,
            target="paper:seed-selection-risk:S001:anchor-1",
        )
        self.enter_paper_ready(
            assessment,
            favorable_seed_selection=True,
            seed_risk_decision_id=risk_question,
            set_anchor=False,
        )
        state_text = self.state.read_text(encoding="utf-8")
        self.assertNotIn(private_queue_marker, state_text)
        stored = json.loads(state_text)
        acceptance = stored["seed_selection_risk_acceptance"]
        self.assertTrue(acceptance["accepted"])
        self.assertEqual(acceptance["science_id"], "S001")
        self.assertEqual(
            set(acceptance),
            {
                "accepted",
                "science_id",
                "evaluation_anchor_revision",
                "decision_source",
                "accepted_at",
                "assessment_payload_sha256",
            },
        )
        self.assertEqual(
            set(acceptance["decision_source"]),
            {"type", "question_id", "outcome"},
        )
        question = next(
            item for item in stored["macro_questions"] if item["id"] == risk_question
        )
        self.assertEqual(question["consumed_by"]["type"], "seed_selection_risk")
        report_text = assessment.read_text(encoding="utf-8")
        self.assertNotIn("favorable_seed_selection", report_text)
        self.assertNotIn("seed-selection-risk", report_text)
        self.run_cli("audit", self.state)

    def test_direct_seed_risk_disclosure_text_is_not_persisted(self) -> None:
        self.init_exploration()
        self.confirm_direction(
            self.add_answer("direction", "Choose D001?", outcome="select")
        )
        self.set_evaluation_anchor()
        self.confirm_science(self.add_answer("science", "Promote S001?"))
        assessment = self.root / "paper-ready-private-seed-risk.md"
        assessment.write_text("# Paper ready\n", encoding="utf-8")
        private_marker = "PRIVATE_SEED_POOL_RULE_AND_RISK_DETAIL"

        self.enter_paper_ready(
            assessment,
            favorable_seed_selection=True,
            seed_risk_pi_decision=private_marker,
            seed_risk_pi_outcome="approve",
            set_anchor=False,
        )
        state_text = self.state.read_text(encoding="utf-8")
        report_text = assessment.read_text(encoding="utf-8")
        self.assertNotIn(private_marker, state_text)
        self.assertNotIn(private_marker, report_text)
        stored = json.loads(state_text)
        self.assertEqual(
            stored["seed_selection_risk_acceptance"]["decision_source"],
            {"type": "direct_pi_instruction", "outcome": "approve"},
        )
        self.run_cli("audit", self.state)

    def test_paper_assessment_drift_blocks_handoff_and_remains_detectable(self) -> None:
        self.init_exploration()
        self.confirm_direction(
            self.add_answer("direction", "Choose D001?", outcome="select")
        )
        self.confirm_science(self.add_answer("science", "Promote S001?"))
        assessment = self.root / "paper-ready-drift.md"
        assessment.write_text("# Paper ready\n\nPASS\n", encoding="utf-8")
        self.enter_paper_ready(assessment)
        gated_text = assessment.read_text(encoding="utf-8")
        gated_bytes = assessment.read_bytes()
        status = json.loads(self.run_cli("status", self.state).stdout)
        self.assertTrue(status["paper_ready_assessment_usable"])

        assessment.write_text(gated_text + "silent rewrite\n", encoding="utf-8")
        changed = json.loads(self.run_cli("status", self.state).stdout)
        changed_codes = {issue["code"] for issue in changed["control_issues"]}
        self.assertFalse(changed["paper_ready_assessment_usable"])
        self.assertIn("PAPER_READY_ASSESSMENT_CHANGED", changed_codes)
        paper_q = self.add_answer("paper", "Use this assessment and claim?")
        blocked = self.run_cli(
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
            ok=False,
        )
        self.assertIn("changed since the gate", blocked.stderr)

        assessment.write_bytes(gated_bytes)
        self.run_cli(
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
        assessment.write_text(
            assessment.read_text(encoding="utf-8") + "post-approval rewrite\n",
            encoding="utf-8",
        )
        after_handoff = json.loads(self.run_cli("status", self.state).stdout)
        after_codes = {issue["code"] for issue in after_handoff["control_issues"]}
        self.assertIn("PAPER_READY_ASSESSMENT_CHANGED", after_codes)
        self.assertIn("PAPER_CHECKPOINT_RECORD_CHANGED", after_codes)

    def test_paper_assessment_payload_tampering_is_detected(self) -> None:
        self.init_exploration()
        self.confirm_direction(
            self.add_answer("direction", "Choose D001?", outcome="select")
        )
        self.confirm_science(self.add_answer("science", "Promote S001?"))
        assessment = self.root / "paper-ready-payload.md"
        assessment.write_text("# Paper ready\n", encoding="utf-8")
        self.enter_paper_ready(assessment)

        state = json.loads(self.state.read_text(encoding="utf-8"))
        state["paper_ready_assessment"]["our_score"] = 0.99
        state["paper_ready_assessment"]["improvement_points"] = 19.0
        self.state.write_text(json.dumps(state), encoding="utf-8")

        status = json.loads(self.run_cli("status", self.state).stdout)
        codes = {issue["code"] for issue in status["control_issues"]}
        self.assertFalse(status["paper_ready_assessment_usable"])
        self.assertIn("PAPER_READY_ASSESSMENT_PAYLOAD_CHANGED", codes)
        paper_q = self.add_answer("paper", "Use this assessment and claim?")
        blocked = self.run_cli(
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
            ok=False,
        )
        self.assertIn("missing, changed since the gate", blocked.stderr)

    def test_five_questions_pause_blocks_phase_advance(self) -> None:
        self.init_exploration()
        self.run_cli(
            "job-add",
            self.state,
            "--id",
            "J001",
            "--description",
            "running screen",
            "--session",
            "session-1",
            "--status",
            "running",
            "--next-poll",
            "after the current run should finish",
            "--next-action",
            "inspect the result artifact",
        )
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
        polling = self.run_cli(
            "job-update",
            self.state,
            "--id",
            "J001",
            "--next-poll",
            "later",
            ok=False,
        )
        self.assertIn("only record a safe terminal status", polling.stderr)
        removal = self.run_cli(
            "job-remove",
            self.state,
            "--id",
            "J001",
            "--force",
            ok=False,
        )
        self.assertIn("safe terminal status first", removal.stderr)
        child = self.root / "new-scope"
        child.mkdir()
        new_scope = self.run_cli(
            "agents-audit",
            self.state,
            "--cwd",
            child,
            ok=False,
        )
        self.assertIn("PAUSED_FOR_PI", new_scope.stderr)
        self.run_cli(
            "job-update",
            self.state,
            "--id",
            "J001",
            "--status",
            "completed",
            "--result",
            "atomic process reached a safe end",
        )
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

    def test_ambiguous_or_invalid_question_state_is_rejected(self) -> None:
        self.init_exploration()
        self.run_cli(
            "question",
            self.state,
            "--layer",
            "other",
            "--target",
            "other:q1",
            "--text",
            "question",
        )
        state = json.loads(self.state.read_text(encoding="utf-8"))
        original = json.loads(json.dumps(state))
        state["macro_questions"].append(dict(state["macro_questions"][0]))
        self.state.write_text(json.dumps(state), encoding="utf-8")
        duplicate = self.run_cli("status", self.state, ok=False)
        self.assertIn("non-empty and unique", duplicate.stderr)

        original["macro_questions"][0]["status"] = "HIDDEN_FROM_PAUSE"
        self.state.write_text(json.dumps(original), encoding="utf-8")
        invalid = self.run_cli("status", self.state, ok=False)
        self.assertIn("invalid status", invalid.stderr)

    def test_empty_operator_records_are_rejected(self) -> None:
        self.init_exploration()
        empty_question = self.run_cli(
            "question",
            self.state,
            "--layer",
            "other",
            "--target",
            "other:empty",
            "--text",
            "   ",
            ok=False,
        )
        self.assertIn("non-empty --text", empty_question.stderr)
        question = self.run_cli(
            "question",
            self.state,
            "--layer",
            "other",
            "--target",
            "other:answer",
            "--text",
            "answer me",
        )
        question_id = json.loads(question.stdout)["added"]["id"]
        empty_answer = self.run_cli(
            "answer",
            self.state,
            "--id",
            question_id,
            "--decision",
            " ",
            "--outcome",
            "reject",
            ok=False,
        )
        self.assertIn("non-empty --decision", empty_answer.stderr)
        empty_notice = self.run_cli(
            "notify", self.state, "--text", " ", ok=False
        )
        self.assertIn("non-empty --text", empty_notice.stderr)
        empty_job = self.run_cli(
            "job-add",
            self.state,
            "--id",
            " ",
            "--description",
            "job",
            "--command",
            "run",
            ok=False,
        )
        self.assertIn("non-empty --id", empty_job.stderr)

    def test_missing_l2_record_blocks_paper_ready_transition(self) -> None:
        self.init_exploration()
        self.confirm_direction(
            self.add_answer("direction", "Choose D001?", outcome="select")
        )
        self.confirm_science(self.add_answer("science", "Promote S001?"))
        self.set_baseline_roster(status="MATCHED")
        self.set_evaluation_anchor()
        self.l2.unlink()
        assessment = self.root / "paper-ready.md"
        assessment.write_text("# Paper ready\n", encoding="utf-8")
        result = self.enter_paper_ready(assessment, ok=False, set_anchor=False)
        self.assertIn("complete L1 and L2", result.stderr)

    def test_phase_rejects_irrelevant_assessment_fields(self) -> None:
        self.init_exploration()
        result = self.run_cli(
            "phase",
            self.state,
            "--set",
            "confirmed_project",
            "--assessment",
            self.l1,
            ok=False,
        )
        self.assertIn("used only when entering paper_ready_pending_pi", result.stderr)

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
        self.assertEqual(summary["schema_version"], 13)
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
            "--primary-dataset",
            "new data",
            "--unexposed-dataset-search",
            "new-data-2 is an unexposed candidate",
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
        stale_science = self.managed_text(self.l2, "SCIENCE_CURRENT")
        self.assertIn("STALE_AFTER_DIRECTION_CHANGE", stale_science)
        self.assertIn("Invalidated by: `D002`", stale_science)

    def test_compass_change_marks_l1_and_l2_current_blocks_stale(self) -> None:
        self.init_exploration()
        self.confirm_direction(
            self.add_answer("direction", "Choose D001?", outcome="select")
        )
        self.confirm_science(self.add_answer("science", "Promote S001?"))

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
            "Change the target venue and domain",
            "--pi-outcome",
            "select",
            "--venue-or-window",
            "KDD",
            "--domain",
            "recommendation",
        )
        stale_direction = self.managed_text(
            self.l1, "DIRECTION_DECISION_CURRENT"
        )
        stale_standard = self.managed_text(
            self.l1, "DIRECTION_STANDARD_CURRENT"
        )
        stale_science = self.managed_text(self.l2, "SCIENCE_CURRENT")
        self.assertIn("STALE_AFTER_COMPASS_CHANGE", stale_direction)
        self.assertIn("Invalidated by: `C002`", stale_direction)
        self.assertIn("STALE_AFTER_COMPASS_CHANGE", stale_standard)
        self.assertNotIn("beat the strongest matched baseline", stale_standard)
        self.assertIn("STALE_AFTER_COMPASS_CHANGE", stale_science)
        self.assertIn("Invalidated by: `C002`", stale_science)

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
            "--problem-id",
            "P-AUTHORITY",
            "--method-cluster-id",
            "M-AUTHORITY",
            "--problem",
            "problem",
            "--nearest-work-gap",
            "gap",
            "--paper-grade-rationale",
            "paper-grade mechanism",
            "--core-mechanism",
            "mechanism",
            "--falsifiable-prediction",
            "prediction",
            "--contribution-type",
            "mechanism",
            "--innovation-claim",
            "claim",
            "--external-baseline-status",
            "matched",
            "--ceiling-summary",
            "summary",
            "--problem-portfolio-record",
            self.l2,
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
            "--primary-dataset",
            "data",
            "--unexposed-dataset-search",
            "searched registry; candidate data-2 found",
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
            "--primary-dataset",
            "Dataset-C",
            "--unexposed-dataset-search",
            "Dataset-D found as an unexposed candidate",
            "--competitive-bar",
            "new-bar",
            "--novelty-sufficiency",
            "new novelty",
            "--generalization-requirement",
            "not required",
            "--paper-ready-threshold",
            "new threshold",
        )
        self.set_baseline_roster(status="IDENTIFIED")
        direction = self.managed_text(self.l1, "DIRECTION_DECISION_CURRENT")
        standard = self.managed_text(self.l1, "DIRECTION_STANDARD_CURRENT")
        self.assertIn("D002", direction)
        self.assertIn("Dataset-C", direction)
        self.assertIn("new-bar", standard)
        self.assertNotIn("beat the strongest matched baseline", standard)

        l2_d2 = self.root / ".codex" / "research" / "L2" / "D002.md"
        initial_l2 = l2_d2.read_text(encoding="utf-8")
        self.assertIn("L1 evidence standard: competitive=new-bar", initial_l2)
        initial_update = next(
            line for line in initial_l2.splitlines() if line.startswith("Last material update:")
        )
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
                "--problem-id",
                f"P-{science_id}",
                "--method-cluster-id",
                f"M-{science_id}",
                "--problem",
                problem,
                "--nearest-work-gap",
                f"nearest-work gap for {science_id}",
                "--paper-grade-rationale",
                f"paper-grade scientific mechanism for {science_id}",
                "--core-mechanism",
                f"mechanism {science_id}",
                "--falsifiable-prediction",
                f"prediction for {science_id}",
                "--contribution-type",
                "mechanism",
                "--innovation-claim",
                f"claim {science_id}",
                "--external-baseline-status",
                "matched",
                "--ceiling-summary",
                "competitive",
                "--problem-portfolio-record",
                l2_d2,
                "--nearest-work-record",
                l2_d2,
                "--baseline-record",
                l2_d2,
                "--result-record",
                l2_d2,
                "--change-notification",
                f"Switch to the {science_id} paper-grade problem and mechanism.",
            )
        science = self.managed_text(l2_d2, "SCIENCE_CURRENT")
        self.assertIn("S002", science)
        self.assertIn("new problem", science)
        self.assertNotIn("old problem", science)
        self.assertEqual(science.count("Last material update:"), 1)
        self.assertNotIn(initial_update, science)

    def test_existing_legacy_l2_gets_one_current_l1_context_block(self) -> None:
        self.init_exploration()
        self.l2.write_text(
            "# D001 scientific story\n\n"
            "Direction ID: `D001`  \n"
            "L1 task and dataset: old task | old data  \n"
            "L1 evidence standard: competitive=old bar  \n"
            "L1 confirmation source: old receipt\n"
            "L2 status: `MAPPING_NEAREST_WORK`  \n"
            "Last material update: old\n\n"
            "## Problem-to-method chain\n\nKeep this scientific note.\n",
            encoding="utf-8",
        )
        self.confirm_direction(
            self.add_answer("direction", "Choose D001?", outcome="select")
        )
        upgraded = self.l2.read_text(encoding="utf-8")
        self.assertEqual(upgraded.count("<!-- RPW:L1_CONTEXT:START -->"), 1)
        self.assertEqual(upgraded.count("<!-- RPW:L1_CONTEXT:END -->"), 1)
        self.assertIn("Dataset-C found as an unexposed transfer candidate", upgraded)
        self.assertIn("competitive=beat the strongest matched baseline", upgraded)
        self.assertNotIn("old bar", upgraded)
        self.assertIn("Keep this scientific note.", upgraded)

        self.run_cli(
            "confirm",
            self.state,
            "--layer",
            "direction",
            "--id",
            "D001",
            "--record",
            self.l1,
            "--pi-decision",
            "Keep D001 with a stronger evidence standard",
            "--pi-outcome",
            "select",
            "--task-type",
            "cross-site classification",
            "--dataset",
            "Dataset-A+Dataset-B",
            "--primary-dataset",
            "Dataset-A",
            "--supporting-dataset",
            "Dataset-B",
            "--unexposed-dataset-search",
            "Dataset-E is now the preferred unexposed candidate",
            "--competitive-bar",
            "beat the strongest fully matched baseline",
            "--novelty-sufficiency",
            "a distinct problem-linked mechanism",
            "--generalization-requirement",
            "second dataset required",
            "--paper-ready-threshold",
            "stable gain and matched external comparison",
        )
        replaced = self.l2.read_text(encoding="utf-8")
        self.assertEqual(replaced.count("<!-- RPW:L1_CONTEXT:START -->"), 1)
        self.assertIn("Dataset-E is now the preferred unexposed candidate", replaced)
        self.assertNotIn("Dataset-C found as an unexposed transfer candidate", replaced)
        self.assertNotIn("competitive=beat the strongest matched baseline |", replaced)
        self.assertIn("Keep this scientific note.", replaced)

    def test_direction_confirmation_requires_unexposed_dataset_search(self) -> None:
        self.init_exploration()
        result = self.run_cli(
            "confirm",
            self.state,
            "--layer",
            "direction",
            "--id",
            "D001",
            "--record",
            self.l1,
            "--pi-decision",
            "Choose D001",
            "--pi-outcome",
            "select",
            "--task-type",
            "task",
            "--dataset",
            "data",
            "--primary-dataset",
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
        self.assertIn("unexposed_dataset_search", result.stderr)

    def test_compass_replacement_preserves_concept_until_explicitly_cleared(self) -> None:
        self.run_cli(
            "init",
            self.state,
            "--project",
            "demo",
            "--phase",
            "exploration",
            "--venue-or-window",
            "KDD",
            "--domain",
            "recommendation",
            "--starting-concept",
            "debias exposure",
            "--pi-decision",
            "Use this compass",
            "--pi-outcome",
            "select",
        )
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
            "Change only the venue window",
            "--pi-outcome",
            "approve",
            "--venue-or-window",
            "WWW",
            "--domain",
            "recommendation",
        )
        state = json.loads(self.state.read_text(encoding="utf-8"))
        self.assertEqual(
            state["layer_checkpoints"]["compass"]["payload"]["starting_concept"],
            "debias exposure",
        )
        self.run_cli(
            "confirm",
            self.state,
            "--layer",
            "compass",
            "--id",
            "C003",
            "--record",
            self.l1,
            "--pi-decision",
            "Clear the optional seed",
            "--pi-outcome",
            "approve",
            "--venue-or-window",
            "WWW",
            "--domain",
            "recommendation",
            "--clear-starting-concept",
        )
        state = json.loads(self.state.read_text(encoding="utf-8"))
        self.assertEqual(
            state["layer_checkpoints"]["compass"]["payload"]["starting_concept"],
            "UNSET",
        )

    def test_optional_concept_only_change_preserves_confirmed_l1_l2(self) -> None:
        self.init_exploration()
        self.confirm_direction(
            self.add_answer("direction", "Choose D001?", outcome="select")
        )
        self.confirm_science(self.add_answer("science", "Promote S001?"))
        self.set_evaluation_anchor()

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
            "Add this as an optional idea without changing the project",
            "--pi-outcome",
            "approve",
            "--venue-or-window",
            "ICASSP",
            "--domain",
            "structural MRI",
            "--starting-concept",
            "try a reliability-weighted view",
        )
        state = json.loads(self.state.read_text(encoding="utf-8"))
        self.assertEqual(state["phase"], "confirmed_project")
        self.assertEqual(
            state["layer_checkpoints"]["direction"]["status"], "CONFIRMED_BY_PI"
        )
        self.assertEqual(
            state["layer_checkpoints"]["science"]["status"], "CONFIRMED_BY_PI"
        )
        self.assertIsNotNone(state["evaluation_anchor"])
        self.run_cli("audit", self.state)

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
            "--primary-dataset",
            "new data",
            "--unexposed-dataset-search",
            "new-data-2 is an unexposed candidate",
            "--competitive-bar",
            "new bar",
            "--novelty-sufficiency",
            "new novelty",
            "--generalization-requirement",
            "none",
            "--paper-ready-threshold",
            "new threshold",
        )
        self.set_baseline_roster(status="IDENTIFIED")
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
            "--problem-id",
            "P-S002",
            "--method-cluster-id",
            "M-S002",
            "--problem",
            "p2",
            "--nearest-work-gap",
            "nearest work leaves p2 unresolved",
            "--paper-grade-rationale",
            "p2 supports a scientific mechanism claim",
            "--core-mechanism",
            "m2",
            "--falsifiable-prediction",
            "m2 improves the primary outcome",
            "--contribution-type",
            "mechanism",
            "--innovation-claim",
            "i2",
            "--external-baseline-status",
            "matched",
            "--ceiling-summary",
            "good",
            "--problem-portfolio-record",
            l2_d2,
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
        unexposed = self.run_cli(
            "freeze",
            self.state,
            "--key",
            "unexposed_dataset_search",
            "--value",
            "candidate data",
            "--pi-decision",
            "Freeze the search result",
            "--pi-outcome",
            "approve",
            ok=False,
        )
        self.assertIn("cannot be duplicated", unexposed.stderr)

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

    def test_additional_frozen_fields_have_one_normalized_identity(self) -> None:
        self.init_exploration()
        self.run_cli(
            "freeze",
            self.state,
            "--key",
            "Model Family",
            "--value",
            "Transformer",
            "--pi-decision",
            "Keep the Transformer family fixed",
            "--pi-outcome",
            "approve",
        )
        stored = json.loads(self.state.read_text(encoding="utf-8"))
        self.assertEqual(list(stored["frozen_by_pi"]), ["model_family"])

        self.run_cli(
            "freeze",
            self.state,
            "--key",
            "model-family",
            "--value",
            "CNN",
            "--pi-decision",
            "Replace the frozen model family with CNN",
            "--pi-outcome",
            "approve",
        )
        replaced = json.loads(self.state.read_text(encoding="utf-8"))
        self.assertEqual(list(replaced["frozen_by_pi"]), ["model_family"])
        self.assertEqual(replaced["frozen_by_pi"]["model_family"]["value"], "CNN")

        queued = self.run_cli(
            "question",
            self.state,
            "--layer",
            "other",
            "--target",
            "frozen:Analysis Plan",
            "--text",
            "Freeze the analysis plan?",
        )
        queued_payload = json.loads(queued.stdout)["added"]
        self.assertEqual(queued_payload["decision_target"], "frozen:analysis_plan")
        self.run_cli(
            "answer",
            self.state,
            "--id",
            queued_payload["id"],
            "--decision",
            "Keep this analysis plan fixed",
            "--outcome",
            "approve",
        )
        self.run_cli(
            "freeze",
            self.state,
            "--key",
            "analysis-plan",
            "--value",
            "Plan A",
            "--decision-id",
            queued_payload["id"],
        )
        replaced = json.loads(self.state.read_text(encoding="utf-8"))

        replaced["frozen_by_pi"]["model family"] = {
            "value": "duplicate",
            "frozen_at": "2026-01-01T00:00:00+00:00",
            "decision_source": {
                "type": "direct_pi_instruction",
                "decision": "duplicate legacy entry",
                "outcome": "approve",
            },
        }
        self.state.write_text(json.dumps(replaced), encoding="utf-8")
        audit = json.loads(self.run_cli("audit", self.state, ok=False).stdout)
        self.assertIn(
            "DUPLICATE_FROZEN_FIELD_IDENTITY",
            {issue["code"] for issue in audit["control_issues"]},
        )

    def test_paper_ready_requires_structured_assessment(self) -> None:
        self.init_exploration()
        self.confirm_direction(
            self.add_answer("direction", "Choose D001?", outcome="select")
        )
        self.confirm_science(self.add_answer("science", "Promote S001?"))
        self.set_evaluation_anchor()
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
        self.assertIn("specific_method", result.stderr)
        self.assertIn("final_results", result.stderr)
        self.assertIn("recent_top_conference_baseline", result.stderr)
        self.assertIn("baseline_venue_year", result.stderr)
        self.assertIn("baseline_search_scope", result.stderr)
        self.assertIn("baseline_score", result.stderr)
        self.assertIn("primary_comparison_dataset", result.stderr)
        self.assertIn("competitive_bar_assessment", result.stderr)
        self.assertIn("evaluation_anchor_evidence", result.stderr)
        self.assertIn("stability_evidence", result.stderr)

    def test_direction_cannot_lower_one_point_paper_floor(self) -> None:
        self.init_exploration()
        question = self.add_answer("direction", "Choose D001?", outcome="select")
        result = self.confirm_direction(question, minimum_gain=0.5, ok=False)
        self.assertIn("cannot lower the 1-point floor", result.stderr)
        state = json.loads(self.state.read_text(encoding="utf-8"))
        self.assertEqual(state["layer_checkpoints"]["direction"]["status"], "UNSET")

    def test_descriptive_paper_threshold_cannot_override_numeric_floor(self) -> None:
        self.init_exploration()
        self.confirm_direction(
            self.add_answer("direction", "Choose D001?", outcome="select"),
            paper_ready_threshold="0.1 point would otherwise be enough",
        )
        self.confirm_science(self.add_answer("science", "Promote S001?"))
        assessment = self.root / "paper-ready-text-threshold.md"
        assessment.write_text("# Candidate paper\n", encoding="utf-8")
        blocked = self.enter_paper_ready(
            assessment,
            ok=False,
            baseline_score=0.80,
            our_score=0.805,
        )
        self.assertIn("below the configured 1-point floor", blocked.stderr)
        standard = json.loads(self.state.read_text(encoding="utf-8"))[
            "layer_checkpoints"
        ]["direction"]["payload"]["evidence_standard"]
        self.assertEqual(standard["minimum_paper_gain_points"], 1.0)
        self.assertEqual(
            standard["paper_ready_threshold"],
            "0.1 point would otherwise be enough",
        )

    def test_exact_one_point_gain_creates_complete_decision_report(self) -> None:
        self.init_exploration()
        self.confirm_direction(
            self.add_answer("direction", "Choose D001?", outcome="select")
        )
        self.confirm_science(self.add_answer("science", "Promote S001?"))
        assessment = self.root / "paper-ready-gain.md"
        original = "# Candidate paper\n"
        assessment.write_text(original, encoding="utf-8")

        blocked = self.enter_paper_ready(
            assessment, ok=False, baseline_score=0.80, our_score=0.809
        )
        self.assertIn("below the configured 1-point floor", blocked.stderr)
        self.assertEqual(assessment.read_text(encoding="utf-8"), original)
        state = json.loads(self.state.read_text(encoding="utf-8"))
        self.assertEqual(state["phase"], "confirmed_project")
        self.assertIsNone(state["paper_ready_assessment"])

        self.enter_paper_ready(assessment, baseline_score=0.80, our_score=0.81)
        report = assessment.read_text(encoding="utf-8")
        for expected in (
            "## Paper-decision report",
            "Current task: cross-site classification",
            "Dataset: Dataset-A+Dataset-B",
            "Problem in current work: site-specific shortcuts",
            "Innovation: remove shortcut information without target labels",
            "Concrete method: residual removal with a source-identifiability penalty",
            "Final results: 0.81 versus 0.8 on the primary matched evaluation",
            "Primary comparison dataset: Dataset-A",
            "Per-dataset external-baseline comparisons:",
            "Strongest recent top-conference protocol-matched baseline:",
            "Baseline venue/year: SIGIR 2025",
            "Baseline search scope: SIGIR/KDD/WWW/RecSys 2022-2026; searched 2026-08-28",
            "Protocol-match evidence: same dataset, split, labels, metric, and evaluation procedure",
            "Improvement (percentage points): 1",
            "Required improvement (percentage points): 1",
        ):
            self.assertIn(expected, report)
        stored = json.loads(self.state.read_text(encoding="utf-8"))[
            "paper_ready_assessment"
        ]
        self.assertEqual(stored["improvement_points"], 1.0)
        self.assertEqual(stored["minimum_paper_gain_points"], 1.0)

    def test_percentage_scale_and_stricter_project_floor(self) -> None:
        self.init_exploration()
        self.confirm_direction(
            self.add_answer("direction", "Choose D001?", outcome="select"),
            minimum_gain=1.5,
        )
        self.confirm_science(self.add_answer("science", "Promote S001?"))
        assessment = self.root / "paper-ready-strict.md"
        assessment.write_text("# Candidate paper\n", encoding="utf-8")

        blocked = self.enter_paper_ready(
            assessment,
            ok=False,
            metric_scale="percentage",
            baseline_score=80.0,
            our_score=81.0,
        )
        self.assertIn("below the configured 1.5-point floor", blocked.stderr)
        self.enter_paper_ready(
            assessment,
            metric_scale="percentage",
            baseline_score=80.0,
            our_score=81.5,
        )
        stored = json.loads(self.state.read_text(encoding="utf-8"))[
            "paper_ready_assessment"
        ]
        self.assertEqual(stored["improvement_points"], 1.5)
        self.assertEqual(stored["minimum_paper_gain_points"], 1.5)

    def test_schema_v8_direction_without_numeric_gain_floor_needs_audit(self) -> None:
        self.init_exploration()
        self.confirm_direction(
            self.add_answer("direction", "Choose D001?", outcome="select")
        )
        state = json.loads(self.state.read_text(encoding="utf-8"))
        state["schema_version"] = 8
        del state["layer_checkpoints"]["direction"]["payload"]["evidence_standard"][
            "minimum_paper_gain_points"
        ]
        self.state.write_text(json.dumps(state), encoding="utf-8")

        self.run_cli("notify", self.state, "--text", "save schema migration")
        migrated = json.loads(self.state.read_text(encoding="utf-8"))
        self.assertEqual(migrated["schema_version"], 13)
        self.assertEqual(
            migrated["layer_checkpoints"]["direction"]["status"],
            "LEGACY_CONFIRMED_NEEDS_AUDIT",
        )

    def test_schema_v9_paper_assessment_receives_legacy_anchor_markers(self) -> None:
        self.init_exploration()
        self.confirm_direction(
            self.add_answer("direction", "Choose D001?", outcome="select")
        )
        self.confirm_science(self.add_answer("science", "Promote S001?"))
        assessment_path = self.root / "paper-ready-schema-v9.md"
        assessment_path.write_text("# Candidate paper\n", encoding="utf-8")
        self.enter_paper_ready(assessment_path)

        state = json.loads(self.state.read_text(encoding="utf-8"))
        state["schema_version"] = 9
        state.pop("evaluation_anchor", None)
        state.pop("evaluation_anchor_history", None)
        state.pop("seed_selection_risk_acceptance", None)
        legacy_assessment = state["paper_ready_assessment"]
        for field in (
            "evaluation_anchor_revision",
            "metric_direction",
            "evaluation_anchor_evidence",
            "stability_evidence",
            "favorable_seed_selection",
            "primary_comparison_dataset",
            "dataset_baseline_matrix",
        ):
            legacy_assessment.pop(field, None)
        legacy_assessment["payload_sha256_at_gate"] = "legacy-schema-v9"
        self.state.write_text(json.dumps(state), encoding="utf-8")

        self.run_cli("notify", self.state, "--text", "save schema-v12 migration")
        migrated = json.loads(self.state.read_text(encoding="utf-8"))
        self.assertEqual(migrated["schema_version"], 13)
        self.assertTrue(migrated["evaluation_anchor"]["legacy_derived"])
        self.assertEqual(migrated["evaluation_anchor"]["revision"], 1)
        self.assertIsNone(migrated["paper_ready_assessment"])
        self.assertEqual(migrated["phase"], "confirmed_project")
        self.assertEqual(
            migrated["layer_checkpoints"]["paper"]["status"], "UNSET"
        )
        self.assertIsNone(migrated["seed_selection_risk_acceptance"])
        audit = json.loads(self.run_cli("audit", self.state, ok=False).stdout)
        codes = {issue["code"] for issue in audit["control_issues"]}
        self.assertIn("EVALUATION_ANCHOR_LEGACY_RELOCK_REQUIRED", codes)
        self.assertIn("DATASET_BASELINE_ROSTER_INVALID", codes)

        self.set_baseline_roster(status="IDENTIFIED")
        self.set_evaluation_anchor()
        relocked = json.loads(self.state.read_text(encoding="utf-8"))
        self.assertEqual(relocked["evaluation_anchor"]["revision"], 2)
        self.assertFalse(relocked["evaluation_anchor"]["legacy_derived"])
        self.assertIsNone(relocked["paper_ready_assessment"])
        final_audit = json.loads(
            self.run_cli("audit", self.state, ok=False).stdout
        )
        self.assertIn(
            "LEGACY_SCIENCE_NEEDS_RECONFIRMATION",
            {issue["code"] for issue in final_audit["control_issues"]},
        )
        self.assertGreaterEqual(
            len(relocked["invalidated_paper_assessments"]), 1
        )

    def test_recent_notifications_are_bounded(self) -> None:
        self.init_exploration()
        for index in range(55):
            self.run_cli("notify", self.state, "--text", f"notice-{index}")
        summary = json.loads(self.run_cli("status", self.state).stdout)
        self.assertEqual(summary["notification_count"], 50)
        self.assertEqual(summary["notification_compacted_count"], 5)
        self.assertEqual(
            [item["text"] for item in summary["recent_notifications"]],
            [f"notice-{index}" for index in range(50, 55)],
        )

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
            "--next-poll",
            "2026-08-28T12:00:00+00:00",
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

    def test_active_job_requires_next_check_and_action(self) -> None:
        self.init_exploration()
        missing_check = self.run_cli(
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
            "inspect the result",
            ok=False,
        )
        self.assertIn("requires --next-poll", missing_check.stderr)

        self.run_cli(
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
            "--next-poll",
            "after the estimated finish",
            "--next-action",
            "inspect the result",
        )
        state = json.loads(self.state.read_text(encoding="utf-8"))
        state["jobs"][0]["next_action"] = ""
        self.state.write_text(json.dumps(state), encoding="utf-8")
        audit = json.loads(self.run_cli("audit", self.state, ok=False).stdout)
        self.assertIn(
            "ACTIVE_JOB_NEXT_ACTION_MISSING",
            {issue["code"] for issue in audit["control_issues"]},
        )

    def test_manual_pause_blocks_execution_until_direct_resume(self) -> None:
        self.init_exploration()
        paused = json.loads(
            self.run_cli(
                "pause",
                self.state,
                "--pi-decision",
                "先暂停所有实验",
                "--reason",
                "我需要检查方向",
            ).stdout
        )
        self.assertEqual(paused["status"], "PAUSED_BY_PI")
        blocked = self.run_cli(
            "job-add",
            self.state,
            "--id",
            "J001",
            "--description",
            "candidate run",
            "--command",
            "python run.py",
            "--status",
            "running",
            "--next-poll",
            "later",
            "--next-action",
            "inspect",
            ok=False,
        )
        self.assertIn("manually paused", blocked.stderr)
        resumed = json.loads(
            self.run_cli(
                "resume",
                self.state,
                "--pi-decision",
                "继续实验",
            ).stdout
        )
        self.assertEqual(resumed["status"], "ACTIVE")
        self.assertIsNone(resumed["manual_pause"])

    def test_state_lock_rejects_overlapping_controller_command(self) -> None:
        self.init_exploration()
        spec = importlib.util.spec_from_file_location("research_queue_lock_test", SCRIPT)
        self.assertIsNotNone(spec)
        self.assertIsNotNone(spec.loader)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        with module.state_file_lock(self.state):
            status = self.run_cli("status", self.state)
            self.assertEqual(json.loads(status.stdout)["project"], "demo")
            blocked = self.run_cli(
                "notify",
                self.state,
                "--text",
                "must not overwrite concurrent state",
                ok=False,
            )
        self.assertIn("Workflow state is busy", blocked.stderr)
        self.run_cli("notify", self.state, "--text", "recorded after lock release")
        stored = json.loads(self.state.read_text(encoding="utf-8"))
        self.assertEqual(
            [item["text"] for item in stored["notifications"]],
            ["recorded after lock release"],
        )

    def test_compact_status_omits_research_payload_and_question_text(self) -> None:
        self.init_exploration()
        self.run_cli(
            "question",
            self.state,
            "--layer",
            "direction",
            "--target",
            "direction:D001",
            "--text",
            "Choose the detailed task and dataset packet?",
        )
        self.run_cli(
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
            "--next-poll",
            "after the estimated finish",
            "--next-action",
            "inspect the result artifact",
        )
        compact = json.loads(
            self.run_cli("status", self.state, "--compact").stdout
        )
        self.assertEqual(compact["pending_macro_ids"], ["Q001"])
        self.assertEqual(compact["active_jobs"][0]["next_action"], "inspect the result artifact")
        self.assertEqual(len(compact["state_sha256"]), 64)
        self.assertEqual(len(compact["wakeup_fingerprint"]), 64)
        self.assertNotIn("layer_checkpoints", compact)
        self.assertNotIn("pending_macro_questions", compact)
        self.assertNotIn("notifications", compact)
        self.assertNotIn("Choose the detailed task", json.dumps(compact))

        self.run_cli(
            "job-update",
            self.state,
            "--id",
            "J001",
            "--next-poll",
            "one hour later",
        )
        rescheduled = json.loads(
            self.run_cli("status", self.state, "--compact").stdout
        )
        self.assertNotEqual(rescheduled["state_sha256"], compact["state_sha256"])
        self.assertEqual(
            rescheduled["wakeup_fingerprint"], compact["wakeup_fingerprint"]
        )

        self.run_cli(
            "job-update",
            self.state,
            "--id",
            "J001",
            "--next-action",
            "analyze the completed artifact",
        )
        changed_action = json.loads(
            self.run_cli("status", self.state, "--compact").stdout
        )
        self.assertNotEqual(
            changed_action["wakeup_fingerprint"],
            rescheduled["wakeup_fingerprint"],
        )

        state = json.loads(self.state.read_text(encoding="utf-8"))
        state["macro_questions"][0]["created_at"] = "2000-01-01T00:00:00+00:00"
        self.state.write_text(
            json.dumps(state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        aged_question = json.loads(
            self.run_cli("status", self.state, "--compact").stdout
        )
        self.assertTrue(aged_question["any_pending_over_20_minutes"])
        self.assertNotEqual(
            aged_question["wakeup_fingerprint"],
            changed_action["wakeup_fingerprint"],
        )

    def test_monitor_ack_persists_processed_semantic_and_artifact_state(self) -> None:
        self.init_exploration()
        self.run_cli(
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
            "--next-poll",
            "after completion",
            "--next-action",
            "inspect results",
        )
        first = json.loads(self.run_cli("status", self.state, "--compact").stdout)
        self.assertTrue(first["wakeup_changed_since_ack"])
        acknowledged = json.loads(
            self.run_cli(
                "monitor-ack",
                self.state,
                "--wakeup-fingerprint",
                first["wakeup_fingerprint"],
                "--job-id",
                "J001",
                "--artifact-fingerprint",
                "results-sha256:abc123",
            ).stdout
        )
        self.assertFalse(acknowledged["wakeup_changed_since_ack"])
        self.assertEqual(
            acknowledged["acknowledged_artifact_fingerprints"]["J001"],
            "results-sha256:abc123",
        )

        self.run_cli("notify", self.state, "--text", "non-semantic status update")
        unchanged = json.loads(
            self.run_cli("status", self.state, "--compact").stdout
        )
        self.assertFalse(unchanged["wakeup_changed_since_ack"])

        self.run_cli(
            "question",
            self.state,
            "--layer",
            "direction",
            "--target",
            "direction:D001",
            "--text",
            "Choose D001?",
        )
        changed = json.loads(self.run_cli("status", self.state, "--compact").stdout)
        self.assertTrue(changed["wakeup_changed_since_ack"])
        stale = self.run_cli(
            "monitor-ack",
            self.state,
            "--wakeup-fingerprint",
            first["wakeup_fingerprint"],
            ok=False,
        )
        self.assertIn("stale monitor result", stale.stderr)

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

    def test_agents_audit_skips_empty_override_like_codex(self) -> None:
        override = self.root / "AGENTS.override.md"
        agents = self.root / "AGENTS.md"
        override.write_bytes(b"")
        agents.write_text("effective root rules\n", encoding="utf-8")
        result = self.run_cli("init", self.state, "--project", "demo")
        summary = json.loads(result.stdout)
        scope = summary["instruction_maintenance"]["audit_scopes"][0]
        self.assertEqual(scope["effective_paths"], ["AGENTS.md"])

        stored = json.loads(self.state.read_text(encoding="utf-8"))
        audit = next(
            iter(stored["instruction_maintenance"]["audits_by_scope"].values())
        )
        self.assertEqual(audit["ignored_empty_files"], ["AGENTS.override.md"])
        observed = {item["path"]: item for item in audit["observed_files"]}
        self.assertEqual(observed["AGENTS.override.md"]["ignored_reason"], "empty")
        self.assertTrue(observed["AGENTS.md"]["selected"])
        duplicate = self.run_cli(
            "agents-audit",
            self.state,
            "--fallback-name",
            "TEAM_GUIDE.md",
            "--fallback-name",
            "TEAM_GUIDE.md",
            ok=False,
        )
        self.assertIn("must be unique", duplicate.stderr)
        standard_collision = self.run_cli(
            "agents-audit",
            self.state,
            "--fallback-name",
            "agents.md",
            ok=False,
        )
        self.assertIn(
            "Invalid project instruction fallback filename",
            standard_collision.stderr,
        )

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

    def test_status_summarizes_instruction_scopes_without_snapshot_dump(self) -> None:
        (self.root / "AGENTS.md").write_text("root\n", encoding="utf-8")
        nested = self.root / "src"
        nested.mkdir()
        (nested / "AGENTS.md").write_text("src\n", encoding="utf-8")
        self.run_cli("init", self.state, "--project", "demo")
        self.run_cli("agents-audit", self.state, "--cwd", nested)

        summary = json.loads(self.run_cli("status", self.state).stdout)
        maintenance = summary["instruction_maintenance"]
        self.assertEqual(maintenance["audit_scope_count"], 2)
        self.assertEqual(
            [scope["scope_cwd"] for scope in maintenance["audit_scopes"]],
            [".", "src"],
        )
        self.assertEqual(
            maintenance["audit_scopes"][1]["removal_target"],
            'instructions-scope:{"cwd":"src","fallback":[]}',
        )
        self.assertTrue(
            all("observed_files" not in scope for scope in maintenance["audit_scopes"])
        )
        stored = json.loads(self.state.read_text(encoding="utf-8"))
        self.assertTrue(
            all(
                "observed_files" in audit
                for audit in stored["instruction_maintenance"]["audits_by_scope"].values()
            )
        )

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

    def test_missing_instruction_scope_can_be_pruned_autonomously(self) -> None:
        (self.root / "AGENTS.md").write_text("root\n", encoding="utf-8")
        nested = self.root / "obsolete"
        nested.mkdir()
        nested_agents = nested / "AGENTS.md"
        nested_agents.write_text("obsolete rules\n", encoding="utf-8")
        self.run_cli("init", self.state, "--project", "demo")
        self.run_cli("agents-audit", self.state, "--cwd", nested)
        nested_agents.unlink()
        nested.rmdir()

        before = self.run_cli("audit", self.state, ok=False)
        codes = {
            issue["code"]
            for issue in json.loads(before.stdout)["control_issues"]
        }
        self.assertIn("PROJECT_INSTRUCTION_AUDIT_SCOPE_INVALID", codes)
        removed = self.run_cli(
            "agents-scope-remove",
            self.state,
            "--cwd",
            nested,
            "--reason",
            "Directory was removed",
            "--summary",
            "清理已经不存在目录的说明审计范围。",
        )
        receipt = json.loads(removed.stdout)["removed_scope"]
        self.assertFalse(receipt["scope_existed_at_removal"])
        self.assertEqual(
            receipt["decision_source"]["type"],
            "autonomous_missing_scope_prune",
        )
        self.run_cli("audit", self.state)

    def test_existing_instruction_scope_removal_requires_scoped_pi_approval(self) -> None:
        (self.root / "AGENTS.md").write_text("root\n", encoding="utf-8")
        nested = self.root / "src"
        nested.mkdir()
        (nested / "AGENTS.md").write_text("src rules\n", encoding="utf-8")
        self.run_cli("init", self.state, "--project", "demo")
        self.run_cli("agents-audit", self.state, "--cwd", nested)

        denied = self.run_cli(
            "agents-scope-remove",
            self.state,
            "--cwd",
            nested,
            "--reason",
            "Stop auditing src",
            "--summary",
            "停止审计 src 目录。",
            ok=False,
        )
        self.assertIn("requires --decision-id", denied.stderr)
        added = self.run_cli(
            "question",
            self.state,
            "--layer",
            "instructions",
            "--target",
            'instructions-scope:{"cwd":"src","fallback":[]}',
            "--text",
            "Stop auditing src?",
        )
        question_id = json.loads(added.stdout)["added"]["id"]
        self.run_cli(
            "answer",
            self.state,
            "--id",
            question_id,
            "--decision",
            "Approve removing this audit scope",
            "--outcome",
            "approve",
        )
        removed = self.run_cli(
            "agents-scope-remove",
            self.state,
            "--cwd",
            nested,
            "--reason",
            "Stop auditing src",
            "--summary",
            "按确认决定停止审计 src 目录。",
            "--decision-id",
            question_id,
        )
        receipt = json.loads(removed.stdout)["removed_scope"]
        self.assertTrue(receipt["scope_existed_at_removal"])
        self.assertEqual(
            receipt["decision_source"]["question_id"], question_id
        )
        state = json.loads(self.state.read_text(encoding="utf-8"))
        question = next(q for q in state["macro_questions"] if q["id"] == question_id)
        self.assertEqual(
            question["consumed_by"]["type"], "instruction_scope_remove"
        )
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

    def test_direction_checkpoint_id_cannot_escape_l2_directory(self) -> None:
        self.init_exploration()
        result = self.run_cli(
            "confirm",
            self.state,
            "--layer",
            "direction",
            "--id",
            "../escape",
            "--record",
            self.l1,
            "--pi-decision",
            "Choose an invalid direction ID",
            "--pi-outcome",
            "select",
            ok=False,
        )
        self.assertIn("cannot contain a path", result.stderr)
        self.assertFalse((self.root / ".codex" / "research" / "escape.md").exists())

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
                "--primary-dataset",
                "data",
                "--unexposed-dataset-search",
                "searched registry; candidate data-2 found",
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

    def test_checkpoint_record_cannot_reuse_controller_or_agents_file(self) -> None:
        self.init_exploration()
        question = self.add_answer("direction", "Choose D001?", outcome="select")
        common = [
            "confirm",
            self.state,
            "--layer",
            "direction",
            "--id",
            "D001",
            "--decision-id",
            question,
            "--task-type",
            "task",
            "--dataset",
            "data",
            "--primary-dataset",
            "data",
            "--unexposed-dataset-search",
            "candidate data-2 found",
            "--competitive-bar",
            "bar",
            "--novelty-sufficiency",
            "novel",
            "--generalization-requirement",
            "none",
            "--paper-ready-threshold",
            "threshold",
        ]
        state_record = self.run_cli(
            *common,
            "--record",
            self.state,
            ok=False,
        )
        self.assertIn("cannot reuse the workflow state", state_record.stderr)
        json.loads(self.state.read_text(encoding="utf-8"))

        agents = self.root / "AGENTS.md"
        agents.write_text("stable project instructions\n", encoding="utf-8")
        agents_record = self.run_cli(
            *common,
            "--record",
            agents,
            ok=False,
        )
        self.assertIn("cannot be written into project AGENTS", agents_record.stderr)
        self.assertEqual(
            agents.read_text(encoding="utf-8"), "stable project instructions\n"
        )

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
                "--problem-id",
                "P-EXTERNAL",
                "--method-cluster-id",
                "M-EXTERNAL",
                "--problem",
                "p",
                "--nearest-work-gap",
                "nearest work leaves the identified failure unresolved",
                "--paper-grade-rationale",
                "the failure identifies a general scientific mechanism",
                "--core-mechanism",
                "m",
                "--falsifiable-prediction",
                "the mechanism improves unseen-domain outcomes",
                "--contribution-type",
                "mechanism",
                "--innovation-claim",
                "i",
                "--external-baseline-status",
                "matched",
                "--ceiling-summary",
                "good",
                "--problem-portfolio-record",
                evidence,
                "--nearest-work-record",
                evidence,
                "--baseline-record",
                evidence,
                "--result-record",
                evidence,
            )
            self.assertEqual(evidence.read_text(encoding="utf-8"), original)
            self.run_cli("audit", self.state)
            evidence.write_text(original + "changed result\n", encoding="utf-8")
            changed = self.run_cli("audit", self.state, ok=False)
            codes = {
                issue["code"]
                for issue in json.loads(changed.stdout)["control_issues"]
            }
            self.assertIn("SCIENCE_EVIDENCE_RECORD_CHANGED", codes)
            assessment = self.root / "paper-ready-after-drift.md"
            assessment.write_text("# assessment\n", encoding="utf-8")
            blocked = self.enter_paper_ready(assessment, ok=False)
            self.assertIn("complete L1 and L2", blocked.stderr)
            evidence.write_text(original, encoding="utf-8")
            self.run_cli("audit", self.state)
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
        self.assertEqual(migrated["schema_version"], 13)
        self.assertEqual(questions[first]["superseded_by"], second)
        self.assertEqual(
            migrated["decision_target_revisions"]["direction:D001"], 2
        )
        self.assertEqual(
            len(migrated["instruction_maintenance"]["audits_by_scope"]), 1
        )

    def test_schema_v7_adds_bounded_scope_removal_history(self) -> None:
        self.init_exploration()
        state = json.loads(self.state.read_text(encoding="utf-8"))
        state["schema_version"] = 7
        state["instruction_maintenance"].pop("recent_scope_removals")
        state["instruction_maintenance"].pop("compacted_scope_removal_count")
        self.state.write_text(json.dumps(state), encoding="utf-8")

        self.run_cli("notify", self.state, "--text", "save schema migration")
        migrated = json.loads(self.state.read_text(encoding="utf-8"))
        self.assertEqual(migrated["schema_version"], 13)
        self.assertEqual(
            migrated["instruction_maintenance"]["recent_scope_removals"], []
        )
        self.assertEqual(
            migrated["instruction_maintenance"]["compacted_scope_removal_count"],
            0,
        )

    def test_schema_v7_direction_requires_unexposed_dataset_search_audit(self) -> None:
        self.init_exploration()
        self.confirm_direction(
            self.add_answer("direction", "Choose D001?", outcome="select")
        )
        state = json.loads(self.state.read_text(encoding="utf-8"))
        state["schema_version"] = 7
        del state["layer_checkpoints"]["direction"]["payload"][
            "unexposed_dataset_search"
        ]
        self.state.write_text(json.dumps(state), encoding="utf-8")

        result = self.run_cli("audit", self.state, ok=False)
        summary = json.loads(result.stdout)
        self.assertEqual(
            summary["layer_checkpoints"]["direction"]["status"],
            "LEGACY_CONFIRMED_NEEDS_AUDIT",
        )
        codes = {issue["code"] for issue in summary["control_issues"]}
        self.assertIn("LEGACY_DIRECTION_NEEDS_RECONFIRMATION", codes)

    def test_baseline_roster_must_cover_every_adopted_dataset(self) -> None:
        self.init_exploration()
        self.confirm_direction(
            self.add_answer("direction", "Choose D001?", outcome="select")
        )
        state = json.loads(self.state.read_text(encoding="utf-8"))
        incomplete = [state["dataset_baseline_roster"]["rows"][0]]
        blocked = self.run_cli(
            "baseline-roster",
            self.state,
            "--rows-json",
            json.dumps(incomplete),
            "--record",
            self.l2,
            "--reason",
            "attempt incomplete coverage",
            ok=False,
        )
        self.assertIn("exactly one row for every adopted dataset", blocked.stderr)

    def test_evaluation_anchor_requires_pre_tuning_baseline_roster(self) -> None:
        self.init_exploration()
        self.confirm_direction(
            self.add_answer("direction", "Choose D001?", outcome="select")
        )
        state = json.loads(self.state.read_text(encoding="utf-8"))
        state["dataset_baseline_roster"] = None
        self.state.write_text(json.dumps(state), encoding="utf-8")
        blocked = self.set_evaluation_anchor(ok=False)
        self.assertIn("baseline roster", blocked.stderr)

    def test_baseline_roster_requires_all_comparison_roles(self) -> None:
        self.init_exploration()
        self.confirm_direction(
            self.add_answer("direction", "Choose D001?", outcome="select")
        )
        state = json.loads(self.state.read_text(encoding="utf-8"))
        rows = state["dataset_baseline_roster"]["rows"]
        del rows[0]["comparison_roles"]["strong_simple"]
        blocked = self.run_cli(
            "baseline-roster",
            self.state,
            "--rows-json",
            json.dumps(rows),
            "--record",
            self.l2,
            "--reason",
            "attempt incomplete role coverage",
            ok=False,
        )
        self.assertIn("comparison_roles must contain exactly", blocked.stderr)

    def test_verified_protocol_cannot_contain_explicit_mismatch(self) -> None:
        self.init_exploration()
        self.confirm_direction(
            self.add_answer("direction", "Choose D001?", outcome="select")
        )
        state = json.loads(self.state.read_text(encoding="utf-8"))
        rows = state["dataset_baseline_roster"]["rows"]
        for row in rows:
            row["status"] = "MATCHED"
            row["protocol_status"] = "VERIFIED_MATCH"
            row["baseline_score"] = 0.80
            row["our_score"] = 0.82
        rows[0]["protocol_match"] = "different split; not comparable"
        blocked = self.run_cli(
            "baseline-roster",
            self.state,
            "--rows-json",
            json.dumps(rows),
            "--record",
            self.l2,
            "--reason",
            "attempt contradictory protocol claim",
            ok=False,
        )
        self.assertIn("claims VERIFIED_MATCH", blocked.stderr)

    def test_nonheadline_comparison_role_can_keep_concrete_blocker(self) -> None:
        self.init_exploration()
        self.confirm_direction(
            self.add_answer("direction", "Choose D001?", outcome="select")
        )
        state = json.loads(self.state.read_text(encoding="utf-8"))
        rows = state["dataset_baseline_roster"]["rows"]
        rows[0]["comparison_roles"]["strong_simple"] = {
            "status": "BLOCKED",
            "evidence": "No official simple baseline supports this label space; narrow the claim",
        }
        result = self.run_cli(
            "baseline-roster",
            self.state,
            "--rows-json",
            json.dumps(rows),
            "--record",
            self.l2,
            "--reason",
            "retain a concrete non-headline blocker",
        )
        roster = json.loads(result.stdout)["dataset_baseline_roster"]
        self.assertEqual(
            roster["rows"][0]["comparison_roles"]["strong_simple"]["status"],
            "BLOCKED",
        )

    def test_paper_gate_requires_recent_top_conference_role_coverage(self) -> None:
        self.init_exploration()
        self.confirm_direction(
            self.add_answer("direction", "Choose D001?", outcome="select")
        )
        state = json.loads(self.state.read_text(encoding="utf-8"))
        rows = state["dataset_baseline_roster"]["rows"]
        for row in rows:
            row["status"] = "MATCHED"
            row["protocol_status"] = "VERIFIED_MATCH"
            row["baseline_score"] = 0.80
            row["our_score"] = 0.82
        rows[0]["comparison_roles"]["recent_top_conference"] = {
            "status": "BLOCKED",
            "evidence": "No eligible recent top-conference comparison has been verified",
        }
        self.run_cli(
            "baseline-roster",
            self.state,
            "--rows-json",
            json.dumps(rows),
            "--record",
            self.l2,
            "--reason",
            "record unresolved headline comparator",
        )
        self.confirm_science(self.add_answer("science", "Promote S001?"))
        self.set_evaluation_anchor()
        assessment = self.root / "paper-ready-role-blocked.md"
        assessment.write_text("# Candidate paper\n", encoding="utf-8")
        blocked = self.enter_paper_ready(
            assessment,
            ok=False,
            set_anchor=False,
            set_roster=False,
        )
        self.assertIn("MATCHED external-baseline row", blocked.stderr)

    def test_live_l2_updates_do_not_invalidate_embedded_roster_receipt(self) -> None:
        self.init_exploration()
        self.confirm_direction(
            self.add_answer("direction", "Choose D001?", outcome="select")
        )
        with self.l2.open("a", encoding="utf-8") as handle:
            handle.write("\n## New problem evidence\n\nA newly verified observation.\n")
        self.set_evaluation_anchor()
        audit = json.loads(self.run_cli("status", self.state).stdout)
        self.assertNotIn(
            "DATASET_BASELINE_ROSTER_RECORD_CHANGED",
            {issue["code"] for issue in audit["control_issues"]},
        )

    def test_roster_change_invalidates_pending_paper_packet(self) -> None:
        self.init_exploration()
        self.confirm_direction(
            self.add_answer("direction", "Choose D001?", outcome="select")
        )
        self.confirm_science(self.add_answer("science", "Promote S001?"))
        assessment = self.root / "paper-ready-roster-stale.md"
        assessment.write_text("# Candidate paper\n", encoding="utf-8")
        self.enter_paper_ready(assessment)
        self.assertEqual(
            json.loads(self.state.read_text(encoding="utf-8"))["phase"],
            "paper_ready_pending_pi",
        )

        self.set_baseline_roster(
            status="MATCHED", baseline_score=0.81, our_score=0.83
        )
        state = json.loads(self.state.read_text(encoding="utf-8"))
        self.assertEqual(state["phase"], "confirmed_project")
        self.assertIsNone(state["paper_ready_assessment"])
        self.assertEqual(
            state["invalidated_paper_assessments"][-1]["reason"],
            "dataset_baseline_roster_change",
        )

    def test_confirmed_problem_or_method_switch_requires_notification(self) -> None:
        self.init_exploration()
        self.confirm_direction(
            self.add_answer("direction", "Choose D001?", outcome="select")
        )
        self.confirm_science(self.add_answer("science", "Promote S001?"))
        common = [
            "confirm",
            self.state,
            "--layer",
            "science",
            "--id",
            "S002",
            "--record",
            self.l2,
            "--pi-decision",
            "Replace the confirmed L2 mechanism",
            "--pi-outcome",
            "approve",
            "--direction-id",
            "D001",
            "--problem-id",
            "P-SHORTCUT-2",
            "--method-cluster-id",
            "M-CAUSAL",
            "--problem",
            "shortcut transport across sites",
            "--nearest-work-gap",
            "nearest methods do not model shortcut transport",
            "--paper-grade-rationale",
            "the transport failure supports a general mechanism claim",
            "--core-mechanism",
            "causal shortcut transport regularization",
            "--falsifiable-prediction",
            "transport regularization improves unseen-site accuracy",
            "--contribution-type",
            "mechanism",
            "--innovation-claim",
            "identify and interrupt shortcut transport",
            "--external-baseline-status",
            "roster identified for every adopted dataset",
            "--ceiling-summary",
            "promising ceiling",
            "--problem-portfolio-record",
            self.l2,
            "--nearest-work-record",
            self.l2,
            "--baseline-record",
            self.l2,
            "--result-record",
            self.l2,
        ]
        blocked = self.run_cli(*common, ok=False)
        self.assertIn("--change-notification", blocked.stderr)
        self.run_cli(
            *common,
            "--change-notification",
            "旧问题已无潜力，改查跨站点 shortcut transport，并切换核心机制。",
        )
        state = json.loads(self.state.read_text(encoding="utf-8"))
        kinds = [item["kind"] for item in state["notifications"][-2:]]
        self.assertEqual(kinds, ["problem_switch", "method_cluster_switch"])
        self.assertEqual(
            state["notifications"][-2]["transition"],
            {"from_id": "P-SHORTCUT", "to_id": "P-SHORTCUT-2"},
        )
        self.assertEqual(
            state["notifications"][-1]["transition"],
            {"from_id": "M-RESIDUAL", "to_id": "M-CAUSAL"},
        )

    def test_exploratory_switch_notification_requires_typed_transition(self) -> None:
        self.init_exploration()
        missing = self.run_cli(
            "notify",
            self.state,
            "--kind",
            "method_cluster_switch",
            "--text",
            "旧方法簇没有潜力，改测另一个机制。",
            ok=False,
        )
        self.assertIn("--from-id and --to-id", missing.stderr)
        before = json.loads(
            self.run_cli("status", self.state, "--compact").stdout
        )["wakeup_fingerprint"]
        self.run_cli(
            "notify",
            self.state,
            "--kind",
            "method_cluster_switch",
            "--from-id",
            "M-OLD",
            "--to-id",
            "M-NEW",
            "--text",
            "旧方法簇没有潜力，改测另一个可证伪机制；L1 不变。",
        )
        compact = json.loads(
            self.run_cli("status", self.state, "--compact").stdout
        )
        self.assertNotEqual(before, compact["wakeup_fingerprint"])
        self.assertEqual(
            compact["latest_scientific_switch"],
            {
                "id": "N001",
                "kind": "method_cluster_switch",
                "transition": {"from_id": "M-OLD", "to_id": "M-NEW"},
            },
        )

    def test_engineering_only_voting_cannot_be_l2_core_mechanism(self) -> None:
        self.init_exploration()
        self.confirm_direction(
            self.add_answer("direction", "Choose D001?", outcome="select")
        )
        blocked = self.run_cli(
            "confirm",
            self.state,
            "--layer",
            "science",
            "--id",
            "S-VOTE",
            "--record",
            self.l2,
            "--pi-decision",
            "Evaluate this candidate",
            "--pi-outcome",
            "approve",
            "--direction-id",
            "D001",
            "--problem-id",
            "P-VOTE",
            "--method-cluster-id",
            "M-VOTE",
            "--problem",
            "model disagreement",
            "--nearest-work-gap",
            "existing systems disagree",
            "--paper-grade-rationale",
            "claimed mechanism",
            "--core-mechanism",
            "weighted expert voting",
            "--falsifiable-prediction",
            "voting raises accuracy",
            "--contribution-type",
            "mechanism",
            "--innovation-claim",
            "combine several experts",
            "--external-baseline-status",
            "roster identified",
            "--ceiling-summary",
            "unknown",
            "--problem-portfolio-record",
            self.l2,
            "--nearest-work-record",
            self.l2,
            "--baseline-record",
            self.l2,
            "--result-record",
            self.l2,
            ok=False,
        )
        self.assertIn("engineering-only", blocked.stderr)
        state = json.loads(self.state.read_text(encoding="utf-8"))
        self.assertEqual(state["layer_checkpoints"]["science"]["status"], "UNSET")

    def test_monitor_artifact_acknowledgements_are_per_job_and_explicitly_cleared(self) -> None:
        self.init_exploration()
        for job_id in ("J001", "J002"):
            self.run_cli(
                "job-add",
                self.state,
                "--id",
                job_id,
                "--description",
                f"run {job_id}",
                "--command",
                f"python {job_id}.py",
                "--status",
                "running",
                "--next-poll",
                "after completion",
                "--next-action",
                "inspect artifact",
            )
        compact = json.loads(self.run_cli("status", self.state, "--compact").stdout)
        for job_id, artifact in (("J001", "sha:a"), ("J002", "sha:b")):
            compact = json.loads(
                self.run_cli(
                    "monitor-ack",
                    self.state,
                    "--wakeup-fingerprint",
                    compact["wakeup_fingerprint"],
                    "--job-id",
                    job_id,
                    "--artifact-fingerprint",
                    artifact,
                ).stdout
            )
        semantic_only = json.loads(
            self.run_cli(
                "monitor-ack",
                self.state,
                "--wakeup-fingerprint",
                compact["wakeup_fingerprint"],
            ).stdout
        )
        self.assertEqual(
            semantic_only["acknowledged_artifact_fingerprints"],
            {"J001": "sha:a", "J002": "sha:b"},
        )
        cleared = json.loads(
            self.run_cli(
                "monitor-ack",
                self.state,
                "--wakeup-fingerprint",
                semantic_only["wakeup_fingerprint"],
                "--job-id",
                "J001",
                "--clear-artifact-fingerprint",
            ).stdout
        )
        self.assertEqual(
            cleared["acknowledged_artifact_fingerprints"], {"J002": "sha:b"}
        )

    def test_schema_v11_migration_retains_invalidated_paper_pointer(self) -> None:
        self.init_exploration()
        self.confirm_direction(
            self.add_answer("direction", "Choose D001?", outcome="select")
        )
        self.confirm_science(self.add_answer("science", "Promote S001?"))
        assessment = self.root / "paper-ready-schema-v11.md"
        assessment.write_text("# Candidate paper\n", encoding="utf-8")
        self.enter_paper_ready(assessment)
        state = json.loads(self.state.read_text(encoding="utf-8"))
        state["schema_version"] = 11
        for row in state["paper_ready_assessment"]["dataset_baseline_matrix"]:
            row.pop("protocol_status", None)
            row.pop("comparison_roles", None)
        state.pop("dataset_baseline_roster", None)
        state.pop("dataset_baseline_roster_history", None)
        state.pop("invalidated_paper_assessments", None)
        state.pop("invalidated_paper_assessment_count", None)
        state["monitoring"] = {
            "last_acknowledged_wakeup_fingerprint": None,
            "last_acknowledged_artifact_fingerprint": "legacy-artifact",
            "acknowledged_at": None,
        }
        state["layer_checkpoints"]["direction"]["payload"].pop(
            "adopted_datasets", None
        )
        for field in (
            "problem_id",
            "method_cluster_id",
            "nearest_work_gap",
            "paper_grade_rationale",
            "falsifiable_prediction",
            "contribution_type",
        ):
            state["layer_checkpoints"]["science"]["payload"].pop(field, None)
        state["layer_checkpoints"]["science"]["payload"]["evidence_refs"].pop(
            "problem_portfolio", None
        )
        self.state.write_text(json.dumps(state), encoding="utf-8")

        self.run_cli("notify", self.state, "--text", "trigger schema-v12 migration")
        migrated = json.loads(self.state.read_text(encoding="utf-8"))
        receipt = migrated["invalidated_paper_assessments"][-1]
        self.assertEqual(receipt["path"], "paper-ready-schema-v11.md")
        self.assertEqual(receipt["direction_id"], "D001")
        self.assertEqual(
            migrated["layer_checkpoints"]["science"]["status"],
            "LEGACY_CONFIRMED_NEEDS_PROBLEM_STRUCTURE",
        )
        self.assertEqual(
            migrated["monitoring"]["legacy_unscoped_artifact_fingerprint"],
            "legacy-artifact",
        )
        self.assertEqual(migrated["schema_version"], 13)
        self.assertTrue(
            migrated["dataset_baseline_roster"]["schema_v13_review_required"]
        )
        self.assertEqual(
            migrated["dataset_baseline_roster"]["rows"][0]["protocol_status"],
            "LEGACY_UNVERIFIED",
        )

    def test_schema_v12_paper_packet_requires_baseline_evidence_review(self) -> None:
        self.init_exploration()
        self.confirm_direction(
            self.add_answer("direction", "Choose D001?", outcome="select")
        )
        self.confirm_science(self.add_answer("science", "Promote S001?"))
        assessment = self.root / "paper-ready-schema-v12.md"
        assessment.write_text("# Candidate paper\n", encoding="utf-8")
        self.enter_paper_ready(assessment)
        state = json.loads(self.state.read_text(encoding="utf-8"))
        state["schema_version"] = 12
        for row in state["dataset_baseline_roster"]["rows"]:
            row.pop("protocol_status", None)
            row.pop("comparison_roles", None)
        for row in state["paper_ready_assessment"]["dataset_baseline_matrix"]:
            row.pop("protocol_status", None)
            row.pop("comparison_roles", None)
        self.state.write_text(json.dumps(state), encoding="utf-8")

        migrated = json.loads(
            self.run_cli("status", self.state).stdout
        )
        self.assertEqual(migrated["schema_version"], 13)
        self.assertEqual(migrated["phase"], "confirmed_project")
        self.assertIsNone(migrated["paper_ready_assessment_usable"])
        self.assertIn(
            "DATASET_BASELINE_ROSTER_INVALID",
            {item["code"] for item in migrated["control_issues"]},
        )


if __name__ == "__main__":
    unittest.main()
