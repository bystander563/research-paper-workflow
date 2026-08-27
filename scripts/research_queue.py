#!/usr/bin/env python3
"""Control durable PI decisions and resumable work for research-paper-workflow.

The controller enforces scoped typed approvals, ordered scientific checkpoints,
active/deferred PI queues, the five-question pause, evidence-record links,
lightweight active-job recovery, bounded project-instruction maintenance, and
control-state audits. It records authority and artifact availability; it does
not judge scientific adequacy, rewrite AGENTS.md, create authority, schedule
itself, or kill processes.
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


SCHEMA_VERSION = 7
SUPPORTED_SCHEMA_VERSIONS = {1, 2, 3, 4, 5, 6, 7}
MAX_MACRO_QUESTIONS = 5
RECENT_NOTIFICATION_LIMIT = 50
RECENT_INSTRUCTION_UPDATE_LIMIT = 20
ROOT_AGENTS_TARGET_BYTES = 8 * 1024
ROOT_AGENTS_REVIEW_BYTES = 12 * 1024
EFFECTIVE_AGENTS_TARGET_BYTES = 16 * 1024
CODEX_PROJECT_DOC_DEFAULT_BYTES = 32 * 1024
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
PAPER_ASSESSMENT_FIELDS = (
    "competitive_bar_assessment",
    "novelty_assessment",
    "generalization_assessment",
    "paper_ready_threshold_assessment",
    "narrowest_supported_claim",
    "strongest_matched_comparison",
    "remaining_objection",
    "necessary_work",
    "optional_work",
)
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
    "competitive_bar",
    "novelty_sufficiency",
    "generalization_requirement",
    "second_dataset_requirement",
    "paper_ready_threshold",
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
    "竞争目标",
    "创新标准",
    "泛化要求",
    "第二数据集要求",
    "论文就绪条件",
    "问题",
    "核心机制",
    "创新点",
    "论文主张",
}


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
        "decision_target_revisions": dict,
        "notifications": list,
        "instruction_maintenance": dict,
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
    fallback_filenames = fallback_filenames or []
    for name in fallback_filenames:
        if Path(name).name != name or name in AGENTS_FILENAMES:
            raise SystemExit(f"Invalid project instruction fallback filename: {name!r}")
    instruction_filenames = AGENTS_FILENAMES + tuple(fallback_filenames)
    if cwd_raw:
        cwd = Path(cwd_raw).expanduser()
        if not cwd.is_absolute():
            cwd = project_root / cwd
        cwd = cwd.resolve()
    else:
        cwd = project_root
    if not cwd.is_dir():
        raise SystemExit(f"Instruction audit working directory does not exist: {cwd}")
    try:
        relative_cwd = cwd.relative_to(project_root)
    except ValueError as exc:
        raise SystemExit(
            f"Instruction audit working directory must stay inside {project_root}: {cwd}"
        ) from exc

    directories = [project_root]
    current = project_root
    for part in relative_cwd.parts:
        current = current / part
        directories.append(current)

    observed: list[dict[str, Any]] = []
    effective: list[dict[str, Any]] = []
    shadowed: list[dict[str, str]] = []
    root_instruction: dict[str, Any] | None = None
    for directory in directories:
        existing = [
            directory / name
            for name in instruction_filenames
            if (directory / name).is_file()
        ]
        selected = existing[0] if existing else None
        selected_stored = (
            selected.relative_to(project_root).as_posix() if selected is not None else None
        )
        for candidate in existing:
            stored = candidate.relative_to(project_root).as_posix()
            entry = {
                "path": stored,
                "bytes": candidate.stat().st_size,
                "sha256": sha256_file(candidate),
                "selected": candidate == selected,
                "shadowed_by": None if candidate == selected else selected_stored,
            }
            observed.append(entry)
            if candidate == selected:
                effective.append(entry)
                if directory == project_root:
                    root_instruction = entry
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


def normalize_project_record(path: Path, raw: str) -> tuple[Path, str, str]:
    record = Path(raw).expanduser()
    if not record.is_absolute():
        record = project_root_for_state(path) / record
    record = record.resolve()
    if not record.is_file():
        raise SystemExit(f"Checkpoint record does not exist: {record}")
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
    return str(raw).strip().lower().replace("-", "_").replace(" ", "_")


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
    receipt = (
        "\n\n## Paper-ready control assessment\n\n"
        f"- Recorded at: {now_iso()}\n"
        "- Structured assessment:\n\n"
        "```json\n"
        + json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True)
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
        return text[:start] + replacement + text[end:]

    start = text.find("L2 status:")
    end_anchor = "Last material update:"
    end = text.find(end_anchor, start) if start >= 0 else -1
    if start >= 0 and end >= 0:
        return text[:start] + replacement + "  \n" + text[end:]
    return text.rstrip() + "\n\n" + replacement + "\n"


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
        text = replace_managed_section(
            text,
            "DIRECTION_STANDARD_CURRENT",
            "## Project evidence standard\n\n"
            f"- Competitive bar: {standard['competitive_bar']}\n"
            f"- Novelty sufficiency: {standard['novelty_sufficiency']}\n"
            "- Generalization or second-dataset requirement: "
            f"{standard['generalization_requirement']}\n"
            f"- Paper-ready threshold: {standard['paper_ready_threshold']}",
            "## Project evidence standard",
        )
        text = replace_managed_section(
            text,
            "DIRECTION_DECISION_CURRENT",
            "## Current PI decision\n\n"
            f"- Checkpoint: `{checkpoint_id}`\n"
            f"- Task type: {payload['task_type']}\n"
            f"- Dataset: {payload['dataset']}\n"
            f"- User decision: {source['decision']}",
            "## Current PI decision",
        )
    elif layer == "science":
        text = replace_science_current_block(
            text,
            "L2 status: `ACTIVE_PI_CONFIRMED`  \n"
            f"Active checkpoint: `{checkpoint_id}`  \n"
            f"Problem: {payload['problem']}  \n"
            f"Core mechanism: {payload['core_mechanism']}  \n"
            f"Innovation claim: {payload['innovation_claim']}  \n"
            f"User decision: {source['decision']}",
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
            "- Paper-ready threshold: UNSET\n"
            "<!-- RPW:DIRECTION_STANDARD_CURRENT:END -->\n\n"
            "## Ranked directions\n\n"
            "| ID | status | task type | dataset | why meaningful | task-data fit | headroom | nearest-work risk | baseline feasibility | cost/time | next action |\n"
            "|---|---|---|---|---|---|---|---|---|---|---|\n\n"
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
            f"# {direction_id} scientific story\n\n"
            f"Direction ID: `{direction_id}`  \n"
            f"L1 task and dataset: {payload['task_type']} | {payload['dataset']}  \n"
            "L1 confirmation source: see workflow state  \n"
            "<!-- RPW:SCIENCE_CURRENT:START -->\n"
            "L2 status: `MAPPING_NEAREST_WORK`  \n"
            "Active problem + method decision source: UNSET\n"
            "<!-- RPW:SCIENCE_CURRENT:END -->  \n"
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


def deferred_questions(state: dict[str, Any]) -> list[dict[str, Any]]:
    return [q for q in state["macro_questions"] if q.get("status") == "DEFERRED_PI"]


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
    if layer == "science":
        evidence_refs = payload.get("evidence_refs")
        if not isinstance(evidence_refs, dict):
            return False
        for key in ("nearest_work", "external_baselines", "results"):
            ref = evidence_refs.get(key)
            if not isinstance(ref, dict) or not ref.get("path"):
                return False
    return bool(checkpoint.get("record_path"))


def checkpoint_usable(state_path: Path, state: dict[str, Any], layer: str) -> bool:
    if not checkpoint_complete(state, layer):
        return False
    record = resolve_stored_path(
        state_path, state["layer_checkpoints"][layer].get("record_path")
    )
    if not record or not record.is_file():
        return False
    if layer == "science":
        refs = state["layer_checkpoints"][layer]["payload"]["evidence_refs"]
        for name in ("nearest_work", "external_baselines", "results"):
            ref = refs[name]
            evidence_path = resolve_stored_path(state_path, ref.get("path"))
            if not evidence_path or not evidence_path.is_file():
                return False
    return True


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
        elif any(not assessment.get(field) for field in PAPER_ASSESSMENT_FIELDS):
            add(
                "PAPER_READY_ASSESSMENT_INCOMPLETE",
                "P0",
                "Paper-ready assessment must explicitly cover the L1 criteria and claim risks",
            )
        else:
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
        if checkpoint.get("status") == "LEGACY_CONFIRMED_NEEDS_AUDIT":
            add(
                f"LEGACY_{layer.upper()}_NEEDS_RECONFIRMATION",
                "P0" if layer in {"direction", "science"} else "P1",
                f"Legacy {layer} approval lacks the structured payload or evidence links required by schema v7",
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
                f"Confirmed {layer} checkpoint lacks required schema-v7 control fields",
            )
        source = checkpoint.get("decision_source") or {}
        if checkpoint.get("status") == "CONFIRMED_BY_PI" and source.get(
            "type"
        ) == "answered_question":
            matches = [
                q
                for q in state["macro_questions"]
                if q.get("id") == source.get("question_id")
            ]
            expected = {
                "type": "checkpoint",
                "layer": layer,
                "id": checkpoint.get("id"),
            }
            if not matches or any(
                (matches[0].get("consumed_by") or {}).get(key) != value
                for key, value in expected.items()
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
    if assessment and (
        assessment.get("direction_id") != direction.get("id")
        or assessment.get("science_id") != science.get("id")
    ):
        add(
            "PAPER_ASSESSMENT_LINK_MISMATCH",
            "P0",
            "Paper-ready assessment is not tied to the active L1/L2 checkpoints",
        )
    for key in state.get("frozen_by_pi", {}):
        if normalized_frozen_key(key) in RESERVED_FROZEN_KEYS:
            add(
                "RESERVED_FIELD_DUPLICATED_IN_FROZEN_BY_PI",
                "P0",
                f"Core scientific field {key!r} must live only in compass/L1/L2 state",
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
                matches = [
                    q
                    for q in state["macro_questions"]
                    if q.get("id") == source.get("question_id")
                ]
                expected = {
                    "type": "instruction_update",
                    "path": update.get("path"),
                    "after_sha256": update.get("after_sha256"),
                }
                if not matches or any(
                    (matches[0].get("consumed_by") or {}).get(key) != value
                    for key, value in expected.items()
                ):
                    add(
                        "INSTRUCTION_DECISION_RECEIPT_NOT_BOUND",
                        "P0",
                        f"Semantic instruction update for {update.get('path')!r} is not bound to one scoped PI decision",
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
        "pending_macro_count": len(pending),
        "pending_macro_questions": pending,
        "deferred_pi_count": len(deferred),
        "deferred_pi_questions": deferred,
        "unused_approvals": unused_approvals,
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
        "instruction_maintenance": state.get("instruction_maintenance"),
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
    initial_audit = analyze_project_instructions(path)
    state["instruction_maintenance"]["audits_by_scope"][
        instruction_scope_key(initial_audit)
    ] = initial_audit
    if args.phase == "exploration":
        l1 = research_root_for_state(path) / "L1-directions.md"
        record, stored, _ = normalize_project_record(path, str(l1))
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
    target = str(args.target).strip()
    if not target:
        raise SystemExit("A PI decision question requires a stable --target")
    open_questions = active_questions(state) + deferred_questions(state)
    if any(q.get("decision_target") == target for q in open_questions):
        raise SystemExit(f"A PI question already exists for decision target: {target}")
    if any(q.get("text") == args.text for q in open_questions):
        raise SystemExit("An identical PI decision question is already open")
    if args.layer in CHECKPOINT_LAYERS and not target.startswith(f"{args.layer}:"):
        raise SystemExit(
            f"A {args.layer} question target must start with {args.layer}:"
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
        "text": args.text,
        "priority": args.priority,
        "reason": args.reason,
        "recommendation": args.recommendation,
        "continue_plan": args.continue_plan,
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
    response = {
        "text": args.decision,
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
        question["decision"] = args.decision
        question["outcome"] = "defer"
        question["answered_at"] = None
        question["deferred_at"] = now_iso()
        question["revisit_condition"] = revisit
    else:
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


def append_notification(state: dict[str, Any], text: str) -> dict[str, Any]:
    state["notification_sequence"] = int(state.get("notification_sequence", 0)) + 1
    notification = {
        "id": f"N{state['notification_sequence']:03d}",
        "text": text,
        "created_at": now_iso(),
    }
    state["notifications"].append(notification)
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
    notification = append_notification(state, args.text)
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
    audit = analyze_project_instructions(path, args.cwd, args.fallback_name)
    maintenance = state["instruction_maintenance"]
    audits = maintenance.setdefault("audits_by_scope", {})
    key = instruction_scope_key(audit)
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
    bootstrapped = key not in audits
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


def cmd_agents_record(args: argparse.Namespace) -> None:
    path = Path(args.state)
    state = load_state(path)
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
        required["evidence_refs"] = {
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
    state["layer_checkpoints"][layer] = stale


def cmd_confirm(args: argparse.Namespace) -> None:
    path = Path(args.state)
    state = load_state(path)
    require_execution_active(state, "confirm a scientific checkpoint")
    payload = checkpoint_payload(args, path, state)
    source = approving_decision_source(state, args, args.layer)
    record, stored, _ = normalize_project_record(path, args.record)
    previous = state["layer_checkpoints"][args.layer]
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
        missing = [
            field for field in PAPER_ASSESSMENT_FIELDS if not getattr(args, field)
        ]
        if missing:
            raise SystemExit(
                "Paper-ready assessment is missing structured fields: "
                + ", ".join(missing)
            )
        record, stored, _ = normalize_project_record(path, args.assessment)
        assessment_payload = {
            "direction_id": state["layer_checkpoints"]["direction"].get("id"),
            "science_id": state["layer_checkpoints"]["science"].get("id"),
            **{field: getattr(args, field) for field in PAPER_ASSESSMENT_FIELDS},
        }
        append_paper_assessment_receipt(record, assessment_payload)
        state["paper_ready_assessment"] = {
            "path": stored,
            "sha256_at_gate": sha256_file(record),
            "recorded_at": now_iso(),
            **assessment_payload,
        }
    if current == "paper_ready_pending_pi" and target == "confirmed_project":
        state["paper_ready_assessment"] = None
    state["phase"] = target
    save_state(path, state)
    print(json.dumps(state_summary(path, state), ensure_ascii=False, indent=2))


def decision_source_for_freeze(state: dict[str, Any], args: argparse.Namespace) -> dict[str, str]:
    if args.decision_id:
        expected_target = f"frozen:{args.key}"
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

    status_parser = subparsers.add_parser("status", help="Show compact state and control issues")
    status_parser.add_argument("state")
    status_parser.set_defaults(func=cmd_status)

    audit_parser = subparsers.add_parser("audit", help="Fail when workflow control issues exist")
    audit_parser.add_argument("state")
    audit_parser.set_defaults(func=cmd_audit)

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
    confirm_parser.add_argument("--nearest-work-record")
    confirm_parser.add_argument("--baseline-record")
    confirm_parser.add_argument("--result-record")
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
