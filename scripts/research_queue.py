#!/usr/bin/env python3
"""Maintain a durable PI decision queue for research-paper-workflow.

The helper records state and enforces the five-unanswered-question pause flag.
It does not schedule work or kill processes.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


SCHEMA_VERSION = 2
SUPPORTED_SCHEMA_VERSIONS = {1, 2}
MAX_MACRO_QUESTIONS = 5
PRIORITY_ORDER = {"high": 0, "medium": 1, "low": 2}
VALID_PHASES = {
    "discussion",
    "exploration",
    "confirmed_project",
    "paper_ready_pending_pi",
}


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def initial_state(project: str, phase: str) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "project": project,
        "phase": phase,
        "status": "ACTIVE",
        "paused_for_pi": False,
        "frozen_by_pi": {},
        "frozen_history": [],
        "macro_questions": [],
        "notifications": [],
        "created_at": now_iso(),
        "updated_at": now_iso(),
    }


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
    if version == 1:
        state.setdefault("frozen_history", [])
        state["schema_version"] = SCHEMA_VERSION
    required_types = {
        "project": str,
        "phase": str,
        "frozen_by_pi": dict,
        "frozen_history": list,
        "macro_questions": list,
        "notifications": list,
    }
    for key, expected_type in required_types.items():
        if not isinstance(state.get(key), expected_type):
            raise SystemExit(
                f"Invalid state field {key!r}: expected {expected_type.__name__}"
            )
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


def active_questions(state: dict[str, Any]) -> list[dict[str, Any]]:
    return [q for q in state["macro_questions"] if q.get("status") == "PENDING_PI"]


def refresh_pause(state: dict[str, Any]) -> None:
    count = len(active_questions(state))
    state["paused_for_pi"] = count >= MAX_MACRO_QUESTIONS
    state["status"] = "PAUSED_FOR_PI" if state["paused_for_pi"] else "ACTIVE"


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


def state_summary(state: dict[str, Any]) -> dict[str, Any]:
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
                "text": question["text"],
                "reason": question.get("reason", ""),
                "recommendation": question.get("recommendation", ""),
                "continue_plan": question.get("continue_plan", ""),
                "age_minutes": None if age is None else round(age, 1),
                "over_20_minutes": None if age is None else age >= 20.0,
            }
        )
    return {
        "schema_version": state["schema_version"],
        "project": state["project"],
        "phase": state["phase"],
        "status": state["status"],
        "paused_for_pi": state["paused_for_pi"],
        "pending_macro_count": len(pending),
        "pending_macro_questions": pending,
        "frozen_by_pi": state["frozen_by_pi"],
        "frozen_history_count": len(state["frozen_history"]),
        "notification_count": len(state["notifications"]),
        "updated_at": state["updated_at"],
    }


def cmd_init(args: argparse.Namespace) -> None:
    path = Path(args.state)
    if path.exists():
        raise SystemExit(f"Refusing to overwrite existing state: {path}")
    state = initial_state(args.project, args.phase)
    save_state(path, state)
    print(json.dumps(state_summary(state), ensure_ascii=False, indent=2))


def cmd_status(args: argparse.Namespace) -> None:
    state = load_state(Path(args.state))
    refresh_pause(state)
    print(json.dumps(state_summary(state), ensure_ascii=False, indent=2))


def cmd_question(args: argparse.Namespace) -> None:
    path = Path(args.state)
    state = load_state(path)
    refresh_pause(state)
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
        "text": args.text,
        "priority": args.priority,
        "reason": args.reason,
        "recommendation": args.recommendation,
        "continue_plan": args.continue_plan,
        "created_at": now_iso(),
        "answered_at": None,
        "decision": None,
    }
    state["macro_questions"].append(question)
    refresh_pause(state)
    save_state(path, state)
    print(json.dumps({"added": question, "state": state_summary(state)}, ensure_ascii=False, indent=2))


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
    question["answered_at"] = now_iso()
    refresh_pause(state)
    save_state(path, state)
    print(json.dumps({"answered": question, "state": state_summary(state)}, ensure_ascii=False, indent=2))


def cmd_notify(args: argparse.Namespace) -> None:
    path = Path(args.state)
    state = load_state(path)
    notification = {
        "id": next_id(state["notifications"], "N"),
        "text": args.text,
        "created_at": now_iso(),
    }
    state["notifications"].append(notification)
    refresh_pause(state)
    save_state(path, state)
    print(json.dumps({"added": notification, "state": state_summary(state)}, ensure_ascii=False, indent=2))


def cmd_phase(args: argparse.Namespace) -> None:
    path = Path(args.state)
    state = load_state(path)
    state["phase"] = args.set
    refresh_pause(state)
    save_state(path, state)
    print(json.dumps(state_summary(state), ensure_ascii=False, indent=2))


def decision_source(state: dict[str, Any], args: argparse.Namespace) -> dict[str, str]:
    if args.decision_id:
        matches = [q for q in state["macro_questions"] if q.get("id") == args.decision_id]
        if not matches:
            raise SystemExit(f"Decision question not found: {args.decision_id}")
        question = matches[0]
        if question.get("status") != "ANSWERED" or not question.get("decision"):
            raise SystemExit(f"Decision question is not answered: {args.decision_id}")
        return {
            "type": "answered_question",
            "question_id": args.decision_id,
            "decision": str(question["decision"]),
        }
    direct_decision = str(args.pi_decision).strip()
    if not direct_decision:
        raise SystemExit("--pi-decision must contain the user's actual decision")
    return {
        "type": "direct_pi_instruction",
        "decision": direct_decision,
    }


def cmd_freeze(args: argparse.Namespace) -> None:
    path = Path(args.state)
    state = load_state(path)
    source = decision_source(state, args)
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
    refresh_pause(state)
    save_state(path, state)
    print(json.dumps(state_summary(state), ensure_ascii=False, indent=2))


def cmd_unfreeze(args: argparse.Namespace) -> None:
    path = Path(args.state)
    state = load_state(path)
    if args.key not in state["frozen_by_pi"]:
        raise SystemExit(f"Frozen key not found: {args.key}")
    source = decision_source(state, args)
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
    refresh_pause(state)
    save_state(path, state)
    print(json.dumps(state_summary(state), ensure_ascii=False, indent=2))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    init_parser = subparsers.add_parser("init", help="Create a new state file")
    init_parser.add_argument("state")
    init_parser.add_argument("--project", required=True)
    init_parser.add_argument("--phase", default="exploration", choices=sorted(VALID_PHASES))
    init_parser.set_defaults(func=cmd_init)

    status_parser = subparsers.add_parser("status", help="Show a compact state summary")
    status_parser.add_argument("state")
    status_parser.set_defaults(func=cmd_status)

    question_parser = subparsers.add_parser("question", help="Add a PI decision question")
    question_parser.add_argument("state")
    question_parser.add_argument("--text", required=True)
    question_parser.add_argument(
        "--priority", choices=sorted(PRIORITY_ORDER), default="medium"
    )
    question_parser.add_argument("--reason", default="")
    question_parser.add_argument("--recommendation", default="")
    question_parser.add_argument("--continue-plan", default="")
    question_parser.set_defaults(func=cmd_question)

    answer_parser = subparsers.add_parser("answer", help="Record the PI decision")
    answer_parser.add_argument("state")
    answer_parser.add_argument("--id", required=True)
    answer_parser.add_argument("--decision", required=True)
    answer_parser.set_defaults(func=cmd_answer)

    notify_parser = subparsers.add_parser("notify", help="Record a non-blocking notification")
    notify_parser.add_argument("state")
    notify_parser.add_argument("--text", required=True)
    notify_parser.set_defaults(func=cmd_notify)

    phase_parser = subparsers.add_parser("phase", help="Change workflow phase")
    phase_parser.add_argument("state")
    phase_parser.add_argument("--set", required=True, choices=sorted(VALID_PHASES))
    phase_parser.set_defaults(func=cmd_phase)

    freeze_parser = subparsers.add_parser("freeze", help="Freeze a user-confirmed field")
    freeze_parser.add_argument("state")
    freeze_parser.add_argument("--key", required=True)
    freeze_parser.add_argument("--value", required=True)
    freeze_source = freeze_parser.add_mutually_exclusive_group(required=True)
    freeze_source.add_argument("--decision-id")
    freeze_source.add_argument("--pi-decision")
    freeze_parser.set_defaults(func=cmd_freeze)

    unfreeze_parser = subparsers.add_parser("unfreeze", help="Remove a frozen field")
    unfreeze_parser.add_argument("state")
    unfreeze_parser.add_argument("--key", required=True)
    unfreeze_source = unfreeze_parser.add_mutually_exclusive_group(required=True)
    unfreeze_source.add_argument("--decision-id")
    unfreeze_source.add_argument("--pi-decision")
    unfreeze_parser.set_defaults(func=cmd_unfreeze)

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    args.func(args)
    return 0


if __name__ == "__main__":
    sys.exit(main())
