#!/usr/bin/env python3
"""Control durable PI decisions and resumable work for research-paper-workflow.

The controller enforces scoped typed approvals, ordered scientific checkpoints,
active/deferred PI queues, the five-question pause, evidence-record links,
manual pause/revocation, persistent monitor acknowledgements, lightweight
active-job recovery, bounded project-instruction maintenance, and control-state
audits. It records authority and artifact availability; it does
not judge scientific adequacy, rewrite AGENTS.md, create authority, schedule
itself, or kill processes.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import re
import sys
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


SCHEMA_VERSION = 16
SUPPORTED_SCHEMA_VERSIONS = set(range(1, SCHEMA_VERSION + 1))
MIN_PAPER_READY_GAIN_POINTS = 1.0
MAX_MACRO_QUESTIONS = 5
RECENT_NOTIFICATION_LIMIT = 50
RECENT_INSTRUCTION_UPDATE_LIMIT = 20
RECENT_INVALIDATED_PAPER_LIMIT = 20
ROOT_AGENTS_TARGET_BYTES = 8 * 1024
ROOT_AGENTS_REVIEW_BYTES = 12 * 1024
EFFECTIVE_AGENTS_TARGET_BYTES = 16 * 1024
CODEX_PROJECT_DOC_DEFAULT_BYTES = 32 * 1024
CHECKPOINT_ID_PATTERN = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,63}\Z")
AGENTS_FILENAMES = ("AGENTS.override.md", "AGENTS.md")
INSTRUCTION_CHANGE_KINDS = {"mechanical", "compaction", "semantic"}
PRIORITY_ORDER = {"high": 0, "medium": 1, "low": 2}
QUESTION_LAYERS = {
    "compass",
    "direction",
    "science",
    "paper",
    "resource",
    "external",
    "instructions",
    "other",
}
CHECKPOINT_LAYERS = ("compass", "direction", "science", "paper")
CHECKPOINT_LAYER_FIELDS = {
    "compass": {"venue_or_window", "domain", "starting_concept", "clear_starting_concept"},
    "direction": {
        "task_type",
        "dataset",
        "primary_dataset",
        "supporting_dataset",
        "unexposed_dataset_search",
        "competitive_bar",
        "novelty_sufficiency",
        "generalization_requirement",
        "paper_ready_threshold",
        "minimum_paper_gain_points",
    },
    "science": {
        "direction_id",
        "problem_path",
        "problem_id",
        "method_cluster_id",
        "problem",
        "nearest_work_gap",
        "paper_grade_rationale",
        "core_mechanism",
        "falsifiable_prediction",
        "simple_combination_counterfactual",
        "contribution_type",
        "innovation_claim",
        "external_baseline_status",
        "ceiling_summary",
        "problem_portfolio_record",
        "nearest_work_record",
        "baseline_record",
        "result_record",
        "change_notification",
    },
    "paper": {"science_id", "headline_claim", "handoff_target"},
}
ALL_CHECKPOINT_FIELDS = set().union(*CHECKPOINT_LAYER_FIELDS.values())
APPROVING_OUTCOMES = {"approve", "select"}
DECISION_OUTCOMES = APPROVING_OUTCOMES | {"reject", "defer", "informational"}
VALID_PHASES = {
    "discussion",
    "exploration",
    "confirmed_project",
    "paper_ready_pending_pi",
    "paper_handoff_approved",
}
ACTIVE_JOB_STATUSES = {"queued", "running"}
JOB_STATUSES = ACTIVE_JOB_STATUSES | {"completed", "failed", "cancelled", "blocked"}
METRIC_DIRECTIONS = {"higher_is_better"}
BASELINE_ROSTER_STATUSES = {"IDENTIFIED", "BLOCKED", "MATCHED"}
BASELINE_PROTOCOL_STATUSES = {
    "BLOCKED",
    "PENDING_MATCH",
    "VERIFIED_MATCH",
}
LEGACY_BASELINE_PROTOCOL_STATUS = "LEGACY_UNVERIFIED"
PROTOCOL_MISMATCH_PATTERNS = {
    "different split",
    "mismatched",
    "not comparable",
    "not matched",
    "unmatched",
    "不可比",
    "不匹配",
    "不同划分",
}
BASELINE_COMPARISON_ROLES = (
    "dataset_origin",
    "recent_top_conference",
    "different_published_mechanism",
    "strong_simple",
)
BASELINE_ROLE_STATUSES = {"COVERED", "BLOCKED"}
LEGACY_BASELINE_ROLE_STATUS = "LEGACY_UNVERIFIED"
PAPER_GRADE_CONTRIBUTION_TYPES = {
    "diagnostic",
    "empirical_finding",
    "estimand",
    "mechanism",
    "objective",
    "theory",
}
NOTIFICATION_KINDS = {
    "general",
    "job_event",
    "l3_scientific_impact",
    "method_cluster_switch",
    "model_family_change",
    "problem_switch",
    "problem_path_change",
}
WINDOW_CARD_KINDS_BY_LAYER = {
    "L1": {"task_dataset"},
    "L2": {"baseline_comparison", "method_cluster", "problem"},
}
WINDOW_CARD_STATUSES = {
    "BLOCKED",
    "CEILING_SEARCH",
    "CLOSED",
    "CURRENT",
    "EXHAUSTED",
    "IDENTIFIED",
    "MATCHED",
    "PROMISING",
    "SCOUTING",
    "SCREENING",
    "SELECTED",
}
WINDOW_TERMINAL_STATUSES = {"BLOCKED", "CLOSED", "EXHAUSTED"}
RESEARCH_OPTIONAL_FIELDS = (
    "starting_result", "best_result", "latest_result", "disposition_reason",
    "problem_path", "hypothesis", "current_action", "comparison_note",
)
WINDOW_MACRO_NOTIFICATION_KINDS = {
    "method_cluster_switch",
    "model_family_change",
    "problem_switch",
    "problem_path_change",
}
SEED_SELECTION_RISK_TARGET_PREFIX = "paper:seed-selection-risk:"
PAPER_ASSESSMENT_TEXT_FIELDS = (
    "competitive_bar_assessment",
    "novelty_assessment",
    "generalization_assessment",
    "paper_ready_threshold_assessment",
    "narrowest_supported_claim",
    "strongest_matched_comparison",
    "remaining_objection",
    "necessary_work",
    "optional_work",
    "specific_method",
    "final_results",
    "primary_comparison_dataset",
    "recent_top_conference_baseline",
    "baseline_venue_year",
    "baseline_search_scope",
    "baseline_source",
    "protocol_match_evidence",
    "primary_metric",
    "evaluation_anchor_evidence",
    "stability_evidence",
)
PAPER_ASSESSMENT_NUMERIC_FIELDS = ("baseline_score", "our_score")
PAPER_ASSESSMENT_CLI_FIELDS = (
    *PAPER_ASSESSMENT_TEXT_FIELDS,
    "dataset_baseline_matrix",
    "metric_scale",
    *PAPER_ASSESSMENT_NUMERIC_FIELDS,
)
PAPER_ASSESSMENT_CONTEXT_FIELDS = (
    "current_task",
    "dataset",
    "adopted_datasets",
    "current_work_problem",
    "problem_path",
    "problem_id",
    "method_cluster_id",
    "innovation",
    "core_mechanism",
    "baseline_roster_revision",
    "baseline_roster_payload_sha256",
    "minimum_paper_gain_points",
    "improvement_points",
    "evaluation_anchor_revision",
    "metric_direction",
)
PAPER_ASSESSMENT_PAYLOAD_FIELDS = (
    "direction_id",
    "science_id",
    *PAPER_ASSESSMENT_CONTEXT_FIELDS,
    *PAPER_ASSESSMENT_CLI_FIELDS,
    "favorable_seed_selection",
    "science_evidence_at_gate",
)
PRIVATE_PAPER_CONTROL_FIELDS = {"favorable_seed_selection"}
RESERVED_FROZEN_KEYS = {
    "venue",
    "venue_or_window",
    "submission_window",
    "conference",
    "domain",
    "starting_concept",
    "task",
    "task_type",
    "dataset",
    "dataset_bundle",
    "unexposed_dataset_search",
    "competitive_bar",
    "novelty_sufficiency",
    "generalization_requirement",
    "second_dataset_requirement",
    "paper_ready_threshold",
    "minimum_paper_gain_points",
    "problem",
    "core_mechanism",
    "innovation_claim",
    "headline_claim",
    "会议",
    "投稿时间",
    "投稿会议",
    "领域",
    "初始构想",
    "任务",
    "任务类型",
    "数据集",
    "非暴露数据集搜索",
    "竞争目标",
    "创新标准",
    "泛化要求",
    "第二数据集要求",
    "论文就绪条件",
    "论文最小增益",
    "论文增益门槛",
    "问题",
    "核心机制",
    "创新点",
    "论文主张",
}


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@contextmanager
def state_file_lock(state_path: Path):
    """Serialize controller commands that target the same workflow state.

    Scheduled wakeups and an interactive Codex task can otherwise read the same
    state revision and silently overwrite each other's updates. A separate
    advisory lock file remains beside the JSON state so replacing the JSON does
    not replace the locked inode or Windows file handle.
    """

    resolved_state = state_path.resolve()
    lock_path = resolved_state.with_name(resolved_state.name + ".lock")
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    handle = lock_path.open("a+b")
    locked = False
    try:
        handle.seek(0, os.SEEK_END)
        if handle.tell() == 0:
            handle.write(b"\0")
            handle.flush()
        handle.seek(0)
        try:
            if os.name == "nt":
                import msvcrt

                msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl

                fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            locked = True
        except (OSError, BlockingIOError) as exc:
            raise SystemExit(
                "Workflow state is busy in another controller command. Do not "
                "bypass the lock or retry in a tight loop; read it again after "
                "the active command finishes."
            ) from exc
        yield
    finally:
        if locked:
            handle.seek(0)
            if os.name == "nt":
                import msvcrt

                msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                import fcntl

                fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
        handle.close()


def validate_checkpoint_id(raw: str) -> str:
    value = str(raw or "")
    if not CHECKPOINT_ID_PATTERN.fullmatch(value):
        raise SystemExit(
            "Checkpoint ID must be 1-64 ASCII letters, digits, dots, underscores, "
            "or hyphens, must start with a letter or digit, and cannot contain a path"
        )
    return value


def normalize_problem_path(
    raw: Any, *, active_leaf: str | None = None, label: str = "problem path"
) -> list[str]:
    if not isinstance(raw, (list, tuple)) or not raw:
        raise SystemExit(f"{label} must contain at least one ordered problem ID")
    normalized = [validate_checkpoint_id(str(item or "")) for item in raw]
    if len(set(normalized)) != len(normalized):
        raise SystemExit(f"{label} cannot repeat a problem ID")
    if active_leaf is not None:
        leaf = validate_checkpoint_id(active_leaf)
        if normalized[-1] != leaf:
            raise SystemExit(
                f"{label} must end at the active problem ID {leaf!r}; do not leave a "
                "disconnected or trailing branch"
            )
    return normalized


def problem_path_complete(raw: Any, active_leaf: Any) -> bool:
    if not nonblank(active_leaf):
        return False
    try:
        normalize_problem_path(raw, active_leaf=str(active_leaf))
    except SystemExit:
        return False
    return True


def simple_combination_counterfactual_complete(value: Any) -> bool:
    return nonblank(value)


def finite_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def nonblank(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def clean_text(value: Any, label: str, *, optional: bool = False) -> str | None:
    if value is None and optional:
        return None
    cleaned = str(value or "").strip()
    if not cleaned:
        raise SystemExit(f"{label} must contain non-whitespace text")
    return cleaned


def calculate_improvement_points(
    metric_scale: str, baseline_score: float, our_score: float
) -> float:
    if not finite_number(baseline_score) or not finite_number(our_score):
        raise SystemExit("--baseline-score and --our-score must be finite numbers")
    if metric_scale == "unit_interval":
        if not (0.0 <= baseline_score <= 1.0 and 0.0 <= our_score <= 1.0):
            raise SystemExit(
                "unit_interval scores must both be between 0 and 1 inclusive"
            )
        gain = (our_score - baseline_score) * 100.0
    elif metric_scale == "percentage":
        if not (0.0 <= baseline_score <= 100.0 and 0.0 <= our_score <= 100.0):
            raise SystemExit(
                "percentage scores must both be between 0 and 100 inclusive"
            )
        gain = our_score - baseline_score
    else:
        raise SystemExit("--metric-scale must be unit_interval or percentage")
    return round(gain, 10)


DATASET_BASELINE_FIELDS = (
    "dataset",
    "role",
    "baseline",
    "venue_year",
    "source",
    "search_scope",
    "protocol_match",
    "protocol_status",
    "comparison_roles",
    "metric",
    "metric_scale",
    "baseline_score",
    "our_score",
    "status",
)


def add_legacy_baseline_metadata(rows: Any) -> Any:
    """Make pre-v13 rows readable without treating missing evidence as verified."""
    if not isinstance(rows, list):
        return rows
    upgraded: list[Any] = []
    for raw in rows:
        if not isinstance(raw, dict):
            upgraded.append(raw)
            continue
        entry = dict(raw)
        entry.setdefault("protocol_status", LEGACY_BASELINE_PROTOCOL_STATUS)
        entry.setdefault(
            "comparison_roles",
            {
                role: {
                    "status": LEGACY_BASELINE_ROLE_STATUS,
                    "evidence": "Not structurally recorded before schema v13",
                }
                for role in BASELINE_COMPARISON_ROLES
            },
        )
        upgraded.append(entry)
    return upgraded


def normalize_adopted_datasets(
    primary_dataset: Any, supporting_datasets: Any
) -> list[dict[str, str]]:
    primary = clean_text(primary_dataset, "--primary-dataset")
    raw_supporting = supporting_datasets or []
    if not isinstance(raw_supporting, list):
        raise SystemExit("--supporting-dataset values must form a list")
    normalized = [{"dataset": primary, "role": "primary"}]
    seen = {primary}
    for index, raw in enumerate(raw_supporting, start=1):
        dataset = clean_text(raw, f"--supporting-dataset #{index}")
        if dataset in seen:
            raise SystemExit(f"Adopted dataset is repeated: {dataset!r}")
        seen.add(dataset)
        normalized.append({"dataset": dataset, "role": "supporting"})
    return normalized


def adopted_datasets_complete(value: Any) -> bool:
    if not isinstance(value, list) or not value:
        return False
    try:
        primary = [item for item in value if item.get("role") == "primary"]
        if len(primary) != 1:
            return False
        normalized = normalize_adopted_datasets(
            primary[0].get("dataset"),
            [item.get("dataset") for item in value if item.get("role") == "supporting"],
        )
    except (AttributeError, SystemExit):
        return False
    return normalized == value


def validate_metric_score(metric_scale: str, value: Any, label: str) -> float:
    if not finite_number(value):
        raise SystemExit(f"{label} must be a finite number")
    score = float(value)
    upper = 1.0 if metric_scale == "unit_interval" else 100.0
    if not 0.0 <= score <= upper:
        raise SystemExit(f"{label} must be between 0 and {upper:g} inclusive")
    return score


def parse_dataset_baseline_matrix(
    raw: Any, *, require_matched: bool = True, allow_legacy_metadata: bool = False
) -> list[dict[str, Any]]:
    if not nonblank(raw):
        raise SystemExit(
            "--dataset-baseline-matrix requires a JSON array with one external-baseline comparison per adopted dataset"
        )
    try:
        matrix = json.loads(str(raw))
    except json.JSONDecodeError as exc:
        raise SystemExit(f"--dataset-baseline-matrix is not valid JSON: {exc}") from exc
    if not isinstance(matrix, list) or not matrix:
        raise SystemExit("--dataset-baseline-matrix must be a non-empty JSON array")
    normalized: list[dict[str, Any]] = []
    seen: set[str] = set()
    for index, raw_entry in enumerate(matrix, start=1):
        if not isinstance(raw_entry, dict):
            raise SystemExit(f"Dataset-baseline row {index} must be a JSON object")
        missing = [
            field
            for field in DATASET_BASELINE_FIELDS
            if field not in raw_entry
            or (
                field not in {"baseline_score", "our_score", "comparison_roles"}
                and not nonblank(raw_entry.get(field))
            )
        ]
        if missing:
            raise SystemExit(
                f"Dataset-baseline row {index} is missing fields: " + ", ".join(missing)
            )
        entry = {
            field: (
                raw_entry[field]
                if field in {"baseline_score", "our_score", "comparison_roles"}
                else str(raw_entry[field]).strip()
            )
            for field in DATASET_BASELINE_FIELDS
        }
        if entry["dataset"] in seen:
            raise SystemExit(
                f"Dataset-baseline matrix repeats dataset {entry['dataset']!r}"
            )
        seen.add(entry["dataset"])
        if entry["role"] not in {"primary", "supporting"}:
            raise SystemExit(
                f"Dataset-baseline row {index} role must be primary or supporting"
            )
        if entry["status"] not in BASELINE_ROSTER_STATUSES:
            raise SystemExit(
                f"Dataset-baseline row {index} status must be one of "
                + ", ".join(sorted(BASELINE_ROSTER_STATUSES))
            )
        allowed_protocol_statuses = set(BASELINE_PROTOCOL_STATUSES)
        if allow_legacy_metadata:
            allowed_protocol_statuses.add(LEGACY_BASELINE_PROTOCOL_STATUS)
        if entry["protocol_status"] not in allowed_protocol_statuses:
            raise SystemExit(
                f"Dataset-baseline row {index} protocol_status must be one of "
                + ", ".join(sorted(allowed_protocol_statuses))
            )
        comparison_roles = entry["comparison_roles"]
        if not isinstance(comparison_roles, dict) or set(comparison_roles) != set(
            BASELINE_COMPARISON_ROLES
        ):
            raise SystemExit(
                f"Dataset-baseline row {index} comparison_roles must contain exactly: "
                + ", ".join(BASELINE_COMPARISON_ROLES)
            )
        normalized_roles: dict[str, dict[str, str]] = {}
        for role in BASELINE_COMPARISON_ROLES:
            role_entry = comparison_roles.get(role)
            if not isinstance(role_entry, dict):
                raise SystemExit(
                    f"Dataset-baseline row {index} comparison role {role!r} "
                    "must be an object"
                )
            role_status = str(role_entry.get("status") or "").strip()
            evidence = str(role_entry.get("evidence") or "").strip()
            allowed_role_statuses = set(BASELINE_ROLE_STATUSES)
            if allow_legacy_metadata:
                allowed_role_statuses.add(LEGACY_BASELINE_ROLE_STATUS)
            if role_status not in allowed_role_statuses:
                raise SystemExit(
                    f"Dataset-baseline row {index} comparison role {role!r} "
                    "status must be one of "
                    + ", ".join(sorted(allowed_role_statuses))
                )
            if not evidence:
                raise SystemExit(
                    f"Dataset-baseline row {index} comparison role {role!r} "
                    "requires source evidence or a concrete blocker"
                )
            normalized_roles[role] = {
                "status": role_status,
                "evidence": evidence,
            }
        entry["comparison_roles"] = normalized_roles
        protocol_status = entry["protocol_status"]
        if protocol_status == "VERIFIED_MATCH":
            normalized_protocol_text = entry["protocol_match"].casefold()
            contradiction = next(
                (
                    pattern
                    for pattern in sorted(PROTOCOL_MISMATCH_PATTERNS)
                    if pattern.casefold() in normalized_protocol_text
                ),
                None,
            )
            if contradiction is not None:
                raise SystemExit(
                    f"Dataset-baseline row {index} claims VERIFIED_MATCH but its "
                    f"protocol evidence says {contradiction!r}"
                )
        if entry["status"] == "MATCHED" and protocol_status != "VERIFIED_MATCH":
            if not (
                allow_legacy_metadata
                and protocol_status == LEGACY_BASELINE_PROTOCOL_STATUS
            ):
                raise SystemExit(
                    f"Dataset-baseline row {index} marked MATCHED requires "
                    "protocol_status VERIFIED_MATCH"
                )
        if entry["status"] == "BLOCKED" and protocol_status != "BLOCKED":
            if not (
                allow_legacy_metadata
                and protocol_status == LEGACY_BASELINE_PROTOCOL_STATUS
            ):
                raise SystemExit(
                    f"Dataset-baseline row {index} marked BLOCKED requires "
                    "protocol_status BLOCKED"
                )
        if entry["status"] == "IDENTIFIED" and protocol_status not in {
            "PENDING_MATCH",
            "VERIFIED_MATCH",
        }:
            if not (
                allow_legacy_metadata
                and protocol_status == LEGACY_BASELINE_PROTOCOL_STATUS
            ):
                raise SystemExit(
                    f"Dataset-baseline row {index} marked IDENTIFIED requires "
                    "protocol_status PENDING_MATCH or VERIFIED_MATCH"
                )
        if require_matched and entry["status"] != "MATCHED":
            raise SystemExit(
                f"Dataset-baseline row {index} must be MATCHED before the paper gate"
            )
        if require_matched and entry["protocol_status"] != "VERIFIED_MATCH":
            if not (
                allow_legacy_metadata
                and entry["protocol_status"] == LEGACY_BASELINE_PROTOCOL_STATUS
            ):
                raise SystemExit(
                    f"Dataset-baseline row {index} must have VERIFIED_MATCH protocol "
                    "status before the paper gate"
                )
        if require_matched and normalized_roles["recent_top_conference"][
            "status"
        ] != "COVERED":
            if not (
                allow_legacy_metadata
                and normalized_roles["recent_top_conference"]["status"]
                == LEGACY_BASELINE_ROLE_STATUS
            ):
                raise SystemExit(
                    f"Dataset-baseline row {index} must cover the recent top-conference "
                    "comparison before the paper gate"
                )
        if entry["metric_scale"] not in {"unit_interval", "percentage"}:
            raise SystemExit(
                f"Dataset-baseline row {index} metric_scale must be unit_interval or percentage"
            )
        baseline_score = entry["baseline_score"]
        our_score = entry["our_score"]
        if entry["status"] == "MATCHED":
            calculate_improvement_points(entry["metric_scale"], baseline_score, our_score)
            entry["baseline_score"] = float(baseline_score)
            entry["our_score"] = float(our_score)
        else:
            entry["baseline_score"] = (
                None
                if baseline_score is None
                else validate_metric_score(
                    entry["metric_scale"], baseline_score, f"row {index} baseline_score"
                )
            )
            entry["our_score"] = (
                None
                if our_score is None
                else validate_metric_score(
                    entry["metric_scale"], our_score, f"row {index} our_score"
                )
            )
        normalized.append(entry)
    if sum(entry["role"] == "primary" for entry in normalized) != 1:
        raise SystemExit("Dataset-baseline matrix must contain exactly one primary row")
    return normalized


def baseline_rows_cover_adopted_datasets(
    rows: Any, adopted_datasets: Any
) -> bool:
    if not isinstance(rows, list) or not adopted_datasets_complete(adopted_datasets):
        return False
    expected = {
        (item["dataset"], item["role"]) for item in adopted_datasets
    }
    actual = {
        (item.get("dataset"), item.get("role"))
        for item in rows
        if isinstance(item, dict)
    }
    return len(rows) == len(expected) and actual == expected


def baseline_roster_payload_sha256(roster: dict[str, Any]) -> str:
    return canonical_payload_sha256(
        {
            "direction_id": roster.get("direction_id"),
            "revision": roster.get("revision"),
            "rows": roster.get("rows"),
        }
    )


def baseline_roster_usable(state: dict[str, Any], *, require_matched: bool = False) -> bool:
    roster = state.get("dataset_baseline_roster")
    direction = state.get("layer_checkpoints", {}).get("direction", {})
    direction_payload = direction.get("payload") or {}
    if not isinstance(roster, dict) or direction.get("status") != "CONFIRMED_BY_PI":
        return False
    if roster.get("schema_v13_review_required"):
        return False
    if roster.get("direction_id") != direction.get("id"):
        return False
    if not isinstance(roster.get("revision"), int) or roster["revision"] < 1:
        return False
    if roster.get("payload_sha256") != baseline_roster_payload_sha256(roster):
        return False
    try:
        rows = parse_dataset_baseline_matrix(
            json.dumps(roster.get("rows"), ensure_ascii=False),
            require_matched=require_matched,
        )
    except SystemExit:
        return False
    return baseline_rows_cover_adopted_datasets(
        rows, direction_payload.get("adopted_datasets")
    )


def baseline_roster_record_usable(state_path: Path, state: dict[str, Any]) -> bool:
    roster = state.get("dataset_baseline_roster") or {}
    record = resolve_stored_path(state_path, roster.get("record_path"))
    receipt_hash = roster.get("record_sha256_at_receipt")
    if not (
        record
        and record.is_file()
        and stored_path_is_project_local(state_path, roster.get("record_path"))
        and nonblank(receipt_hash)
    ):
        return False
    if roster.get("record_kind") == "legacy_paper_assessment":
        return sha256_file(record) == receipt_hash
    if roster.get("record_kind") != "baseline_roster_receipt":
        return False
    try:
        text = record.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return False
    return bool(
        "## Dataset baseline roster receipt" in text
        and f"`{roster.get('payload_sha256')}`" in text
    )


def dataset_baseline_matrix_complete(assessment: dict[str, Any]) -> bool:
    matrix = assessment.get("dataset_baseline_matrix")
    if not isinstance(matrix, list) or not matrix:
        return False
    try:
        normalized = parse_dataset_baseline_matrix(
            json.dumps(matrix, ensure_ascii=False)
        )
    except SystemExit:
        return False
    primary = [entry for entry in normalized if entry["role"] == "primary"]
    if len(primary) != 1:
        return False
    if not baseline_rows_cover_adopted_datasets(
        normalized, assessment.get("adopted_datasets")
    ):
        return False
    row = primary[0]
    return bool(
        row["dataset"] == assessment.get("primary_comparison_dataset")
        and row["baseline"] == assessment.get("recent_top_conference_baseline")
        and row["venue_year"] == assessment.get("baseline_venue_year")
        and row["source"] == assessment.get("baseline_source")
        and row["search_scope"] == assessment.get("baseline_search_scope")
        and row["metric"] == assessment.get("primary_metric")
        and row["metric_scale"] == assessment.get("metric_scale")
        and math.isclose(
            row["baseline_score"], assessment.get("baseline_score"), abs_tol=1e-9
        )
        and math.isclose(
            row["our_score"], assessment.get("our_score"), abs_tol=1e-9
        )
    )


def evaluation_anchor_complete(anchor: Any) -> bool:
    if not isinstance(anchor, dict):
        return False
    if not isinstance(anchor.get("revision"), int) or anchor["revision"] < 1:
        return False
    if any(
        not isinstance(anchor.get(field), str) or not anchor[field].strip()
        for field in (
            "direction_id",
            "problem_id",
            "method_cluster_id",
            "falsifiable_prediction",
            "primary_metric",
            "metric_scale",
            "metric_direction",
            "locked_at",
            "reason",
        )
    ):
        return False
    return (
        problem_path_complete(anchor.get("problem_path"), anchor.get("problem_id"))
        and anchor["metric_scale"] in {"unit_interval", "percentage"}
        and anchor["metric_direction"] in METRIC_DIRECTIONS
    )


def evaluation_anchor_usable(state: dict[str, Any]) -> bool:
    anchor = state.get("evaluation_anchor")
    direction = state.get("layer_checkpoints", {}).get("direction", {})
    return bool(
        evaluation_anchor_complete(anchor)
        and not anchor.get("legacy_derived")
        and not anchor.get("legacy_scientific_scope_unscoped")
        and direction.get("status") == "CONFIRMED_BY_PI"
        and anchor.get("direction_id") == direction.get("id")
    )


def science_matches_evaluation_anchor(state: dict[str, Any]) -> bool:
    anchor = state.get("evaluation_anchor") or {}
    science = (state.get("layer_checkpoints") or {}).get("science") or {}
    payload = science.get("payload") or {}
    return bool(
        evaluation_anchor_usable(state)
        and science.get("status") == "CONFIRMED_BY_PI"
        and payload.get("direction_id") == anchor.get("direction_id")
        and payload.get("problem_path") == anchor.get("problem_path")
        and payload.get("problem_id") == anchor.get("problem_id")
        and payload.get("method_cluster_id") == anchor.get("method_cluster_id")
        and payload.get("falsifiable_prediction")
        == anchor.get("falsifiable_prediction")
        and simple_combination_counterfactual_complete(
            payload.get("simple_combination_counterfactual")
        )
        and not payload.get("legacy_method_counterfactual_unscoped")
    )


def paper_assessment_complete(assessment: Any) -> bool:
    if not isinstance(assessment, dict):
        return False
    if any(
        not isinstance(assessment.get(field), str)
        or not assessment[field].strip()
        for field in PAPER_ASSESSMENT_TEXT_FIELDS
    ):
        return False
    if assessment.get("metric_scale") not in {"unit_interval", "percentage"}:
        return False
    if assessment.get("metric_direction") not in METRIC_DIRECTIONS:
        return False
    if not isinstance(assessment.get("evaluation_anchor_revision"), int) or assessment[
        "evaluation_anchor_revision"
    ] < 1:
        return False
    if not isinstance(assessment.get("favorable_seed_selection"), bool):
        return False
    if any(
        not finite_number(assessment.get(field))
        for field in (
            *PAPER_ASSESSMENT_NUMERIC_FIELDS,
            "minimum_paper_gain_points",
            "improvement_points",
        )
    ):
        return False
    if any(
        not isinstance(assessment.get(field), str)
        or not assessment[field].strip()
        for field in (
            "current_task",
            "dataset",
            "current_work_problem",
            "problem_id",
            "method_cluster_id",
            "innovation",
            "core_mechanism",
            "baseline_roster_payload_sha256",
        )
    ):
        return False
    if not adopted_datasets_complete(assessment.get("adopted_datasets")):
        return False
    if not problem_path_complete(
        assessment.get("problem_path"), assessment.get("problem_id")
    ):
        return False
    if not isinstance(assessment.get("baseline_roster_revision"), int) or assessment[
        "baseline_roster_revision"
    ] < 1:
        return False
    try:
        calculated = calculate_improvement_points(
            assessment["metric_scale"],
            assessment["baseline_score"],
            assessment["our_score"],
        )
    except SystemExit:
        return False
    return (
        dataset_baseline_matrix_complete(assessment)
        and assessment["minimum_paper_gain_points"] >= MIN_PAPER_READY_GAIN_POINTS
        and math.isclose(
            assessment["improvement_points"], calculated, abs_tol=1e-9
        )
        and calculated + 1e-9 >= assessment["minimum_paper_gain_points"]
    )


def paper_assessment_payload_sha256(assessment: dict[str, Any]) -> str:
    payload = {
        field: assessment.get(field) for field in PAPER_ASSESSMENT_PAYLOAD_FIELDS
    }
    canonical = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()


def canonical_payload_sha256(payload: Any) -> str:
    canonical = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()


def reject_irrelevant_checkpoint_fields(args: argparse.Namespace) -> None:
    allowed = CHECKPOINT_LAYER_FIELDS[args.layer]
    unexpected = []
    for name in sorted(ALL_CHECKPOINT_FIELDS - allowed):
        value = getattr(args, name, None)
        if value is not None and value is not False:
            unexpected.append("--" + name.replace("_", "-"))
    if unexpected:
        raise SystemExit(
            f"Checkpoint layer {args.layer!r} does not use: " + ", ".join(unexpected)
        )


def empty_checkpoint() -> dict[str, Any]:
    return {
        "status": "UNSET",
        "id": None,
        "summary": None,
        "payload": None,
        "confirmed_at": None,
        "decision_source": None,
        "record_path": None,
        "record_sha256_at_confirmation": None,
    }


def empty_instruction_maintenance() -> dict[str, Any]:
    return {
        "policy": {
            "root_target_bytes": ROOT_AGENTS_TARGET_BYTES,
            "root_review_bytes": ROOT_AGENTS_REVIEW_BYTES,
            "effective_chain_target_bytes": EFFECTIVE_AGENTS_TARGET_BYTES,
            "codex_project_doc_default_bytes": CODEX_PROJECT_DOC_DEFAULT_BYTES,
        },
        "audits_by_scope": {},
        "recent_updates": [],
        "compacted_update_count": 0,
        "recent_scope_removals": [],
        "compacted_scope_removal_count": 0,
    }


def empty_monitoring() -> dict[str, Any]:
    return {
        "last_acknowledged_wakeup_fingerprint": None,
        "artifact_fingerprints_by_job": {},
        "legacy_unscoped_artifact_fingerprint": None,
        "acknowledged_at": None,
    }


def empty_research_window() -> dict[str, Any]:
    """Return the non-authoritative current-run reporting cache.

    The sequence survives window replacement, but prior cards do not.  This is
    deliberately not an experiment history or a scientific checkpoint.
    """

    return {
        "sequence": 0,
        "id": None,
        "status": "NOT_STARTED",
        "started_at": None,
        "instruction": None,
        "start_snapshot": None,
        "revision": 0,
        "cards": [],
        "current_focus": None,
    }


def validate_research_window_state(window: Any) -> None:
    if not isinstance(window, dict):
        raise SystemExit("Invalid research_window: expected an object")
    for field in ("sequence", "revision"):
        value = window.get(field)
        if isinstance(value, bool) or not isinstance(value, int) or value < 0:
            raise SystemExit(f"Invalid research_window.{field}: expected a non-negative integer")
    if window.get("status") not in {"NOT_STARTED", "ACTIVE"}:
        raise SystemExit("Invalid research_window.status")
    cards = window.get("cards")
    if not isinstance(cards, list):
        raise SystemExit("Invalid research_window.cards: expected a list")
    if window.get("status") == "ACTIVE" and not all(
        nonblank(window.get(field)) for field in ("id", "started_at", "instruction")
    ):
        raise SystemExit("An active research window requires id, started_at, and instruction")
    seen: set[tuple[str, str, str]] = set()
    required_card_fields = (
        "layer",
        "kind",
        "subject_id",
        "title",
        "status",
        "verified_observation",
        "interpretation",
        "external_baseline_gap",
        "next_action",
        "first_recorded_at",
        "updated_at",
    )
    for card in cards:
        if not isinstance(card, dict):
            raise SystemExit("Invalid research_window card: expected an object")
        if any(not nonblank(card.get(field)) for field in required_card_fields):
            raise SystemExit("Invalid research_window card: required text field is blank")
        layer = str(card["layer"])
        kind = str(card["kind"])
        if layer not in WINDOW_CARD_KINDS_BY_LAYER or kind not in WINDOW_CARD_KINDS_BY_LAYER[layer]:
            raise SystemExit("Research-window cards may contain only supported L1/L2 scientific kinds")
        if card.get("status") not in WINDOW_CARD_STATUSES:
            raise SystemExit("Invalid research_window card status")
        key = (layer, kind, str(card["subject_id"]))
        if key in seen:
            raise SystemExit("Duplicate research_window card identity")
        seen.add(key)
        if "problem_path" in card:
            if layer != "L2" or kind != "problem":
                raise SystemExit("Only an L2 problem card may carry a problem_path")
            normalize_problem_path(
                card.get("problem_path"),
                active_leaf=str(card["subject_id"]),
                label="research-window problem path",
            )
    focus = window.get("current_focus")
    if focus is not None:
        if not isinstance(focus, dict):
            raise SystemExit("Invalid research_window.current_focus")
        for field in (
            "layer",
            "kind",
            "subject_id",
            "hypothesis",
            "current_action",
            "latest_result",
            "next_action",
            "updated_at",
        ):
            if not nonblank(focus.get(field)):
                raise SystemExit(f"Invalid research_window.current_focus.{field}")
        key = (str(focus["layer"]), str(focus["kind"]), str(focus["subject_id"]))
        if key not in seen:
            raise SystemExit("research_window.current_focus must reference an existing card")


def initial_state(project: str) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "project": project,
        "phase": "discussion",
        "status": "ACTIVE",
        "paused_for_pi": False,
        "manual_pause": None,
        "last_manual_pause_event": None,
        "monitoring": empty_monitoring(),
        "research_window": empty_research_window(),
        "frozen_by_pi": {},
        "frozen_history": [],
        "layer_checkpoints": {
            layer: empty_checkpoint() for layer in CHECKPOINT_LAYERS
        },
        "checkpoint_history": [],
        "evaluation_anchor": None,
        "evaluation_anchor_history": [],
        "dataset_baseline_roster": None,
        "dataset_baseline_roster_history": [],
        "seed_selection_risk_acceptance": None,
        "paper_ready_assessment": None,
        "invalidated_paper_assessments": [],
        "invalidated_paper_assessment_count": 0,
        "macro_questions": [],
        "decision_target_revisions": {},
        "notifications": [],
        "notification_compacted_count": 0,
        "notification_sequence": 0,
        "notification_policy": {
            "mode": "recent_only",
            "recent_limit": RECENT_NOTIFICATION_LIMIT,
        },
        "instruction_maintenance": empty_instruction_maintenance(),
        "jobs": [],
        "created_at": now_iso(),
        "updated_at": now_iso(),
    }


def archive_invalidated_paper_assessment(
    state: dict[str, Any], reason: str, replacement_id: str | None = None
) -> None:
    assessment = state.get("paper_ready_assessment")
    if not isinstance(assessment, dict):
        state["paper_ready_assessment"] = None
        state["seed_selection_risk_acceptance"] = None
        return
    history = state.setdefault("invalidated_paper_assessments", [])
    history.append(
        {
            "path": assessment.get("path"),
            "sha256_at_gate": assessment.get("sha256_at_gate"),
            "payload_sha256_at_gate": assessment.get("payload_sha256_at_gate"),
            "direction_id": assessment.get("direction_id"),
            "science_id": assessment.get("science_id"),
            "recorded_at": assessment.get("recorded_at"),
            "invalidated_at": now_iso(),
            "reason": reason,
            "replacement_id": replacement_id,
        }
    )
    if len(history) > RECENT_INVALIDATED_PAPER_LIMIT:
        overflow = len(history) - RECENT_INVALIDATED_PAPER_LIMIT
        del history[:overflow]
        state["invalidated_paper_assessment_count"] = int(
            state.get("invalidated_paper_assessment_count") or 0
        ) + overflow
    state["paper_ready_assessment"] = None
    state["seed_selection_risk_acceptance"] = None


def invalidate_baseline_roster(
    state: dict[str, Any], reason: str, replacement_id: str
) -> None:
    roster = state.get("dataset_baseline_roster")
    if isinstance(roster, dict):
        state.setdefault("dataset_baseline_roster_history", []).append(
            {
                **roster,
                "invalidated_at": now_iso(),
                "invalidated_by": reason,
                "replacement_id": replacement_id,
            }
        )
    state["dataset_baseline_roster"] = None


def migrate_state(state: dict[str, Any], version: int) -> dict[str, Any]:
    if version == 1:
        state.setdefault("frozen_history", [])
    if version in {1, 2}:
        state.setdefault(
            "layer_checkpoints",
            {
                "direction": empty_checkpoint(),
                "science": empty_checkpoint(),
            },
        )
        state.setdefault("checkpoint_history", [])
    if version in {1, 2, 3}:
        checkpoints = state.setdefault("layer_checkpoints", {})
        for layer in CHECKPOINT_LAYERS:
            checkpoints.setdefault(layer, empty_checkpoint())
        for layer in CHECKPOINT_LAYERS:
            checkpoint = checkpoints[layer]
            if not isinstance(checkpoint, dict):
                checkpoints[layer] = empty_checkpoint()
                continue
            for key, value in empty_checkpoint().items():
                checkpoint.setdefault(key, value)
            if (
                checkpoint.get("status") == "CONFIRMED_BY_PI"
                and not checkpoint.get("payload")
            ):
                checkpoint["status"] = "LEGACY_CONFIRMED_NEEDS_AUDIT"
        state.setdefault("paper_ready_assessment", None)
        state.setdefault(
            "notification_compacted_count", state.pop("notification_archive_count", 0)
        )
        sequence = 0
        for item in state.get("notifications", []):
            raw = str(item.get("id", ""))
            if raw.startswith("N") and raw[1:].isdigit():
                sequence = max(sequence, int(raw[1:]))
        state.setdefault("notification_sequence", sequence)
        state.setdefault(
            "notification_policy",
            {"mode": "preserve_legacy", "recent_limit": RECENT_NOTIFICATION_LIMIT},
        )
        state.setdefault("jobs", [])
        for question in state.setdefault("macro_questions", []):
            question.setdefault("outcome", None)
    if version in {1, 2, 3, 4}:
        for question in state.setdefault("macro_questions", []):
            question.setdefault("decision_target", None)
            question.setdefault("consumed_by", None)
            question.setdefault("responses", [])
            question.setdefault("revisit_condition", None)
            question.setdefault("deferred_at", None)
            question.setdefault("reopened_at", None)
        checkpoints = state.setdefault("layer_checkpoints", {})
        for layer in CHECKPOINT_LAYERS:
            checkpoint = checkpoints.setdefault(layer, empty_checkpoint())
            source = checkpoint.get("decision_source") or {}
            question_id = source.get("question_id")
            if not question_id:
                continue
            matches = [
                q for q in state["macro_questions"] if q.get("id") == question_id
            ]
            if not matches:
                continue
            question = matches[0]
            target = f"{layer}:{checkpoint.get('id')}"
            question["decision_target"] = question.get("decision_target") or target
            question["consumed_by"] = question.get("consumed_by") or {
                "type": "checkpoint",
                "layer": layer,
                "id": checkpoint.get("id"),
                "migrated_at": now_iso(),
            }
        science = checkpoints.get("science", {})
        if science.get("status") == "CONFIRMED_BY_PI":
            payload = science.get("payload") or {}
            if not payload.get("evidence_refs"):
                science["status"] = "LEGACY_CONFIRMED_NEEDS_AUDIT"
    if version in {1, 2, 3, 4, 5}:
        state.setdefault("instruction_maintenance", empty_instruction_maintenance())
    if version in {1, 2, 3, 4, 5, 6}:
        maintenance = state.setdefault("instruction_maintenance", empty_instruction_maintenance())
        audits = maintenance.setdefault("audits_by_scope", {})
        legacy_audit = maintenance.pop("last_audit", None)
        if isinstance(legacy_audit, dict):
            audits[instruction_scope_key(legacy_audit)] = legacy_audit

        revisions: dict[str, int] = {}
        latest_by_target: dict[str, dict[str, Any]] = {}
        for question in state.setdefault("macro_questions", []):
            target = str(question.get("decision_target") or "").strip()
            if not target:
                question.setdefault("target_revision", None)
                question.setdefault("superseded_by", None)
                continue
            revisions[target] = revisions.get(target, 0) + 1
            question["target_revision"] = revisions[target]
            question["superseded_by"] = None
            previous = latest_by_target.get(target)
            if previous is not None and not previous.get("consumed_by"):
                previous["superseded_by"] = question.get("id")
            latest_by_target[target] = question
        state["decision_target_revisions"] = revisions
        for update in maintenance.setdefault("recent_updates", []):
            update.setdefault("after_absent", False)
            if "canonical_sources" not in update:
                update["canonical_sources"] = []
                if update.get("kind") == "compaction":
                    update["legacy_source_unverified"] = True
    if version in {1, 2, 3, 4, 5, 6, 7}:
        maintenance = state.setdefault("instruction_maintenance", empty_instruction_maintenance())
        maintenance.setdefault("recent_scope_removals", [])
        maintenance.setdefault("compacted_scope_removal_count", 0)
        direction = state.setdefault("layer_checkpoints", {}).setdefault(
            "direction", empty_checkpoint()
        )
        if direction.get("status") == "CONFIRMED_BY_PI" and not (
            (direction.get("payload") or {}).get("unexposed_dataset_search")
        ):
            direction["status"] = "LEGACY_CONFIRMED_NEEDS_AUDIT"
    if version in {1, 2, 3, 4, 5, 6, 7, 8}:
        direction = state.setdefault("layer_checkpoints", {}).setdefault(
            "direction", empty_checkpoint()
        )
        standard = (direction.get("payload") or {}).get("evidence_standard") or {}
        legacy_minimum = standard.get("minimum_paper_gain_points")
        if direction.get("status") == "CONFIRMED_BY_PI" and (
            not finite_number(legacy_minimum)
            or legacy_minimum < MIN_PAPER_READY_GAIN_POINTS
        ):
            direction["status"] = "LEGACY_CONFIRMED_NEEDS_AUDIT"
    if version in {1, 2, 3, 4, 5, 6, 7, 8, 9}:
        state.setdefault("evaluation_anchor_history", [])
        state.setdefault("seed_selection_risk_acceptance", None)
        assessment = state.get("paper_ready_assessment")
        if (
            isinstance(assessment, dict)
            and assessment.get("primary_metric")
            and assessment.get("metric_scale")
        ):
            locked_at = (
                assessment.get("recorded_at")
                or state.get("updated_at")
                or now_iso()
            )
            anchor = {
                "revision": 1,
                "direction_id": assessment.get("direction_id"),
                "primary_metric": assessment.get("primary_metric"),
                "metric_scale": assessment.get("metric_scale"),
                "metric_direction": "higher_is_better",
                "locked_at": locked_at,
                "reason": (
                    "Migrated from a pre-v10 paper assessment; prospective "
                    "pre-tuning lock timing was not recorded"
                ),
                "legacy_derived": True,
            }
            if not isinstance(state.get("evaluation_anchor"), dict):
                state["evaluation_anchor"] = anchor
            assessment.setdefault("evaluation_anchor_revision", 1)
            assessment.setdefault("metric_direction", "higher_is_better")
            assessment.setdefault(
                "evaluation_anchor_evidence",
                "Legacy pre-v10 assessment imported without a prospective lock receipt",
            )
            assessment.setdefault(
                "stability_evidence",
                "Legacy pre-v10 assessment did not structurally capture stability evidence",
            )
            assessment.setdefault("favorable_seed_selection", False)
            assessment["payload_sha256_at_gate"] = paper_assessment_payload_sha256(
                assessment
            )
        else:
            state.setdefault("evaluation_anchor", None)
    if version in {1, 2, 3, 4, 5, 6, 7, 8, 9, 10}:
        state.setdefault("manual_pause", None)
        state.setdefault("last_manual_pause_event", None)
        state.setdefault(
            "monitoring",
            {
                "last_acknowledged_wakeup_fingerprint": None,
                "last_acknowledged_artifact_fingerprint": None,
                "acknowledged_at": None,
            },
        )
        assessment = state.get("paper_ready_assessment")
        if isinstance(assessment, dict) and not (
            nonblank(assessment.get("primary_comparison_dataset"))
            and isinstance(assessment.get("dataset_baseline_matrix"), list)
            and bool(assessment.get("dataset_baseline_matrix"))
        ):
            # A pre-v11 paper packet did not prove per-dataset external-baseline
            # coverage. Preserve the project direction and science, but make the
            # paper packet ineligible until it is rebuilt.
            archive_invalidated_paper_assessment(
                state,
                "schema_v11_dataset_baseline_reassessment",
                "schema-v11-dataset-baseline-reassessment",
            )
            if state.get("phase") in {"paper_ready_pending_pi", "paper_handoff_approved"}:
                state["phase"] = "confirmed_project"
            paper = state.setdefault("layer_checkpoints", {}).setdefault(
                "paper", empty_checkpoint()
            )
            if paper.get("status") != "UNSET":
                state.setdefault("checkpoint_history", []).append(
                    {
                        "layer": "paper",
                        "previous": paper,
                        "replacement_id": "schema-v11-dataset-baseline-reassessment",
                        "decision_source": {"type": "schema_v11_migration"},
                        "created_at": now_iso(),
                    }
                )
                state["layer_checkpoints"]["paper"] = empty_checkpoint()
    if version in set(range(1, 12)):
        state.setdefault("dataset_baseline_roster_history", [])
        state.setdefault("invalidated_paper_assessments", [])
        state.setdefault("invalidated_paper_assessment_count", 0)

        legacy_monitoring = state.get("monitoring") or {}
        legacy_artifact = legacy_monitoring.get(
            "last_acknowledged_artifact_fingerprint"
        )
        state["monitoring"] = {
            "last_acknowledged_wakeup_fingerprint": legacy_monitoring.get(
                "last_acknowledged_wakeup_fingerprint"
            ),
            "artifact_fingerprints_by_job": {},
            "legacy_unscoped_artifact_fingerprint": legacy_artifact,
            "acknowledged_at": legacy_monitoring.get("acknowledged_at"),
        }

        direction = state.setdefault("layer_checkpoints", {}).setdefault(
            "direction", empty_checkpoint()
        )
        direction_payload = direction.get("payload") or {}
        assessment = state.get("paper_ready_assessment")
        migrated_rows = None
        if isinstance(assessment, dict) and isinstance(
            assessment.get("dataset_baseline_matrix"), list
        ):
            try:
                migrated_rows = parse_dataset_baseline_matrix(
                    json.dumps(
                        add_legacy_baseline_metadata(
                            assessment["dataset_baseline_matrix"]
                        ),
                        ensure_ascii=False,
                    ),
                    allow_legacy_metadata=True,
                )
                migrated_rows = [
                    row for row in migrated_rows if row["role"] == "primary"
                ] + [row for row in migrated_rows if row["role"] == "supporting"]
            except SystemExit:
                migrated_rows = None
        if direction.get("status") == "CONFIRMED_BY_PI":
            if migrated_rows:
                direction_payload["adopted_datasets"] = [
                    {"dataset": row["dataset"], "role": row["role"]}
                    for row in migrated_rows
                ]
                direction["payload"] = direction_payload
            elif not adopted_datasets_complete(
                direction_payload.get("adopted_datasets")
            ):
                direction["status"] = "LEGACY_CONFIRMED_NEEDS_DATASET_INVENTORY"

        if migrated_rows and direction.get("id"):
            roster = {
                "direction_id": direction.get("id"),
                "revision": 1,
                "rows": migrated_rows,
                "reason": "Migrated from the schema-v11 locked paper assessment",
                "recorded_at": assessment.get("recorded_at") if assessment else now_iso(),
                "record_path": assessment.get("path") if assessment else None,
                "record_kind": "legacy_paper_assessment",
                "record_sha256_at_receipt": (
                    assessment.get("sha256_after_handoff")
                    or assessment.get("sha256_at_gate")
                    if assessment
                    else None
                ),
            }
            roster["payload_sha256"] = baseline_roster_payload_sha256(roster)
            state["dataset_baseline_roster"] = roster
        else:
            state.setdefault("dataset_baseline_roster", None)

        science = state["layer_checkpoints"].setdefault("science", empty_checkpoint())
        if science.get("status") == "CONFIRMED_BY_PI":
            science["status"] = "LEGACY_CONFIRMED_NEEDS_PROBLEM_STRUCTURE"
            if isinstance(state.get("paper_ready_assessment"), dict):
                archive_invalidated_paper_assessment(
                    state,
                    "schema_v12_problem_method_structure_required",
                    "schema-v12-problem-method-reassessment",
                )
                if state.get("phase") in {
                    "paper_ready_pending_pi",
                    "paper_handoff_approved",
                }:
                    state["phase"] = "confirmed_project"
                paper = state["layer_checkpoints"].setdefault(
                    "paper", empty_checkpoint()
                )
                if paper.get("status") != "UNSET":
                    state.setdefault("checkpoint_history", []).append(
                        {
                            "layer": "paper",
                            "previous": paper,
                            "replacement_id": "schema-v12-problem-method-reassessment",
                            "decision_source": {"type": "schema_v12_migration"},
                            "created_at": now_iso(),
                        }
                    )
                    state["layer_checkpoints"]["paper"] = empty_checkpoint()
    if version in set(range(1, 13)):
        roster = state.get("dataset_baseline_roster")
        if isinstance(roster, dict) and isinstance(roster.get("rows"), list):
            previous_roster = dict(roster)
            roster["rows"] = add_legacy_baseline_metadata(roster["rows"])
            roster["payload_sha256"] = baseline_roster_payload_sha256(roster)
            roster["schema_v13_review_required"] = True
            state.setdefault("dataset_baseline_roster_history", []).append(
                {
                    **previous_roster,
                    "invalidated_at": now_iso(),
                    "invalidated_by": "schema_v13_baseline_evidence_upgrade",
                    "replacement_id": "schema-v13-baseline-evidence-review",
                }
            )
        if version == 12 and isinstance(state.get("paper_ready_assessment"), dict):
            archive_invalidated_paper_assessment(
                state,
                "schema_v13_baseline_evidence_upgrade",
                "schema-v13-baseline-evidence-review",
            )
            if state.get("phase") in {
                "paper_ready_pending_pi",
                "paper_handoff_approved",
            }:
                state["phase"] = "confirmed_project"
            paper = state.setdefault("layer_checkpoints", {}).setdefault(
                "paper", empty_checkpoint()
            )
            if paper.get("status") != "UNSET":
                state.setdefault("checkpoint_history", []).append(
                    {
                        "layer": "paper",
                        "previous": paper,
                        "replacement_id": "schema-v13-baseline-evidence-review",
                        "decision_source": {"type": "schema_v13_migration"},
                        "created_at": now_iso(),
                    }
                )
                state["layer_checkpoints"]["paper"] = empty_checkpoint()
    if version in set(range(1, 14)):
        # Pre-v14 projects have no trustworthy boundary for "since the PI last
        # asked the agent to run".  Start empty rather than reconstructing or
        # fabricating activity from jobs, notifications, or file timestamps.
        state["research_window"] = empty_research_window()
    if version in set(range(1, 15)):
        science = state.setdefault("layer_checkpoints", {}).setdefault(
            "science", empty_checkpoint()
        )
        payload = science.get("payload") if isinstance(science.get("payload"), dict) else {}
        if nonblank(payload.get("problem_id")):
            # The prior approved leaf is the only ancestry v14 can prove.  Do
            # not invent broader motivation nodes during migration.
            payload["problem_path"] = [str(payload["problem_id"])]
            if not nonblank(payload.get("simple_combination_counterfactual")):
                payload["legacy_method_counterfactual_unscoped"] = True
            science["payload"] = payload
            science["summary"] = json.dumps(payload, ensure_ascii=False, sort_keys=True)
        anchor = state.get("evaluation_anchor")
        if isinstance(anchor, dict):
            anchor["legacy_scientific_scope_unscoped"] = True
            invalidate_evaluation_anchor(
                state,
                "schema_v15_scientific_scope_upgrade",
                "schema-v15-scientific-scope-relock",
            )
        if isinstance(state.get("paper_ready_assessment"), dict):
            archive_invalidated_paper_assessment(
                state,
                "schema_v15_scientific_scope_upgrade",
                "schema-v15-scientific-scope-relock",
            )
            if state.get("phase") in {
                "paper_ready_pending_pi",
                "paper_handoff_approved",
            }:
                state["phase"] = "confirmed_project"
            paper = state["layer_checkpoints"].setdefault("paper", empty_checkpoint())
            if paper.get("status") != "UNSET":
                state.setdefault("checkpoint_history", []).append(
                    {
                        "layer": "paper",
                        "previous": paper,
                        "replacement_id": "schema-v15-scientific-scope-relock",
                        "decision_source": {"type": "schema_v15_migration"},
                        "created_at": now_iso(),
                    }
                )
                state["layer_checkpoints"]["paper"] = empty_checkpoint()
    state["schema_version"] = SCHEMA_VERSION
    return state


def load_state(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise SystemExit(f"State file does not exist: {path}")
    try:
        state = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise SystemExit(f"Cannot read valid JSON state from {path}: {exc}") from exc
    version = state.get("schema_version")
    if version not in SUPPORTED_SCHEMA_VERSIONS:
        raise SystemExit(
            f"Unsupported schema_version={version!r}; "
            f"expected one of {sorted(SUPPORTED_SCHEMA_VERSIONS)}"
        )
    state = migrate_state(state, int(version))
    required_types = {
        "project": str,
        "phase": str,
        "frozen_by_pi": dict,
        "frozen_history": list,
        "layer_checkpoints": dict,
        "checkpoint_history": list,
        "evaluation_anchor_history": list,
        "dataset_baseline_roster_history": list,
        "macro_questions": list,
        "decision_target_revisions": dict,
        "notifications": list,
        "instruction_maintenance": dict,
        "jobs": list,
        "monitoring": dict,
        "research_window": dict,
        "invalidated_paper_assessments": list,
    }
    for key, expected_type in required_types.items():
        if not isinstance(state.get(key), expected_type):
            raise SystemExit(
                f"Invalid state field {key!r}: expected {expected_type.__name__}"
            )
    validate_research_window_state(state.get("research_window"))
    if state.get("evaluation_anchor") is not None and not isinstance(
        state.get("evaluation_anchor"), dict
    ):
        raise SystemExit("Invalid evaluation_anchor: expected an object or null")
    if state.get("dataset_baseline_roster") is not None and not isinstance(
        state.get("dataset_baseline_roster"), dict
    ):
        raise SystemExit("Invalid dataset_baseline_roster: expected an object or null")
    monitoring = state.get("monitoring") or {}
    if not isinstance(monitoring.get("artifact_fingerprints_by_job"), dict):
        raise SystemExit(
            "Invalid monitoring.artifact_fingerprints_by_job: expected an object"
        )
    if state.get("seed_selection_risk_acceptance") is not None and not isinstance(
        state.get("seed_selection_risk_acceptance"), dict
    ):
        raise SystemExit(
            "Invalid seed_selection_risk_acceptance: expected an object or null"
        )
    if state.get("manual_pause") is not None and not isinstance(
        state.get("manual_pause"), dict
    ):
        raise SystemExit("Invalid manual_pause: expected an object or null")
    for layer in CHECKPOINT_LAYERS:
        checkpoint = state["layer_checkpoints"].get(layer)
        if not isinstance(checkpoint, dict):
            raise SystemExit(f"Invalid or missing layer checkpoint: {layer}")
    seen_question_ids: set[str] = set()
    for question in state["macro_questions"]:
        if not isinstance(question, dict):
            raise SystemExit("Every PI question must be a structured object")
        question_id = str(question.get("id") or "")
        if not question_id or question_id in seen_question_ids:
            raise SystemExit("PI question IDs must be non-empty and unique")
        seen_question_ids.add(question_id)
        if question.get("status") not in {"PENDING_PI", "DEFERRED_PI", "ANSWERED"}:
            raise SystemExit(
                f"PI question {question_id} has an invalid status: "
                f"{question.get('status')!r}"
            )
    if any(not isinstance(job, dict) for job in state["jobs"]):
        raise SystemExit("Every job record must be a structured object")
    refresh_pause(state)
    return state


def save_state(path: Path, state: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    state["updated_at"] = now_iso()
    temp = path.with_name(path.name + ".tmp")
    temp.write_text(
        json.dumps(state, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    os.replace(temp, path)


def project_root_for_state(path: Path) -> Path:
    parent = path.resolve().parent
    return parent.parent if parent.name == ".codex" else parent


def research_root_for_state(path: Path) -> Path:
    return path.resolve().parent / "research"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def project_local_path(state_path: Path, raw: str, *, require_file: bool = False) -> tuple[Path, str]:
    project_root = project_root_for_state(state_path).resolve()
    target = Path(raw).expanduser()
    if not target.is_absolute():
        target = project_root / target
    target = target.resolve()
    try:
        stored = target.relative_to(project_root).as_posix()
    except ValueError as exc:
        raise SystemExit(
            f"Project instruction path must stay inside {project_root}: {target}"
        ) from exc
    if require_file and not target.is_file():
        raise SystemExit(f"Project instruction file does not exist: {target}")
    return target, stored


def analyze_project_instructions(
    state_path: Path,
    cwd_raw: str | None = None,
    fallback_filenames: list[str] | None = None,
) -> dict[str, Any]:
    """Inspect the project-local AGENTS chain for one working directory.

    This intentionally excludes global Codex instructions because they are not
    owned by the research project. The 32 KiB comparison is therefore
    conservative: global instructions may consume additional context.
    """

    project_root = project_root_for_state(state_path).resolve()
    cwd, descriptor = normalized_instruction_scope(
        state_path, cwd_raw, fallback_filenames
    )
    fallback_filenames = descriptor["fallback_filenames"]
    instruction_filenames = AGENTS_FILENAMES + tuple(fallback_filenames)
    if not cwd.is_dir():
        raise SystemExit(f"Instruction audit working directory does not exist: {cwd}")
    relative_cwd = cwd.relative_to(project_root)

    directories = [project_root]
    current = project_root
    for part in relative_cwd.parts:
        current = current / part
        directories.append(current)

    observed: list[dict[str, Any]] = []
    effective: list[dict[str, Any]] = []
    shadowed: list[dict[str, str]] = []
    ignored_empty: list[str] = []
    root_instruction: dict[str, Any] | None = None
    for directory in directories:
        existing = [
            directory / name
            for name in instruction_filenames
            if (directory / name).is_file()
        ]
        nonempty = [candidate for candidate in existing if candidate.stat().st_size > 0]
        selected = nonempty[0] if nonempty else None
        selected_stored = (
            selected.relative_to(project_root).as_posix() if selected is not None else None
        )
        for candidate in existing:
            stored = candidate.relative_to(project_root).as_posix()
            candidate_bytes = candidate.stat().st_size
            ignored_reason = "empty" if candidate_bytes == 0 else None
            entry = {
                "path": stored,
                "bytes": candidate_bytes,
                "sha256": sha256_file(candidate),
                "selected": candidate == selected,
                "shadowed_by": (
                    selected_stored
                    if candidate != selected and ignored_reason is None
                    else None
                ),
                "ignored_reason": ignored_reason,
            }
            observed.append(entry)
            if candidate == selected:
                effective.append(entry)
                if directory == project_root:
                    root_instruction = entry
            elif ignored_reason == "empty":
                ignored_empty.append(stored)
            else:
                shadowed.append({"path": stored, "shadowed_by": str(selected_stored)})

    chain_bytes = sum(int(item["bytes"]) for item in effective)
    issues: list[dict[str, str]] = []

    def add(code: str, severity: str, message: str) -> None:
        issues.append({"code": code, "severity": severity, "message": message})

    if root_instruction:
        root_bytes = int(root_instruction["bytes"])
        if root_bytes > ROOT_AGENTS_REVIEW_BYTES:
            add(
                "ROOT_AGENTS_REVIEW_REQUIRED",
                "P1",
                f"Root project instructions use {root_bytes} bytes; compact or route details before further growth",
            )
        elif root_bytes > ROOT_AGENTS_TARGET_BYTES:
            add(
                "ROOT_AGENTS_TARGET_EXCEEDED",
                "P2",
                f"Root project instructions use {root_bytes} bytes, above the {ROOT_AGENTS_TARGET_BYTES}-byte target",
            )
    if chain_bytes > CODEX_PROJECT_DOC_DEFAULT_BYTES:
        add(
            "PROJECT_INSTRUCTION_CHAIN_DEFAULT_LIMIT_EXCEEDED",
            "P0",
            f"The project-local effective chain alone uses {chain_bytes} bytes, above the default {CODEX_PROJECT_DOC_DEFAULT_BYTES}-byte Codex project-doc budget",
        )
    elif chain_bytes > EFFECTIVE_AGENTS_TARGET_BYTES:
        add(
            "PROJECT_INSTRUCTION_CHAIN_TARGET_EXCEEDED",
            "P1",
            f"The project-local effective chain uses {chain_bytes} bytes, above the {EFFECTIVE_AGENTS_TARGET_BYTES}-byte target",
        )

    status = "OK"
    if any(issue["severity"] == "P0" for issue in issues):
        status = "OVER_DEFAULT_LIMIT"
    elif issues:
        status = "REVIEW"
    elif not effective:
        status = "NO_PROJECT_INSTRUCTIONS"
    return {
        "audited_at": now_iso(),
        "scope_cwd": "." if str(relative_cwd) == "." else relative_cwd.as_posix(),
        "fallback_filenames": fallback_filenames,
        "project_local_only": True,
        "status": status,
        "effective_chain_bytes": chain_bytes,
        "effective_files": effective,
        "observed_files": observed,
        "shadowed_files": shadowed,
        "ignored_empty_files": ignored_empty,
        "issues": issues,
    }


def instruction_snapshot_signature(audit: dict[str, Any]) -> list[tuple[str, str, bool]]:
    return sorted(
        (
            str(item.get("path")),
            str(item.get("sha256")),
            bool(item.get("selected")),
        )
        for item in audit.get("observed_files", [])
    )


def instruction_scope_key(audit: dict[str, Any]) -> str:
    return json.dumps(
        {
            "cwd": str(audit.get("scope_cwd") or "."),
            "fallback": list(audit.get("fallback_filenames") or []),
        },
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )


def normalized_instruction_scope(
    state_path: Path,
    cwd_raw: str | None,
    fallback_filenames: list[str] | None,
) -> tuple[Path, dict[str, Any]]:
    project_root = project_root_for_state(state_path).resolve()
    fallbacks = list(fallback_filenames or [])
    if len({os.path.normcase(name) for name in fallbacks}) != len(fallbacks):
        raise SystemExit("Project instruction fallback filenames must be unique")
    standard_names = {os.path.normcase(name) for name in AGENTS_FILENAMES}
    for name in fallbacks:
        if (
            not name
            or Path(name).name != name
            or os.path.normcase(name) in standard_names
        ):
            raise SystemExit(f"Invalid project instruction fallback filename: {name!r}")
    cwd = Path(cwd_raw).expanduser() if cwd_raw else project_root
    if not cwd.is_absolute():
        cwd = project_root / cwd
    cwd = cwd.resolve()
    try:
        relative_cwd = cwd.relative_to(project_root)
    except ValueError as exc:
        raise SystemExit(
            f"Instruction audit working directory must stay inside {project_root}: {cwd}"
        ) from exc
    descriptor = {
        "scope_cwd": "." if str(relative_cwd) == "." else relative_cwd.as_posix(),
        "fallback_filenames": fallbacks,
    }
    return cwd, descriptor


def instruction_scope_target(audit: dict[str, Any]) -> str:
    return "instructions-scope:" + instruction_scope_key(audit)


def normalize_project_record(path: Path, raw: str) -> tuple[Path, str, str]:
    record = Path(raw).expanduser()
    if not record.is_absolute():
        record = project_root_for_state(path) / record
    record = record.resolve()
    if not record.is_file():
        raise SystemExit(f"Checkpoint record does not exist: {record}")
    state_path = path.resolve()
    protected_controller_paths = {
        state_path,
        state_path.with_name(state_path.name + ".lock"),
        state_path.with_name(state_path.name + ".tmp"),
    }
    if record in protected_controller_paths:
        raise SystemExit(
            "Checkpoint and assessment records cannot reuse the workflow state, "
            "lock, or temporary state path"
        )
    if record.name in AGENTS_FILENAMES:
        raise SystemExit(
            "Checkpoint and assessment records cannot be written into project "
            "AGENTS instructions"
        )
    project_root = project_root_for_state(path).resolve()
    try:
        stored = record.relative_to(project_root).as_posix()
    except ValueError as exc:
        raise SystemExit(
            f"Checkpoint and assessment records must stay inside {project_root}: {record}"
        ) from exc
    return record, stored, sha256_file(record)


def normalize_readonly_reference(path: Path, raw: str) -> tuple[Path, str, str]:
    reference = Path(raw).expanduser()
    if not reference.is_absolute():
        reference = project_root_for_state(path) / reference
    reference = reference.resolve()
    if not reference.is_file():
        raise SystemExit(f"Evidence reference does not exist: {reference}")
    project_root = project_root_for_state(path).resolve()
    try:
        stored = reference.relative_to(project_root).as_posix()
    except ValueError:
        stored = str(reference)
    return reference, stored, sha256_file(reference)


def evidence_reference(state_path: Path, raw: str, label: str) -> dict[str, str]:
    if not str(raw or "").strip():
        raise SystemExit(f"Science confirmation requires --{label.replace('_', '-')}")
    _, stored, digest = normalize_readonly_reference(state_path, raw)
    return {"path": stored, "sha256_at_confirmation": digest}


def normalized_frozen_key(raw: str) -> str:
    value = re.sub(r"[-\s]+", "_", str(raw).strip().lower())
    return re.sub(r"_+", "_", value).strip("_")


def resolved_frozen_key(state: dict[str, Any], raw: str) -> str:
    normalized = normalized_frozen_key(raw)
    if not normalized:
        raise SystemExit("A frozen field requires a non-empty --key")
    matches = [
        key
        for key in state.get("frozen_by_pi", {})
        if normalized_frozen_key(key) == normalized
    ]
    if len(matches) > 1:
        raise SystemExit(
            f"Frozen field {raw!r} is ambiguous because existing keys normalize to "
            f"the same identity: {matches}"
        )
    return matches[0] if matches else normalized


def append_checkpoint_receipt(
    record: Path,
    layer: str,
    checkpoint_id: str,
    payload: dict[str, Any],
    source: dict[str, str],
) -> None:
    receipt = (
        f"\n\n## Confirmed {layer} checkpoint `{checkpoint_id}`\n\n"
        f"- Confirmed at: {now_iso()}\n"
        f"- Decision outcome: `{source['outcome']}`\n"
        f"- User decision: {source['decision']}\n"
        "- Structured payload:\n\n"
        "```json\n"
        + json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True)
        + "\n```\n"
    )
    with record.open("a", encoding="utf-8", newline="") as handle:
        handle.write(receipt)


def append_paper_assessment_receipt(record: Path, payload: dict[str, Any]) -> None:
    public_payload = {
        key: value
        for key, value in payload.items()
        if key not in PRIVATE_PAPER_CONTROL_FIELDS
    }
    receipt = (
        "\n\n## Paper-decision report\n\n"
        f"- Recorded at: {now_iso()}\n"
        f"- Current task: {payload['current_task']}\n"
        f"- Dataset: {payload['dataset']}\n"
        "- Adopted datasets: "
        + ", ".join(
            f"{item['dataset']} ({item['role']})"
            for item in payload["adopted_datasets"]
        )
        + "\n"
        f"- Problem in current work: {payload['current_work_problem']}\n"
        f"- Active problem path: {' -> '.join(payload['problem_path'])}\n"
        f"- Problem ID: `{payload['problem_id']}`\n"
        f"- Method-cluster ID: `{payload['method_cluster_id']}`\n"
        f"- Innovation: {payload['innovation']}\n"
        f"- Core mechanism: {payload['core_mechanism']}\n"
        f"- Concrete method: {payload['specific_method']}\n"
        f"- Final results: {payload['final_results']}\n"
        f"- Primary comparison dataset: {payload['primary_comparison_dataset']}\n"
        "- Baseline roster: revision "
        f"{payload['baseline_roster_revision']} | payload "
        f"`{payload['baseline_roster_payload_sha256']}`\n"
        "- Per-dataset external-baseline comparisons:\n\n"
        "```json\n"
        + json.dumps(
            payload["dataset_baseline_matrix"],
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
        + "\n```\n\n"
        "- Strongest recent top-conference protocol-matched baseline: "
        f"{payload['recent_top_conference_baseline']}\n"
        f"- Baseline venue/year: {payload['baseline_venue_year']}\n"
        f"- Baseline search scope: {payload['baseline_search_scope']}\n"
        f"- Baseline source: {payload['baseline_source']}\n"
        f"- Protocol-match evidence: {payload['protocol_match_evidence']}\n"
        "- Evaluation anchor: revision "
        f"{payload['evaluation_anchor_revision']} | "
        f"direction `{payload['metric_direction']}`\n"
        f"- Primary metric: {payload['primary_metric']}\n"
        f"- Metric scale: `{payload['metric_scale']}`\n"
        f"- Evaluation-anchor evidence: {payload['evaluation_anchor_evidence']}\n"
        f"- Stability evidence: {payload['stability_evidence']}\n"
        f"- Baseline score: {payload['baseline_score']:.10g}\n"
        f"- Our score: {payload['our_score']:.10g}\n"
        "- Improvement (percentage points): "
        f"{payload['improvement_points']:.10g}\n"
        "- Required improvement (percentage points): "
        f"{payload['minimum_paper_gain_points']:.10g}\n"
        f"- Competitive-bar assessment: {payload['competitive_bar_assessment']}\n"
        f"- Novelty assessment: {payload['novelty_assessment']}\n"
        f"- Generalization assessment: {payload['generalization_assessment']}\n"
        "- Additional paper-ready-requirements assessment: "
        f"{payload['paper_ready_threshold_assessment']}\n"
        f"- Narrowest supported claim: {payload['narrowest_supported_claim']}\n"
        f"- Strongest matched comparison: {payload['strongest_matched_comparison']}\n"
        f"- Remaining objection: {payload['remaining_objection']}\n"
        f"- Necessary work: {payload['necessary_work']}\n"
        f"- Optional work: {payload['optional_work']}\n\n"
        "The paper decision remains with the PI; this report only establishes that "
        "the configured evidence floor is met.\n\n"
        "- Structured assessment:\n\n"
        "```json\n"
        + json.dumps(public_payload, ensure_ascii=False, indent=2, sort_keys=True)
        + "\n```\n"
    )
    with record.open("a", encoding="utf-8", newline="") as handle:
        handle.write(receipt)


def append_baseline_roster_receipt(
    record: Path, roster: dict[str, Any], reason: str
) -> None:
    receipt = (
        "\n\n## Dataset baseline roster receipt\n\n"
        f"- Recorded at: {roster['recorded_at']}\n"
        f"- Direction: `{roster['direction_id']}`\n"
        f"- Revision: `{roster['revision']}`\n"
        f"- Reason: {reason}\n"
        f"- Payload SHA-256: `{roster['payload_sha256']}`\n\n"
        "```json\n"
        + json.dumps(roster["rows"], ensure_ascii=False, indent=2, sort_keys=True)
        + "\n```\n"
    )
    with record.open("a", encoding="utf-8", newline="") as handle:
        handle.write(receipt)


def atomic_write_text(path: Path, text: str) -> None:
    temp = path.with_name(path.name + ".research-paper-workflow.tmp")
    temp.write_text(text, encoding="utf-8")
    os.replace(temp, path)


def managed_block(name: str, body: str) -> str:
    return (
        f"<!-- RPW:{name}:START -->\n"
        f"{body.rstrip()}\n"
        f"<!-- RPW:{name}:END -->"
    )


def replace_managed_section(
    text: str,
    name: str,
    body: str,
    legacy_heading: str,
) -> str:
    replacement = managed_block(name, body)
    start_marker = f"<!-- RPW:{name}:START -->"
    end_marker = f"<!-- RPW:{name}:END -->"
    if start_marker in text and end_marker in text:
        start = text.index(start_marker)
        end = text.index(end_marker, start) + len(end_marker)
        return text[:start] + replacement + text[end:]

    heading_at = text.find(legacy_heading)
    if heading_at < 0:
        separator = "" if text.endswith("\n\n") else "\n\n"
        return text + separator + replacement + "\n"
    next_heading = text.find("\n## ", heading_at + len(legacy_heading))
    end = len(text) if next_heading < 0 else next_heading + 1
    suffix = "" if end == len(text) else "\n"
    return text[:heading_at] + replacement + suffix + text[end:]


def replace_science_current_block(text: str, body: str) -> str:
    name = "SCIENCE_CURRENT"
    replacement = managed_block(name, body)
    start_marker = f"<!-- RPW:{name}:START -->"
    end_marker = f"<!-- RPW:{name}:END -->"
    if start_marker in text and end_marker in text:
        start = text.index(start_marker)
        end = text.index(end_marker, start) + len(end_marker)
        legacy_update = text.find("Last material update:", end)
        next_heading = text.find("\n## ", end)
        if legacy_update >= 0 and (next_heading < 0 or legacy_update < next_heading):
            legacy_update_end = text.find("\n", legacy_update)
            end = len(text) if legacy_update_end < 0 else legacy_update_end + 1
        return text[:start] + replacement + text[end:]

    start = text.find("L2 status:")
    end_anchor = "Last material update:"
    update_start = text.find(end_anchor, start) if start >= 0 else -1
    if start >= 0 and update_start >= 0:
        update_end = text.find("\n", update_start)
        end = len(text) if update_end < 0 else update_end + 1
        return text[:start] + replacement + "\n" + text[end:]
    return text.rstrip() + "\n\n" + replacement + "\n"


def l1_context_body(direction_id: str, payload: dict[str, Any]) -> str:
    standard = payload["evidence_standard"]
    dataset_inventory = ", ".join(
        f"{item['dataset']} ({item['role']})"
        for item in payload["adopted_datasets"]
    )
    return (
        f"Direction ID: `{direction_id}`  \n"
        f"L1 task and dataset: {payload['task_type']} | {payload['dataset']}  \n"
        f"Adopted dataset inventory: {dataset_inventory}  \n"
        "Unexposed-dataset search: "
        f"{payload['unexposed_dataset_search']}  \n"
        "L1 evidence standard: "
        f"competitive={standard['competitive_bar']} | "
        f"novelty={standard['novelty_sufficiency']} | "
        f"generalization={standard['generalization_requirement']} | "
        f"additional-paper-ready={standard['paper_ready_threshold']} | "
        "minimum gain over the strongest recent top-conference protocol-matched "
        f"baseline={standard['minimum_paper_gain_points']:.10g} percentage points  \n"
        f"L1 confirmation source: direction checkpoint `{direction_id}` in workflow state"
    )


def replace_l1_context_block(
    text: str, direction_id: str, payload: dict[str, Any]
) -> str:
    name = "L1_CONTEXT"
    replacement = managed_block(name, l1_context_body(direction_id, payload))
    start_marker = f"<!-- RPW:{name}:START -->"
    end_marker = f"<!-- RPW:{name}:END -->"
    if start_marker in text and end_marker in text:
        start = text.index(start_marker)
        end = text.index(end_marker, start) + len(end_marker)
        return text[:start] + replacement + text[end:]

    start = text.find("Direction ID:")
    science_marker = text.find("<!-- RPW:SCIENCE_CURRENT:START -->")
    legacy_science = text.find("L2 status:")
    end_candidates = [
        candidate
        for candidate in (science_marker, legacy_science)
        if candidate >= 0 and (start < 0 or candidate > start)
    ]
    if start >= 0 and end_candidates:
        end = min(end_candidates)
        return text[:start] + replacement + "\n" + text[end:]

    first_newline = text.find("\n")
    insert_at = len(text) if first_newline < 0 else first_newline + 1
    return text[:insert_at] + "\n" + replacement + "\n" + text[insert_at:]


def update_record_placeholders(
    record: Path,
    layer: str,
    checkpoint_id: str,
    payload: dict[str, Any],
    source: dict[str, str],
) -> None:
    text = record.read_text(encoding="utf-8")
    if layer == "compass":
        text = replace_managed_section(
            text,
            "COMPASS_CURRENT",
            "## Research compass\n\n"
            f"- Venue or submission window: {payload['venue_or_window']}\n"
            f"- Domain: {payload['domain']}\n"
            f"- Optional starting concept: {payload['starting_concept']}",
            "## Research compass",
        )
    elif layer == "direction":
        standard = payload["evidence_standard"]
        dataset_inventory = ", ".join(
            f"{item['dataset']} ({item['role']})"
            for item in payload["adopted_datasets"]
        )
        text = replace_managed_section(
            text,
            "DIRECTION_STANDARD_CURRENT",
            "## Project evidence standard\n\n"
            f"- Competitive bar: {standard['competitive_bar']}\n"
            f"- Novelty sufficiency: {standard['novelty_sufficiency']}\n"
            "- Generalization or second-dataset requirement: "
            f"{standard['generalization_requirement']}\n"
            "- Additional paper-ready requirements: "
            f"{standard['paper_ready_threshold']}\n"
            "- Minimum gain over the strongest recent top-conference protocol-matched "
            f"baseline: {standard['minimum_paper_gain_points']:.10g} percentage points",
            "## Project evidence standard",
        )
        text = replace_managed_section(
            text,
            "DIRECTION_DECISION_CURRENT",
            "## Current PI decision\n\n"
            f"- Checkpoint: `{checkpoint_id}`\n"
            f"- Task type: {payload['task_type']}\n"
            f"- Dataset: {payload['dataset']}\n"
            f"- Adopted dataset inventory: {dataset_inventory}\n"
            "- Unexposed-dataset search: "
            f"{payload['unexposed_dataset_search']}\n"
            f"- User decision: {source['decision']}",
            "## Current PI decision",
        )
    elif layer == "science":
        text = replace_science_current_block(
            text,
            "L2 status: `ACTIVE_PI_CONFIRMED`  \n"
            f"Active checkpoint: `{checkpoint_id}`  \n"
            f"Active problem path: {' -> '.join(payload['problem_path'])}  \n"
            f"Problem: {payload['problem']}  \n"
            f"Problem ID: `{payload['problem_id']}`  \n"
            f"Method-cluster ID: `{payload['method_cluster_id']}`  \n"
            f"Nearest-work gap: {payload['nearest_work_gap']}  \n"
            f"Paper-grade rationale: {payload['paper_grade_rationale']}  \n"
            f"Core mechanism: {payload['core_mechanism']}  \n"
            f"Falsifiable prediction: {payload['falsifiable_prediction']}  \n"
            "Why the relevant simpler alternative is insufficient: "
            f"{payload['simple_combination_counterfactual']}  \n"
            f"Contribution type: `{payload['contribution_type']}`  \n"
            f"Innovation claim: {payload['innovation_claim']}  \n"
            f"User decision: {source['decision']}  \n"
            f"Last material update: {now_iso()}",
        )
    atomic_write_text(record, text)


def resolve_stored_path(state_path: Path, raw: str | None) -> Path | None:
    if not raw:
        return None
    candidate = Path(raw)
    if candidate.is_absolute():
        return candidate
    return project_root_for_state(state_path) / candidate


def stored_path_is_project_local(state_path: Path, raw: str | None) -> bool:
    resolved = resolve_stored_path(state_path, raw)
    if resolved is None:
        return False
    try:
        resolved.resolve().relative_to(project_root_for_state(state_path).resolve())
    except ValueError:
        return False
    return True


def ensure_scaffold(state_path: Path, project: str) -> None:
    research_root = research_root_for_state(state_path)
    l2_root = research_root / "L2"
    l2_root.mkdir(parents=True, exist_ok=True)
    l1_path = research_root / "L1-directions.md"
    if not l1_path.exists():
        l1_path.write_text(
            "# Research direction portfolio\n\n"
            f"Project: {project}\n\n"
            "<!-- RPW:COMPASS_CURRENT:START -->\n"
            "## Research compass\n\n"
            "- Venue or submission window: UNSET\n"
            "- Domain: UNSET\n"
            "- Optional starting concept: UNSET\n"
            "<!-- RPW:COMPASS_CURRENT:END -->\n\n"
            "<!-- RPW:DIRECTION_STANDARD_CURRENT:START -->\n"
            "## Project evidence standard\n\n"
            "- Competitive bar: UNSET\n"
            "- Novelty sufficiency: UNSET\n"
            "- Generalization or second-dataset requirement: UNSET\n"
            "- Additional paper-ready requirements: UNSET\n"
            "- Minimum gain over the strongest recent top-conference protocol-matched baseline: 1 percentage point\n"
            "<!-- RPW:DIRECTION_STANDARD_CURRENT:END -->\n\n"
            "## Ranked directions\n\n"
            "| ID | status | task type | dataset | why meaningful | task-data fit | headroom | nearest-work risk | baseline feasibility | unexposed-data option | cost/time | next action |\n"
            "|---|---|---|---|---|---|---|---|---|---|---|---|\n\n"
            "<!-- RPW:DIRECTION_DECISION_CURRENT:START -->\n"
            "## Current PI decision\n\n"
            "UNSET\n"
            "<!-- RPW:DIRECTION_DECISION_CURRENT:END -->\n",
            encoding="utf-8",
        )


def ensure_l2_scaffold(state_path: Path, direction_id: str, payload: dict[str, Any]) -> Path:
    l2_path = research_root_for_state(state_path) / "L2" / f"{direction_id}.md"
    if not l2_path.exists():
        l2_path.write_text(
            f"# {direction_id}: problem, method and evidence\n\n"
            "<!-- RPW:L1_CONTEXT:START -->\n"
            f"{l1_context_body(direction_id, payload)}\n"
            "<!-- RPW:L1_CONTEXT:END -->\n"
            "<!-- RPW:SCIENCE_CURRENT:START -->\n"
            "Confirmed L2 selection: UNSET (exploration may proceed within L1).\n"
            f"Last material update: {now_iso()}\n"
            "<!-- RPW:SCIENCE_CURRENT:END -->\n\n"
            "## Working research\n\n"
            "Keep one evolving entry per meaningful mechanism: unresolved problem/leaf, "
            "nearest-work gap, suspected cause, intuition, prediction, necessary mathematics, "
            "relevant simpler alternative, evidence and next test. One problem node is valid.\n\n"
            "Distinguish working hypotheses, supported findings and PI-confirmed selections. "
            "Use research-update to maintain the note and progress view together. "
            "Do not make a separate ceiling table repeating the method entry.\n\n"
            "## Literature and comparison evidence\n\n"
            "Link primary sources and decision-relevant artifacts. Nearest-work novelty and "
            "experimental baseline roles are distinct. The generated baseline roster owns "
            "comparison numbers; internal variants are not external competitors.\n\n"
            "## Selected alternatives and decisions\n\n"
            "Keep only changes and conclusions needed to understand the current direction. "
            "Routine implementation and discarded tuning traces stay in project-native L3 tools.\n",
            encoding="utf-8",
        )
    else:
        text = l2_path.read_text(encoding="utf-8")
        updated = replace_l1_context_block(text, direction_id, payload)
        if updated != text:
            atomic_write_text(l2_path, updated)
    return l2_path


def active_questions(state: dict[str, Any]) -> list[dict[str, Any]]:
    return [q for q in state["macro_questions"] if q.get("status") == "PENDING_PI"]


def deferred_questions(state: dict[str, Any]) -> list[dict[str, Any]]:
    return [q for q in state["macro_questions"] if q.get("status") == "DEFERRED_PI"]


def refresh_pause(state: dict[str, Any]) -> None:
    count = len(active_questions(state))
    state["paused_for_pi"] = count >= MAX_MACRO_QUESTIONS
    if state["paused_for_pi"]:
        state["status"] = "PAUSED_FOR_PI"
    elif isinstance(state.get("manual_pause"), dict):
        state["status"] = "PAUSED_BY_PI"
    else:
        state["status"] = "ACTIVE"


def require_execution_active(state: dict[str, Any], action: str) -> None:
    refresh_pause(state)
    if state["paused_for_pi"]:
        raise SystemExit(
            f"Cannot {action}: five PI decisions are pending and the workflow is PAUSED_FOR_PI"
        )
    if isinstance(state.get("manual_pause"), dict):
        raise SystemExit(
            f"Cannot {action}: the PI manually paused execution; use resume after a direct PI instruction"
        )


def research_window_active(state: dict[str, Any]) -> bool:
    window = state.get("research_window") or {}
    return window.get("status") == "ACTIVE" and nonblank(window.get("id"))


def research_window_start_snapshot(state: dict[str, Any]) -> dict[str, Any]:
    roster = state.get("dataset_baseline_roster") or {}
    anchor = state.get("evaluation_anchor") or {}
    return {
        "phase": state.get("phase"),
        "checkpoints": {
            layer: {
                "id": (state.get("layer_checkpoints") or {}).get(layer, {}).get("id"),
                "status": (state.get("layer_checkpoints") or {}).get(layer, {}).get("status"),
            }
            for layer in CHECKPOINT_LAYERS
        },
        "baseline_roster_revision": roster.get("revision"),
        "baseline_roster_payload_sha256": roster.get("payload_sha256"),
        "evaluation_anchor_revision": anchor.get("revision"),
    }


def research_focus_scope(state: dict[str, Any]) -> dict[str, Any]:
    """Scientific context, independent of changing evidence and reporting receipts."""
    checkpoints = state.get("layer_checkpoints") or {}
    fields = {
        "compass": ("venue_or_window", "domain"),
        "direction": ("task_type", "dataset", "adopted_datasets", "evidence_standard"),
        "science": (
            "direction_id", "problem_path", "problem_id", "method_cluster_id",
            "problem", "nearest_work_gap", "core_mechanism", "falsifiable_prediction",
            "contribution_type", "innovation_claim",
        ),
    }
    scope = {}
    for layer, names in fields.items():
        checkpoint = checkpoints.get(layer) or {}
        payload = checkpoint.get("payload") or {}
        scope[layer] = {
            "id": checkpoint.get("id"),
            "status": checkpoint.get("status"),
            "selection": {name: payload.get(name) for name in names},
        }
    anchor = state.get("evaluation_anchor") or {}
    scope["anchor"] = {
        name: anchor.get(name) for name in (
            "direction_id", "problem_path", "problem_id", "method_cluster_id",
            "falsifiable_prediction", "primary_metric", "metric_scale", "metric_direction",
        )
    }
    return scope


def normalize_window_subject_id(value: Any) -> str:
    subject_id = str(value or "").strip()
    if not subject_id:
        raise SystemExit("A research-window card requires a non-empty subject ID")
    if len(subject_id) > 160:
        raise SystemExit("A research-window subject ID must be at most 160 characters")
    return subject_id


def upsert_research_window_card(
    state: dict[str, Any],
    *,
    layer: str,
    kind: str,
    subject_id: str,
    title: str,
    status: str,
    verified_observation: str,
    interpretation: str,
    external_baseline_gap: str,
    next_action: str,
    starting_result: str | None = None,
    best_result: str | None = None,
    latest_result: str | None = None,
    disposition_reason: str | None = None,
    problem_path: list[str] | None = None,
    focus: dict[str, str] | None = None,
    inherit_existing: bool = True,
) -> dict[str, Any] | None:
    """Upsert one macro L1/L2 card in the active, replace-on-start cache."""

    if not research_window_active(state):
        return None
    if layer not in WINDOW_CARD_KINDS_BY_LAYER or kind not in WINDOW_CARD_KINDS_BY_LAYER[layer]:
        raise SystemExit("Research-window cards support only L1/L2 scientific kinds; L3 is internal")
    if status not in WINDOW_CARD_STATUSES:
        raise SystemExit(
            "Research-window card status must be one of: "
            + ", ".join(sorted(WINDOW_CARD_STATUSES))
        )
    subject_id = normalize_window_subject_id(subject_id)
    required_values = {
        "title": title,
        "verified_observation": verified_observation,
        "interpretation": interpretation,
        "external_baseline_gap": external_baseline_gap,
        "next_action": next_action,
    }
    cleaned = {
        name: clean_text(value, f"research-window {name.replace('_', ' ')}")
        for name, value in required_values.items()
    }
    window = state["research_window"]
    key = (layer, kind, subject_id)
    existing = next(
        (
            card
            for card in window["cards"]
            if (card.get("layer"), card.get("kind"), card.get("subject_id")) == key
        ),
        None,
    )
    timestamp = now_iso()
    card = {
        "layer": layer,
        "kind": kind,
        "subject_id": subject_id,
        "title": cleaned["title"],
        "status": status,
        "verified_observation": cleaned["verified_observation"],
        "interpretation": cleaned["interpretation"],
        "external_baseline_gap": cleaned["external_baseline_gap"],
        "next_action": cleaned["next_action"],
        "first_recorded_at": (
            existing.get("first_recorded_at") if isinstance(existing, dict) else timestamp
        ),
        "updated_at": timestamp,
    }
    if problem_path is not None:
        if layer != "L2" or kind != "problem":
            raise SystemExit("--problem-path is valid only for an L2 problem card")
        card["problem_path"] = normalize_problem_path(
            problem_path,
            active_leaf=subject_id,
            label="research-window problem path",
        )
    elif inherit_existing and isinstance(existing, dict) and isinstance(existing.get("problem_path"), list):
        card["problem_path"] = list(existing["problem_path"])
    for name, value in (
        ("starting_result", starting_result),
        ("best_result", best_result),
        ("latest_result", latest_result),
        ("disposition_reason", disposition_reason),
    ):
        if nonblank(value):
            card[name] = str(value).strip()
        elif inherit_existing and isinstance(existing, dict) and nonblank(existing.get(name)):
            card[name] = str(existing.get(name)).strip()
    if existing is None:
        window["cards"].append(card)
    else:
        existing.clear()
        existing.update(card)
        card = existing
    window["revision"] = int(window.get("revision") or 0) + 1
    current = window.get("current_focus")
    if status in WINDOW_TERMINAL_STATUSES and isinstance(current, dict) and (
        current.get("layer"), current.get("kind"), current.get("subject_id")
    ) == key:
        window["current_focus"] = None
    carried = (window.get("start_snapshot") or {}).get("carried_focus")
    if status in WINDOW_TERMINAL_STATUSES and isinstance(carried, dict) and (
        carried.get("layer"), carried.get("kind"), carried.get("subject_id")
    ) == key:
        window["start_snapshot"].pop("carried_focus", None)
    if focus is not None:
        if status in WINDOW_TERMINAL_STATUSES:
            raise SystemExit("A closed or exhausted candidate cannot be the current focus")
        focus_values = {
            "hypothesis": clean_text(focus.get("hypothesis"), "current-focus hypothesis"),
            "current_action": clean_text(
                focus.get("current_action"), "current-focus current action"
            ),
            "latest_result": clean_text(
                focus.get("latest_result"), "current-focus latest result"
            ),
            "next_action": clean_text(focus.get("next_action"), "current-focus next action"),
        }
        window["current_focus"] = {
            "layer": layer,
            "kind": kind,
            "subject_id": subject_id,
            **focus_values,
            "updated_at": timestamp,
            "scope_snapshot": research_focus_scope(state),
        }
    return card


def baseline_gap_summary(row: dict[str, Any]) -> str:
    baseline = row.get("baseline_score")
    ours = row.get("our_score")
    if finite_number(baseline) and finite_number(ours):
        gain = float(ours) - float(baseline)
        unit = "points on 0-100 scale" if row.get("metric_scale") == "percentage" else "raw on 0-1 scale"
        return f"ours-baseline={gain:+.6g} {unit}; protocol={row.get('protocol_status')}"
    return (
        f"status={row.get('status')}; protocol={row.get('protocol_status')}; "
        "matched numeric gap not yet available"
    )


def external_reference_summary(state: dict[str, Any]) -> str:
    """The external opponent stays visible; a free-text trial is not a matched score."""
    if not baseline_roster_usable(state):
        return "External reference unresolved: establish the adopted datasets' source-checked baseline roster; internal gains are not an external win."
    rows = state["dataset_baseline_roster"]["rows"]
    targets = [
        f"{row['dataset']}: {row['baseline']} ({row['venue_year']}) = "
        f"{row['baseline_score'] if row['baseline_score'] is not None else 'score unresolved'} "
        f"[{row['metric']}, {row['metric_scale']}, {row['protocol_status']}]"
        for row in rows
    ]
    return "; ".join(targets) + ". Compare this candidate under the matching dataset/protocol; internal variant gains do not replace that comparison."


def read_research_entry(text: str, identity: str) -> tuple[dict[str, Any], str | None]:
    """Read the one durable record, not a previous window's disposable projection."""
    start_marker = f"<!-- RPW:RESEARCH_{identity}:START -->"
    end_marker = f"<!-- RPW:RESEARCH_{identity}:END -->"
    if start_marker not in text:
        return {}, None
    start = text.index(start_marker) + len(start_marker)
    end = text.find(end_marker, start)
    if end < 0:
        raise SystemExit("Incomplete research record: inspect/repair its managed block before updating")
    body = text[start:end].strip()
    match = re.search(r"^<!-- RPW:RESEARCH_DATA (.+) -->$", body, re.MULTILINE)
    if not match:
        return {}, body  # Keep pre-metadata notes, without inventing their scope.
    try:
        entry = json.loads(match.group(1))
    except json.JSONDecodeError as exc:
        raise SystemExit("Invalid research record metadata; repair the record before updating") from exc
    if not isinstance(entry, dict) or not isinstance(entry.get("scope_snapshot"), dict):
        raise SystemExit("Research record metadata is missing its scientific scope")
    return entry, None


