#!/usr/bin/env python3
"""Control durable PI decisions and resumable work for research-paper-workflow.

The controller enforces typed approvals, ordered scientific checkpoints, the
five-question pause, lightweight active-job recovery, and project-state audits.
It records authority; it does not create authority, schedule itself, or kill
processes.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


SCHEMA_VERSION = 4
SUPPORTED_SCHEMA_VERSIONS = {1, 2, 3, 4}
MAX_MACRO_QUESTIONS = 5
RECENT_NOTIFICATION_LIMIT = 50
PRIORITY_ORDER = {"high": 0, "medium": 1, "low": 2}
QUESTION_LAYERS = {
    "compass",
    "direction",
    "science",
    "paper",
    "resource",
    "external",
    "other",
}
CHECKPOINT_LAYERS = ("compass", "direction", "science", "paper")
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


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


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


def initial_state(project: str) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "project": project,
        "phase": "discussion",
        "status": "ACTIVE",
        "paused_for_pi": False,
        "frozen_by_pi": {},
        "frozen_history": [],
        "layer_checkpoints": {
            layer: empty_checkpoint() for layer in CHECKPOINT_LAYERS
        },
        "checkpoint_history": [],
        "paper_ready_assessment": None,
        "macro_questions": [],
        "notifications": [],
        "notification_compacted_count": 0,
        "notification_sequence": 0,
        "notification_policy": {
            "mode": "recent_only",
            "recent_limit": RECENT_NOTIFICATION_LIMIT,
        },
        "jobs": [],
        "created_at": now_iso(),
        "updated_at": now_iso(),
    }


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
        "macro_questions": list,
        "notifications": list,
        "jobs": list,
    }
    for key, expected_type in required_types.items():
        if not isinstance(state.get(key), expected_type):
            raise SystemExit(
                f"Invalid state field {key!r}: expected {expected_type.__name__}"
            )
    for layer in CHECKPOINT_LAYERS:
        checkpoint = state["layer_checkpoints"].get(layer)
        if not isinstance(checkpoint, dict):
            raise SystemExit(f"Invalid or missing layer checkpoint: {layer}")
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


def normalize_record(path: Path, raw: str) -> tuple[Path, str, str]:
    record = Path(raw).expanduser()
    if not record.is_absolute():
        record = Path.cwd() / record
    record = record.resolve()
    if not record.is_file():
        raise SystemExit(f"Checkpoint record does not exist: {record}")
    project_root = project_root_for_state(path)
    try:
        stored = record.relative_to(project_root).as_posix()
    except ValueError:
        stored = str(record)
    return record, stored, sha256_file(record)


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


def update_record_placeholders(
    record: Path,
    layer: str,
    checkpoint_id: str,
    payload: dict[str, Any],
    source: dict[str, str],
) -> None:
    text = record.read_text(encoding="utf-8")
    if layer == "compass":
        text = text.replace(
            "- Venue or submission window: UNSET",
            f"- Venue or submission window: {payload['venue_or_window']}",
            1,
        )
        text = text.replace("- Domain: UNSET", f"- Domain: {payload['domain']}", 1)
        text = text.replace(
            "- Optional starting concept: UNSET",
            f"- Optional starting concept: {payload['starting_concept']}",
            1,
        )
    elif layer == "direction":
        standard = payload["evidence_standard"]
        replacements = {
            "- Competitive bar: UNSET": f"- Competitive bar: {standard['competitive_bar']}",
            "- Novelty sufficiency: UNSET": f"- Novelty sufficiency: {standard['novelty_sufficiency']}",
            "- Generalization or second-dataset requirement: UNSET": (
                "- Generalization or second-dataset requirement: "
                f"{standard['generalization_requirement']}"
            ),
            "- Paper-ready threshold: UNSET": (
                f"- Paper-ready threshold: {standard['paper_ready_threshold']}"
            ),
            "## Current PI decision\n\nUNSET": (
                "## Current PI decision\n\n"
                f"`{checkpoint_id}`: {source['decision']}"
            ),
        }
        for old, new in replacements.items():
            text = text.replace(old, new, 1)
    elif layer == "science":
        text = text.replace(
            "L2 status: `MAPPING_NEAREST_WORK`",
            "L2 status: `ACTIVE_PI_CONFIRMED`",
            1,
        )
        text = text.replace(
            "Active problem + method decision source: UNSET",
            f"Active problem + method decision source: {source['decision']}",
            1,
        )
    record.write_text(text, encoding="utf-8")


def resolve_stored_path(state_path: Path, raw: str | None) -> Path | None:
    if not raw:
        return None
    candidate = Path(raw)
    if candidate.is_absolute():
        return candidate
    return project_root_for_state(state_path) / candidate


def ensure_scaffold(state_path: Path, project: str) -> None:
    research_root = research_root_for_state(state_path)
    l2_root = research_root / "L2"
    l2_root.mkdir(parents=True, exist_ok=True)
    l1_path = research_root / "L1-directions.md"
    if not l1_path.exists():
        l1_path.write_text(
            "# Research direction portfolio\n\n"
            f"Project: {project}\n\n"
            "## Research compass\n\n"
            "- Venue or submission window: UNSET\n"
            "- Domain: UNSET\n"
            "- Optional starting concept: UNSET\n\n"
            "## Project evidence standard\n\n"
            "- Competitive bar: UNSET\n"
            "- Novelty sufficiency: UNSET\n"
            "- Generalization or second-dataset requirement: UNSET\n"
            "- Paper-ready threshold: UNSET\n\n"
            "## Ranked directions\n\n"
            "| ID | status | task type | dataset | why meaningful | task-data fit | headroom | nearest-work risk | baseline feasibility | cost/time | next action |\n"
            "|---|---|---|---|---|---|---|---|---|---|---|\n\n"
            "## Current PI decision\n\n"
            "UNSET\n",
            encoding="utf-8",
        )


def ensure_l2_scaffold(state_path: Path, direction_id: str, payload: dict[str, Any]) -> Path:
    l2_path = research_root_for_state(state_path) / "L2" / f"{direction_id}.md"
    if not l2_path.exists():
        l2_path.write_text(
            f"# {direction_id} scientific story\n\n"
            f"Direction ID: `{direction_id}`  \n"
            f"L1 task and dataset: {payload['task_type']} | {payload['dataset']}  \n"
            "L1 confirmation source: see workflow state  \n"
            "L2 status: `MAPPING_NEAREST_WORK`  \n"
            "Active problem + method decision source: UNSET  \n"
            f"Last material update: {now_iso()}\n\n"
            "## Problem-to-method chain\n\nUNSET\n\n"
            "## Nearest work and external baselines\n\nUNSET\n\n"
            "## Decision-relevant results\n\nUNSET\n\n"
            "## Candidate and ceiling summary\n\nUNSET\n",
            encoding="utf-8",
        )
    return l2_path


def active_questions(state: dict[str, Any]) -> list[dict[str, Any]]:
    return [q for q in state["macro_questions"] if q.get("status") == "PENDING_PI"]


def refresh_pause(state: dict[str, Any]) -> None:
    count = len(active_questions(state))
    state["paused_for_pi"] = count >= MAX_MACRO_QUESTIONS
    state["status"] = "PAUSED_FOR_PI" if state["paused_for_pi"] else "ACTIVE"


def require_execution_active(state: dict[str, Any], action: str) -> None:
    refresh_pause(state)
    if state["paused_for_pi"]:
        raise SystemExit(
            f"Cannot {action}: five PI decisions are pending and the workflow is PAUSED_FOR_PI"
        )


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


def checkpoint_complete(state: dict[str, Any], layer: str) -> bool:
    checkpoint = state["layer_checkpoints"].get(layer, {})
    if checkpoint.get("status") != "CONFIRMED_BY_PI":
        return False
    source = checkpoint.get("decision_source") or {}
    if source.get("outcome") not in APPROVING_OUTCOMES:
        return False
    payload = checkpoint.get("payload")
    if not isinstance(payload, dict):
        return False
    required: dict[str, tuple[str, ...]] = {
        "compass": ("venue_or_window", "domain"),
        "direction": ("task_type", "dataset", "evidence_standard"),
        "science": (
            "direction_id",
            "problem",
            "core_mechanism",
            "innovation_claim",
            "external_baseline_status",
            "ceiling_summary",
        ),
        "paper": ("science_id", "headline_claim", "handoff_target"),
    }
    if any(not payload.get(key) for key in required[layer]):
        return False
    if layer == "direction":
        standard = payload.get("evidence_standard")
        if not isinstance(standard, dict):
            return False
        keys = (
            "competitive_bar",
            "novelty_sufficiency",
            "generalization_requirement",
            "paper_ready_threshold",
        )
        if any(not standard.get(key) for key in keys):
            return False
    return bool(checkpoint.get("record_path"))


def checkpoint_usable(state_path: Path, state: dict[str, Any], layer: str) -> bool:
    if not checkpoint_complete(state, layer):
        return False
    record = resolve_stored_path(
        state_path, state["layer_checkpoints"][layer].get("record_path")
    )
    return bool(record and record.is_file())


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
    if state["phase"] in {"paper_ready_pending_pi", "paper_handoff_approved"}:
        assessment = state.get("paper_ready_assessment")
        if not isinstance(assessment, dict) or not assessment.get("path"):
            add(
                "PAPER_READY_ASSESSMENT_MISSING",
                "P0",
                "Paper-ready phase requires a recorded assessment artifact",
            )
    for layer in CHECKPOINT_LAYERS:
        checkpoint = state["layer_checkpoints"].get(layer, {})
        if checkpoint.get("status") == "LEGACY_CONFIRMED_NEEDS_AUDIT":
            add(
                f"LEGACY_{layer.upper()}_NEEDS_RECONFIRMATION",
                "P0" if layer in {"direction", "science"} else "P1",
                f"Legacy {layer} approval lacks the structured payload required by schema v4",
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
    l1_path = research_root_for_state(state_path) / "L1-directions.md"
    if state["phase"] != "discussion" and not l1_path.is_file():
        add("L1_FILE_MISSING", "P0", f"Missing durable L1 file: {l1_path}")
    seen_jobs: set[str] = set()
    for job in state.get("jobs", []):
        job_id = str(job.get("id", ""))
        if not job_id or job_id in seen_jobs:
            add("INVALID_JOB_ID", "P1", "Job IDs must be non-empty and unique")
        seen_jobs.add(job_id)
        if job.get("status") not in JOB_STATUSES:
            add("INVALID_JOB_STATUS", "P1", f"Invalid job status for {job_id}")
        if job.get("status") in ACTIVE_JOB_STATUSES and not (
            job.get("command") or job.get("session")
        ):
            add(
                "ACTIVE_JOB_NOT_RESUMABLE",
                "P1",
                f"Active job {job_id} has neither a command nor a session identifier",
            )
    return issues


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
    issues = audit_state(state_path, state)
    return {
        "schema_version": state["schema_version"],
        "project": state["project"],
        "phase": state["phase"],
        "status": state["status"],
        "paused_for_pi": state["paused_for_pi"],
        "pending_macro_count": len(pending),
        "pending_macro_questions": pending,
        "layer_checkpoints": state["layer_checkpoints"],
        "missing_required_checkpoints": [
            layer
            for layer in required_layers_for_phase(state["phase"])
            if not checkpoint_complete(state, layer)
        ],
        "incomplete_checkpoints": [
            layer for layer in CHECKPOINT_LAYERS if not checkpoint_complete(state, layer)
        ],
        "frozen_by_pi": state["frozen_by_pi"],
        "frozen_history_count": len(state["frozen_history"]),
        "notification_count": len(state["notifications"]),
        "notification_compacted_count": state.get("notification_compacted_count", 0),
        "active_jobs": active_jobs,
        "control_issues": issues,
        "updated_at": state["updated_at"],
    }


def cmd_init(args: argparse.Namespace) -> None:
    path = Path(args.state)
    if path.exists():
        raise SystemExit(f"Refusing to overwrite existing state: {path}")
    if args.phase not in {"discussion", "exploration"}:
        raise SystemExit("A new workflow may start only in discussion or exploration")
    if args.phase == "exploration" and not (
        args.venue_or_window
        and args.domain
        and args.pi_decision
        and args.pi_outcome in APPROVING_OUTCOMES
    ):
        raise SystemExit(
            "Starting in exploration requires --venue-or-window, --domain, "
            "--pi-decision, and --pi-outcome approve|select"
        )
    state = initial_state(args.project)
    ensure_scaffold(path, args.project)
    if args.phase == "exploration":
        l1 = research_root_for_state(path) / "L1-directions.md"
        record, stored, _ = normalize_record(path, str(l1))
        payload = {
            "venue_or_window": args.venue_or_window,
            "domain": args.domain,
            "starting_concept": args.starting_concept or "UNSET",
        }
        source = {
            "type": "direct_pi_instruction",
            "decision": args.pi_decision,
            "outcome": args.pi_outcome,
        }
        update_record_placeholders(record, "compass", "C001", payload, source)
        append_checkpoint_receipt(record, "compass", "C001", payload, source)
        digest = sha256_file(record)
        state["layer_checkpoints"]["compass"] = {
            "status": "CONFIRMED_BY_PI",
            "id": "C001",
            "summary": f"venue_or_window={args.venue_or_window}; domain={args.domain}",
            "payload": payload,
            "confirmed_at": now_iso(),
            "decision_source": source,
            "record_path": stored,
            "record_sha256_at_confirmation": digest,
        }
        state["phase"] = "exploration"
    save_state(path, state)
    print(json.dumps(state_summary(path, state), ensure_ascii=False, indent=2))


def cmd_status(args: argparse.Namespace) -> None:
    path = Path(args.state)
    state = load_state(path)
    print(json.dumps(state_summary(path, state), ensure_ascii=False, indent=2))


def cmd_audit(args: argparse.Namespace) -> None:
    path = Path(args.state)
    state = load_state(path)
    summary = state_summary(path, state)
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    if summary["control_issues"]:
        raise SystemExit(2)


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
    if any(q.get("text") == args.text for q in pending):
        raise SystemExit("An identical PI decision question is already pending")
    question = {
        "id": next_id(state["macro_questions"], "Q"),
        "status": "PENDING_PI",
        "layer": args.layer,
        "text": args.text,
        "priority": args.priority,
        "reason": args.reason,
        "recommendation": args.recommendation,
        "continue_plan": args.continue_plan,
        "created_at": now_iso(),
        "answered_at": None,
        "decision": None,
        "outcome": None,
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
    if question.get("status") != "PENDING_PI":
        raise SystemExit(f"Question is not pending: {args.id}")
    question["status"] = "ANSWERED"
    question["decision"] = args.decision
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


def cmd_notify(args: argparse.Namespace) -> None:
    path = Path(args.state)
    state = load_state(path)
    state["notification_sequence"] = int(state.get("notification_sequence", 0)) + 1
    notification = {
        "id": f"N{state['notification_sequence']:03d}",
        "text": args.text,
        "created_at": now_iso(),
    }
    state["notifications"].append(notification)
    compact_recent_notifications(state)
    save_state(path, state)
    print(
        json.dumps(
            {"added": notification, "state": state_summary(path, state)},
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
    if args.decision_id:
        matches = [q for q in state["macro_questions"] if q.get("id") == args.decision_id]
        if not matches:
            raise SystemExit(f"Decision question not found: {args.decision_id}")
        question = matches[0]
        if question.get("status") != "ANSWERED" or not question.get("decision"):
            raise SystemExit(f"Decision question is not answered: {args.decision_id}")
        question_layer = question.get("layer", "other")
        if question_layer not in {"other", layer}:
            raise SystemExit(
                f"Question {args.decision_id} belongs to layer "
                f"{question_layer!r}, not {layer!r}"
            )
        outcome = question.get("outcome")
        if outcome not in APPROVING_OUTCOMES:
            raise SystemExit(
                f"Question {args.decision_id} outcome {outcome!r} cannot confirm a checkpoint"
            )
        return {
            "type": "answered_question",
            "question_id": args.decision_id,
            "decision": str(question["decision"]),
            "outcome": str(outcome),
        }
    direct_decision = str(args.pi_decision or "").strip()
    if not direct_decision:
        raise SystemExit("--pi-decision must contain the user's actual decision")
    if args.pi_outcome not in APPROVING_OUTCOMES:
        raise SystemExit("Direct checkpoint confirmation requires --pi-outcome approve or select")
    return {
        "type": "direct_pi_instruction",
        "decision": direct_decision,
        "outcome": args.pi_outcome,
    }


def checkpoint_payload(
    args: argparse.Namespace, state_path: Path, state: dict[str, Any]
) -> dict[str, Any]:
    if args.layer == "compass":
        if not (args.venue_or_window and args.domain):
            raise SystemExit("Compass confirmation requires --venue-or-window and --domain")
        return {
            "venue_or_window": args.venue_or_window,
            "domain": args.domain,
            "starting_concept": args.starting_concept or "UNSET",
        }
    if args.layer == "direction":
        if not checkpoint_usable(state_path, state, "compass"):
            raise SystemExit("Cannot confirm direction before a complete research compass")
        required = {
            "task_type": args.task_type,
            "dataset": args.dataset,
            "competitive_bar": args.competitive_bar,
            "novelty_sufficiency": args.novelty_sufficiency,
            "generalization_requirement": args.generalization_requirement,
            "paper_ready_threshold": args.paper_ready_threshold,
        }
        missing = [key for key, value in required.items() if not value]
        if missing:
            raise SystemExit(
                "Direction confirmation is missing structured fields: " + ", ".join(missing)
            )
        return {
            "task_type": args.task_type,
            "dataset": args.dataset,
            "evidence_standard": {
                "competitive_bar": args.competitive_bar,
                "novelty_sufficiency": args.novelty_sufficiency,
                "generalization_requirement": args.generalization_requirement,
                "paper_ready_threshold": args.paper_ready_threshold,
            },
        }
    if args.layer == "science":
        required = {
            "direction_id": args.direction_id,
            "problem": args.problem,
            "core_mechanism": args.core_mechanism,
            "innovation_claim": args.innovation_claim,
            "external_baseline_status": args.external_baseline_status,
            "ceiling_summary": args.ceiling_summary,
        }
        missing = [key for key, value in required.items() if not value]
        if missing:
            raise SystemExit(
                "Science confirmation is missing structured fields: " + ", ".join(missing)
            )
        direction = state["layer_checkpoints"]["direction"]
        if not checkpoint_usable(state_path, state, "direction"):
            raise SystemExit("Cannot confirm science before a complete L1 direction")
        if args.direction_id != direction.get("id"):
            raise SystemExit("--direction-id must match the active confirmed direction")
        return required
    if args.layer == "paper":
        required = {
            "science_id": args.science_id,
            "headline_claim": args.headline_claim,
            "handoff_target": args.handoff_target,
        }
        missing = [key for key, value in required.items() if not value]
        if missing:
            raise SystemExit(
                "Paper confirmation is missing structured fields: " + ", ".join(missing)
            )
        science = state["layer_checkpoints"]["science"]
        if not checkpoint_usable(state_path, state, "science"):
            raise SystemExit("Cannot confirm paper handoff before a complete L2 story")
        if args.science_id != science.get("id"):
            raise SystemExit("--science-id must match the active confirmed science checkpoint")
        if state.get("phase") != "paper_ready_pending_pi":
            raise SystemExit("Paper handoff requires phase paper_ready_pending_pi")
        if not state.get("paper_ready_assessment"):
            raise SystemExit("Paper handoff requires a recorded paper-ready assessment")
        assessment_path = resolve_stored_path(
            state_path, state["paper_ready_assessment"].get("path")
        )
        if not assessment_path or not assessment_path.is_file():
            raise SystemExit("The recorded paper-ready assessment is unavailable")
        return required
    raise SystemExit(f"Unsupported checkpoint layer: {args.layer}")


def invalidate_checkpoint(
    state: dict[str, Any], layer: str, reason: str, replacement_id: str
) -> None:
    previous = state["layer_checkpoints"][layer]
    if previous.get("status") == "UNSET":
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
    state["layer_checkpoints"][layer] = stale


def cmd_confirm(args: argparse.Namespace) -> None:
    path = Path(args.state)
    state = load_state(path)
    require_execution_active(state, "confirm a scientific checkpoint")
    payload = checkpoint_payload(args, path, state)
    source = approving_decision_source(state, args, args.layer)
    record, stored, _ = normalize_record(path, args.record)
    previous = state["layer_checkpoints"][args.layer]
    if (
        previous.get("status") == "CONFIRMED_BY_PI"
        and previous.get("id") == args.id
        and previous.get("payload") == payload
    ):
        raise SystemExit(f"Layer is already confirmed to this value: {args.layer}")
    if previous.get("status") != "UNSET":
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
    digest = sha256_file(record)
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
        for layer in ("direction", "science", "paper"):
            invalidate_checkpoint(state, layer, "compass_change", args.id)
        state["paper_ready_assessment"] = None
        state["phase"] = "exploration"
    elif args.layer == "direction":
        for layer in ("science", "paper"):
            invalidate_checkpoint(state, layer, "direction_change", args.id)
        state["paper_ready_assessment"] = None
        state["phase"] = "confirmed_project"
        ensure_l2_scaffold(path, args.id, payload)
    elif args.layer == "science":
        invalidate_checkpoint(state, "paper", "science_change", args.id)
        state["paper_ready_assessment"] = None
        state["phase"] = "confirmed_project"
    elif args.layer == "paper":
        state["phase"] = "paper_handoff_approved"
    refresh_pause(state)
    save_state(path, state)
    print(json.dumps(state_summary(path, state), ensure_ascii=False, indent=2))


def cmd_phase(args: argparse.Namespace) -> None:
    path = Path(args.state)
    state = load_state(path)
    require_execution_active(state, "advance the workflow phase")
    current = state["phase"]
    target = args.set
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
        _, stored, digest = normalize_record(path, args.assessment)
        state["paper_ready_assessment"] = {
            "path": stored,
            "sha256_at_gate": digest,
            "recorded_at": now_iso(),
        }
    if current == "paper_ready_pending_pi" and target == "confirmed_project":
        state["paper_ready_assessment"] = None
    state["phase"] = target
    save_state(path, state)
    print(json.dumps(state_summary(path, state), ensure_ascii=False, indent=2))


def decision_source_for_freeze(state: dict[str, Any], args: argparse.Namespace) -> dict[str, str]:
    if args.decision_id:
        matches = [q for q in state["macro_questions"] if q.get("id") == args.decision_id]
        if not matches:
            raise SystemExit(f"Decision question not found: {args.decision_id}")
        question = matches[0]
        if question.get("status") != "ANSWERED" or not question.get("decision"):
            raise SystemExit(f"Decision question is not answered: {args.decision_id}")
        if question.get("outcome") not in APPROVING_OUTCOMES:
            raise SystemExit("A rejected, deferred, or informational answer cannot freeze a field")
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
    save_state(path, state)
    print(json.dumps(state_summary(path, state), ensure_ascii=False, indent=2))


def cmd_unfreeze(args: argparse.Namespace) -> None:
    path = Path(args.state)
    state = load_state(path)
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
    save_state(path, state)
    print(json.dumps(state_summary(path, state), ensure_ascii=False, indent=2))


def cmd_job_add(args: argparse.Namespace) -> None:
    path = Path(args.state)
    state = load_state(path)
    require_execution_active(state, "add an active job")
    if any(job.get("id") == args.id for job in state["jobs"]):
        raise SystemExit(f"Job already exists: {args.id}")
    if args.status in ACTIVE_JOB_STATUSES and not (args.command or args.session):
        raise SystemExit("An active job requires --command or --session")
    job = {
        "id": args.id,
        "description": args.description,
        "command": args.command,
        "session": args.session,
        "status": args.status,
        "next_poll": args.next_poll,
        "next_action": args.next_action,
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
    matches = [job for job in state["jobs"] if job.get("id") == args.id]
    if not matches:
        raise SystemExit(f"Job not found: {args.id}")
    job = matches[0]
    new_status = args.status or job.get("status")
    if state["paused_for_pi"] and new_status in ACTIVE_JOB_STATUSES and new_status != job.get("status"):
        raise SystemExit("Cannot start or queue a job while PAUSED_FOR_PI")
    for field in ("status", "session", "next_poll", "next_action", "result"):
        value = getattr(args, field)
        if value is not None:
            job[field] = value
    if job.get("status") in ACTIVE_JOB_STATUSES and not (job.get("command") or job.get("session")):
        raise SystemExit("An active job requires a command or session identifier")
    job["updated_at"] = now_iso()
    save_state(path, state)
    print(json.dumps({"updated": job, "state": state_summary(path, state)}, ensure_ascii=False, indent=2))


def cmd_job_remove(args: argparse.Namespace) -> None:
    path = Path(args.state)
    state = load_state(path)
    matches = [job for job in state["jobs"] if job.get("id") == args.id]
    if not matches:
        raise SystemExit(f"Job not found: {args.id}")
    job = matches[0]
    if job.get("status") in ACTIVE_JOB_STATUSES and not args.force:
        raise SystemExit("Refusing to remove an active job without --force")
    state["jobs"] = [item for item in state["jobs"] if item.get("id") != args.id]
    save_state(path, state)
    print(json.dumps({"removed": job, "state": state_summary(path, state)}, ensure_ascii=False, indent=2))


def add_decision_source_args(parser: argparse.ArgumentParser) -> None:
    source = parser.add_mutually_exclusive_group(required=True)
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

    status_parser = subparsers.add_parser("status", help="Show compact state and control issues")
    status_parser.add_argument("state")
    status_parser.set_defaults(func=cmd_status)

    audit_parser = subparsers.add_parser("audit", help="Fail when workflow control issues exist")
    audit_parser.add_argument("state")
    audit_parser.set_defaults(func=cmd_audit)

    question_parser = subparsers.add_parser("question", help="Add a PI decision question")
    question_parser.add_argument("state")
    question_parser.add_argument("--text", required=True)
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
    answer_parser.set_defaults(func=cmd_answer)

    notify_parser = subparsers.add_parser("notify", help="Record a recent non-blocking notification")
    notify_parser.add_argument("state")
    notify_parser.add_argument("--text", required=True)
    notify_parser.set_defaults(func=cmd_notify)

    compact_parser = subparsers.add_parser(
        "compact-notifications", help="Keep only the most recent notification records"
    )
    compact_parser.add_argument("state")
    compact_parser.add_argument("--keep", type=int, default=RECENT_NOTIFICATION_LIMIT)
    compact_parser.set_defaults(func=cmd_compact_notifications)

    phase_parser = subparsers.add_parser("phase", help="Apply a legal workflow transition")
    phase_parser.add_argument("state")
    phase_parser.add_argument("--set", required=True, choices=sorted(VALID_PHASES))
    phase_parser.add_argument("--assessment")
    phase_parser.set_defaults(func=cmd_phase)

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
    confirm_parser.add_argument("--starting-concept")
    confirm_parser.add_argument("--task-type")
    confirm_parser.add_argument("--dataset")
    confirm_parser.add_argument("--competitive-bar")
    confirm_parser.add_argument("--novelty-sufficiency")
    confirm_parser.add_argument("--generalization-requirement")
    confirm_parser.add_argument("--paper-ready-threshold")
    confirm_parser.add_argument("--direction-id")
    confirm_parser.add_argument("--problem")
    confirm_parser.add_argument("--core-mechanism")
    confirm_parser.add_argument("--innovation-claim")
    confirm_parser.add_argument("--external-baseline-status")
    confirm_parser.add_argument("--ceiling-summary")
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
    args.func(args)
    return 0


if __name__ == "__main__":
    sys.exit(main())