def sync_baseline_roster_to_window(state: dict[str, Any], roster: dict[str, Any]) -> None:
    if not research_window_active(state):
        return
    for row in roster.get("rows") or []:
        dataset = str(row.get("dataset") or "UNSET")
        upsert_research_window_card(
            state,
            layer="L2",
            kind="baseline_comparison",
            subject_id=f"dataset:{dataset}",
            title=f"External comparison for {dataset}",
            status=str(row.get("status") or "IDENTIFIED"),
            verified_observation=(
                f"Comparator={row.get('baseline')}; venue/year={row.get('venue_year')}; "
                f"metric={row.get('metric')} ({row.get('metric_scale')}); "
                f"baseline={row.get('baseline_score')}; ours={row.get('our_score')}"
            ),
            interpretation=(
                "This is the current dataset-specific external comparison receipt; "
                "scientific comparability remains governed by the baseline roster."
            ),
            external_baseline_gap=baseline_gap_summary(row),
            next_action=(
                "Complete or recheck the protocol-matched comparison"
                if row.get("status") != "MATCHED"
                else "Use this row only with its verified protocol evidence"
            ),
            latest_result=(
                f"baseline={row.get('baseline_score')}; ours={row.get('our_score')}"
                if finite_number(row.get("baseline_score")) and finite_number(row.get("our_score"))
                else None
            ),
            inherit_existing=False,
        )


def sync_checkpoint_to_window(
    state: dict[str, Any], layer: str, checkpoint_id: str, payload: dict[str, Any]
) -> None:
    if not research_window_active(state):
        return
    if layer == "direction":
        adopted = payload.get("adopted_datasets") or []
        dataset_names = ", ".join(str(item.get("dataset")) for item in adopted) or str(
            payload.get("dataset")
        )
        upsert_research_window_card(
            state,
            layer="L1",
            kind="task_dataset",
            subject_id=checkpoint_id,
            title=f"{payload.get('task_type')} on {dataset_names}",
            status="SELECTED",
            verified_observation="The PI confirmed this L1 task-dataset direction.",
            interpretation=(
                f"Competitive bar={((payload.get('evidence_standard') or {}).get('competitive_bar'))}; "
                f"generalization={((payload.get('evidence_standard') or {}).get('generalization_requirement'))}."
            ),
            external_baseline_gap="See the dataset-indexed baseline roster; it may not yet be complete.",
            next_action="Map paper-grade nearest-work problems and source-check external baselines.",
            focus={
                "hypothesis": "The selected task-data direction contains a paper-grade unresolved problem.",
                "current_action": "Map nearest-work problems and dataset-specific external baselines.",
                "latest_result": "L1 direction confirmed; L2 evidence is not yet established.",
                "next_action": "Screen problem-linked method clusters inside the confirmed direction.",
            },
        )
    elif layer == "science":
        problem_id = str(payload.get("problem_id"))
        method_id = str(payload.get("method_cluster_id"))
        common_gap = str(payload.get("external_baseline_status"))
        upsert_research_window_card(
            state,
            layer="L2",
            kind="problem",
            subject_id=problem_id,
            title=str(payload.get("problem")),
            status="SELECTED",
            verified_observation=str(payload.get("nearest_work_gap")),
            interpretation=str(payload.get("paper_grade_rationale")),
            external_baseline_gap=common_gap,
            next_action="Complete evidence for the confirmed problem and its contribution boundary.",
            latest_result=str(payload.get("ceiling_summary")),
            problem_path=list(payload.get("problem_path") or []),
        )
        upsert_research_window_card(
            state,
            layer="L2",
            kind="method_cluster",
            subject_id=method_id,
            title=str(payload.get("core_mechanism")),
            status="SELECTED",
            verified_observation=str(payload.get("ceiling_summary")),
            interpretation=str(payload.get("innovation_claim")),
            external_baseline_gap=common_gap,
            next_action="Complete matched evidence against every adopted dataset baseline.",
            latest_result=str(payload.get("ceiling_summary")),
            focus={
                "hypothesis": str(payload.get("falsifiable_prediction")),
                "current_action": "Complete the confirmed mechanism's decision-relevant evidence.",
                "latest_result": str(payload.get("ceiling_summary")),
                "next_action": "Assess the confirmed story against the L1 evidence standard.",
            },
        )


def sync_scientific_switch_to_window(
    state: dict[str, Any], kind: str, text: str, to_id: str
) -> None:
    if not research_window_active(state):
        return
    card_kind = "problem" if kind == "problem_switch" else "method_cluster"
    window = state["research_window"]
    for owner, key in (
        (window, "current_focus"),
        (window.get("start_snapshot") or {}, "carried_focus"),
    ):
        focus = owner.get(key)
        if focus and (focus.get("kind"), focus.get("subject_id")) != (card_kind, to_id):
            owner[key] = None
    upsert_research_window_card(
        state,
        layer="L2",
        kind=card_kind,
        subject_id=to_id,
        title=f"New {card_kind.replace('_', ' ')} {to_id}",
        status="CURRENT",
        verified_observation=text,
        interpretation=(
            "The scientific branch changed. Record its hypothesis and representative "
            "evidence before the next scientific action."
        ),
        external_baseline_gap="Not yet recorded for this new branch.",
        next_action="Update this card with its macro hypothesis, evidence, and external comparison.",
    )


def start_research_window_state(state: dict[str, Any], instruction: Any) -> dict[str, Any]:
    require_execution_active(state, "start a research execution window")
    if state.get("phase") == "discussion":
        raise SystemExit(
            "Cannot start a research window in discussion; confirm the research compass first"
        )
    instruction_text = clean_text(instruction, "research-window instruction")
    previous = state.get("research_window") or empty_research_window()
    snapshot = research_window_start_snapshot(state)
    # A reporting boundary resets deltas, not our understanding of current work.
    # Carry context only across the same scientific scope; never invent history.
    previous_focus = previous.get("current_focus") or (previous.get("start_snapshot") or {}).get("carried_focus")
    if isinstance(previous_focus, dict):
        if previous_focus.get("scope_snapshot") == research_focus_scope(state):
            snapshot["carried_focus"] = previous_focus
    sequence = int(previous.get("sequence") or 0) + 1
    state["research_window"] = {
        "sequence": sequence,
        "id": f"W{sequence:03d}",
        "status": "ACTIVE",
        "started_at": now_iso(),
        "instruction": instruction_text,
        "start_snapshot": snapshot,
        "revision": 1,
        "cards": [],
        "current_focus": None,
    }
    return state["research_window"]


def next_id(items: list[dict[str, Any]], prefix: str) -> str:
    highest = 0
    for item in items:
        raw = str(item.get("id", ""))
        if raw.startswith(prefix) and raw[len(prefix) :].isdigit():
            highest = max(highest, int(raw[len(prefix) :]))
    return f"{prefix}{highest + 1:03d}"


def age_minutes(timestamp: str) -> float | None:
    try:
        created = datetime.fromisoformat(timestamp)
    except (TypeError, ValueError):
        return None
    if created.tzinfo is None:
        created = created.replace(tzinfo=timezone.utc)
    return max(0.0, (datetime.now(timezone.utc) - created).total_seconds() / 60.0)


def timestamp_at_or_after(candidate: Any, boundary: Any) -> bool:
    try:
        candidate_time = datetime.fromisoformat(str(candidate))
        boundary_time = datetime.fromisoformat(str(boundary))
    except (TypeError, ValueError):
        return False
    if candidate_time.tzinfo is None:
        candidate_time = candidate_time.replace(tzinfo=timezone.utc)
    if boundary_time.tzinfo is None:
        boundary_time = boundary_time.replace(tzinfo=timezone.utc)
    return candidate_time >= boundary_time


def answered_question_binding_usable(
    state: dict[str, Any],
    source: dict[str, Any],
    *,
    expected_layer: str | None,
    expected_target: str,
    expected_consumer: dict[str, Any],
    not_before: str | None = None,
    require_decision_text_match: bool = True,
) -> bool:
    if source.get("type") != "answered_question" or not source.get("question_id"):
        return False
    matches = [
        question
        for question in state.get("macro_questions", [])
        if question.get("id") == source.get("question_id")
    ]
    if len(matches) != 1:
        return False
    question = matches[0]
    if (
        question.get("status") != "ANSWERED"
        or question.get("decision_target") != expected_target
        or question.get("outcome") not in APPROVING_OUTCOMES
        or source.get("outcome") != question.get("outcome")
    ):
        return False
    if expected_layer is not None and question.get("layer") != expected_layer:
        return False
    if require_decision_text_match and source.get("decision") != question.get(
        "decision"
    ):
        return False
    consumed = question.get("consumed_by") or {}
    if any(consumed.get(key) != value for key, value in expected_consumer.items()):
        return False
    if not_before is not None and (
        not timestamp_at_or_after(question.get("created_at"), not_before)
        or not timestamp_at_or_after(question.get("answered_at"), not_before)
    ):
        return False
    return True


def checkpoint_complete(state: dict[str, Any], layer: str) -> bool:
    checkpoint = state["layer_checkpoints"].get(layer, {})
    if checkpoint.get("status") != "CONFIRMED_BY_PI":
        return False
    if not (
        checkpoint.get("id")
        and checkpoint.get("confirmed_at")
        and checkpoint.get("record_path")
        and checkpoint.get("record_sha256_at_confirmation")
    ):
        return False
    source = checkpoint.get("decision_source") or {}
    if (
        source.get("outcome") not in APPROVING_OUTCOMES
        or not nonblank(source.get("decision"))
    ):
        return False
    payload = checkpoint.get("payload")
    if not isinstance(payload, dict):
        return False
    required: dict[str, tuple[str, ...]] = {
        "compass": ("venue_or_window", "domain"),
        "direction": (
            "task_type",
            "dataset",
            "adopted_datasets",
            "unexposed_dataset_search",
            "evidence_standard",
        ),
        "science": (
            "direction_id",
            "problem_id",
            "method_cluster_id",
            "problem",
            "nearest_work_gap",
            "paper_grade_rationale",
            "core_mechanism",
            "falsifiable_prediction",
            "contribution_type",
            "innovation_claim",
            "external_baseline_status",
            "ceiling_summary",
        ),
        "paper": ("science_id", "headline_claim", "handoff_target"),
    }
    if any(
        not nonblank(payload.get(key))
        for key in required[layer]
        if key not in {"evidence_standard", "adopted_datasets"}
    ):
        return False
    if layer == "direction":
        if not adopted_datasets_complete(payload.get("adopted_datasets")):
            return False
        standard = payload.get("evidence_standard")
        if not isinstance(standard, dict):
            return False
        keys = (
            "competitive_bar",
            "novelty_sufficiency",
            "generalization_requirement",
            "paper_ready_threshold",
            "minimum_paper_gain_points",
        )
        if any(
            not nonblank(standard.get(key))
            for key in keys
            if key != "minimum_paper_gain_points"
        ):
            return False
        if not finite_number(standard.get("minimum_paper_gain_points")) or standard[
            "minimum_paper_gain_points"
        ] < MIN_PAPER_READY_GAIN_POINTS:
            return False
    if layer == "science":
        if not problem_path_complete(payload.get("problem_path"), payload.get("problem_id")):
            return False
        if not simple_combination_counterfactual_complete(
            payload.get("simple_combination_counterfactual")
        ) and not payload.get("legacy_method_counterfactual_unscoped"):
            return False
        if payload.get("contribution_type") not in PAPER_GRADE_CONTRIBUTION_TYPES:
            return False
        evidence_refs = payload.get("evidence_refs")
        if not isinstance(evidence_refs, dict):
            return False
        for key in (
            "problem_portfolio",
            "nearest_work",
            "external_baselines",
            "results",
        ):
            ref = evidence_refs.get(key)
            if (
                not isinstance(ref, dict)
                or not ref.get("path")
                or not ref.get("sha256_at_confirmation")
            ):
                return False
    return True


def checkpoint_usable(state_path: Path, state: dict[str, Any], layer: str) -> bool:
    if not checkpoint_complete(state, layer):
        return False
    record = resolve_stored_path(
        state_path, state["layer_checkpoints"][layer].get("record_path")
    )
    if not record or not record.is_file():
        return False
    if layer == "paper":
        expected = state["layer_checkpoints"][layer].get(
            "record_sha256_at_confirmation"
        )
        if not expected or sha256_file(record) != expected:
            return False
    if layer == "science":
        refs = state["layer_checkpoints"][layer]["payload"]["evidence_refs"]
        for name in (
            "problem_portfolio",
            "nearest_work",
            "external_baselines",
            "results",
        ):
            ref = refs[name]
            evidence_path = resolve_stored_path(state_path, ref.get("path"))
            if not evidence_path or not evidence_path.is_file():
                return False
    return True


def science_evidence_snapshot(
    state_path: Path, state: dict[str, Any], paper_record: Path | None = None
) -> dict[str, Any]:
    """Evidence versions, separate from PI authority over the scientific selection."""
    science = state["layer_checkpoints"]["science"]
    refs = (science.get("payload") or {}).get("evidence_refs") or {}
    paper_record = paper_record or resolve_stored_path(
        state_path, (state.get("paper_ready_assessment") or {}).get("path")
    )
    snapshot = {}
    for name, ref in refs.items():
        record = resolve_stored_path(state_path, ref.get("path"))
        snapshot[name] = {
            "path": ref.get("path"),
            "sha256": (
                "LOCKED_BY_PAPER_REPORT"
                if record and paper_record and record.resolve() == paper_record.resolve()
                else sha256_file(record) if record and record.is_file() else None
            ),
        }
    return snapshot


def seed_selection_risk_acceptance_usable(
    state: dict[str, Any], assessment: dict[str, Any]
) -> bool:
    if not assessment.get("favorable_seed_selection"):
        return True
    acceptance = state.get("seed_selection_risk_acceptance")
    if not isinstance(acceptance, dict) or not acceptance.get("accepted"):
        return False
    source = acceptance.get("decision_source") or {}
    if source.get("outcome") not in APPROVING_OUTCOMES:
        return False
    if (
        acceptance.get("science_id") != assessment.get("science_id")
        or acceptance.get("evaluation_anchor_revision")
        != assessment.get("evaluation_anchor_revision")
        or acceptance.get("assessment_payload_sha256")
        != paper_assessment_payload_sha256(assessment)
    ):
        return False
    if source.get("type") == "answered_question":
        expected = {
            "type": "seed_selection_risk",
            "science_id": assessment.get("science_id"),
            "evaluation_anchor_revision": assessment.get(
                "evaluation_anchor_revision"
            ),
        }
        expected_target = (
            f"paper:seed-selection-risk:{assessment.get('science_id')}:"
            f"anchor-{assessment.get('evaluation_anchor_revision')}"
        )
        if not answered_question_binding_usable(
            state,
            source,
            expected_layer="paper",
            expected_target=expected_target,
            expected_consumer=expected,
            require_decision_text_match=False,
        ):
            return False
    return True


def paper_ready_assessment_usable(state_path: Path, state: dict[str, Any]) -> bool:
    assessment = state.get("paper_ready_assessment")
    if not paper_assessment_complete(assessment):
        return False
    if assessment.get("science_evidence_at_gate") != science_evidence_snapshot(state_path, state):
        return False
    if assessment.get("payload_sha256_at_gate") != paper_assessment_payload_sha256(
        assessment
    ):
        return False
    direction = state["layer_checkpoints"].get("direction", {})
    science = state["layer_checkpoints"].get("science", {})
    direction_payload = direction.get("payload") or {}
    science_payload = science.get("payload") or {}
    anchor = state.get("evaluation_anchor") or {}
    roster = state.get("dataset_baseline_roster") or {}
    minimum_gain = (direction_payload.get("evidence_standard") or {}).get(
        "minimum_paper_gain_points"
    )
    if (
        assessment.get("direction_id") != direction.get("id")
        or assessment.get("science_id") != science.get("id")
        or assessment.get("current_task") != direction_payload.get("task_type")
        or assessment.get("dataset") != direction_payload.get("dataset")
        or assessment.get("adopted_datasets")
        != direction_payload.get("adopted_datasets")
        or assessment.get("current_work_problem") != science_payload.get("problem")
        or assessment.get("problem_path") != science_payload.get("problem_path")
        or assessment.get("problem_id") != science_payload.get("problem_id")
        or assessment.get("method_cluster_id")
        != science_payload.get("method_cluster_id")
        or assessment.get("innovation") != science_payload.get("innovation_claim")
        or assessment.get("core_mechanism") != science_payload.get("core_mechanism")
        or not evaluation_anchor_usable(state)
        or not science_matches_evaluation_anchor(state)
        or assessment.get("evaluation_anchor_revision") != anchor.get("revision")
        or assessment.get("primary_metric") != anchor.get("primary_metric")
        or assessment.get("metric_scale") != anchor.get("metric_scale")
        or assessment.get("metric_direction") != anchor.get("metric_direction")
        or not baseline_roster_usable(state, require_matched=True)
        or not baseline_roster_record_usable(state_path, state)
        or assessment.get("baseline_roster_revision") != roster.get("revision")
        or assessment.get("baseline_roster_payload_sha256")
        != roster.get("payload_sha256")
        or assessment.get("dataset_baseline_matrix") != roster.get("rows")
        or not finite_number(minimum_gain)
        or not math.isclose(
            assessment.get("minimum_paper_gain_points"), minimum_gain, abs_tol=1e-9
        )
    ):
        return False
    if not seed_selection_risk_acceptance_usable(state, assessment):
        return False
    record = resolve_stored_path(state_path, assessment.get("path"))
    if (
        not record
        or not record.is_file()
        or not stored_path_is_project_local(state_path, assessment.get("path"))
    ):
        return False
    expected = assessment.get("sha256_after_handoff") or assessment.get(
        "sha256_at_gate"
    )
    return bool(expected and sha256_file(record) == expected)


def required_layers_for_phase(phase: str) -> tuple[str, ...]:
    return {
        "discussion": (),
        "exploration": ("compass",),
        "confirmed_project": ("compass", "direction"),
        "paper_ready_pending_pi": ("compass", "direction", "science"),
        "paper_handoff_approved": ("compass", "direction", "science", "paper"),
    }.get(phase, ())


def audit_state(state_path: Path, state: dict[str, Any]) -> list[dict[str, str]]:
    issues: list[dict[str, str]] = []

    def add(code: str, severity: str, message: str) -> None:
        issues.append({"code": code, "severity": severity, "message": message})

    if not nonblank(state.get("project")):
        add("INVALID_PROJECT_NAME", "P1", "Project name must contain non-whitespace text")
    if state.get("phase") not in VALID_PHASES:
        add("INVALID_PHASE", "P0", f"Unknown phase: {state.get('phase')!r}")
        return issues
    for layer in required_layers_for_phase(state["phase"]):
        if not checkpoint_complete(state, layer):
            add(
                f"{layer.upper()}_CHECKPOINT_INCOMPLETE",
                "P0" if layer in {"direction", "science", "paper"} else "P1",
                f"Phase {state['phase']} requires a complete typed {layer} checkpoint",
            )
    anchor = state.get("evaluation_anchor")
    if anchor is not None and not evaluation_anchor_complete(anchor):
        add(
            "EVALUATION_ANCHOR_INCOMPLETE",
            "P0",
            "The evaluation anchor must contain a direction, ordered problem path, active leaf, method cluster, falsifiable prediction, primary metric, scale, directionality, revision, reason, and lock time",
        )
    elif anchor is not None and anchor.get("legacy_derived"):
        add(
            "EVALUATION_ANCHOR_LEGACY_RELOCK_REQUIRED",
            "P0",
            "A migrated pre-v10 paper assessment cannot prove that its metric was locked before broad tuning; return to confirmed_project and set the evaluation anchor again",
        )
    elif anchor is not None and not evaluation_anchor_usable(state):
        add(
            "EVALUATION_ANCHOR_DIRECTION_MISMATCH",
            "P0",
            "The evaluation anchor is not tied to the active confirmed L1 direction",
        )
    roster = state.get("dataset_baseline_roster")
    if roster is not None and not baseline_roster_usable(state):
        add(
            "DATASET_BASELINE_ROSTER_INVALID",
            "P0",
            "The external-baseline roster is incomplete, changed, or does not exactly cover the adopted datasets",
        )
    elif roster is not None and not baseline_roster_record_usable(state_path, state):
        add(
            "DATASET_BASELINE_ROSTER_RECORD_CHANGED",
            "P0",
            "The durable external-baseline roster record is missing, outside the project, or lacks its recording receipt",
        )
    if state["phase"] in {"paper_ready_pending_pi", "paper_handoff_approved"}:
        if not evaluation_anchor_usable(state):
            add(
                "EVALUATION_ANCHOR_REQUIRED",
                "P0",
                "Paper-ready phases require a usable pre-tuning evaluation anchor",
            )
        assessment = state.get("paper_ready_assessment")
        if not isinstance(assessment, dict) or not assessment.get("path"):
            add(
                "PAPER_READY_ASSESSMENT_MISSING",
                "P0",
                "Paper-ready phase requires a recorded assessment artifact",
            )
        elif not paper_assessment_complete(assessment):
            add(
                "PAPER_READY_ASSESSMENT_INCOMPLETE",
                "P0",
                "Paper-ready assessment must include the decision report and meet the numeric gain floor",
            )
        else:
            if not seed_selection_risk_acceptance_usable(state, assessment):
                add(
                    "FAVORABLE_SEED_RISK_UNAPPROVED",
                    "P0",
                    "A favorable-seed paper result requires a scoped PI risk acceptance",
                )
            assessment_path = resolve_stored_path(state_path, assessment.get("path"))
            if not assessment_path or not assessment_path.is_file():
                add(
                    "PAPER_READY_ASSESSMENT_RECORD_MISSING",
                    "P0",
                    "Paper-ready assessment record is unavailable",
                )
            if not stored_path_is_project_local(state_path, assessment.get("path")):
                add(
                    "PAPER_READY_ASSESSMENT_OUTSIDE_PROJECT",
                    "P0",
                    "Paper-ready assessment must be a project-local durable record",
                )
    for layer in CHECKPOINT_LAYERS:
        checkpoint = state["layer_checkpoints"].get(layer, {})
        checkpoint_id = checkpoint.get("id")
        if checkpoint_id is not None and not CHECKPOINT_ID_PATTERN.fullmatch(
            str(checkpoint_id)
        ):
            add(
                "INVALID_CHECKPOINT_ID",
                "P0",
                f"Checkpoint {layer!r} has an unsafe or invalid ID: {checkpoint_id!r}",
            )
        if str(checkpoint.get("status") or "").startswith(
            "LEGACY_CONFIRMED_NEEDS_"
        ):
            add(
                f"LEGACY_{layer.upper()}_NEEDS_RECONFIRMATION",
                "P0" if layer in {"direction", "science"} else "P1",
                f"Legacy {layer} approval lacks the structured controls required by schema v13",
            )
        record = resolve_stored_path(state_path, checkpoint.get("record_path"))
        if checkpoint.get("status") == "CONFIRMED_BY_PI" and (
            record is None or not record.is_file()
        ):
            add(
                f"{layer.upper()}_RECORD_MISSING",
                "P0",
                f"Confirmed {layer} checkpoint has no available durable record",
            )
        if checkpoint.get("status") == "CONFIRMED_BY_PI" and not stored_path_is_project_local(
            state_path, checkpoint.get("record_path")
        ):
            add(
                f"{layer.upper()}_RECORD_OUTSIDE_PROJECT",
                "P0",
                f"Confirmed {layer} checkpoint record must stay inside the project",
            )
        if checkpoint.get("status") == "CONFIRMED_BY_PI" and not checkpoint_complete(
            state, layer
        ):
            add(
                f"{layer.upper()}_CONFIRMED_PAYLOAD_INCOMPLETE",
                "P0",
                f"Confirmed {layer} checkpoint lacks required schema-v13 control fields",
            )
        if (
            layer == "paper"
            and checkpoint.get("status") == "CONFIRMED_BY_PI"
            and record is not None
            and record.is_file()
            and checkpoint.get("record_sha256_at_confirmation")
            and sha256_file(record)
            != checkpoint.get("record_sha256_at_confirmation")
        ):
            add(
                "PAPER_CHECKPOINT_RECORD_CHANGED",
                "P0",
                "The approved paper-handoff record changed after confirmation",
            )
        source = checkpoint.get("decision_source") or {}
        if layer == "paper" and checkpoint.get("status") == "CONFIRMED_BY_PI":
            current_assessment = state.get("paper_ready_assessment") or {}
            if (
                source.get("paper_assessment_payload_sha256")
                != current_assessment.get("payload_sha256_at_gate")
                or source.get("paper_assessment_recorded_at")
                != current_assessment.get("recorded_at")
            ):
                add(
                    "PAPER_DECISION_ASSESSMENT_NOT_BOUND",
                    "P0",
                    "The paper decision is not bound to the current paper-decision report receipt",
                )
        if checkpoint.get("status") == "CONFIRMED_BY_PI" and source.get(
            "type"
        ) == "answered_question":
            expected = {
                "type": "checkpoint",
                "layer": layer,
                "id": checkpoint.get("id"),
            }
            if not answered_question_binding_usable(
                state,
                source,
                expected_layer=layer,
                expected_target=f"{layer}:{checkpoint.get('id')}",
                expected_consumer=expected,
                not_before=(
                    (state.get("paper_ready_assessment") or {}).get("recorded_at")
                    if layer == "paper"
                    else None
                ),
            ):
                add(
                    f"{layer.upper()}_DECISION_RECEIPT_NOT_BOUND",
                    "P0",
                    f"Confirmed {layer} checkpoint is not bound to a single scoped PI decision",
                )
    direction = state["layer_checkpoints"].get("direction", {})
    science = state["layer_checkpoints"].get("science", {})
    paper = state["layer_checkpoints"].get("paper", {})
    if science.get("status") == "CONFIRMED_BY_PI":
        science_payload = science.get("payload") or {}
        if not problem_path_complete(
            science_payload.get("problem_path"), science_payload.get("problem_id")
        ):
            add(
                "SCIENCE_PROBLEM_PATH_INVALID",
                "P0",
                "Confirmed L2 science requires an ordered problem path ending at the active problem ID",
            )
        if science_payload.get(
            "legacy_method_counterfactual_unscoped"
        ) or not simple_combination_counterfactual_complete(
            science_payload.get("simple_combination_counterfactual")
        ):
            add(
                "SCIENCE_SIMPLE_COMBINATION_AUDIT_REQUIRED",
                (
                    "P0"
                    if state.get("phase")
                    in {"paper_ready_pending_pi", "paper_handoff_approved"}
                    else "P1"
                ),
                "The migrated L2 method still needs an agent-owned audit explaining why an ordinary combination cannot solve the active leaf",
            )
        if (
            state.get("phase")
            in {"paper_ready_pending_pi", "paper_handoff_approved"}
            and evaluation_anchor_usable(state)
            and not science_matches_evaluation_anchor(state)
        ):
            add(
                "SCIENCE_EVALUATION_ANCHOR_SCOPE_MISMATCH",
                "P0",
                "The current experimental anchor targets a different problem path, leaf, method cluster, or falsifiable prediction than the confirmed L2 story",
            )
        if not baseline_roster_usable(state) or not baseline_roster_record_usable(
            state_path, state
        ):
            add(
                "SCIENCE_BASELINE_ROSTER_REQUIRED",
                "P0",
                "Confirmed L2 science requires one structured external-baseline roster row per adopted dataset",
            )
        if (science.get("payload") or {}).get("direction_id") != direction.get("id"):
            add(
                "SCIENCE_DIRECTION_LINK_MISMATCH",
                "P0",
                "Confirmed science checkpoint does not reference the active L1 direction",
            )
        raw_refs = (science.get("payload") or {}).get("evidence_refs")
        refs = raw_refs if isinstance(raw_refs, dict) else {}
        for name, ref in refs.items():
            if not isinstance(ref, dict):
                add(
                    "SCIENCE_EVIDENCE_RECORD_INVALID",
                    "P0",
                    f"Science evidence record {name!r} is not a structured reference",
                )
                continue
            evidence_path = resolve_stored_path(state_path, ref.get("path"))
            if not evidence_path or not evidence_path.is_file():
                add(
                    "SCIENCE_EVIDENCE_RECORD_MISSING",
                    "P0",
                    f"Science evidence record {name!r} is unavailable",
                )
    if paper.get("status") == "CONFIRMED_BY_PI" and (
        (paper.get("payload") or {}).get("science_id") != science.get("id")
    ):
        add(
            "PAPER_SCIENCE_LINK_MISMATCH",
            "P0",
            "Confirmed paper checkpoint does not reference the active L2 story",
        )
    assessment = state.get("paper_ready_assessment") or {}
    direction_payload = direction.get("payload") or {}
    science_payload = science.get("payload") or {}
    assessment_anchor = state.get("evaluation_anchor") or {}
    assessment_roster = state.get("dataset_baseline_roster") or {}
    direction_minimum = (direction_payload.get("evidence_standard") or {}).get(
        "minimum_paper_gain_points"
    )
    assessment_minimum = assessment.get("minimum_paper_gain_points")
    minimum_mismatch = not (
        finite_number(direction_minimum)
        and finite_number(assessment_minimum)
        and math.isclose(direction_minimum, assessment_minimum, abs_tol=1e-9)
    )
    if assessment and (
        assessment.get("direction_id") != direction.get("id")
        or assessment.get("science_id") != science.get("id")
        or assessment.get("current_task") != direction_payload.get("task_type")
        or assessment.get("dataset") != direction_payload.get("dataset")
        or assessment.get("adopted_datasets")
        != direction_payload.get("adopted_datasets")
        or assessment.get("current_work_problem") != science_payload.get("problem")
        or assessment.get("problem_path") != science_payload.get("problem_path")
        or assessment.get("problem_id") != science_payload.get("problem_id")
        or assessment.get("method_cluster_id")
        != science_payload.get("method_cluster_id")
        or assessment.get("innovation") != science_payload.get("innovation_claim")
        or assessment.get("core_mechanism") != science_payload.get("core_mechanism")
        or assessment.get("evaluation_anchor_revision")
        != assessment_anchor.get("revision")
        or assessment.get("primary_metric") != assessment_anchor.get("primary_metric")
        or assessment.get("metric_scale") != assessment_anchor.get("metric_scale")
        or assessment.get("metric_direction")
        != assessment_anchor.get("metric_direction")
        or assessment.get("baseline_roster_revision")
        != assessment_roster.get("revision")
        or assessment.get("baseline_roster_payload_sha256")
        != assessment_roster.get("payload_sha256")
        or assessment.get("dataset_baseline_matrix")
        != assessment_roster.get("rows")
        or minimum_mismatch
    ):
        add(
            "PAPER_ASSESSMENT_LINK_MISMATCH",
            "P0",
            "Paper-ready assessment content is not tied to the active L1/L2 checkpoints and gain floor",
        )
    active_job_ids = {
        job.get("id")
        for job in state.get("jobs", [])
        if job.get("status") in ACTIVE_JOB_STATUSES
    }
    artifact_job_ids = set(
        ((state.get("monitoring") or {}).get("artifact_fingerprints_by_job") or {})
    )
    stale_artifact_jobs = sorted(artifact_job_ids - active_job_ids)
    if stale_artifact_jobs:
        add(
            "STALE_MONITOR_ARTIFACT_ACK",
            "P1",
            "Artifact acknowledgements reference inactive jobs: "
            + ", ".join(stale_artifact_jobs),
        )
    if assessment:
        if assessment.get("science_evidence_at_gate") != science_evidence_snapshot(state_path, state):
            add(
                "PAPER_EVIDENCE_REVIEW_REQUIRED", "P1",
                "Evidence changed or has no gate snapshot; rebuild the paper report from current evidence. L2 selection remains approved.",
            )
        assessment_path = resolve_stored_path(state_path, assessment.get("path"))
        expected_payload_sha = assessment.get("payload_sha256_at_gate")
        if not expected_payload_sha:
            add(
                "PAPER_READY_ASSESSMENT_PAYLOAD_HASH_MISSING",
                "P0",
                "Paper-ready assessment lacks its structured-payload hash",
            )
        elif expected_payload_sha != paper_assessment_payload_sha256(assessment):
            add(
                "PAPER_READY_ASSESSMENT_PAYLOAD_CHANGED",
                "P0",
                "Paper-ready structured assessment changed after the gate",
            )
        expected_assessment_sha = assessment.get(
            "sha256_after_handoff"
        ) or assessment.get("sha256_at_gate")
        if not expected_assessment_sha:
            add(
                "PAPER_READY_ASSESSMENT_HASH_MISSING",
                "P0",
                "Paper-ready assessment lacks a recorded content hash",
            )
        elif assessment_path is not None and assessment_path.is_file() and (
            sha256_file(assessment_path) != expected_assessment_sha
        ):
            add(
                "PAPER_READY_ASSESSMENT_CHANGED",
                "P0",
                "Paper-ready assessment changed after the gate; reassess it before seeking or using PI approval",
            )
    normalized_frozen: dict[str, str] = {}
    for key, entry in state.get("frozen_by_pi", {}).items():
        normalized_key = normalized_frozen_key(key)
        if not normalized_key:
            add(
                "INVALID_FROZEN_FIELD_KEY",
                "P0",
                "A frozen field has an empty key",
            )
            continue
        previous_key = normalized_frozen.get(normalized_key)
        if previous_key is not None:
            add(
                "DUPLICATE_FROZEN_FIELD_IDENTITY",
                "P0",
                f"Frozen fields {previous_key!r} and {key!r} normalize to the same identity",
            )
        else:
            normalized_frozen[normalized_key] = key
        if normalized_frozen_key(key) in RESERVED_FROZEN_KEYS:
            add(
                "RESERVED_FIELD_DUPLICATED_IN_FROZEN_BY_PI",
                "P0",
                f"Core scientific field {key!r} must live only in compass/L1/L2 state",
            )
        if not isinstance(entry, dict) or not str(entry.get("value") or "").strip():
            add(
                "FROZEN_FIELD_VALUE_INVALID",
                "P0",
                f"Frozen field {key!r} has no non-empty value",
            )
            continue
        source = entry.get("decision_source") or {}
        if source.get("outcome") not in APPROVING_OUTCOMES or not source.get(
            "decision"
        ):
            add(
                "FROZEN_FIELD_DECISION_INVALID",
                "P0",
                f"Frozen field {key!r} lacks an approving PI decision receipt",
            )
        elif source.get("type") == "answered_question" and not any(
            answered_question_binding_usable(
                state,
                source,
                expected_layer=None,
                expected_target=target,
                expected_consumer={
                    "type": "frozen_field",
                    "key": key,
                    "action": "freeze",
                },
            )
            for target in {
                f"frozen:{normalized_frozen_key(key)}",
                f"frozen:{key}",
            }
        ):
            add(
                "FROZEN_FIELD_DECISION_NOT_BOUND",
                "P0",
                f"Frozen field {key!r} is not bound to its scoped PI decision",
            )
    maintenance = state.get("instruction_maintenance") or {}
    for update in maintenance.get("recent_updates", []):
        kind = update.get("kind")
        if kind not in INSTRUCTION_CHANGE_KINDS:
            add(
                "INVALID_INSTRUCTION_UPDATE_KIND",
                "P1",
                f"Instruction update has invalid kind {kind!r}",
            )
            continue
        if not update.get("path") or (
            not update.get("after_absent") and not update.get("after_sha256")
        ):
            add(
                "INSTRUCTION_UPDATE_RECEIPT_INCOMPLETE",
                "P1",
                "Instruction update receipt lacks its path or resulting hash",
            )
        if (
            kind == "compaction"
            and not update.get("canonical_sources")
            and not update.get("legacy_source_unverified")
        ):
            add(
                "INSTRUCTION_COMPACTION_SOURCE_MISSING",
                "P1",
                f"Instruction compaction for {update.get('path')!r} has no canonical surviving source",
            )
        for source in update.get("canonical_sources") or []:
            source_path = resolve_stored_path(state_path, source.get("path"))
            if not source_path or not source_path.is_file():
                add(
                    "INSTRUCTION_COMPACTION_SOURCE_UNAVAILABLE",
                    "P1",
                    f"Canonical source {source.get('path')!r} for instruction compaction is unavailable",
                )
        if kind == "semantic":
            source = update.get("decision_source") or {}
            if source.get("outcome") not in APPROVING_OUTCOMES:
                add(
                    "SEMANTIC_INSTRUCTION_UPDATE_UNAPPROVED",
                    "P0",
                    f"Semantic instruction update for {update.get('path')!r} lacks PI approval",
                )
            if source.get("type") == "answered_question":
                expected = {
                    "type": "instruction_update",
                    "path": update.get("path"),
                    "after_sha256": update.get("after_sha256"),
                }
                if not answered_question_binding_usable(
                    state,
                    source,
                    expected_layer="instructions",
                    expected_target=f"instructions:{update.get('path')}",
                    expected_consumer=expected,
                ):
                    add(
                        "INSTRUCTION_DECISION_RECEIPT_NOT_BOUND",
                        "P0",
                        f"Semantic instruction update for {update.get('path')!r} is not bound to one scoped PI decision",
                    )
    for removal in maintenance.get("recent_scope_removals", []):
        if not removal.get("scope_key") or not removal.get("scope_cwd"):
            add(
                "INSTRUCTION_SCOPE_REMOVAL_RECEIPT_INCOMPLETE",
                "P1",
                "Instruction-scope removal receipt lacks its scope identity",
            )
        source = removal.get("decision_source") or {}
        if removal.get("scope_existed_at_removal"):
            if source.get("outcome") not in APPROVING_OUTCOMES:
                add(
                    "INSTRUCTION_SCOPE_REMOVAL_UNAPPROVED",
                    "P0",
                    f"Removal of existing instruction scope {removal.get('scope_cwd')!r} lacks PI approval",
                )
            if source.get("type") == "answered_question":
                expected = {
                    "type": "instruction_scope_remove",
                    "scope_key": removal.get("scope_key"),
                }
                if not answered_question_binding_usable(
                    state,
                    source,
                    expected_layer="instructions",
                    expected_target=(
                        "instructions-scope:" + str(removal.get("scope_key") or "")
                    ),
                    expected_consumer=expected,
                ):
                    add(
                        "INSTRUCTION_SCOPE_DECISION_RECEIPT_NOT_BOUND",
                        "P0",
                        f"Removal of instruction scope {removal.get('scope_cwd')!r} is not bound to one scoped PI decision",
                    )
    for scope_key, last_instruction_audit in maintenance.get(
        "audits_by_scope", {}
    ).items():
        if not isinstance(last_instruction_audit, dict):
            add(
                "PROJECT_INSTRUCTION_AUDIT_INVALID",
                "P1",
                f"Instruction audit entry {scope_key!r} is not structured",
            )
            continue
        try:
            current_instruction_audit = analyze_project_instructions(
                state_path,
                last_instruction_audit.get("scope_cwd"),
                last_instruction_audit.get("fallback_filenames"),
            )
        except SystemExit as exc:
            add("PROJECT_INSTRUCTION_AUDIT_SCOPE_INVALID", "P1", str(exc))
        else:
            if instruction_snapshot_signature(
                current_instruction_audit
            ) != instruction_snapshot_signature(last_instruction_audit):
                add(
                    "PROJECT_INSTRUCTIONS_CHANGED_SINCE_AUDIT",
                    "P1",
                    "Project AGENTS instructions changed in scope "
                    f"{last_instruction_audit.get('scope_cwd')!r}; record the update before resetting any snapshot",
                )
    revisions = state.get("decision_target_revisions", {})
    for question in state.get("macro_questions", []):
        target = str(question.get("decision_target") or "").strip()
        if not target:
            continue
        revision = int(question.get("target_revision") or 0)
        latest = int(revisions.get(target, 0))
        if revision < latest and not question.get("consumed_by") and not question.get(
            "superseded_by"
        ):
            add(
                "STALE_PI_DECISION_NOT_SUPERSEDED",
                "P0",
                f"PI question {question.get('id')} is older than the current decision for {target!r} but remains usable",
            )
    active_targets: set[str] = set()
    for question in active_questions(state) + deferred_questions(state):
        target = str(question.get("decision_target") or "").strip()
        if not target:
            add(
                "UNSCOPED_PI_QUESTION",
                "P1",
                f"PI question {question.get('id')} has no stable decision target",
            )
            continue
        if target in active_targets:
            add(
                "DUPLICATE_PI_DECISION_TARGET",
                "P1",
                f"Multiple open PI questions use target {target!r}",
            )
        active_targets.add(target)
        if question.get("status") == "DEFERRED_PI" and not question.get(
            "revisit_condition"
        ):
            add(
                "DEFERRED_QUESTION_WITHOUT_REVISIT_CONDITION",
                "P1",
                f"Deferred PI question {question.get('id')} lacks a revisit condition",
            )
    l1_path = research_root_for_state(state_path) / "L1-directions.md"
    if state["phase"] != "discussion" and not l1_path.is_file():
        add("L1_FILE_MISSING", "P0", f"Missing durable L1 file: {l1_path}")
    seen_jobs: set[str] = set()
    for job in state.get("jobs", []):
        job_id = str(job.get("id", "")).strip()
        if not job_id or job_id in seen_jobs:
            add("INVALID_JOB_ID", "P1", "Job IDs must be non-empty and unique")
        seen_jobs.add(job_id)
        if job.get("status") not in JOB_STATUSES:
            add("INVALID_JOB_STATUS", "P1", f"Invalid job status for {job_id}")
        if job.get("status") in ACTIVE_JOB_STATUSES and not (
            nonblank(job.get("command")) or nonblank(job.get("session"))
        ):
            add(
                "ACTIVE_JOB_NOT_RESUMABLE",
                "P1",
                f"Active job {job_id} has neither a command nor a session identifier",
            )
        if (
            state.get("phase") == "discussion"
            and job.get("status") in ACTIVE_JOB_STATUSES
        ):
            add(
                "ACTIVE_JOB_IN_DISCUSSION",
                "P1",
                f"Active job {job_id} is registered before the research compass is confirmed",
            )
        if job.get("status") in ACTIVE_JOB_STATUSES and not str(
            job.get("next_poll") or ""
        ).strip():
            add(
                "ACTIVE_JOB_NEXT_CHECK_MISSING",
                "P1",
                f"Active job {job_id} has no next meaningful check time",
            )
        if job.get("status") in ACTIVE_JOB_STATUSES and not str(
            job.get("next_action") or ""
        ).strip():
            add(
                "ACTIVE_JOB_NEXT_ACTION_MISSING",
                "P1",
                f"Active job {job_id} has no resumable next action",
            )
    manual_pause = state.get("manual_pause")
    if isinstance(manual_pause, dict) and not nonblank(manual_pause.get("decision")):
        add(
            "MANUAL_PAUSE_DECISION_INVALID",
            "P0",
            "Manual pause lacks the PI's direct instruction",
        )
    monitoring = state.get("monitoring")
    if not isinstance(monitoring, dict):
        add(
            "MONITORING_STATE_INVALID",
            "P1",
            "Monitoring acknowledgement state is invalid",
        )
    else:
        acknowledged = monitoring.get("last_acknowledged_wakeup_fingerprint")
        if acknowledged is not None and not re.fullmatch(
            r"[0-9a-f]{64}", str(acknowledged)
        ):
            add(
                "MONITOR_ACK_FINGERPRINT_INVALID",
                "P1",
                "Stored monitor acknowledgement fingerprint is invalid",
            )
    return issues


def instruction_maintenance_summary(state: dict[str, Any]) -> dict[str, Any]:
    """Return operator-useful maintenance state without dumping every snapshot."""

    maintenance = state.get("instruction_maintenance") or {}
    scopes = []
    for audit in maintenance.get("audits_by_scope", {}).values():
        if not isinstance(audit, dict):
            continue
        scopes.append(
            {
                "scope_cwd": audit.get("scope_cwd"),
                "fallback_filenames": audit.get("fallback_filenames") or [],
                "status": audit.get("status"),
                "effective_chain_bytes": audit.get("effective_chain_bytes"),
                "effective_paths": [
                    item.get("path") for item in audit.get("effective_files", [])
                ],
                "issue_codes": [
                    issue.get("code") for issue in audit.get("issues", [])
                ],
                "removal_target": instruction_scope_target(audit),
                "audited_at": audit.get("audited_at"),
            }
        )
    scopes.sort(
        key=lambda item: (
            str(item.get("scope_cwd") or "."),
            tuple(item.get("fallback_filenames") or []),
        )
    )
    recent_updates = maintenance.get("recent_updates", [])
    recent_removals = maintenance.get("recent_scope_removals", [])
    return {
        "policy": maintenance.get("policy"),
        "audit_scope_count": len(maintenance.get("audits_by_scope", {})),
        "audit_scopes": scopes,
        "recent_update_count": len(recent_updates),
        "recent_updates": recent_updates[-5:],
        "compacted_update_count": maintenance.get("compacted_update_count", 0),
        "recent_scope_removal_count": len(recent_removals),
        "recent_scope_removals": recent_removals[-5:],
        "compacted_scope_removal_count": maintenance.get(
            "compacted_scope_removal_count", 0
        ),
    }


def state_summary(state_path: Path, state: dict[str, Any]) -> dict[str, Any]:
    pending = []
    ordered_questions = sorted(
        active_questions(state),
        key=lambda q: (
            PRIORITY_ORDER.get(str(q.get("priority", "medium")), 1),
            str(q.get("created_at", "")),
        ),
    )
    for question in ordered_questions:
        age = age_minutes(question.get("created_at", ""))
        pending.append(
            {
                "id": question["id"],
                "priority": question.get("priority", "medium"),
                "layer": question.get("layer", "other"),
                "decision_target": question.get("decision_target"),
                "text": question["text"],
                "reason": question.get("reason", ""),
                "recommendation": question.get("recommendation", ""),
                "continue_plan": question.get("continue_plan", ""),
                "age_minutes": None if age is None else round(age, 1),
                "over_20_minutes": None if age is None else age >= 20.0,
            }
        )
    active_jobs = [
        job for job in state.get("jobs", []) if job.get("status") in ACTIVE_JOB_STATUSES
    ]
    deferred = [
        {
            "id": question.get("id"),
            "priority": question.get("priority", "medium"),
            "layer": question.get("layer", "other"),
            "decision_target": question.get("decision_target"),
            "text": question.get("text"),
            "revisit_condition": question.get("revisit_condition"),
            "deferred_at": question.get("deferred_at"),
        }
        for question in sorted(
            deferred_questions(state),
            key=lambda q: (
                PRIORITY_ORDER.get(str(q.get("priority", "medium")), 1),
                str(q.get("deferred_at", "")),
            ),
        )
    ]
    unused_approvals = [
        {
            "id": question.get("id"),
            "decision_target": question.get("decision_target"),
            "decision": question.get("decision"),
            "outcome": question.get("outcome"),
        }
        for question in state["macro_questions"]
        if question.get("status") == "ANSWERED"
        and question.get("outcome") in APPROVING_OUTCOMES
        and not question.get("consumed_by")
        and not question.get("superseded_by")
    ]
    issues = audit_state(state_path, state)
    return {
        "schema_version": state["schema_version"],
        "project": state["project"],
        "phase": state["phase"],
        "status": state["status"],
        "paused_for_pi": state["paused_for_pi"],
        "manual_pause": state.get("manual_pause"),
        "last_manual_pause_event": state.get("last_manual_pause_event"),
        "monitoring": state.get("monitoring"),
        "research_window": state.get("research_window"),
        "pending_macro_count": len(pending),
        "pending_macro_questions": pending,
        "deferred_pi_count": len(deferred),
        "deferred_pi_questions": deferred,
        "unused_approvals": unused_approvals,
        "layer_checkpoints": state["layer_checkpoints"],
        "evaluation_anchor": state.get("evaluation_anchor"),
        "evaluation_anchor_history_count": len(
            state.get("evaluation_anchor_history", [])
        ),
        "seed_selection_risk_acceptance": state.get(
            "seed_selection_risk_acceptance"
        ),
        "dataset_baseline_roster": state.get("dataset_baseline_roster"),
        "dataset_baseline_roster_history_count": len(
            state.get("dataset_baseline_roster_history", [])
        ),
        "invalidated_paper_assessment_count": int(
            state.get("invalidated_paper_assessment_count", 0)
        )
        + len(state.get("invalidated_paper_assessments", [])),
        "recent_invalidated_paper_assessments": state.get(
            "invalidated_paper_assessments", []
        )[-5:],
        "missing_required_checkpoints": [
            layer
            for layer in required_layers_for_phase(state["phase"])
            if not checkpoint_complete(state, layer)
        ],
        "incomplete_checkpoints": [
            layer for layer in CHECKPOINT_LAYERS if not checkpoint_complete(state, layer)
        ],
        "unusable_required_checkpoints": [
            layer
            for layer in required_layers_for_phase(state["phase"])
            if not checkpoint_usable(state_path, state, layer)
        ],
        "paper_ready_assessment_usable": (
            paper_ready_assessment_usable(state_path, state)
            if state.get("paper_ready_assessment")
            else None
        ),
        "frozen_by_pi": state["frozen_by_pi"],
        "frozen_history_count": len(state["frozen_history"]),
        "notification_count": len(state["notifications"]),
        "recent_notifications": state["notifications"][-5:],
        "notification_compacted_count": state.get("notification_compacted_count", 0),
        "instruction_maintenance": instruction_maintenance_summary(state),
        "active_jobs": active_jobs,
        "control_issues": issues,
        "updated_at": state["updated_at"],
    }


def window_status_summary(state_path: Path, state: dict[str, Any]) -> dict[str, Any]:
    """Return the macro-only user supervision view for the current run window."""

    window = state.get("research_window") or empty_research_window()
    active = research_window_active(state)
    direction = (state.get("layer_checkpoints") or {}).get("direction") or {}
    science = (state.get("layer_checkpoints") or {}).get("science") or {}
    direction_payload = direction.get("payload") or {}
    science_payload = science.get("payload") or {}
    roster = state.get("dataset_baseline_roster") or {}
    anchor = state.get("evaluation_anchor") or {}
    macro_notifications = [
        item
        for item in state.get("notifications", [])
        if (
            active
            and isinstance(item, dict)
            and item.get("kind") in WINDOW_MACRO_NOTIFICATION_KINDS
            and timestamp_at_or_after(item.get("created_at"), window.get("started_at"))
        )
    ][-5:]
    pending_questions = [
        {
            "id": item.get("id"),
            "layer": item.get("layer"),
            "decision_target": item.get("decision_target"),
            "text": item.get("text"),
            "recommendation": item.get("recommendation"),
        }
        for item in active_questions(state)
    ]
    deferred = [
        {
            "id": item.get("id"),
            "layer": item.get("layer"),
            "decision_target": item.get("decision_target"),
            "text": item.get("text"),
            "revisit_condition": item.get("revisit_condition"),
        }
        for item in deferred_questions(state)
    ]
    cards = window.get("cards") or []
    # Refresh generated references on read, even when no roster change happened
    # in this reporting window. Do not relabel old narrative as a verified win.
    cards = [
        {**card, "external_baseline_gap": external_reference_summary(state)}
        if card.get("research_record") and card.get("layer") == "L2" else card
        for card in cards
    ]
    focus = window.get("current_focus")
    carried = (window.get("start_snapshot") or {}).get("carried_focus")
    scope = research_focus_scope(state)
    if focus is not None and focus.get("scope_snapshot") != scope:
        focus = None
    if focus is None and carried and carried.get("scope_snapshot") == scope:
        focus = {**carried, "context_origin": "carried_forward_not_new_progress"}
    return {
        "schema_version": state.get("schema_version"),
        "project": state.get("project"),
        "phase": state.get("phase"),
        "status": state.get("status"),
        "window_availability": "ACTIVE" if active else "NOT_RECORDED",
        "missing_window_notice": (
            None
            if active
            else (
                "No trustworthy since-last-run window exists. Report only the current "
                "verified L1/L2 state; do not reconstruct activity from L3 jobs or logs."
            )
        ),
        "research_window": {
            "id": window.get("id"),
            "started_at": window.get("started_at"),
            "instruction": window.get("instruction"),
            "revision": window.get("revision"),
            "start_snapshot": window.get("start_snapshot"),
            "l1_cards": [card for card in cards if card.get("layer") == "L1"],
            "l2_cards": [card for card in cards if card.get("layer") == "L2"],
            "current_focus": focus,
        },
        "current_l1": {
            "id": direction.get("id"),
            "status": direction.get("status"),
            "task_type": direction_payload.get("task_type"),
            "dataset": direction_payload.get("dataset"),
            "adopted_datasets": direction_payload.get("adopted_datasets"),
            "evidence_standard": direction_payload.get("evidence_standard"),
        },
        "current_l2": {
            "id": science.get("id"),
            "status": science.get("status"),
            "problem_path": science_payload.get("problem_path"),
            "problem_id": science_payload.get("problem_id"),
            "problem": science_payload.get("problem"),
            "method_cluster_id": science_payload.get("method_cluster_id"),
            "core_mechanism": science_payload.get("core_mechanism"),
            "falsifiable_prediction": science_payload.get("falsifiable_prediction"),
            "innovation_claim": science_payload.get("innovation_claim"),
            "simple_combination_counterfactual": science_payload.get(
                "simple_combination_counterfactual"
            ),
            "ceiling_summary": science_payload.get("ceiling_summary"),
        },
        "evaluation_anchor": {
            "revision": anchor.get("revision"),
            "problem_path": anchor.get("problem_path"),
            "problem_id": anchor.get("problem_id"),
            "method_cluster_id": anchor.get("method_cluster_id"),
            "falsifiable_prediction": anchor.get("falsifiable_prediction"),
            "primary_metric": anchor.get("primary_metric"),
            "metric_scale": anchor.get("metric_scale"),
            "metric_direction": anchor.get("metric_direction"),
        },
        "current_external_baselines": [
            {
                "dataset": row.get("dataset"),
                "role": row.get("role"),
                "baseline": row.get("baseline"),
                "venue_year": row.get("venue_year"),
                "source": row.get("source"),
                "search_scope": row.get("search_scope"),
                "metric": row.get("metric"),
                "metric_scale": row.get("metric_scale"),
                "baseline_score": row.get("baseline_score"),
                "our_score": row.get("our_score"),
                "status": row.get("status"),
                "protocol_status": row.get("protocol_status"),
                "gap": baseline_gap_summary(row),
            }
            for row in roster.get("rows") or []
        ],
        "macro_notifications": macro_notifications,
        "pending_pi_questions": pending_questions,
        "deferred_pi_questions": deferred,
        "updated_at": state.get("updated_at"),
    }


def compact_state_summary(state_path: Path, state: dict[str, Any]) -> dict[str, Any]:
    pending = active_questions(state)
    pending_ages = [
        age
        for age in (age_minutes(question.get("created_at", "")) for question in pending)
        if age is not None
    ]
    any_pending_over_20_minutes = any(age >= 20.0 for age in pending_ages)
    issues = audit_state(state_path, state)
    checkpoint_status = {
        layer: {
            "id": state["layer_checkpoints"][layer].get("id"),
            "status": state["layer_checkpoints"][layer].get("status"),
        }
        for layer in CHECKPOINT_LAYERS
    }
    active_jobs = [
        {
            "id": job.get("id"),
            "status": job.get("status"),
            "session": job.get("session"),
            "next_poll": job.get("next_poll"),
            "next_action": job.get("next_action"),
            "updated_at": job.get("updated_at"),
        }
        for job in state.get("jobs", [])
        if job.get("status") in ACTIVE_JOB_STATUSES
    ]
    issue_codes = [issue["code"] for issue in issues]
    recent_instruction_updates = (
        (state.get("instruction_maintenance") or {}).get("recent_updates") or []
    )
    latest_notification_raw = next(
        (
            item
            for item in reversed(state.get("notifications", []))
            if isinstance(item, dict)
            and item.get("kind")
            in {"problem_switch", "problem_path_change", "method_cluster_switch"}
        ),
        None,
    )
    latest_notification = (
        {
            "id": latest_notification_raw.get("id"),
            "kind": latest_notification_raw.get("kind"),
            "transition": latest_notification_raw.get("transition"),
        }
        if isinstance(latest_notification_raw, dict)
        else None
    )
    wakeup_signal = {
        "phase": state["phase"],
        "status": state["status"],
        "research_window": {
            "id": (state.get("research_window") or {}).get("id"),
            "revision": (state.get("research_window") or {}).get("revision"),
        },
        "checkpoint_payloads": {
            layer: {
                "id": state["layer_checkpoints"][layer].get("id"),
                "status": state["layer_checkpoints"][layer].get("status"),
                "payload": state["layer_checkpoints"][layer].get("payload"),
            }
            for layer in CHECKPOINT_LAYERS
        },
        "evaluation_anchor": state.get("evaluation_anchor"),
        "dataset_baseline_roster_payload_sha256": (
            (state.get("dataset_baseline_roster") or {}).get("payload_sha256")
        ),
        "paper_assessment_payload_sha256": (
            (state.get("paper_ready_assessment") or {}).get(
                "payload_sha256_at_gate"
            )
        ),
        "open_questions": [
            {
                "id": question.get("id"),
                "status": question.get("status"),
                "target": question.get("decision_target"),
                "target_revision": question.get("target_revision"),
                "response_count": len(question.get("responses") or []),
            }
            for question in active_questions(state) + deferred_questions(state)
        ],
        "any_pending_over_20_minutes": any_pending_over_20_minutes,
        "active_jobs": [
            {
                "id": job.get("id"),
                "status": job.get("status"),
                "session": job.get("session"),
                "next_action": job.get("next_action"),
            }
            for job in state.get("jobs", [])
            if job.get("status") in ACTIVE_JOB_STATUSES
        ],
        "frozen_by_pi": state.get("frozen_by_pi"),
        "latest_instruction_update": (
            recent_instruction_updates[-1] if recent_instruction_updates else None
        ),
        "latest_scientific_switch": latest_notification,
        "control_issue_codes": issue_codes,
    }
    wakeup_fingerprint = canonical_payload_sha256(wakeup_signal)
    monitoring = state.get("monitoring") or {}
    last_acknowledged = monitoring.get("last_acknowledged_wakeup_fingerprint")
    active_job_ids = {job["id"] for job in active_jobs if nonblank(job.get("id"))}
    saved_artifacts = monitoring.get("artifact_fingerprints_by_job") or {}
    active_artifacts = {
        job_id: fingerprint
        for job_id, fingerprint in saved_artifacts.items()
        if job_id in active_job_ids
    }
    return {
        "schema_version": state["schema_version"],
        "project": state["project"],
        "phase": state["phase"],
        "status": state["status"],
        "paused_for_pi": state["paused_for_pi"],
        "manually_paused": isinstance(state.get("manual_pause"), dict),
        "state_sha256": sha256_file(state_path),
        "wakeup_fingerprint": wakeup_fingerprint,
        "wakeup_changed_since_ack": wakeup_fingerprint != last_acknowledged,
        "last_acknowledged_wakeup_fingerprint": last_acknowledged,
        "acknowledged_artifact_fingerprints": active_artifacts,
        "legacy_unscoped_artifact_fingerprint": monitoring.get(
            "legacy_unscoped_artifact_fingerprint"
        ),
        "monitor_acknowledged_at": monitoring.get("acknowledged_at"),
        "latest_scientific_switch": latest_notification,
        "updated_at": state["updated_at"],
        "pending_macro_count": len(pending),
        "pending_macro_ids": [question.get("id") for question in pending],
        "any_pending_over_20_minutes": any_pending_over_20_minutes,
        "deferred_pi_count": len(deferred_questions(state)),
        "checkpoint_status": checkpoint_status,
        "research_window_id": (state.get("research_window") or {}).get("id"),
        "research_window_revision": (state.get("research_window") or {}).get(
            "revision"
        ),
        "evaluation_anchor_revision": (
            (state.get("evaluation_anchor") or {}).get("revision")
        ),
        "baseline_roster_revision": (
            (state.get("dataset_baseline_roster") or {}).get("revision")
        ),
        "baseline_roster_all_matched": baseline_roster_usable(
            state, require_matched=True
        ),
        "paper_ready_assessment_present": bool(state.get("paper_ready_assessment")),
        "active_jobs": active_jobs,
        "control_issue_codes": issue_codes,
    }


def cmd_init(args: argparse.Namespace) -> None:
    path = Path(args.state)
    if path.exists():
        raise SystemExit(f"Refusing to overwrite existing state: {path}")
    if args.phase not in {"discussion", "exploration"}:
        raise SystemExit("A new workflow may start only in discussion or exploration")
    if args.phase == "discussion" and any(
        value is not None
        for value in (
            args.venue_or_window,
            args.domain,
            args.starting_concept,
            args.pi_decision,
            args.pi_outcome,
        )
    ):
        raise SystemExit(
            "Compass and PI-decision arguments require --phase exploration; "
            "otherwise omit them and confirm the compass later"
        )
    if args.phase == "exploration" and not (
        nonblank(args.venue_or_window)
        and nonblank(args.domain)
        and nonblank(args.pi_decision)
        and args.pi_outcome in APPROVING_OUTCOMES
    ):
        raise SystemExit(
            "Starting in exploration requires --venue-or-window, --domain, "
            "--pi-decision, and --pi-outcome approve|select"
        )
    project = clean_text(args.project, "--project")
    state = initial_state(project)
    ensure_scaffold(path, project)
    initial_audit = analyze_project_instructions(path)
    state["instruction_maintenance"]["audits_by_scope"][
        instruction_scope_key(initial_audit)
    ] = initial_audit
    if args.phase == "exploration":
        venue_or_window = clean_text(args.venue_or_window, "--venue-or-window")
        domain = clean_text(args.domain, "--domain")
        starting_concept = (
            clean_text(args.starting_concept, "--starting-concept")
            if args.starting_concept is not None
            else "UNSET"
        )
        pi_decision = clean_text(args.pi_decision, "--pi-decision")
        l1 = research_root_for_state(path) / "L1-directions.md"
        record, stored, _ = normalize_project_record(path, str(l1))
        payload = {
            "venue_or_window": venue_or_window,
            "domain": domain,
            "starting_concept": starting_concept,
        }
        source = {
            "type": "direct_pi_instruction",
            "decision": pi_decision,
            "outcome": args.pi_outcome,
        }
        update_record_placeholders(record, "compass", "C001", payload, source)
        append_checkpoint_receipt(record, "compass", "C001", payload, source)
        digest = sha256_file(record)
        state["layer_checkpoints"]["compass"] = {
            "status": "CONFIRMED_BY_PI",
            "id": "C001",
            "summary": f"venue_or_window={venue_or_window}; domain={domain}",
            "payload": payload,
            "confirmed_at": now_iso(),
            "decision_source": source,
            "record_path": stored,
            "record_sha256_at_confirmation": digest,
        }
        state["phase"] = "exploration"
        start_research_window_state(state, pi_decision)
    save_state(path, state)
    print(json.dumps(state_summary(path, state), ensure_ascii=False, indent=2))


def cmd_status(args: argparse.Namespace) -> None:
    path = Path(args.state)
    state = load_state(path)
    if args.window:
        summary = window_status_summary(path, state)
    elif args.compact:
        summary = compact_state_summary(path, state)
    else:
        summary = state_summary(path, state)
    print(json.dumps(summary, ensure_ascii=False, indent=2))


def cmd_window_start(args: argparse.Namespace) -> None:
    path = Path(args.state)
    state = load_state(path)
    start_research_window_state(state, args.instruction)
    save_state(path, state)
    print(json.dumps(window_status_summary(path, state), ensure_ascii=False, indent=2))


def cmd_window_note(args: argparse.Namespace) -> None:
    path = Path(args.state)
    state = load_state(path)
    require_execution_active(state, "record active research progress")
    if not research_window_active(state):
        raise SystemExit(
            "No active research window; use window-start after an explicit PI run instruction"
        )
    record = None
    durable = args.command == "research-update"
    incoming_latest = args.latest_result
    prior = {}
    legacy_body = None
    scope = research_focus_scope(state)
    key = (args.layer, args.kind, args.subject_id)
    current = state["research_window"].get("current_focus") or (
        state["research_window"].get("start_snapshot") or {}
    ).get("carried_focus")
    current_matches = bool(
        current and tuple(current.get(name) for name in ("layer", "kind", "subject_id")) == key
        and current.get("scope_snapshot") == scope
    )
    if durable:
        if args.kind == "baseline_comparison":
            raise SystemExit("Use baseline-roster for comparison updates; do not maintain a second numeric source")
        if args.notification is not None and not args.notify_kind:
            raise SystemExit("--notification requires --notify-kind")
        if args.notification is not None:
            args.notification = clean_text(args.notification, "--notification")
        if args.layer == "L2" and not checkpoint_usable(path, state, "direction"):
            raise SystemExit("L2 research updates require confirmed L1; discuss/scout first")
        if state.get("phase") == "paper_handoff_approved":
            raise SystemExit("Writing is approved; revoke the handoff before restarting research")
        direction = state["layer_checkpoints"]["direction"] or {}
        science = state["layer_checkpoints"]["science"] or {}
        direction_id = direction.get("id")
        active_record = direction.get("record_path") if args.layer == "L1" else (
            science.get("record_path")
            if science.get("status") == "CONFIRMED_BY_PI"
            and (science.get("payload") or {}).get("direction_id") == direction_id
            else None
        )
        default_record = (
            research_root_for_state(path) / "L1-directions.md" if args.layer == "L1"
            else research_root_for_state(path) / "L2" / f"{direction_id}.md"
        )
        record, _, _ = normalize_project_record(path, args.record or active_record or str(default_record))
        if record.suffix.lower() not in {".md", ".markdown"}:
            raise SystemExit("A research update requires an existing Markdown research record")
        if args.status == "SELECTED":
            selected = state["layer_checkpoints"]["direction" if args.layer == "L1" else "science"]
            selected_id = selected.get("id") if args.layer == "L1" else (selected.get("payload") or {}).get(
                "problem_id" if args.kind == "problem" else "method_cluster_id"
            )
            if selected.get("status") != "CONFIRMED_BY_PI" or selected_id != args.subject_id:
                raise SystemExit("SELECTED must refer to an actual PI-confirmed choice; use an exploratory status")
        if args.notify_kind in {"problem_switch", "method_cluster_switch"}:
            if not args.from_id or args.from_id == args.subject_id:
                raise SystemExit("A switch needs a distinct --from-id; --subject-id is the new identity")
            expected_kind = "problem" if args.notify_kind == "problem_switch" else "method_cluster"
            if args.layer != "L2" or args.kind != expected_kind:
                raise SystemExit("Switch kind must match the L2 research subject")
        elif args.from_id:
            raise SystemExit("--from-id is only valid for a problem or method switch")
        identity = canonical_payload_sha256(list(key))[:16]
        text = record.read_text(encoding="utf-8")
        stored_entry, legacy_body = read_research_entry(text, identity)
        if stored_entry.get("scope_snapshot") == scope:
            prior = {name: stored_entry[name] for name in RESEARCH_OPTIONAL_FIELDS if name in stored_entry}
        # A legacy current-window card has an independently scoped current focus.
        # Retain its optional fields only when that scope is actually known.
        elif not stored_entry and current_matches:
            old_card = next((item for item in state["research_window"]["cards"] if (
                item.get("layer"), item.get("kind"), item.get("subject_id")
            ) == key), {})
            prior = {name: old_card[name] for name in RESEARCH_OPTIONAL_FIELDS if name in old_card}
            prior.update({name: current[name] for name in ("hypothesis", "current_action")})
        for name in args.clear_field or []:
            if name != "comparison_note" and getattr(args, name, None) is not None:
                raise SystemExit(f"Cannot both set and clear {name}")
            if name == "comparison_note" and args.external_baseline_gap is not None:
                raise SystemExit("Cannot both set and clear comparison_note")
            prior.pop(name, None)
        for name in RESEARCH_OPTIONAL_FIELDS:
            if name == "comparison_note":
                if args.external_baseline_gap is not None:
                    prior[name] = clean_text(args.external_baseline_gap, "comparison note")
            elif getattr(args, name, None) is not None:
                prior[name] = getattr(args, name)
        for name in RESEARCH_OPTIONAL_FIELDS:
            if name not in {"hypothesis", "current_action", "comparison_note"}:
                setattr(args, name, prior.get(name))
    elif args.record or args.notify_kind or args.notification or args.from_id or args.clear_field:
        raise SystemExit("Durable record/notification options require research-update, not legacy window-note")
    focus = None
    if args.set_current:
        focus = {
            "hypothesis": args.hypothesis or prior.get("hypothesis"),
            "current_action": args.current_action or prior.get("current_action"),
            "latest_result": args.focus_latest_result or incoming_latest or args.verified_observation,
            "next_action": args.next_action,
        }
    elif any(
        value is not None
        for value in (args.hypothesis, args.current_action, args.focus_latest_result)
    ):
        raise SystemExit(
            "--hypothesis, --current-action, and --focus-latest-result require --set-current"
        )
    elif durable and current_matches and args.status not in WINDOW_TERMINAL_STATUSES:
        if prior.get("hypothesis") and prior.get("current_action"):
            focus = {
                "hypothesis": prior["hypothesis"], "current_action": prior["current_action"],
                "latest_result": incoming_latest or args.verified_observation,
                "next_action": args.next_action,
            }
        else:
            state["research_window"]["current_focus"] = None
            (state["research_window"].get("start_snapshot") or {}).pop("carried_focus", None)
    card = upsert_research_window_card(
        state,
        layer=args.layer,
        kind=args.kind,
        subject_id=args.subject_id,
        title=args.title,
        status=args.status,
        verified_observation=args.verified_observation,
        interpretation=args.interpretation,
        external_baseline_gap=(
            external_reference_summary(state) if durable and args.layer == "L2"
            else args.external_baseline_gap or "See the dataset baseline roster; comparison not yet recorded here."
        ),
        next_action=args.next_action,
        starting_result=args.starting_result,
        best_result=args.best_result,
        latest_result=args.latest_result,
        disposition_reason=args.disposition_reason,
        problem_path=args.problem_path,
        focus=focus,
        inherit_existing=not durable,
    )
    if durable:
        # One input yields a durable note, reporting projection and notification.
        # It never confirms a PI selection or changes a verified comparison score.
        if args.notify_kind:
            transition = (
                {"from_id": args.from_id, "to_id": args.subject_id}
                if args.notify_kind in {"problem_switch", "method_cluster_switch"} else {}
            )
            saved_card, saved_focus = dict(card), state["research_window"].get("current_focus")
            append_notification(state, args.notification or args.interpretation, args.notify_kind, **transition)
            card.clear()
            card.update(saved_card)
            if focus is not None:
                state["research_window"]["current_focus"] = saved_focus
        card.update({
            "scope_snapshot": scope, "research_record": str(record),
            **{name: prior[name] for name in ("hypothesis", "current_action", "comparison_note") if name in prior},
        })
        if focus:
            card.update({name: focus[name] for name in ("hypothesis", "current_action")})
        # The readable body and this recovery payload are generated together in
        # the existing note. No separate history/cache becomes authoritative.
        entry = {**card, "external_baseline_gap": "See the canonical dataset_baseline_roster/current_external_baselines; compare external first."}
        metadata = json.dumps(entry, ensure_ascii=False, separators=(",", ":")).replace("<", "\\u003c").replace(">", "\\u003e")
        body = "\n".join([
            f"### {card['title']} ({card['subject_id']})",
            f"Status: {card['status']} | Updated: {card['updated_at']}",
            f"Observation: {card['verified_observation']}",
            f"Interpretation: {card['interpretation']}",
            f"External comparison: {entry['external_baseline_gap']}",
            *[f"{name}: {card[name]}" for name in ("starting_result", "best_result", "latest_result", "disposition_reason", "problem_path") if name in card],
            f"Next: {card['next_action']}",
            *[f"{label}: {card[name]}" for name, label in (
                ("hypothesis", "Hypothesis"), ("current_action", "Current test"),
                ("comparison_note", "Additional comparison note"),
            ) if card.get(name)],
            "This is evolving research evidence, not PI approval.",
            f"<!-- RPW:RESEARCH_DATA {metadata} -->",
        ])
        if legacy_body is not None:
            text = text.replace(f"RPW:RESEARCH_{identity}:", f"RPW:LEGACY_RESEARCH_{identity}:")
            text = text.replace(f"## RPW research {identity}", f"## Legacy research {identity}")
            text += "\nLegacy research summary above is retained for review, not automatically revalidated.\n"
        atomic_write_text(record, replace_managed_section(text, f"RESEARCH_{identity}", body, f"## RPW research {identity}"))
        if state.get("paper_ready_assessment"):
            archive_invalidated_paper_assessment(state, "research_evidence_update", args.subject_id)
            state["phase"] = "confirmed_project"
    save_state(path, state)
    print(
        json.dumps(
            {
                "updated_card": card,
                "record_path": str(record),
                "window_id": state["research_window"]["id"],
            } if durable else {"updated_card": card, "window": window_status_summary(path, state)},
            ensure_ascii=False,
            indent=2,
        )
    )


def cmd_monitor_ack(args: argparse.Namespace) -> None:
    path = Path(args.state)
    state = load_state(path)
    current = compact_state_summary(path, state)["wakeup_fingerprint"]
    expected = str(args.wakeup_fingerprint or "").strip()
    if not expected:
        raise SystemExit("--wakeup-fingerprint must be non-empty")
    if expected != current:
        raise SystemExit(
            "Refusing to acknowledge a stale monitor result: read status --compact again"
        )
    artifact = (
        clean_text(
            args.artifact_fingerprint,
            "--artifact-fingerprint",
        )
        if args.artifact_fingerprint is not None
        else None
    )
    has_artifact_action = artifact is not None or args.clear_artifact_fingerprint
    if bool(args.job_id) != has_artifact_action:
        raise SystemExit(
            "--job-id and either --artifact-fingerprint or "
            "--clear-artifact-fingerprint must be supplied together"
        )
    monitoring = state.setdefault("monitoring", empty_monitoring())
    fingerprints = monitoring.setdefault("artifact_fingerprints_by_job", {})
    if has_artifact_action:
        job_id = clean_text(args.job_id, "--job-id")
        active_job_ids = {
            job.get("id")
            for job in state.get("jobs", [])
            if job.get("status") in ACTIVE_JOB_STATUSES
        }
        if job_id not in active_job_ids:
            raise SystemExit(
                "Artifact acknowledgement requires an existing active --job-id"
            )
        if args.clear_artifact_fingerprint:
            fingerprints.pop(job_id, None)
        else:
            fingerprints[job_id] = artifact
        monitoring["legacy_unscoped_artifact_fingerprint"] = None
    monitoring["last_acknowledged_wakeup_fingerprint"] = current
    monitoring["acknowledged_at"] = now_iso()
    save_state(path, state)
    print(json.dumps(compact_state_summary(path, state), ensure_ascii=False, indent=2))


def cmd_audit(args: argparse.Namespace) -> None:
    path = Path(args.state)
    state = load_state(path)
    summary = state_summary(path, state)
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    if summary["control_issues"]:
        raise SystemExit(2)


def cmd_pause(args: argparse.Namespace) -> None:
    path = Path(args.state)
    state = load_state(path)
    if isinstance(state.get("manual_pause"), dict):
        raise SystemExit("Execution is already manually paused by the PI")
    decision = clean_text(args.pi_decision, "--pi-decision")
    event = {
        "action": "pause",
        "decision": decision,
        "reason": clean_text(args.reason, "--reason", optional=True),
        "created_at": now_iso(),
    }
    state["manual_pause"] = event
    state["last_manual_pause_event"] = event
    refresh_pause(state)
    save_state(path, state)
    print(json.dumps(state_summary(path, state), ensure_ascii=False, indent=2))


def cmd_resume(args: argparse.Namespace) -> None:
    path = Path(args.state)
    state = load_state(path)
    if not isinstance(state.get("manual_pause"), dict):
        raise SystemExit("Execution is not manually paused")
    decision = clean_text(args.pi_decision, "--pi-decision")
    event = {
        "action": "resume",
        "decision": decision,
        "reason": clean_text(args.reason, "--reason", optional=True),
        "previous_pause": state["manual_pause"],
        "created_at": now_iso(),
    }
    state["manual_pause"] = None
    state["last_manual_pause_event"] = event
    refresh_pause(state)
    save_state(path, state)
    print(json.dumps(state_summary(path, state), ensure_ascii=False, indent=2))


def cmd_paper_revoke(args: argparse.Namespace) -> None:
    path = Path(args.state)
    state = load_state(path)
    if state.get("phase") != "paper_handoff_approved":
        raise SystemExit("Paper handoff can be revoked only after paper approval")
    decision = clean_text(args.pi_decision, "--pi-decision")
    reason = clean_text(args.reason, "--reason")
    previous = state["layer_checkpoints"]["paper"]
    revoked_at = now_iso()
    state["checkpoint_history"].append(
        {
            "layer": "paper",
            "previous": previous,
            "replacement_id": "revoked-by-pi",
            "decision_source": {
                "type": "direct_pi_revocation",
                "decision": decision,
                "reason": reason,
            },
            "created_at": revoked_at,
        }
    )
    record = resolve_stored_path(path, previous.get("record_path"))
    if record is not None and record.is_file():
        with record.open("a", encoding="utf-8", newline="") as handle:
            handle.write(
                "\n\n## Paper handoff revoked by PI\n\n"
                f"- Revoked at: {revoked_at}\n"
                f"- User decision: {decision}\n"
                f"- Reason: {reason}\n"
                "- L1/L2 remain active; a new paper report and decision are required.\n"
            )
    state["layer_checkpoints"]["paper"] = empty_checkpoint()
    archive_invalidated_paper_assessment(
        state, "paper_handoff_revoked_by_pi", "revoked-by-pi"
    )
    state["phase"] = "confirmed_project"
    refresh_pause(state)
    save_state(path, state)
    print(json.dumps(state_summary(path, state), ensure_ascii=False, indent=2))


def cmd_question(args: argparse.Namespace) -> None:
    path = Path(args.state)
    state = load_state(path)
    pending = active_questions(state)
    if len(pending) >= MAX_MACRO_QUESTIONS:
        save_state(path, state)
        raise SystemExit(
            "Cannot add another PI decision question: five are already pending. "
            "The workflow is PAUSED_FOR_PI until at least one is answered."
        )
    target = str(args.target).strip()
    if not target:
        raise SystemExit("A PI decision question requires a stable --target")
    if target.startswith("frozen:"):
        frozen_target = normalized_frozen_key(target.split(":", 1)[1])
        if not frozen_target:
            raise SystemExit("A frozen-field decision target requires a non-empty key")
        target = f"frozen:{frozen_target}"
    question_text = str(args.text).strip()
    if not question_text:
        raise SystemExit("A PI decision question requires non-empty --text")
    open_questions = active_questions(state) + deferred_questions(state)
    if any(q.get("decision_target") == target for q in open_questions):
        raise SystemExit(f"A PI question already exists for decision target: {target}")
    if any(q.get("text") == question_text for q in open_questions):
        raise SystemExit("An identical PI decision question is already open")
    if args.layer in CHECKPOINT_LAYERS and not target.startswith(f"{args.layer}:"):
        raise SystemExit(
            f"A {args.layer} question target must start with {args.layer}:"
        )
    private_seed_risk = target.startswith(SEED_SELECTION_RISK_TARGET_PREFIX)
    if private_seed_risk:
        if args.layer != "paper":
            raise SystemExit("A favorable-seed risk question must use --layer paper")
        question_text = (
            "Accept the project-specific favorable-seed risk already disclosed "
            "in the current user conversation?"
        )
    question_id = next_id(state["macro_questions"], "Q")
    revisions = state.setdefault("decision_target_revisions", {})
    target_revision = int(revisions.get(target, 0)) + 1
    for previous in state["macro_questions"]:
        if (
            previous.get("decision_target") == target
            and not previous.get("consumed_by")
        ):
            previous["superseded_by"] = question_id
    revisions[target] = target_revision
    question = {
        "id": question_id,
        "status": "PENDING_PI",
        "layer": args.layer,
        "decision_target": target,
        "target_revision": target_revision,
        "superseded_by": None,
        "text": question_text,
        "priority": args.priority,
        "reason": (
            "The paper gate requires scoped user acceptance for this private risk."
            if private_seed_risk
            else args.reason
        ),
        "recommendation": (
            "Use only the user's conversation-level decision."
            if private_seed_risk
            else args.recommendation
        ),
        "continue_plan": (
            "Continue independent authorized work; do not use this result at the paper gate."
            if private_seed_risk
            else args.continue_plan
        ),
        "created_at": now_iso(),
        "answered_at": None,
        "decision": None,
        "outcome": None,
        "responses": [],
        "revisit_condition": None,
        "deferred_at": None,
        "reopened_at": None,
        "consumed_by": None,
    }
    state["macro_questions"].append(question)
    refresh_pause(state)
    save_state(path, state)
    print(
        json.dumps(
            {"added": question, "state": state_summary(path, state)},
            ensure_ascii=False,
            indent=2,
        )
    )


def cmd_answer(args: argparse.Namespace) -> None:
    path = Path(args.state)
    state = load_state(path)
    matches = [q for q in state["macro_questions"] if q.get("id") == args.id]
    if not matches:
        raise SystemExit(f"Question not found: {args.id}")
    question = matches[0]
    if question.get("status") not in {"PENDING_PI", "DEFERRED_PI"}:
        raise SystemExit(f"Question is not open: {args.id}")
    decision_text = str(args.decision).strip()
    if not decision_text:
        raise SystemExit("A PI reply requires non-empty --decision")
    if str(question.get("decision_target") or "").startswith(
        SEED_SELECTION_RISK_TARGET_PREFIX
    ):
        decision_text = "PI response recorded for the private favorable-seed risk."
    response = {
        "text": decision_text,
        "outcome": args.outcome,
        "created_at": now_iso(),
    }
    question.setdefault("responses", []).append(response)
    if args.outcome == "informational":
        refresh_pause(state)
        save_state(path, state)
        print(
            json.dumps(
                {"recorded_information": response, "question": question, "state": state_summary(path, state)},
                ensure_ascii=False,
                indent=2,
            )
        )
        return
    if args.outcome == "defer":
        revisit = str(args.revisit_condition or "").strip()
        if not revisit:
            raise SystemExit("A deferred decision requires --revisit-condition")
        question["status"] = "DEFERRED_PI"
        question["decision"] = decision_text
        question["outcome"] = "defer"
        question["answered_at"] = None
        question["deferred_at"] = now_iso()
        question["revisit_condition"] = revisit
    else:
        question["status"] = "ANSWERED"
        question["decision"] = decision_text
        question["outcome"] = args.outcome
        question["answered_at"] = now_iso()
    refresh_pause(state)
    save_state(path, state)
    print(
        json.dumps(
            {"answered": question, "state": state_summary(path, state)},
            ensure_ascii=False,
            indent=2,
        )
    )


def cmd_reopen(args: argparse.Namespace) -> None:
    path = Path(args.state)
    state = load_state(path)
    if len(active_questions(state)) >= MAX_MACRO_QUESTIONS:
        raise SystemExit(
            "Cannot reopen a deferred question while five PI decisions are active"
        )
    matches = [q for q in state["macro_questions"] if q.get("id") == args.id]
    if not matches:
        raise SystemExit(f"Question not found: {args.id}")
    question = matches[0]
    if question.get("status") != "DEFERRED_PI":
        raise SystemExit(f"Question is not deferred: {args.id}")
    question.setdefault("responses", []).append(
        {
            "text": str(args.reason or "Revisit condition reached"),
            "outcome": "reopened",
            "created_at": now_iso(),
        }
    )
    question["status"] = "PENDING_PI"
    question["decision"] = None
    question["outcome"] = None
    question["answered_at"] = None
    question["reopened_at"] = now_iso()
    refresh_pause(state)
    save_state(path, state)
    print(
        json.dumps(
            {"reopened": question, "state": state_summary(path, state)},
            ensure_ascii=False,
            indent=2,
        )
    )


def compact_recent_notifications(state: dict[str, Any]) -> None:
    policy = state.get("notification_policy") or {}
    if policy.get("mode") != "recent_only":
        return
    limit = int(policy.get("recent_limit", RECENT_NOTIFICATION_LIMIT))
    if limit < 0:
        limit = RECENT_NOTIFICATION_LIMIT
    excess = max(0, len(state["notifications"]) - limit)
    if excess:
        state["notifications"] = state["notifications"][excess:]
        state["notification_compacted_count"] = (
            int(state.get("notification_compacted_count", 0)) + excess
        )


def append_notification(
    state: dict[str, Any],
    text: str,
    kind: str = "general",
    *,
    from_id: str | None = None,
    to_id: str | None = None,
) -> dict[str, Any]:
    if kind not in NOTIFICATION_KINDS:
        raise SystemExit(
            "Notification kind must be one of: "
            + ", ".join(sorted(NOTIFICATION_KINDS))
        )
    state["notification_sequence"] = int(state.get("notification_sequence", 0)) + 1
    notification = {
        "id": f"N{state['notification_sequence']:03d}",
        "kind": kind,
        "text": text,
        "created_at": now_iso(),
    }
    if from_id is not None or to_id is not None:
        if kind not in {"problem_switch", "method_cluster_switch"}:
            raise SystemExit(
                "Structured from/to IDs are only valid for scientific switch notifications"
            )
        previous_id = validate_checkpoint_id(str(from_id or ""))
        next_id_value = validate_checkpoint_id(str(to_id or ""))
        if previous_id == next_id_value:
            raise SystemExit("A scientific switch must change from_id to a different to_id")
        notification["transition"] = {
            "from_id": previous_id,
            "to_id": next_id_value,
        }
    state["notifications"].append(notification)
    if kind in {"problem_switch", "method_cluster_switch"}:
        sync_scientific_switch_to_window(state, kind, text, notification["transition"]["to_id"])
    compact_recent_notifications(state)
    return notification


def current_answered_approval(
    state: dict[str, Any],
    decision_id: str,
    expected_layer: str | None,
    expected_target: str,
    purpose: str,
) -> dict[str, Any]:
    matches = [q for q in state["macro_questions"] if q.get("id") == decision_id]
    if not matches:
        raise SystemExit(f"Decision question not found: {decision_id}")
    question = matches[0]
    if question.get("status") != "ANSWERED" or not question.get("decision"):
        raise SystemExit(f"Decision question is not answered: {decision_id}")
    if expected_layer is not None and question.get("layer", "other") != expected_layer:
        raise SystemExit(
            f"Question {decision_id} belongs to layer "
            f"{question.get('layer', 'other')!r}, not {expected_layer!r}"
        )
    if question.get("decision_target") != expected_target:
        raise SystemExit(
            f"Question {decision_id} targets {question.get('decision_target')!r}, "
            f"not {expected_target!r}"
        )
    if question.get("consumed_by"):
        raise SystemExit(
            f"Question {decision_id} approval was already consumed by "
            f"{question.get('consumed_by')}"
        )
    if question.get("superseded_by"):
        raise SystemExit(
            f"Question {decision_id} was superseded by {question.get('superseded_by')}; "
            "use the latest PI decision for this target"
        )
    latest_revision = int(
        state.get("decision_target_revisions", {}).get(expected_target, 0)
    )
    if int(question.get("target_revision") or 0) != latest_revision:
        raise SystemExit(
            f"Question {decision_id} is not the latest PI decision for {expected_target!r}"
        )
    if question.get("outcome") not in APPROVING_OUTCOMES:
        raise SystemExit(
            f"Question {decision_id} outcome {question.get('outcome')!r} "
            f"cannot authorize {purpose}"
        )
    return question


def cmd_notify(args: argparse.Namespace) -> None:
    path = Path(args.state)
    state = load_state(path)
    notification_text = str(args.text).strip()
    if not notification_text:
        raise SystemExit("A notification requires non-empty --text")
    switch_kind = args.kind in {"problem_switch", "method_cluster_switch"}
    if switch_kind and not (args.from_id and args.to_id):
        raise SystemExit(
            "Scientific switch notifications require both --from-id and --to-id"
        )
    if not switch_kind and (args.from_id or args.to_id):
        raise SystemExit(
            "--from-id/--to-id are only valid with problem_switch or "
            "method_cluster_switch"
        )
    notification = append_notification(
        state,
        notification_text,
        args.kind,
        from_id=args.from_id,
        to_id=args.to_id,
    )
    save_state(path, state)
    print(
        json.dumps(
            {"added": notification, "state": state_summary(path, state)},
            ensure_ascii=False,
            indent=2,
        )
    )


def instruction_decision_source(
    state: dict[str, Any], args: argparse.Namespace, stored_path: str
) -> dict[str, str]:
    expected_target = f"instructions:{stored_path}"
    if args.decision_id:
        question = current_answered_approval(
            state,
            args.decision_id,
            "instructions",
            expected_target,
            "a semantic instruction update",
        )
        return {
            "type": "answered_question",
            "question_id": args.decision_id,
            "decision": str(question["decision"]),
            "outcome": str(question["outcome"]),
        }
    decision = str(args.pi_decision or "").strip()
    if not decision:
        raise SystemExit(
            "Semantic instruction maintenance requires --decision-id or the user's actual --pi-decision"
        )
    if args.pi_outcome not in APPROVING_OUTCOMES:
        raise SystemExit(
            "Direct semantic instruction maintenance requires --pi-outcome approve or select"
        )
    return {
        "type": "direct_pi_instruction",
        "decision": decision,
        "outcome": args.pi_outcome,
    }


def compact_recent_instruction_updates(maintenance: dict[str, Any]) -> None:
    updates = maintenance.setdefault("recent_updates", [])
    excess = max(0, len(updates) - RECENT_INSTRUCTION_UPDATE_LIMIT)
    if excess:
        del updates[:excess]
        maintenance["compacted_update_count"] = (
            int(maintenance.get("compacted_update_count", 0)) + excess
        )


def compact_recent_scope_removals(maintenance: dict[str, Any]) -> None:
    removals = maintenance.setdefault("recent_scope_removals", [])
    excess = max(0, len(removals) - RECENT_INSTRUCTION_UPDATE_LIMIT)
    if excess:
        del removals[:excess]
        maintenance["compacted_scope_removal_count"] = (
            int(maintenance.get("compacted_scope_removal_count", 0)) + excess
        )


def instruction_scope_removal_source(
    state: dict[str, Any],
    args: argparse.Namespace,
    audit: dict[str, Any],
    scope_exists: bool,
) -> dict[str, str]:
    if not scope_exists:
        if args.decision_id or args.pi_decision or args.pi_outcome:
            raise SystemExit(
                "A missing instruction scope is pruned autonomously; omit decision arguments"
            )
        return {"type": "autonomous_missing_scope_prune"}
    expected_target = instruction_scope_target(audit)
    if args.decision_id:
        question = current_answered_approval(
            state,
            args.decision_id,
            "instructions",
            expected_target,
            "removal of an existing instruction-audit scope",
        )
        return {
            "type": "answered_question",
            "question_id": args.decision_id,
            "decision": str(question["decision"]),
            "outcome": str(question["outcome"]),
        }
    decision = str(args.pi_decision or "").strip()
    if not decision:
        raise SystemExit(
            "Removing an instruction scope whose directory still exists requires "
            f"--decision-id for target {expected_target!r} or the user's actual --pi-decision"
        )
    if args.pi_outcome not in APPROVING_OUTCOMES:
        raise SystemExit(
            "Direct removal of an existing instruction scope requires --pi-outcome approve or select"
        )
    return {
        "type": "direct_pi_instruction",
        "decision": decision,
        "outcome": args.pi_outcome,
    }


def audit_covers_target(state_path: Path, audit: dict[str, Any], target: Path) -> bool:
    project_root = project_root_for_state(state_path).resolve()
    audited_cwd = (project_root / str(audit.get("scope_cwd") or ".")).resolve()
    try:
        audited_cwd.relative_to(target.parent.resolve())
    except ValueError:
        return False
    return target.name in (
        AGENTS_FILENAMES + tuple(audit.get("fallback_filenames") or [])
    )


def current_instruction_audits(
    state_path: Path, maintenance: dict[str, Any]
) -> dict[str, dict[str, Any]]:
    current: dict[str, dict[str, Any]] = {}
    for key, previous in maintenance.get("audits_by_scope", {}).items():
        if not isinstance(previous, dict):
            continue
        current[key] = analyze_project_instructions(
            state_path,
            previous.get("scope_cwd"),
            previous.get("fallback_filenames"),
        )
    return current


def canonical_source_receipts(
    state_path: Path, raw_sources: list[str], target: Path
) -> list[dict[str, Any]]:
    if not raw_sources:
        raise SystemExit(
            "Compaction requires at least one --canonical-source that retains the removed detail"
        )
    receipts: list[dict[str, Any]] = []
    for raw in raw_sources:
        source, stored, digest = normalize_readonly_reference(state_path, raw)
        if source == target:
            raise SystemExit("A compacted instruction file cannot be its own canonical source")
        receipts.append(
            {
                "path": stored,
                "sha256_at_recording": digest,
                "bytes": source.stat().st_size,
            }
        )
    return receipts


def cmd_agents_audit(args: argparse.Namespace) -> None:
    path = Path(args.state)
    state = load_state(path)
    maintenance = state["instruction_maintenance"]
    audits = maintenance.setdefault("audits_by_scope", {})
    _, descriptor = normalized_instruction_scope(path, args.cwd, args.fallback_name)
    key = instruction_scope_key(descriptor)
    bootstrapped = key not in audits
    if bootstrapped:
        require_execution_active(state, "bootstrap a new project-instruction audit scope")
    audit = analyze_project_instructions(path, args.cwd, args.fallback_name)
    changed_scopes = []
    for stored_key, current in current_instruction_audits(path, maintenance).items():
        previous = audits[stored_key]
        if instruction_snapshot_signature(current) != instruction_snapshot_signature(
            previous
        ):
            changed_scopes.append(str(previous.get("scope_cwd") or "."))
    if changed_scopes:
        print(
            json.dumps(
                {
                    "instruction_audit": audit,
                    "snapshot_updated": False,
                    "changed_scopes": sorted(set(changed_scopes)),
                    "state": state_summary(path, state),
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        raise SystemExit(2)
    if bootstrapped:
        audits[key] = audit
        save_state(path, state)
    print(
        json.dumps(
            {
                "instruction_audit": audit,
                "snapshot_updated": bootstrapped,
                "state": state_summary(path, state),
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    if audit["status"] == "OVER_DEFAULT_LIMIT":
        raise SystemExit(2)


def cmd_agents_scope_remove(args: argparse.Namespace) -> None:
    path = Path(args.state)
    state = load_state(path)
    require_execution_active(state, "remove a project-instruction audit scope")
    maintenance = state["instruction_maintenance"]
    audits = maintenance.get("audits_by_scope", {})
    scope_path, descriptor = normalized_instruction_scope(
        path, args.cwd, args.fallback_name
    )
    key = instruction_scope_key(descriptor)
    previous = audits.get(key)
    if not isinstance(previous, dict):
        raise SystemExit(
            f"Instruction-audit scope is not recorded: {descriptor['scope_cwd']}"
        )
    scope_exists = scope_path.is_dir()
    source = instruction_scope_removal_source(
        state, args, previous, scope_exists
    )
    receipt = {
        "scope_key": key,
        "scope_cwd": previous.get("scope_cwd"),
        "fallback_filenames": previous.get("fallback_filenames") or [],
        "scope_existed_at_removal": scope_exists,
        "reason": args.reason,
        "summary": args.summary,
        "previous_status": previous.get("status"),
        "previous_observed_paths": [
            item.get("path") for item in previous.get("observed_files", [])
        ],
        "decision_source": source,
        "removed_at": now_iso(),
    }
    del audits[key]
    maintenance.setdefault("recent_scope_removals", []).append(receipt)
    compact_recent_scope_removals(maintenance)
    if scope_exists:
        consume_question(
            state,
            args.decision_id,
            {"type": "instruction_scope_remove", "scope_key": key},
        )
    notification = append_notification(state, f"项目说明审计范围维护：{args.summary}")
    refresh_pause(state)
    save_state(path, state)
    print(
        json.dumps(
            {
                "removed_scope": receipt,
                "notification": notification,
                "state": state_summary(path, state),
            },
            ensure_ascii=False,
            indent=2,
        )
    )


def cmd_agents_record(args: argparse.Namespace) -> None:
    path = Path(args.state)
    state = load_state(path)
    require_execution_active(state, "record a project-instruction change")
    maintenance = state["instruction_maintenance"]
    audits = maintenance.get("audits_by_scope", {})
    if not audits:
        raise SystemExit("Run agents-audit before editing project instructions")

    target, stored = project_local_path(
        path, args.path, require_file=not args.after_absent
    )
    if args.before_absent and args.after_absent:
        raise SystemExit("--before-absent and --after-absent cannot be used together")
    if args.after_absent and target.exists():
        raise SystemExit(f"{stored} still exists; remove --after-absent")
    relevant = {
        key: previous
        for key, previous in audits.items()
        if isinstance(previous, dict) and audit_covers_target(path, previous, target)
    }
    if not relevant:
        raise SystemExit(
            "No recorded instruction-audit scope covers this file; run agents-audit "
            "for a working directory at or below its directory before editing"
        )
    current_by_scope = current_instruction_audits(path, maintenance)
    changed_paths: set[str] = set()
    for key, previous_audit in audits.items():
        if not isinstance(previous_audit, dict):
            continue
        current_audit = current_by_scope[key]
        before_all = {
            str(item.get("path")): item
            for item in previous_audit.get("observed_files", [])
        }
        after_all = {
            str(item.get("path")): item
            for item in current_audit.get("observed_files", [])
        }
        changed_paths.update(
            candidate
            for candidate in set(before_all) | set(after_all)
            if (before_all.get(candidate) or {}).get("sha256")
            != (after_all.get(candidate) or {}).get("sha256")
        )
    before_entries: list[dict[str, Any]] = []
    after_entries: list[dict[str, Any]] = []
    for key, previous_audit in relevant.items():
        current_audit = current_by_scope[key]
        before_by_path = {
            str(item.get("path")): item
            for item in previous_audit.get("observed_files", [])
        }
        after_by_path = {
            str(item.get("path")): item
            for item in current_audit.get("observed_files", [])
        }
        if stored in before_by_path:
            before_entries.append(before_by_path[stored])
        if stored in after_by_path:
            after_entries.append(after_by_path[stored])
    if sorted(changed_paths) != [stored]:
        raise SystemExit(
            "Record one instruction-file content change at a time; changed paths are: "
            + (", ".join(sorted(changed_paths)) if changed_paths else "none")
        )

    before = before_entries[0] if before_entries else None
    if len({item.get("sha256") for item in before_entries}) > 1:
        raise SystemExit(f"Stored audit scopes disagree about the previous hash for {stored}")
    if before is None:
        if not args.before_absent:
            raise SystemExit(
                f"{stored} was absent from the last audit; use --before-absent only for a newly created file"
            )
        before_sha = None
        before_bytes = 0
    else:
        if args.before_absent:
            raise SystemExit(f"{stored} existed in the last audit; remove --before-absent")
        before_sha = str(before["sha256"])
        before_bytes = int(before["bytes"])

    after = after_entries[0] if after_entries else None
    if len({item.get("sha256") for item in after_entries}) > 1:
        raise SystemExit(f"Current audit scopes disagree about the resulting hash for {stored}")
    if args.after_absent:
        if after is not None:
            raise SystemExit(f"{stored} is still present in the instruction audit")
        if before is None:
            raise SystemExit(f"{stored} was absent before and after; there is no deletion to record")
        after_sha = None
        after_bytes = 0
    else:
        if after is None:
            raise SystemExit(f"{stored} is absent; use --after-absent for a deletion")
        after_sha = str(after["sha256"])
        after_bytes = int(after["bytes"])
    if args.kind == "compaction" and after_bytes >= before_bytes:
        raise SystemExit(
            "A compaction receipt requires the resulting instruction file to be smaller"
        )

    canonical_sources = (
        canonical_source_receipts(path, args.canonical_source, target)
        if args.kind == "compaction"
        else []
    )
    if args.canonical_source and args.kind != "compaction":
        raise SystemExit("--canonical-source is used only with --kind compaction")

    if args.kind == "semantic":
        source = instruction_decision_source(state, args, stored)
    else:
        if args.decision_id or args.pi_decision or args.pi_outcome:
            raise SystemExit(
                "Mechanical and compaction maintenance do not consume PI approval; omit decision arguments"
            )
        source = {"type": "autonomous_maintenance"}

    receipt = {
        "path": stored,
        "kind": args.kind,
        "reason": args.reason,
        "summary": args.summary,
        "before_sha256": before_sha,
        "before_bytes": before_bytes,
        "after_sha256": after_sha,
        "after_bytes": after_bytes,
        "after_absent": args.after_absent,
        "canonical_sources": canonical_sources,
        "decision_source": source,
        "recorded_at": now_iso(),
    }
    maintenance["recent_updates"].append(receipt)
    compact_recent_instruction_updates(maintenance)
    if args.kind == "semantic":
        consume_question(
            state,
            args.decision_id,
            {
                "type": "instruction_update",
                "path": stored,
                "after_sha256": after_sha,
            },
        )
    notification = append_notification(state, f"项目说明维护：{args.summary}")
    for key in relevant:
        audits[key] = current_by_scope[key]
    refresh_pause(state)
    save_state(path, state)
    print(
        json.dumps(
            {
                "recorded": receipt,
                "notification": notification,
                "instruction_audits": [current_by_scope[key] for key in relevant],
                "state": state_summary(path, state),
            },
            ensure_ascii=False,
            indent=2,
        )
    )


def cmd_compact_notifications(args: argparse.Namespace) -> None:
    path = Path(args.state)
    state = load_state(path)
    keep = args.keep
    if keep < 0:
        raise SystemExit("--keep must be non-negative")
    removed = max(0, len(state["notifications"]) - keep)
    if removed:
        state["notifications"] = state["notifications"][removed:]
        state["notification_compacted_count"] = (
            int(state.get("notification_compacted_count", 0)) + removed
        )
    state["notification_policy"] = {"mode": "recent_only", "recent_limit": keep}
    save_state(path, state)
    print(
        json.dumps(
            {"removed": removed, "state": state_summary(path, state)},
            ensure_ascii=False,
            indent=2,
        )
    )


def approving_decision_source(
    state: dict[str, Any], args: argparse.Namespace, layer: str
) -> dict[str, str]:
    assessment_hash = None
    assessment_recorded_at = None
    if layer == "paper":
        assessment = state.get("paper_ready_assessment") or {}
        assessment_hash = str(assessment.get("payload_sha256_at_gate") or "").strip()
        assessment_recorded_at = str(assessment.get("recorded_at") or "").strip()
        if not assessment_hash or not assessment_recorded_at:
            raise SystemExit(
                "Paper approval requires a current paper-decision report receipt"
            )
    if args.decision_id:
        expected_target = f"{layer}:{args.id}"
        question = current_answered_approval(
            state,
            args.decision_id,
            layer,
            expected_target,
            "a checkpoint confirmation",
        )
        outcome = question.get("outcome")
        source = {
            "type": "answered_question",
            "question_id": args.decision_id,
            "decision": str(question["decision"]),
            "outcome": str(outcome),
        }
        if layer == "paper":
            if not timestamp_at_or_after(
                question.get("created_at"), assessment_recorded_at
            ) or not timestamp_at_or_after(
                question.get("answered_at"), assessment_recorded_at
            ):
                raise SystemExit(
                    "The paper decision question must be created and answered after "
                    "the current paper-decision report is generated"
                )
            source["paper_assessment_payload_sha256"] = assessment_hash
            source["paper_assessment_recorded_at"] = assessment_recorded_at
        return source
    direct_decision = str(args.pi_decision or "").strip()
    if not direct_decision:
        raise SystemExit("--pi-decision must contain the user's actual decision")
    if args.pi_outcome not in APPROVING_OUTCOMES:
        raise SystemExit("Direct checkpoint confirmation requires --pi-outcome approve or select")
    source = {
        "type": "direct_pi_instruction",
        "decision": direct_decision,
        "outcome": args.pi_outcome,
    }
    if layer == "paper":
        source["paper_assessment_payload_sha256"] = assessment_hash
        source["paper_assessment_recorded_at"] = assessment_recorded_at
    return source


def consume_question(
    state: dict[str, Any], decision_id: str | None, consumer: dict[str, str]
) -> None:
    if not decision_id:
        return
    matches = [q for q in state["macro_questions"] if q.get("id") == decision_id]
    if not matches:
        raise SystemExit(f"Decision question not found: {decision_id}")
    question = matches[0]
    if question.get("consumed_by"):
        raise SystemExit(f"Decision question was already consumed: {decision_id}")
    question["consumed_by"] = {**consumer, "consumed_at": now_iso()}


def seed_selection_risk_decision_source(
    state: dict[str, Any],
    args: argparse.Namespace,
    science_id: str,
    anchor_revision: int,
) -> dict[str, str]:
    expected_target = (
        f"paper:seed-selection-risk:{science_id}:anchor-{anchor_revision}"
    )
    if args.seed_risk_decision_id:
        question = current_answered_approval(
            state,
            args.seed_risk_decision_id,
            "paper",
            expected_target,
            "favorable-seed selection risk acceptance",
        )
        return {
            "type": "answered_question",
            "question_id": args.seed_risk_decision_id,
            "outcome": str(question["outcome"]),
        }
    direct_decision = str(args.seed_risk_pi_decision or "").strip()
    if not direct_decision:
        raise SystemExit(
            "Favorable-seed selection requires --seed-risk-decision-id or the "
            "user's direct --seed-risk-pi-decision"
        )
    if args.seed_risk_pi_outcome not in APPROVING_OUTCOMES:
        raise SystemExit(
            "Direct favorable-seed risk acceptance requires "
            "--seed-risk-pi-outcome approve or select"
        )
    return {
        "type": "direct_pi_instruction",
        "outcome": args.seed_risk_pi_outcome,
    }


def checkpoint_payload(
    args: argparse.Namespace, state_path: Path, state: dict[str, Any]
) -> dict[str, Any]:
    if args.layer == "compass":
        if not (nonblank(args.venue_or_window) and nonblank(args.domain)):
            raise SystemExit("Compass confirmation requires --venue-or-window and --domain")
        previous = state["layer_checkpoints"].get("compass", {})
        previous_payload = previous.get("payload") or {}
        if args.clear_starting_concept:
            starting_concept = "UNSET"
        elif args.starting_concept is not None:
            starting_concept = clean_text(args.starting_concept, "--starting-concept")
        else:
            starting_concept = (
                str(previous_payload.get("starting_concept") or "UNSET").strip()
                or "UNSET"
            )
        return {
            "venue_or_window": clean_text(args.venue_or_window, "--venue-or-window"),
            "domain": clean_text(args.domain, "--domain"),
            "starting_concept": starting_concept,
        }
    if args.layer == "direction":
        if not checkpoint_usable(state_path, state, "compass"):
            raise SystemExit("Cannot confirm direction before a complete research compass")
        minimum_gain = (
            MIN_PAPER_READY_GAIN_POINTS
            if args.minimum_paper_gain_points is None
            else args.minimum_paper_gain_points
        )
        if (
            not finite_number(minimum_gain)
            or minimum_gain < MIN_PAPER_READY_GAIN_POINTS
            or minimum_gain > 100.0
        ):
            raise SystemExit(
                "--minimum-paper-gain-points must be a finite number from 1 to 100; "
                "a project may set a stricter bar but cannot lower the 1-point floor"
            )
        required = {
            "task_type": args.task_type,
            "dataset": args.dataset,
            "primary_dataset": args.primary_dataset,
            "unexposed_dataset_search": args.unexposed_dataset_search,
            "competitive_bar": args.competitive_bar,
            "novelty_sufficiency": args.novelty_sufficiency,
            "generalization_requirement": args.generalization_requirement,
            "paper_ready_threshold": args.paper_ready_threshold,
        }
        missing = [key for key, value in required.items() if not nonblank(value)]
        if missing:
            raise SystemExit(
                "Direction confirmation is missing structured fields: " + ", ".join(missing)
            )
        return {
            "task_type": str(args.task_type).strip(),
            "dataset": str(args.dataset).strip(),
            "adopted_datasets": normalize_adopted_datasets(
                args.primary_dataset, args.supporting_dataset
            ),
            "unexposed_dataset_search": str(args.unexposed_dataset_search).strip(),
            "evidence_standard": {
                "competitive_bar": str(args.competitive_bar).strip(),
                "novelty_sufficiency": str(args.novelty_sufficiency).strip(),
                "generalization_requirement": str(args.generalization_requirement).strip(),
                "paper_ready_threshold": str(args.paper_ready_threshold).strip(),
                "minimum_paper_gain_points": float(minimum_gain),
            },
        }
    if args.layer == "science":
        required = {
            "direction_id": args.direction_id,
            "problem_id": args.problem_id,
            "method_cluster_id": args.method_cluster_id,
            "problem": args.problem,
            "nearest_work_gap": args.nearest_work_gap,
            "paper_grade_rationale": args.paper_grade_rationale,
            "core_mechanism": args.core_mechanism,
            "falsifiable_prediction": args.falsifiable_prediction,
            "simple_combination_counterfactual": args.simple_combination_counterfactual,
            "contribution_type": args.contribution_type,
            "innovation_claim": args.innovation_claim,
            "external_baseline_status": args.external_baseline_status,
            "ceiling_summary": args.ceiling_summary,
        }
        missing = [key for key, value in required.items() if not nonblank(value)]
        if missing:
            raise SystemExit(
                "Science confirmation is missing structured fields: " + ", ".join(missing)
            )
        direction = state["layer_checkpoints"]["direction"]
        if not checkpoint_usable(state_path, state, "direction"):
            raise SystemExit("Cannot confirm science before a complete L1 direction")
        if not baseline_roster_usable(state) or not baseline_roster_record_usable(
            state_path, state
        ):
            raise SystemExit(
                "Cannot confirm science before every adopted dataset has a structured "
                "external-baseline roster entry"
            )
        required = {key: str(value).strip() for key, value in required.items()}
        required["problem_id"] = validate_checkpoint_id(required["problem_id"])
        required["problem_path"] = normalize_problem_path(
            args.problem_path,
            active_leaf=required["problem_id"],
            label="--problem-path",
        )
        required["method_cluster_id"] = validate_checkpoint_id(
            required["method_cluster_id"]
        )
        if required["contribution_type"] not in PAPER_GRADE_CONTRIBUTION_TYPES:
            raise SystemExit(
                "--contribution-type must name a paper-grade scientific contribution: "
                + ", ".join(sorted(PAPER_GRADE_CONTRIBUTION_TYPES))
            )
        # Scientific adequacy depends on the nearest alternative and evidence,
        # not substrings in a mechanism description (including negated examples).
        if required["direction_id"] != direction.get("id"):
            raise SystemExit("--direction-id must match the active confirmed direction")
        anchor = state.get("evaluation_anchor") or {}
        if not evaluation_anchor_usable(state):
            raise SystemExit(
                "Cannot confirm science before a scientific-scope evaluation anchor is "
                "locked for this candidate before broad tuning"
            )
        for field in (
            "problem_path",
            "problem_id",
            "method_cluster_id",
            "falsifiable_prediction",
        ):
            if required.get(field) != anchor.get(field):
                raise SystemExit(
                    "L2 confirmation must match the current pre-tuning evaluation anchor "
                    f"for {field}; replace the anchor or confirm the anchored candidate"
                )
        required["evidence_refs"] = {
            "problem_portfolio": evidence_reference(
                state_path, args.problem_portfolio_record, "problem_portfolio_record"
            ),
            "nearest_work": evidence_reference(
                state_path, args.nearest_work_record, "nearest_work_record"
            ),
            "external_baselines": evidence_reference(
                state_path, args.baseline_record, "baseline_record"
            ),
            "results": evidence_reference(
                state_path, args.result_record, "result_record"
            ),
        }
        if args.change_notification is not None:
            required["change_notification"] = clean_text(
                args.change_notification, "--change-notification"
            )
        return required
    if args.layer == "paper":
        required = {
            "science_id": args.science_id,
            "headline_claim": args.headline_claim,
            "handoff_target": args.handoff_target,
        }
        missing = [key for key, value in required.items() if not nonblank(value)]
        if missing:
            raise SystemExit(
                "Paper confirmation is missing structured fields: " + ", ".join(missing)
            )
        science = state["layer_checkpoints"]["science"]
        if not checkpoint_usable(state_path, state, "science"):
            raise SystemExit("Cannot confirm paper handoff before a complete L2 story")
        required = {key: str(value).strip() for key, value in required.items()}
        if required["science_id"] != science.get("id"):
            raise SystemExit("--science-id must match the active confirmed science checkpoint")
        if state.get("phase") != "paper_ready_pending_pi":
            raise SystemExit("Paper handoff requires phase paper_ready_pending_pi")
        if not state.get("paper_ready_assessment"):
            raise SystemExit("Paper handoff requires a recorded paper-ready assessment")
        if not paper_ready_assessment_usable(state_path, state):
            raise SystemExit(
                "The recorded paper-ready assessment is missing, changed since the gate, "
                "or no longer tied to the active L1/L2 checkpoints"
            )
        return required
    raise SystemExit(f"Unsupported checkpoint layer: {args.layer}")


def mark_checkpoint_record_stale(
    state_path: Path,
    layer: str,
    checkpoint: dict[str, Any],
    reason: str,
    replacement_id: str,
) -> None:
    record = resolve_stored_path(state_path, checkpoint.get("record_path"))
    if not record or not record.is_file():
        return
    stale_status = f"STALE_AFTER_{reason.upper()}"
    if layer == "direction":
        text = record.read_text(encoding="utf-8")
        text = replace_managed_section(
            text,
            "DIRECTION_STANDARD_CURRENT",
            "## Project evidence standard\n\n"
            f"- Status: `{stale_status}`\n"
            f"- Previous checkpoint: `{checkpoint.get('id')}`\n"
            f"- Invalidated by: `{replacement_id}`\n"
            "- Next action: adopt a new L1 evidence standard with the direction",
            "## Project evidence standard",
        )
        text = replace_managed_section(
            text,
            "DIRECTION_DECISION_CURRENT",
            "## Current PI decision\n\n"
            f"- Status: `{stale_status}`\n"
            f"- Previous checkpoint: `{checkpoint.get('id')}`\n"
            f"- Invalidated by: `{replacement_id}`\n"
            "- Next action: present and confirm a new L1 task-dataset direction",
            "## Current PI decision",
        )
        atomic_write_text(record, text)
    elif layer == "science":
        text = record.read_text(encoding="utf-8")
        text = replace_science_current_block(
            text,
            f"L2 status: `{stale_status}`  \n"
            f"Previous checkpoint: `{checkpoint.get('id')}`  \n"
            f"Invalidated by: `{replacement_id}`  \n"
            "Next action: remap or reconfirm the scientific story inside the active L1  \n"
            f"Last material update: {now_iso()}",
        )
        atomic_write_text(record, text)


def invalidate_checkpoint(
    state_path: Path,
    state: dict[str, Any],
    layer: str,
    reason: str,
    replacement_id: str,
) -> None:
    previous = state["layer_checkpoints"][layer]
    if previous.get("status") == "UNSET":
        return
    if str(previous.get("status") or "").startswith("STALE_AFTER_"):
        return
    state["checkpoint_history"].append(
        {
            "layer": layer,
            "previous": previous,
            "replacement_id": replacement_id,
            "decision_source": {"type": reason},
            "created_at": now_iso(),
        }
    )
    stale = dict(previous)
    stale["status"] = f"STALE_AFTER_{reason.upper()}"
    stale["decision_source"] = {"type": reason, "replacement_id": replacement_id}
    mark_checkpoint_record_stale(
        state_path, layer, previous, reason, replacement_id
    )
    state["layer_checkpoints"][layer] = stale


def invalidate_evaluation_anchor(
    state: dict[str, Any], reason: str, replacement_id: str
) -> None:
    anchor = state.get("evaluation_anchor")
    if isinstance(anchor, dict):
        state.setdefault("evaluation_anchor_history", []).append(
            {
                **anchor,
                "invalidated_at": now_iso(),
                "invalidated_by": reason,
                "replacement_id": replacement_id,
            }
        )
    state["evaluation_anchor"] = None
    state["seed_selection_risk_acceptance"] = None


def record_baseline_roster(
    path: Path, state: dict[str, Any], rows: list[dict[str, Any]],
    record: Path, stored: str, reason: str,
) -> None:
    """Write one numeric authority and its existing receipt/history projections."""
    direction = state["layer_checkpoints"]["direction"]
    current = state.get("dataset_baseline_roster")
    revision = int((current or {}).get("revision") or 0) + 1
    roster = {
        "direction_id": direction.get("id"),
        "revision": revision,
        "rows": rows,
        "reason": reason,
        "recorded_at": now_iso(),
        "record_path": stored,
        "record_kind": "baseline_roster_receipt",
    }
    roster["payload_sha256"] = baseline_roster_payload_sha256(roster)
    if isinstance(current, dict):
        state.setdefault("dataset_baseline_roster_history", []).append(
            {
                **current,
                "replaced_at": now_iso(),
                "replacement_revision": revision,
                "replacement_reason": reason,
            }
        )
    append_baseline_roster_receipt(record, roster, reason)
    roster["record_sha256_at_receipt"] = sha256_file(record)
    state["dataset_baseline_roster"] = roster
    sync_baseline_roster_to_window(state, roster)
    archive_invalidated_paper_assessment(
        state, "dataset_baseline_roster_change", f"baseline-roster-r{revision}"
    )
    invalidate_checkpoint(
        path, state, "paper", "baseline_roster_change", f"baseline-roster-r{revision}"
    )
    state["phase"] = "confirmed_project"


def cmd_baseline_roster(args: argparse.Namespace) -> None:
    path = Path(args.state)
    state = load_state(path)
    require_execution_active(state, "record the dataset baseline roster")
    if state.get("phase") not in {"confirmed_project", "paper_ready_pending_pi"}:
        raise SystemExit(
            "The dataset baseline roster may be set or revised only in "
            "confirmed_project or paper_ready_pending_pi; an approved handoff must be "
            "revoked by the PI first"
        )
    if not checkpoint_usable(path, state, "direction"):
        raise SystemExit("A usable confirmed L1 direction is required")
    reason = clean_text(args.reason, "--reason")
    record, stored, _ = normalize_project_record(path, args.record)
    if args.rows_file is not None:
        rows_path, _, _ = normalize_project_record(path, args.rows_file)
        raw_rows = rows_path.read_text(encoding="utf-8")
    else:
        raw_rows = args.rows_json
    rows = parse_dataset_baseline_matrix(raw_rows, require_matched=False)
    direction = state["layer_checkpoints"]["direction"]
    adopted = (direction.get("payload") or {}).get("adopted_datasets")
    if not baseline_rows_cover_adopted_datasets(rows, adopted):
        raise SystemExit(
            "The baseline roster must contain exactly one row for every adopted dataset, "
            "with the same primary/supporting roles"
        )
    current = state.get("dataset_baseline_roster")
    if isinstance(current, dict) and (
        current.get("direction_id") == direction.get("id")
        and current.get("rows") == rows
    ):
        raise SystemExit("Dataset baseline roster is already set to these values")
    record_baseline_roster(path, state, rows, record, stored, reason)
    save_state(path, state)
    print(json.dumps(state_summary(path, state), ensure_ascii=False, indent=2))


def cmd_direction_datasets(args: argparse.Namespace) -> None:
    path = Path(args.state)
    state = load_state(path)
    require_execution_active(state, "normalize a legacy adopted-dataset inventory")
    direction = state["layer_checkpoints"].get("direction", {})
    if direction.get("status") != "LEGACY_CONFIRMED_NEEDS_DATASET_INVENTORY":
        raise SystemExit(
            "direction-datasets is only for an unambiguous migrated L1 checkpoint"
        )
    if not args.unambiguous:
        raise SystemExit(
            "Refusing agent-owned normalization without --unambiguous; if dataset "
            "identity or role is uncertain, reconfirm L1 with the PI"
        )
    reason = clean_text(args.reason, "--reason")
    adopted = normalize_adopted_datasets(
        args.primary_dataset, args.supporting_dataset
    )
    record = resolve_stored_path(path, direction.get("record_path"))
    if record is None or not record.is_file() or not stored_path_is_project_local(
        path, direction.get("record_path")
    ):
        raise SystemExit("The migrated L1 durable record is unavailable")
    payload = dict(direction.get("payload") or {})
    payload["adopted_datasets"] = adopted
    source = direction.get("decision_source") or {}
    update_record_placeholders(record, "direction", direction["id"], payload, source)
    with record.open("a", encoding="utf-8", newline="") as handle:
        handle.write(
            "\n\n## Schema-v12 adopted-dataset normalization\n\n"
            f"- Recorded at: {now_iso()}\n"
            f"- Reason this is unambiguous: {reason}\n"
            "- This receipt makes no new L1 choice; uncertainty requires PI reconfirmation.\n"
            "- Adopted datasets:\n\n"
            "```json\n"
            + json.dumps(adopted, ensure_ascii=False, indent=2)
            + "\n```\n"
        )
    direction["payload"] = payload
    direction["summary"] = json.dumps(payload, ensure_ascii=False, sort_keys=True)
    direction["status"] = "CONFIRMED_BY_PI"
    direction["record_sha256_at_confirmation"] = sha256_file(record)
    append_notification(
        state,
        "旧版 L1 的数据集清单已按现有记录补齐，没有更换任务或数据集。"
        f"理由：{reason}",
    )
    ensure_l2_scaffold(path, direction["id"], payload)
    save_state(path, state)
    print(json.dumps(state_summary(path, state), ensure_ascii=False, indent=2))


def cmd_evaluation_anchor(args: argparse.Namespace) -> None:
    path = Path(args.state)
    state = load_state(path)
    require_execution_active(state, "set the evaluation anchor")
    if state.get("phase") != "confirmed_project":
        raise SystemExit(
            "The evaluation anchor may be set or replaced only in confirmed_project; "
            "leave the paper gate before changing it"
        )
    if not checkpoint_usable(path, state, "direction"):
        raise SystemExit("A usable confirmed L1 direction is required")
    if not baseline_roster_usable(state) or not baseline_roster_record_usable(
        path, state
    ):
        raise SystemExit(
            "Set a structured external-baseline roster for every adopted dataset "
            "before locking the evaluation anchor"
        )
    primary_metric = str(args.primary_metric or "").strip()
    reason = str(args.reason or "").strip()
    problem_id = validate_checkpoint_id(args.problem_id)
    method_cluster_id = validate_checkpoint_id(args.method_cluster_id)
    problem_path = normalize_problem_path(
        args.problem_path, active_leaf=problem_id, label="--problem-path"
    )
    falsifiable_prediction = str(args.falsifiable_prediction or "").strip()
    if not primary_metric or not reason or not falsifiable_prediction:
        raise SystemExit(
            "Evaluation anchoring requires a non-empty metric, reason, and falsifiable prediction"
        )
    direction_id = state["layer_checkpoints"]["direction"].get("id")
    current = state.get("evaluation_anchor")
    identity = {
        "direction_id": direction_id,
        "problem_path": problem_path,
        "problem_id": problem_id,
        "method_cluster_id": method_cluster_id,
        "falsifiable_prediction": falsifiable_prediction,
        "primary_metric": primary_metric,
        "metric_scale": args.metric_scale,
        "metric_direction": args.metric_direction,
    }
    if (
        isinstance(current, dict)
        and not current.get("legacy_derived")
        and all(current.get(key) == value for key, value in identity.items())
    ):
        raise SystemExit("Evaluation anchor is already set to these values")
    science = state["layer_checkpoints"].get("science") or {}
    science_payload = science.get("payload") or {}
    legacy_enrichment_match = (
        science.get("status") == "CONFIRMED_BY_PI"
        and science_payload.get("legacy_method_counterfactual_unscoped")
        and science_payload.get("direction_id") == identity["direction_id"]
        and science_payload.get("problem_id") == identity["problem_id"]
        and science_payload.get("method_cluster_id") == identity["method_cluster_id"]
        and science_payload.get("falsifiable_prediction")
        == identity["falsifiable_prediction"]
    )
    if args.legacy_simple_combination_counterfactual is not None and not legacy_enrichment_match:
        raise SystemExit(
            "--legacy-simple-combination-counterfactual is valid only when relocking "
            "the exact migrated L2 leaf, method cluster, and falsifiable prediction"
        )
    if legacy_enrichment_match:
        counterfactual = clean_text(
            args.legacy_simple_combination_counterfactual,
            "--legacy-simple-combination-counterfactual",
        )
        science_payload["problem_path"] = list(problem_path)
        science_payload["simple_combination_counterfactual"] = counterfactual
        science_payload.pop("legacy_method_counterfactual_unscoped", None)
        science["payload"] = science_payload
        science["summary"] = json.dumps(
            science_payload, ensure_ascii=False, sort_keys=True
        )
        record = resolve_stored_path(path, science.get("record_path"))
        if (
            record is None
            or not record.is_file()
            or not stored_path_is_project_local(path, science.get("record_path"))
        ):
            raise SystemExit(
                "Cannot perform agent-owned legacy L2 enrichment because its durable record is unavailable"
            )
        update_record_placeholders(
            record,
            "science",
            str(science.get("id")),
            science_payload,
            science.get("decision_source") or {"decision": "legacy PI decision"},
        )
        with record.open("a", encoding="utf-8", newline="") as handle:
            handle.write(
                "\n\n## Schema-v15 scientific-scope normalization\n\n"
                f"- Recorded at: {now_iso()}\n"
                f"- Active problem path: {' -> '.join(problem_path)}\n"
                "- Existing leaf, method cluster, falsifiable prediction, core mechanism, "
                "contribution type, and innovation claim were not changed.\n"
                f"- Simple-combination counterfactual: {counterfactual}\n"
                "- This was an agent-owned meaning-preserving enrichment; any semantic "
                "change requires the existing scoped PI decision path.\n"
            )
        science["record_sha256_at_confirmation"] = sha256_file(record)
        append_notification(
            state,
            "旧版 L2 已补齐问题路径和‘为什么普通组合解决不了’的说明；"
            "叶子问题、核心方法和创新点均未更换。",
        )
        sync_checkpoint_to_window(state, "science", str(science.get("id")), science_payload)
    revision = 1
    if isinstance(current, dict):
        revision = int(current.get("revision") or 0) + 1
        state.setdefault("evaluation_anchor_history", []).append(
            {
                **current,
                "replaced_at": now_iso(),
                "replacement_reason": reason,
                "replacement_revision": revision,
            }
        )
    elif state.get("evaluation_anchor_history"):
        prior_revisions = [
            int(item.get("revision") or 0)
            for item in state["evaluation_anchor_history"]
            if isinstance(item, dict)
        ]
        revision = max(prior_revisions, default=0) + 1
    state["evaluation_anchor"] = {
        "revision": revision,
        **identity,
        "locked_at": now_iso(),
        "reason": reason,
        "legacy_derived": False,
    }
    scope_changed = isinstance(current, dict) and any(
        current.get(key) != value for key, value in identity.items()
    )
    roster = state["dataset_baseline_roster"]
    if scope_changed and any(row.get("our_score") is not None for row in roster["rows"]):
        # Keep the external target, not a previous mechanism's current score.
        # Existing history retains the old comparison; a rerun or explicit
        # reassessment may register a score with baseline-roster again.
        rows = [dict(row) for row in roster["rows"]]
        for row in rows:
            if row.get("our_score") is not None:
                row["our_score"] = None
                if row["status"] == "MATCHED":
                    row["status"] = "IDENTIFIED"
        record, stored, _ = normalize_project_record(path, roster["record_path"])
        record_baseline_roster(
            path, state, rows, record, stored,
            "Evaluation scope changed: external references retained; previous our_score "
            "requires rerun or explicit reassessment before use with the new anchor. " + reason,
        )
    if research_window_active(state):
        state["research_window"]["revision"] = int(
            state["research_window"].get("revision") or 0
        ) + 1
    archive_invalidated_paper_assessment(
        state, "evaluation_anchor_change", f"evaluation-anchor-r{revision}"
    )
    save_state(path, state)
    print(json.dumps(state_summary(path, state), ensure_ascii=False, indent=2))


def cmd_confirm(args: argparse.Namespace) -> None:
    path = Path(args.state)
    state = load_state(path)
    require_execution_active(state, "confirm a scientific checkpoint")
    args.id = validate_checkpoint_id(args.id)
    reject_irrelevant_checkpoint_fields(args)
    payload = checkpoint_payload(args, path, state)
    source = approving_decision_source(state, args, args.layer)
    record, stored, _ = normalize_project_record(path, args.record)
    previous = state["layer_checkpoints"][args.layer]
    science_problem_changed = False
    science_method_changed = False
    if args.layer == "science" and previous.get("status") == "CONFIRMED_BY_PI":
        previous_payload = previous.get("payload") or {}
        science_problem_changed = (
            previous_payload.get("problem_path") != payload.get("problem_path")
            or previous_payload.get("problem_id") != payload.get("problem_id")
            or previous_payload.get("problem") != payload.get("problem")
        )
        science_method_changed = (
            previous_payload.get("method_cluster_id")
            != payload.get("method_cluster_id")
            or previous_payload.get("core_mechanism")
            != payload.get("core_mechanism")
            or previous_payload.get("falsifiable_prediction")
            != payload.get("falsifiable_prediction")
            or previous_payload.get("simple_combination_counterfactual")
            != payload.get("simple_combination_counterfactual")
            or previous_payload.get("contribution_type")
            != payload.get("contribution_type")
            or previous_payload.get("innovation_claim")
            != payload.get("innovation_claim")
        )
        if (science_problem_changed or science_method_changed) and not nonblank(
            args.change_notification
        ):
            raise SystemExit(
                "Replacing the confirmed L2 problem path, active leaf, or method cluster requires a "
                "plain-language --change-notification for the PI"
            )
    if (
        previous.get("status") == "CONFIRMED_BY_PI"
        and previous.get("id") == args.id
        and previous.get("payload") == payload
    ):
        raise SystemExit(f"Layer is already confirmed to this value: {args.layer}")
    if previous.get("status") != "UNSET" and not str(
        previous.get("status") or ""
    ).startswith("STALE_AFTER_"):
        state["checkpoint_history"].append(
            {
                "layer": args.layer,
                "previous": previous,
                "replacement_id": args.id,
                "decision_source": source,
                "created_at": now_iso(),
            }
        )
    update_record_placeholders(record, args.layer, args.id, payload, source)
    append_checkpoint_receipt(record, args.layer, args.id, payload, source)
    consume_question(
        state,
        args.decision_id,
        {"type": "checkpoint", "layer": args.layer, "id": args.id},
    )
    digest = sha256_file(record)
    if args.layer == "paper":
        assessment = state.get("paper_ready_assessment") or {}
        assessment_path = resolve_stored_path(path, assessment.get("path"))
        if assessment_path is not None and assessment_path.resolve() == record.resolve():
            assessment["sha256_after_handoff"] = digest
    summary = json.dumps(payload, ensure_ascii=False, sort_keys=True)
    state["layer_checkpoints"][args.layer] = {
        "status": "CONFIRMED_BY_PI",
        "id": args.id,
        "summary": summary,
        "payload": payload,
        "confirmed_at": now_iso(),
        "decision_source": source,
        "record_path": stored,
        "record_sha256_at_confirmation": digest,
    }
    if args.layer == "compass":
        previous_payload = previous.get("payload") or {}
        scope_changed = (
            previous.get("status") != "CONFIRMED_BY_PI"
            or previous_payload.get("venue_or_window") != payload["venue_or_window"]
            or previous_payload.get("domain") != payload["domain"]
        )
        if scope_changed:
            invalidate_evaluation_anchor(state, "compass_change", args.id)
            invalidate_baseline_roster(state, "compass_change", args.id)
            for layer in ("direction", "science", "paper"):
                invalidate_checkpoint(path, state, layer, "compass_change", args.id)
            archive_invalidated_paper_assessment(
                state, "compass_change", args.id
            )
            state["phase"] = "exploration"
        elif state["phase"] == "discussion":
            state["phase"] = "exploration"
    elif args.layer == "direction":
        invalidate_evaluation_anchor(state, "direction_change", args.id)
        invalidate_baseline_roster(state, "direction_change", args.id)
        for layer in ("science", "paper"):
            invalidate_checkpoint(path, state, layer, "direction_change", args.id)
        archive_invalidated_paper_assessment(state, "direction_change", args.id)
        state["phase"] = "confirmed_project"
        ensure_l2_scaffold(path, args.id, payload)
    elif args.layer == "science":
        invalidate_checkpoint(path, state, "paper", "science_change", args.id)
        archive_invalidated_paper_assessment(state, "science_change", args.id)
        if science_problem_changed:
            previous_payload = previous.get("payload") or {}
            if previous_payload.get("problem_id") != payload.get("problem_id"):
                append_notification(
                    state,
                    "L2 活跃叶子问题已更换："
                    f"`{previous_payload.get('problem_id')}` → "
                    f"`{payload.get('problem_id')}`。{payload.get('change_notification')}",
                    "problem_switch",
                    from_id=previous_payload.get("problem_id"),
                    to_id=payload.get("problem_id"),
                )
            else:
                append_notification(
                    state,
                    "L2 问题路径已调整，但活跃叶子不变："
                    f"{' -> '.join(previous_payload.get('problem_path') or [])} → "
                    f"{' -> '.join(payload.get('problem_path') or [])}。"
                    f"{payload.get('change_notification')}",
                    "problem_path_change",
                )
        if science_method_changed:
            old_method = (previous.get("payload") or {}).get("method_cluster_id")
            new_method = payload.get("method_cluster_id")
            transition = {"from_id": old_method, "to_id": new_method} if old_method != new_method else {}
            append_notification(
                state,
                f"L2 已确认的方法说明已更新：{payload.get('change_notification')}",
                "method_cluster_switch" if transition else "general",
                **transition,
            )
        state["phase"] = "confirmed_project"
    elif args.layer == "paper":
        state["phase"] = "paper_handoff_approved"
    if args.layer in {"direction", "science"}:
        sync_checkpoint_to_window(state, args.layer, args.id, payload)
    refresh_pause(state)
    save_state(path, state)
    print(json.dumps(state_summary(path, state), ensure_ascii=False, indent=2))


def cmd_phase(args: argparse.Namespace) -> None:
    path = Path(args.state)
    state = load_state(path)
    require_execution_active(state, "advance the workflow phase")
    current = state["phase"]
    target = args.set
    assessment_args_present = bool(args.assessment) or any(
        getattr(args, field) is not None for field in PAPER_ASSESSMENT_CLI_FIELDS
    ) or bool(args.favorable_seed_selection) or any(
        value is not None
        for value in (
            args.seed_risk_decision_id,
            args.seed_risk_pi_decision,
            args.seed_risk_pi_outcome,
        )
    )
    if target != "paper_ready_pending_pi" and assessment_args_present:
        raise SystemExit(
            "Paper-assessment arguments are used only when entering "
            "paper_ready_pending_pi"
        )
    allowed = {
        ("discussion", "exploration"),
        ("exploration", "confirmed_project"),
        ("confirmed_project", "paper_ready_pending_pi"),
        ("paper_ready_pending_pi", "confirmed_project"),
    }
    if (current, target) not in allowed:
        raise SystemExit(f"Illegal phase transition: {current} -> {target}")
    if target == "exploration" and not checkpoint_usable(path, state, "compass"):
        raise SystemExit("Cannot enter exploration before the research compass is confirmed")
    if target == "confirmed_project" and current == "exploration":
        if not checkpoint_usable(path, state, "direction"):
            raise SystemExit("Cannot enter confirmed_project before L1 is confirmed")
    if target == "paper_ready_pending_pi":
        if not (
            checkpoint_usable(path, state, "direction")
            and checkpoint_usable(path, state, "science")
        ):
            raise SystemExit("Cannot enter paper-ready phase before complete L1 and L2 checkpoints")
        if not args.assessment:
            raise SystemExit("Entering paper-ready phase requires --assessment")
        if not evaluation_anchor_usable(state):
            raise SystemExit(
                "Entering paper-ready phase requires an evaluation anchor locked "
                "before broad tuning"
            )
        if not science_matches_evaluation_anchor(state):
            raise SystemExit(
                "Entering paper-ready phase requires the confirmed L2 problem path, "
                "active leaf, method cluster, and falsifiable prediction to match the "
                "current pre-tuning evaluation anchor"
            )
        missing = [
            field
            for field in PAPER_ASSESSMENT_TEXT_FIELDS
            if not isinstance(getattr(args, field), str)
            or not getattr(args, field).strip()
        ]
        missing.extend(
            field
            for field in ("metric_scale", *PAPER_ASSESSMENT_NUMERIC_FIELDS)
            if getattr(args, field) is None
        )
        if missing:
            raise SystemExit(
                "Paper-ready assessment is missing structured fields: "
                + ", ".join(missing)
            )
        direction_payload = state["layer_checkpoints"]["direction"]["payload"]
        science_payload = state["layer_checkpoints"]["science"]["payload"]
        anchor = state["evaluation_anchor"]
        roster = state.get("dataset_baseline_roster") or {}
        if not baseline_roster_usable(
            state, require_matched=True
        ) or not baseline_roster_record_usable(path, state):
            raise SystemExit(
                "Entering paper-ready phase requires a current MATCHED external-baseline "
                "row for every adopted dataset"
            )
        assessment_text = {
            field: str(getattr(args, field)).strip()
            for field in PAPER_ASSESSMENT_TEXT_FIELDS
        }
        dataset_baseline_matrix = roster["rows"]
        if args.dataset_baseline_matrix is not None:
            supplied_matrix = parse_dataset_baseline_matrix(
                args.dataset_baseline_matrix
            )
            if supplied_matrix != dataset_baseline_matrix:
                raise SystemExit(
                    "--dataset-baseline-matrix does not match the current baseline roster; "
                    "update the roster first or omit this compatibility argument"
                )
        if (
            assessment_text["primary_metric"] != anchor["primary_metric"]
            or args.metric_scale != anchor["metric_scale"]
        ):
            raise SystemExit(
                "Paper-ready metric and scale must match the current evaluation "
                "anchor. Replace the anchor first; results from the previous anchor "
                "cannot directly satisfy the paper gate."
            )
        risk_source = None
        if args.favorable_seed_selection:
            risk_source = seed_selection_risk_decision_source(
                state,
                args,
                state["layer_checkpoints"]["science"].get("id"),
                anchor["revision"],
            )
        elif any(
            value is not None
            for value in (
                args.seed_risk_decision_id,
                args.seed_risk_pi_decision,
                args.seed_risk_pi_outcome,
            )
        ):
            raise SystemExit(
                "Seed-risk decision arguments require --favorable-seed-selection"
            )
        minimum_gain = direction_payload["evidence_standard"][
            "minimum_paper_gain_points"
        ]
        improvement_points = calculate_improvement_points(
            args.metric_scale, args.baseline_score, args.our_score
        )
        if improvement_points + 1e-9 < minimum_gain:
            raise SystemExit(
                "Paper-ready gate not met: our primary score improves over the strongest "
                "recent top-conference protocol-matched baseline by "
                f"{improvement_points:.10g} percentage points, below the configured "
                f"{minimum_gain:.10g}-point floor. Continue experiments; do not ask the PI "
                "for a paper decision yet."
            )
        record, stored, _ = normalize_project_record(path, args.assessment)
        assessment_payload = {
            "direction_id": state["layer_checkpoints"]["direction"].get("id"),
            "science_id": state["layer_checkpoints"]["science"].get("id"),
            "current_task": direction_payload["task_type"],
            "dataset": direction_payload["dataset"],
            "adopted_datasets": direction_payload["adopted_datasets"],
            "current_work_problem": science_payload["problem"],
            "problem_path": science_payload["problem_path"],
            "problem_id": science_payload["problem_id"],
            "method_cluster_id": science_payload["method_cluster_id"],
            "innovation": science_payload["innovation_claim"],
            "core_mechanism": science_payload["core_mechanism"],
            "baseline_roster_revision": roster["revision"],
            "baseline_roster_payload_sha256": roster["payload_sha256"],
            "minimum_paper_gain_points": float(minimum_gain),
            "improvement_points": improvement_points,
            "evaluation_anchor_revision": anchor["revision"],
            "metric_direction": anchor["metric_direction"],
            "favorable_seed_selection": bool(args.favorable_seed_selection),
            "science_evidence_at_gate": science_evidence_snapshot(path, state, record),
            **assessment_text,
            "dataset_baseline_matrix": dataset_baseline_matrix,
            "metric_scale": args.metric_scale,
            "baseline_score": args.baseline_score,
            "our_score": args.our_score,
        }
        if not dataset_baseline_matrix_complete(assessment_payload):
            raise SystemExit(
                "The primary dataset-baseline row must exactly match "
                "--primary-comparison-dataset, baseline identity/venue/source/search "
                "scope, primary metric/scale, and the headline baseline/our scores"
            )
        if not paper_assessment_complete(assessment_payload):
            raise SystemExit("Internal paper-ready assessment validation failed")
        append_paper_assessment_receipt(record, assessment_payload)
        assessment_payload_sha256 = paper_assessment_payload_sha256(
            assessment_payload
        )
        state["paper_ready_assessment"] = {
            "path": stored,
            "sha256_at_gate": sha256_file(record),
            "payload_sha256_at_gate": assessment_payload_sha256,
            "recorded_at": now_iso(),
            **assessment_payload,
        }
        if risk_source is not None:
            state["seed_selection_risk_acceptance"] = {
                "accepted": True,
                "science_id": state["layer_checkpoints"]["science"].get("id"),
                "evaluation_anchor_revision": anchor["revision"],
                "decision_source": risk_source,
                "accepted_at": now_iso(),
                "assessment_payload_sha256": assessment_payload_sha256,
            }
            consume_question(
                state,
                args.seed_risk_decision_id,
                {
                    "type": "seed_selection_risk",
                    "science_id": state["layer_checkpoints"]["science"].get("id"),
                    "evaluation_anchor_revision": anchor["revision"],
                },
            )
        else:
            state["seed_selection_risk_acceptance"] = None
    if current == "paper_ready_pending_pi" and target == "confirmed_project":
        archive_invalidated_paper_assessment(
            state, "paper_ready_withdrawn", "confirmed-project-return"
        )
    state["phase"] = target
    save_state(path, state)
    print(json.dumps(state_summary(path, state), ensure_ascii=False, indent=2))


def decision_source_for_freeze(state: dict[str, Any], args: argparse.Namespace) -> dict[str, str]:
    if args.decision_id:
        expected_target = f"frozen:{normalized_frozen_key(args.key)}"
        matches = [
            question
            for question in state.get("macro_questions", [])
            if question.get("id") == args.decision_id
        ]
        if len(matches) == 1:
            recorded_target = str(matches[0].get("decision_target") or "")
            if recorded_target.startswith("frozen:") and normalized_frozen_key(
                recorded_target.split(":", 1)[1]
            ) == normalized_frozen_key(args.key):
                expected_target = recorded_target
        question = current_answered_approval(
            state,
            args.decision_id,
            None,
            expected_target,
            "a frozen-field change",
        )
        return {
            "type": "answered_question",
            "question_id": args.decision_id,
            "decision": str(question["decision"]),
            "outcome": str(question["outcome"]),
        }
    if not str(args.pi_decision or "").strip():
        raise SystemExit("--pi-decision must contain the user's actual decision")
    if args.pi_outcome not in APPROVING_OUTCOMES:
        raise SystemExit("Direct freeze requires --pi-outcome approve or select")
    return {
        "type": "direct_pi_instruction",
        "decision": str(args.pi_decision).strip(),
        "outcome": args.pi_outcome,
    }


def cmd_freeze(args: argparse.Namespace) -> None:
    path = Path(args.state)
    state = load_state(path)
    args.key = resolved_frozen_key(state, args.key)
    args.value = str(args.value).strip()
    if not args.value:
        raise SystemExit("A frozen field requires a non-empty --value")
    if normalized_frozen_key(args.key) in RESERVED_FROZEN_KEYS:
        raise SystemExit(
            "Core compass/L1/L2 fields cannot be duplicated in frozen_by_pi; "
            "update the corresponding checkpoint instead"
        )
    source = decision_source_for_freeze(state, args)
    previous = state["frozen_by_pi"].get(args.key)
    if previous is not None and previous.get("value") == args.value:
        raise SystemExit(f"Field is already frozen to this value: {args.key}")
    if previous is not None:
        state["frozen_history"].append(
            {
                "action": "replaced",
                "key": args.key,
                "previous": previous,
                "new_value": args.value,
                "decision_source": source,
                "created_at": now_iso(),
            }
        )
    state["frozen_by_pi"][args.key] = {
        "value": args.value,
        "frozen_at": now_iso(),
        "decision_source": source,
    }
    consume_question(
        state,
        args.decision_id,
        {"type": "frozen_field", "key": args.key, "action": "freeze"},
    )
    save_state(path, state)
    print(json.dumps(state_summary(path, state), ensure_ascii=False, indent=2))


def cmd_unfreeze(args: argparse.Namespace) -> None:
    path = Path(args.state)
    state = load_state(path)
    args.key = resolved_frozen_key(state, args.key)
    if args.key not in state["frozen_by_pi"]:
        raise SystemExit(f"Frozen key not found: {args.key}")
    source = decision_source_for_freeze(state, args)
    previous = state["frozen_by_pi"][args.key]
    state["frozen_history"].append(
        {
            "action": "unfrozen",
            "key": args.key,
            "previous": previous,
            "decision_source": source,
            "created_at": now_iso(),
        }
    )
    del state["frozen_by_pi"][args.key]
    consume_question(
        state,
        args.decision_id,
        {"type": "frozen_field", "key": args.key, "action": "unfreeze"},
    )
    save_state(path, state)
    print(json.dumps(state_summary(path, state), ensure_ascii=False, indent=2))


def cmd_job_add(args: argparse.Namespace) -> None:
    path = Path(args.state)
    state = load_state(path)
    require_execution_active(state, "add an active job")
    job_id = str(args.id).strip()
    description = str(args.description).strip()
    if not job_id:
        raise SystemExit("A job requires non-empty --id")
    if not description:
        raise SystemExit("A job requires non-empty --description")
    if any(job.get("id") == job_id for job in state["jobs"]):
        raise SystemExit(f"Job already exists: {job_id}")
    if args.status in ACTIVE_JOB_STATUSES and state.get("phase") == "discussion":
        raise SystemExit(
            "Cannot register active execution in discussion; confirm the research compass first"
        )
    command = clean_text(args.command, "--command", optional=True)
    session = clean_text(args.session, "--session", optional=True)
    next_poll = clean_text(args.next_poll, "--next-poll", optional=True)
    next_action = clean_text(args.next_action, "--next-action", optional=True)
    if args.status in ACTIVE_JOB_STATUSES and not (command or session):
        raise SystemExit("An active job requires --command or --session")
    if args.status in ACTIVE_JOB_STATUSES and not next_poll:
        raise SystemExit("An active job requires --next-poll at a meaningful check time")
    if args.status in ACTIVE_JOB_STATUSES and not next_action:
        raise SystemExit("An active job requires a non-empty --next-action")
    job = {
        "id": job_id,
        "description": description,
        "command": command,
        "session": session,
        "status": args.status,
        "next_poll": next_poll,
        "next_action": next_action,
        "result": None,
        "created_at": now_iso(),
        "updated_at": now_iso(),
    }
    state["jobs"].append(job)
    save_state(path, state)
    print(json.dumps({"added": job, "state": state_summary(path, state)}, ensure_ascii=False, indent=2))


def cmd_job_update(args: argparse.Namespace) -> None:
    path = Path(args.state)
    state = load_state(path)
    job_id = clean_text(args.id, "--id")
    matches = [job for job in state["jobs"] if job.get("id") == job_id]
    if not matches:
        raise SystemExit(f"Job not found: {job_id}")
    job = matches[0]
    new_status = args.status or job.get("status")
    refresh_pause(state)
    if state["status"] != "ACTIVE" and new_status in ACTIVE_JOB_STATUSES:
        raise SystemExit(
            f"Cannot continue, poll, or advance an active job while {state['status']}; "
            "only record a safe terminal status"
        )
    for field in ("status", "session", "next_poll", "next_action", "result"):
        value = getattr(args, field)
        if value is not None:
            job[field] = (
                str(value).strip()
                if field in {"session", "next_poll", "next_action", "result"}
                else value
            )
    if job.get("status") in ACTIVE_JOB_STATUSES and not (
        nonblank(job.get("command")) or nonblank(job.get("session"))
    ):
        raise SystemExit("An active job requires a command or session identifier")
    if job.get("status") in ACTIVE_JOB_STATUSES and not str(
        job.get("next_poll") or ""
    ).strip():
        raise SystemExit("An active job requires a meaningful next check time")
    if job.get("status") in ACTIVE_JOB_STATUSES and not str(
        job.get("next_action") or ""
    ).strip():
        raise SystemExit("An active job requires a resumable next action")
    if job.get("status") not in ACTIVE_JOB_STATUSES:
        (state.get("monitoring") or {}).get(
            "artifact_fingerprints_by_job", {}
        ).pop(job_id, None)
    job["updated_at"] = now_iso()
    save_state(path, state)
    print(json.dumps({"updated": job, "state": state_summary(path, state)}, ensure_ascii=False, indent=2))


def cmd_job_remove(args: argparse.Namespace) -> None:
    path = Path(args.state)
    state = load_state(path)
    job_id = clean_text(args.id, "--id")
    matches = [job for job in state["jobs"] if job.get("id") == job_id]
    if not matches:
        raise SystemExit(f"Job not found: {job_id}")
    job = matches[0]
    refresh_pause(state)
    if state["status"] != "ACTIVE" and job.get("status") in ACTIVE_JOB_STATUSES:
        raise SystemExit(
            f"Cannot remove tracking for an active job while {state['status']}; "
            "record its safe terminal status first"
        )
    if job.get("status") in ACTIVE_JOB_STATUSES and not args.force:
        raise SystemExit("Refusing to remove an active job without --force")
    state["jobs"] = [item for item in state["jobs"] if item.get("id") != job_id]
    (state.get("monitoring") or {}).get("artifact_fingerprints_by_job", {}).pop(
        job_id, None
    )
    save_state(path, state)
    print(json.dumps({"removed": job, "state": state_summary(path, state)}, ensure_ascii=False, indent=2))


def add_decision_source_args(parser: argparse.ArgumentParser) -> None:
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--decision-id")
    source.add_argument("--pi-decision")
    parser.add_argument("--pi-outcome", choices=sorted(APPROVING_OUTCOMES))


def add_optional_decision_source_args(parser: argparse.ArgumentParser) -> None:
    source = parser.add_mutually_exclusive_group()
    source.add_argument("--decision-id")
    source.add_argument("--pi-decision")
    parser.add_argument("--pi-outcome", choices=sorted(APPROVING_OUTCOMES))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    init_parser = subparsers.add_parser("init", help="Create state and L1/L2 scaffolds")
    init_parser.add_argument("state")
    init_parser.add_argument("--project", required=True)
    init_parser.add_argument(
        "--phase", default="discussion", choices=["discussion", "exploration"]
    )
    init_parser.add_argument("--venue-or-window")
    init_parser.add_argument("--domain")
    init_parser.add_argument("--starting-concept")
    init_parser.add_argument("--pi-decision")
    init_parser.add_argument("--pi-outcome", choices=sorted(APPROVING_OUTCOMES))
    init_parser.set_defaults(func=cmd_init)

    status_parser = subparsers.add_parser("status", help="Show workflow state and control issues")
    status_parser.add_argument("state")
    status_mode = status_parser.add_mutually_exclusive_group()
    status_mode.add_argument(
        "--compact",
        action="store_true",
        help="Show only wakeup-critical state, hashes, jobs, and issue codes",
    )
    status_mode.add_argument(
        "--window",
        action="store_true",
        help="Show the macro-only L1/L2 changes since the latest explicit PI run instruction",
    )
    status_parser.set_defaults(func=cmd_status)

    window_start_parser = subparsers.add_parser(
        "window-start",
        help="Replace the current reporting window after an explicit PI start/continue instruction",
    )
    window_start_parser.add_argument("state")
    window_start_parser.add_argument(
        "--instruction",
        required=True,
        help="Concise faithful summary of the PI instruction that started this execution window",
    )
    window_start_parser.set_defaults(func=cmd_window_start)

    window_note_parser = subparsers.add_parser(
        "research-update",
        aliases=["window-note"],
        help="Update a durable research note and its progress view (window-note is projection-only)",
    )
    window_note_parser.add_argument("state")
    window_note_parser.add_argument("--layer", required=True, choices=sorted(WINDOW_CARD_KINDS_BY_LAYER))
    window_note_parser.add_argument(
        "--kind",
        required=True,
        choices=sorted(set().union(*WINDOW_CARD_KINDS_BY_LAYER.values())),
    )
    window_note_parser.add_argument("--subject-id", required=True)
    window_note_parser.add_argument("--title", required=True)
    window_note_parser.add_argument("--status", required=True, choices=sorted(WINDOW_CARD_STATUSES))
    window_note_parser.add_argument("--verified-observation", "--observation", required=True)
    window_note_parser.add_argument("--interpretation", required=True)
    window_note_parser.add_argument("--external-baseline-gap", help="Additional comparison note; research-update still uses the external roster as its reference")
    window_note_parser.add_argument("--clear-field", action="append", choices=RESEARCH_OPTIONAL_FIELDS,
                                    help="research-update: explicitly clear an invalid/superseded optional field")
    window_note_parser.add_argument("--record", help="research-update: existing project-local L1/L2 record; defaults to the active layer record")
    window_note_parser.add_argument("--notify-kind", choices=sorted(WINDOW_MACRO_NOTIFICATION_KINDS))
    window_note_parser.add_argument("--notification", help="Optional notification; defaults to interpretation")
    window_note_parser.add_argument("--from-id", help="Previous identity when notifying a problem/method switch")
    window_note_parser.add_argument("--next-action", required=True)
    window_note_parser.add_argument("--starting-result")
    window_note_parser.add_argument("--best-result")
    window_note_parser.add_argument("--latest-result")
    window_note_parser.add_argument("--disposition-reason")
    window_note_parser.add_argument(
        "--problem-path",
        action="append",
        help="Ordered unresolved problem ID; repeat from broadest retained node to the active leaf",
    )
    window_note_parser.add_argument("--set-current", action="store_true")
    window_note_parser.add_argument("--hypothesis")
    window_note_parser.add_argument("--current-action")
    window_note_parser.add_argument("--focus-latest-result")
    window_note_parser.set_defaults(func=cmd_window_note)

    monitor_ack_parser = subparsers.add_parser(
        "monitor-ack",
        help="Persist the semantic state and optional artifact fingerprint already processed",
    )
    monitor_ack_parser.add_argument("state")
    monitor_ack_parser.add_argument("--wakeup-fingerprint", required=True)
    monitor_ack_parser.add_argument("--job-id")
    monitor_artifact = monitor_ack_parser.add_mutually_exclusive_group()
    monitor_artifact.add_argument(
        "--artifact-fingerprint",
        help="Project-specific job/result fingerprint processed in this wakeup",
    )
    monitor_artifact.add_argument(
        "--clear-artifact-fingerprint",
        action="store_true",
        help="Explicitly clear the saved artifact fingerprint for --job-id",
    )
    monitor_ack_parser.set_defaults(func=cmd_monitor_ack)

    audit_parser = subparsers.add_parser("audit", help="Fail when workflow control issues exist")
    audit_parser.add_argument("state")
    audit_parser.set_defaults(func=cmd_audit)

    pause_parser = subparsers.add_parser(
        "pause", help="Record a direct PI instruction to pause all workflow execution"
    )
    pause_parser.add_argument("state")
    pause_parser.add_argument("--pi-decision", required=True)
    pause_parser.add_argument("--reason")
    pause_parser.set_defaults(func=cmd_pause)

    resume_parser = subparsers.add_parser(
        "resume", help="Record a direct PI instruction to resume a manual pause"
    )
    resume_parser.add_argument("state")
    resume_parser.add_argument("--pi-decision", required=True)
    resume_parser.add_argument("--reason")
    resume_parser.set_defaults(func=cmd_resume)

    paper_revoke_parser = subparsers.add_parser(
        "paper-revoke",
        help="Revoke an approved paper handoff while retaining the active L1/L2 story",
    )
    paper_revoke_parser.add_argument("state")
    paper_revoke_parser.add_argument("--pi-decision", required=True)
    paper_revoke_parser.add_argument("--reason", required=True)
    paper_revoke_parser.set_defaults(func=cmd_paper_revoke)

    question_parser = subparsers.add_parser("question", help="Add a PI decision question")
    question_parser.add_argument("state")
    question_parser.add_argument("--text", required=True)
    question_parser.add_argument("--target", required=True)
    question_parser.add_argument("--layer", choices=sorted(QUESTION_LAYERS), default="other")
    question_parser.add_argument("--priority", choices=sorted(PRIORITY_ORDER), default="medium")
    question_parser.add_argument("--reason", default="")
    question_parser.add_argument("--recommendation", default="")
    question_parser.add_argument("--continue-plan", default="")
    question_parser.set_defaults(func=cmd_question)

    answer_parser = subparsers.add_parser("answer", help="Record a typed PI decision")
    answer_parser.add_argument("state")
    answer_parser.add_argument("--id", required=True)
    answer_parser.add_argument("--decision", required=True)
    answer_parser.add_argument("--outcome", required=True, choices=sorted(DECISION_OUTCOMES))
    answer_parser.add_argument("--revisit-condition")
    answer_parser.set_defaults(func=cmd_answer)

    reopen_parser = subparsers.add_parser(
        "reopen", help="Move a deferred PI decision back to the active queue"
    )
    reopen_parser.add_argument("state")
    reopen_parser.add_argument("--id", required=True)
    reopen_parser.add_argument("--reason", default="")
    reopen_parser.set_defaults(func=cmd_reopen)

    notify_parser = subparsers.add_parser("notify", help="Record a recent non-blocking notification")
    notify_parser.add_argument("state")
    notify_parser.add_argument("--text", required=True)
    notify_parser.add_argument(
        "--kind", choices=sorted(NOTIFICATION_KINDS), default="general"
    )
    notify_parser.add_argument(
        "--from-id",
        help="Previous problem or method-cluster ID for a scientific switch",
    )
    notify_parser.add_argument(
        "--to-id",
        help="New problem or method-cluster ID for a scientific switch",
    )
    notify_parser.set_defaults(func=cmd_notify)

    compact_parser = subparsers.add_parser(
        "compact-notifications", help="Keep only the most recent notification records"
    )
    compact_parser.add_argument("state")
    compact_parser.add_argument("--keep", type=int, default=RECENT_NOTIFICATION_LIMIT)
    compact_parser.set_defaults(func=cmd_compact_notifications)

    agents_audit_parser = subparsers.add_parser(
        "agents-audit",
        help="Compare one project-local AGENTS scope or bootstrap its first snapshot",
    )
    agents_audit_parser.add_argument("state")
    agents_audit_parser.add_argument(
        "--cwd", help="Project subdirectory whose effective instruction chain should be audited"
    )
    agents_audit_parser.add_argument(
        "--fallback-name",
        action="append",
        default=[],
        help="Configured project_doc_fallback_filenames entry; repeat in precedence order",
    )
    agents_audit_parser.set_defaults(func=cmd_agents_audit)

    agents_scope_remove_parser = subparsers.add_parser(
        "agents-scope-remove",
        help="Remove one saved AGENTS audit scope with appropriate authority",
    )
    agents_scope_remove_parser.add_argument("state")
    agents_scope_remove_parser.add_argument(
        "--cwd", help="Recorded project subdirectory scope to remove"
    )
    agents_scope_remove_parser.add_argument(
        "--fallback-name",
        action="append",
        default=[],
        help="Fallback basename set used by the recorded scope; repeat in precedence order",
    )
    agents_scope_remove_parser.add_argument("--reason", required=True)
    agents_scope_remove_parser.add_argument(
        "--summary", required=True, help="Plain-language notification for the user"
    )
    add_optional_decision_source_args(agents_scope_remove_parser)
    agents_scope_remove_parser.set_defaults(func=cmd_agents_scope_remove)

    agents_record_parser = subparsers.add_parser(
        "agents-record",
        help="Record one audited AGENTS instruction-file update",
    )
    agents_record_parser.add_argument("state")
    agents_record_parser.add_argument("--path", required=True)
    agents_record_parser.add_argument(
        "--kind", required=True, choices=sorted(INSTRUCTION_CHANGE_KINDS)
    )
    agents_record_parser.add_argument("--reason", required=True)
    agents_record_parser.add_argument(
        "--summary", required=True, help="Plain-language notification for the user"
    )
    agents_record_parser.add_argument(
        "--before-absent",
        action="store_true",
        help="Declare that this file did not exist in the immediately preceding audit",
    )
    agents_record_parser.add_argument(
        "--after-absent",
        action="store_true",
        help="Declare and record that an audited instruction file was deleted",
    )
    agents_record_parser.add_argument(
        "--canonical-source",
        action="append",
        default=[],
        help="File retaining detail removed by compaction; repeat when needed",
    )
    add_optional_decision_source_args(agents_record_parser)
    agents_record_parser.set_defaults(func=cmd_agents_record)

    phase_parser = subparsers.add_parser("phase", help="Apply a legal workflow transition")
    phase_parser.add_argument("state")
    phase_parser.add_argument("--set", required=True, choices=sorted(VALID_PHASES))
    phase_parser.add_argument("--assessment")
    phase_parser.add_argument("--competitive-bar-assessment")
    phase_parser.add_argument("--novelty-assessment")
    phase_parser.add_argument("--generalization-assessment")
    phase_parser.add_argument("--paper-ready-threshold-assessment")
    phase_parser.add_argument("--narrowest-supported-claim")
    phase_parser.add_argument("--strongest-matched-comparison")
    phase_parser.add_argument("--remaining-objection")
    phase_parser.add_argument("--necessary-work")
    phase_parser.add_argument("--optional-work")
    phase_parser.add_argument(
        "--specific-method", help="Concrete implementation of the confirmed mechanism"
    )
    phase_parser.add_argument(
        "--final-results", help="Plain-language final decision-relevant result summary"
    )
    phase_parser.add_argument(
        "--primary-comparison-dataset",
        help="Dataset whose matched row supplies the headline numeric paper gate",
    )
    phase_parser.add_argument(
        "--dataset-baseline-matrix",
        help=(
            "JSON array with one MATCHED recent top-conference external-baseline row "
            "for every adopted dataset"
        ),
    )
    phase_parser.add_argument(
        "--recent-top-conference-baseline",
        help="Identity of the strongest recent top-conference matched baseline found",
    )
    phase_parser.add_argument(
        "--baseline-venue-year", help="Venue and year for that baseline"
    )
    phase_parser.add_argument(
        "--baseline-search-scope",
        help="Venues, year range, and search date supporting the strongest-baseline claim",
    )
    phase_parser.add_argument(
        "--baseline-source", help="Primary paper or official source for the baseline"
    )
    phase_parser.add_argument(
        "--protocol-match-evidence",
        help="Why task, data/split, labels, inference information, metric, and evaluation match",
    )
    phase_parser.add_argument(
        "--evaluation-anchor-evidence",
        help="Evidence that the scored result was produced or reassessed under the current metric anchor",
    )
    phase_parser.add_argument(
        "--stability-evidence",
        help="Project-appropriate repeat, uncertainty, or stability evidence; no universal seed count is imposed",
    )
    phase_parser.add_argument(
        "--primary-metric", help="Higher-is-better primary metric used for the hard gate"
    )
    phase_parser.add_argument(
        "--metric-scale",
        choices=("unit_interval", "percentage"),
        help="Use unit_interval for 0-1 scores or percentage for 0-100 scores",
    )
    phase_parser.add_argument(
        "--baseline-score", type=float, help="Matched baseline score on the primary metric"
    )
    phase_parser.add_argument(
        "--our-score", type=float, help="Our score on the same primary metric and protocol"
    )
    phase_parser.add_argument(
        "--favorable-seed-selection",
        action="store_true",
        help="Declare use of favorably selected seeds; requires a scoped PI risk acceptance",
    )
    seed_risk_source = phase_parser.add_mutually_exclusive_group()
    seed_risk_source.add_argument("--seed-risk-decision-id")
    seed_risk_source.add_argument(
        "--seed-risk-pi-decision",
        help="Concise direct PI acceptance; detailed disclosure stays in the user conversation",
    )
    phase_parser.add_argument(
        "--seed-risk-pi-outcome", choices=sorted(APPROVING_OUTCOMES)
    )
    phase_parser.set_defaults(func=cmd_phase)

    evaluation_parser = subparsers.add_parser(
        "evaluation-anchor",
        help="Lock or replace the agent-owned scientific scope and primary metric before broad tuning",
    )
    evaluation_parser.add_argument("state")
    evaluation_parser.add_argument(
        "--problem-path",
        action="append",
        required=True,
        help="Ordered unresolved problem ID; repeat from broadest retained node to the active leaf",
    )
    evaluation_parser.add_argument("--problem-id", required=True)
    evaluation_parser.add_argument("--method-cluster-id", required=True)
    evaluation_parser.add_argument("--falsifiable-prediction", required=True)
    evaluation_parser.add_argument("--primary-metric", required=True)
    evaluation_parser.add_argument(
        "--metric-scale",
        required=True,
        choices=("unit_interval", "percentage"),
    )
    evaluation_parser.add_argument(
        "--metric-direction",
        required=True,
        choices=sorted(METRIC_DIRECTIONS),
    )
    evaluation_parser.add_argument(
        "--reason",
        required=True,
        help="Why this metric definition is appropriate before broad tuning",
    )
    evaluation_parser.add_argument(
        "--legacy-simple-combination-counterfactual",
        help="Meaning-preserving v14 L2 enrichment used only when relocking the exact migrated leaf, method, and prediction",
    )
    evaluation_parser.set_defaults(func=cmd_evaluation_anchor)

    baseline_roster_parser = subparsers.add_parser(
        "baseline-roster",
        help="Maintain one external-baseline row for every adopted dataset",
    )
    baseline_roster_parser.add_argument("state")
    baseline_rows = baseline_roster_parser.add_mutually_exclusive_group(required=True)
    baseline_rows.add_argument(
        "--rows-json",
        help=(
            "JSON array with one row per adopted dataset, typed protocol_status, "
            "and exact comparison_roles coverage"
        ),
    )
    baseline_rows.add_argument(
        "--rows-file", help="Project-local UTF-8 JSON file containing the roster rows"
    )
    baseline_roster_parser.add_argument(
        "--record", required=True, help="Project-local durable L2 record to append"
    )
    baseline_roster_parser.add_argument("--reason", required=True)
    baseline_roster_parser.set_defaults(func=cmd_baseline_roster)

    direction_datasets_parser = subparsers.add_parser(
        "direction-datasets",
        help="Normalize an unambiguous migrated L1 adopted-dataset inventory",
    )
    direction_datasets_parser.add_argument("state")
    direction_datasets_parser.add_argument("--primary-dataset", required=True)
    direction_datasets_parser.add_argument(
        "--supporting-dataset", action="append"
    )
    direction_datasets_parser.add_argument("--reason", required=True)
    direction_datasets_parser.add_argument(
        "--unambiguous", action="store_true"
    )
    direction_datasets_parser.set_defaults(func=cmd_direction_datasets)

    confirm_parser = subparsers.add_parser(
        "confirm", help="Record a typed user-confirmed checkpoint"
    )
    confirm_parser.add_argument("state")
    confirm_parser.add_argument("--layer", required=True, choices=CHECKPOINT_LAYERS)
    confirm_parser.add_argument("--id", required=True)
    confirm_parser.add_argument("--record", required=True)
    add_decision_source_args(confirm_parser)
    confirm_parser.add_argument("--venue-or-window")
    confirm_parser.add_argument("--domain")
    concept_group = confirm_parser.add_mutually_exclusive_group()
    concept_group.add_argument("--starting-concept")
    concept_group.add_argument(
        "--clear-starting-concept",
        action="store_true",
        help="Explicitly clear the current optional starting concept",
    )
    confirm_parser.add_argument("--task-type")
    confirm_parser.add_argument("--dataset")
    confirm_parser.add_argument("--primary-dataset")
    confirm_parser.add_argument(
        "--supporting-dataset",
        action="append",
        help="Adopted supporting dataset; repeat for each dataset",
    )
    confirm_parser.add_argument("--unexposed-dataset-search")
    confirm_parser.add_argument("--competitive-bar")
    confirm_parser.add_argument("--novelty-sufficiency")
    confirm_parser.add_argument("--generalization-requirement")
    confirm_parser.add_argument(
        "--paper-ready-threshold",
        help="Additional paper-ready requirements; cannot lower the numeric gain floor",
    )
    confirm_parser.add_argument(
        "--minimum-paper-gain-points",
        type=float,
        help="Numeric project paper-ready gain floor in percentage points; defaults to 1 and cannot be lower",
    )
    confirm_parser.add_argument("--direction-id")
    confirm_parser.add_argument(
        "--problem-path",
        action="append",
        help="Ordered unresolved problem ID; repeat from broadest retained node to the active leaf",
    )
    confirm_parser.add_argument("--problem-id")
    confirm_parser.add_argument("--method-cluster-id")
    confirm_parser.add_argument("--problem")
    confirm_parser.add_argument("--nearest-work-gap")
    confirm_parser.add_argument("--paper-grade-rationale")
    confirm_parser.add_argument("--core-mechanism")
    confirm_parser.add_argument("--falsifiable-prediction")
    confirm_parser.add_argument("--alternative-explanation", "--simple-combination-counterfactual", dest="simple_combination_counterfactual", help="Why the nearest relevant simpler alternative does not explain/solve the problem; legacy field retained")
    confirm_parser.add_argument(
        "--contribution-type", choices=sorted(PAPER_GRADE_CONTRIBUTION_TYPES)
    )
    confirm_parser.add_argument("--innovation-claim")
    confirm_parser.add_argument(
        "--external-baseline-status",
        help="Per-dataset external-baseline coverage, protocol match, and blockers",
    )
    confirm_parser.add_argument("--ceiling-summary")
    confirm_parser.add_argument("--problem-portfolio-record")
    confirm_parser.add_argument("--nearest-work-record")
    confirm_parser.add_argument("--baseline-record")
    confirm_parser.add_argument("--result-record")
    confirm_parser.add_argument(
        "--change-notification",
        help="Plain-language PI notification when replacing a confirmed problem or method cluster",
    )
    confirm_parser.add_argument("--science-id")
    confirm_parser.add_argument("--headline-claim")
    confirm_parser.add_argument("--handoff-target")
    confirm_parser.set_defaults(func=cmd_confirm)

    freeze_parser = subparsers.add_parser("freeze", help="Freeze a user-confirmed field")
    freeze_parser.add_argument("state")
    freeze_parser.add_argument("--key", required=True)
    freeze_parser.add_argument("--value", required=True)
    add_decision_source_args(freeze_parser)
    freeze_parser.set_defaults(func=cmd_freeze)

    unfreeze_parser = subparsers.add_parser("unfreeze", help="Remove a frozen field")
    unfreeze_parser.add_argument("state")
    unfreeze_parser.add_argument("--key", required=True)
    add_decision_source_args(unfreeze_parser)
    unfreeze_parser.set_defaults(func=cmd_unfreeze)

    job_add = subparsers.add_parser("job-add", help="Register a resumable active job")
    job_add.add_argument("state")
    job_add.add_argument("--id", required=True)
    job_add.add_argument("--description", required=True)
    job_add.add_argument("--command")
    job_add.add_argument("--session")
    job_add.add_argument("--status", choices=sorted(JOB_STATUSES), default="queued")
    job_add.add_argument("--next-poll")
    job_add.add_argument("--next-action", default="")
    job_add.set_defaults(func=cmd_job_add)

    job_update = subparsers.add_parser("job-update", help="Update a resumable job")
    job_update.add_argument("state")
    job_update.add_argument("--id", required=True)
    job_update.add_argument("--status", choices=sorted(JOB_STATUSES))
    job_update.add_argument("--session")
    job_update.add_argument("--next-poll")
    job_update.add_argument("--next-action")
    job_update.add_argument("--result")
    job_update.set_defaults(func=cmd_job_update)

    job_remove = subparsers.add_parser("job-remove", help="Remove an unneeded job record")
    job_remove.add_argument("state")
    job_remove.add_argument("--id", required=True)
    job_remove.add_argument("--force", action="store_true")
    job_remove.set_defaults(func=cmd_job_remove)

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    state_path = Path(args.state)
    if args.command in {"status", "audit"} or (
        args.command != "init" and not state_path.exists()
    ):
        args.func(args)
    else:
        with state_file_lock(state_path):
            args.func(args)
    return 0


if __name__ == "__main__":
    sys.exit(main())
