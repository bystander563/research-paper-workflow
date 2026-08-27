---
name: research-paper-workflow
description: Coordinate paper-oriented problem and dataset scouting, literature-grounded method exploration, external-baseline comparison, experiment iteration, monitoring, and asynchronous PI decisions. Use when the user wants Codex to explore or continue an active research project autonomously while preserving user ownership of the research direction. Do not use for ordinary one-off paper drafting or to invent project-specific data and evaluation protocols.
---

# Research Paper Workflow

Run routine research work autonomously inside a user-confirmed direction. The
user chooses the scientific direction at explicit checkpoints; elapsed time,
existing code, or a good result never substitutes for that decision.

Project instructions, `AGENTS.md`, frozen contracts, and the user's latest
message override this skill. Do not turn one project's protocol into a universal
rule.

## Shortest flow

```text
user confirms venue/time + domain (+ optional idea)
-> scout meaningful task-dataset pairs
-> USER L1: select task + dataset + project evidence standard
-> map nearest work, external baselines, failure, method, and evidence
-> tune only promising methods to estimate their current-project ceiling
-> USER L2: promote problem + core mechanism + innovation claim
-> complete the L1 evidence standard
-> USER PAPER: enter writing + select headline claim
-> hand off the fixed package to the submission workflow
```

L1/L2/L3 describe what information is maintained. `discussion`, `exploration`,
`confirmed_project`, `paper_ready_pending_pi`, and
`paper_handoff_approved` describe when work happens. Instruction maintenance
and `PAUSED_FOR_PI` are overlays, not scientific layers or approvals.

## User authority

The user decides:

- confirmation or change of the venue/submission window and research domain;
- L1 task-dataset direction and its evidence standard;
- L2 problem, core mechanism, and innovation claim;
- any additional explicitly frozen project choice;
- semantic changes to stable project instructions;
- paid compute or rental;
- entry into paper writing and the headline claim;
- external submission, publication, or sending.

The agent may scout candidates, inspect data, reproduce baselines, run cheap
screens, tune promising methods, repair code, and close low-potential branches
within the confirmed direction. Metrics, hyperparameters, implementation
choices, and routine debugging do not need approval. Notify model-family
changes and any implementation repair that changes scientific meaning.

Silence or a 20-minute timeout grants no authority. Record direct user decisions
even when no question was queued. A newer decision for the same target
supersedes every older unconsumed approval.

## Core invariants

- L1 and L2 are durable, selective scientific state. Preserve current facts,
  decision-relevant evidence, user decisions, and material replacements—not
  every attempt.
- L3 is agent/project-managed. Keep or discard logs, failed runs, tuning traces,
  and stop notes according to current utility and project rules. Never delete
  existing artifacts merely because this skill would not have required them.
- A corrected bug or protocol invalidation must propagate to L2 immediately.
- Compass, L1, L2, and paper fields have one typed source of truth. Use
  `frozen_by_pi` only for additional choices.
- No generic sealed-set, external-label, metric, second-dataset, or unexposed-
  dataset protocol is created by this skill. Put adopted requirements in L1.
- External baselines are published methods or conventional comparators, not
  another dataset. Keep them separate from internal variants.
- Project checkpoint and assessment records must be project-local. External
  literature or evidence artifacts may be referenced read-only.
- `AGENTS.md` is a bounded stable contract and router, not research state.

## Activate or resume

Ordinary discussion is analysis-only. Enter execution when the user asks to
start, continue, run, iterate, or monitor.

Before open-ended exploration, obtain a user-confirmed venue/submission window
and domain. An optional idea is a seed unless the user explicitly freezes an
additional constraint around it.

For an existing state, run `scripts/research_queue.py audit STATE`. Audit the
relevant project-instruction scope when instructions exist or the working
directory changed. Instruction audit is compare-only for an existing scope; an
unrecorded change must be classified and recorded, not accepted by rerunning
the audit.

If a project has no workflow state, classify it first. Route a substantially
fixed task, method, experiment package, and manuscript direction directly to a
submission workflow. For active method research, initialize the earliest
missing checkpoint; do not infer it from historical experiments.

## PI checkpoints

### L1 direction

Scout a small ranked shortlist. Show task meaning, task-data fit, headroom,
nearest-work collision risk, external-baseline feasibility, cost, venue/time
fit, and a recommendation. Ask the user to select the task-dataset pair and set
the competitive bar, novelty sufficiency, generalization/second-dataset
expectation, and paper-ready threshold. “Not required” and “decide later” are
user choices.

Cheap verification may continue while waiting. Sustained method search and
broad tuning require confirmed L1. Changing L1 requires a new scoped decision.

### L2 scientific story

Inside L1, map current primary literature and real external baselines, diagnose
one concrete failure, derive a problem-to-intuition-to-mathematics mechanism,
run a falsifiable screen, and tune only promising candidates. After a ceiling
summary and external comparison exist, ask whether to promote the problem,
core mechanism, and innovation claim.

L2 must link resolvable nearest-work, external-baseline, and result evidence.
The best internal variant never becomes the story automatically. Changing L2
requires a new scoped decision.

### Paper decision

When L2 appears to meet L1, create a project-local assessment of every L1
criterion. Report the narrowest supported claim, strongest matched comparison,
remaining reviewer objection, and necessary versus optional work. Ask whether
to enter writing and which headline claim to use. Only a typed paper checkpoint
may enter `paper_handoff_approved`.

## Execution and collaboration

Before broad ceiling tuning, source-check the external comparison roster and
ensure a plausible path to competitiveness. Prefer one testable mechanism over
an engineering-heavy stack. Use available GPU compute by default; use CPU or
no-GPU mode when requested or required. Never rent paid compute without a user
decision.

For a promising method, report its starting and best result, matched-baseline
gap, stability, cost, weakness, and paper potential in plain language. Close a
well-checked low-potential branch autonomously and notify only when the closure
changes project-level interpretation or a confirmed choice.

Questions use stable targets. `select`/`approve` authorize the matching target;
`reject` resolves it; `informational` leaves it active; `defer` moves it to a
visible deferred queue with a revisit condition. A queued approval is consumed
once. Notifications never count toward the cap.

Continue independent authorized work while questions are unanswered. At five
active PI decisions, set `PAUSED_FOR_PI` and stop at the next safe checkpoint.
Register long-running work that must survive context compaction. The skill does
not wake, poll, or schedule itself.

## Routing

| Need | Read or run |
|---|---|
| Phase transitions and gates | [references/workflow.md](references/workflow.md) |
| Task/data/literature/baseline/method judgment | [references/exploration-policy.md](references/exploration-policy.md) |
| Questions, notifications, timeout, pause | [references/collaboration-policy.md](references/collaboration-policy.md) |
| L1/L2/L3 record content | [references/research-state.md](references/research-state.md) |
| Project `AGENTS.md` maintenance | [references/agents-maintenance.md](references/agents-maintenance.md) |
| State, checkpoints, jobs, and audits | `scripts/research_queue.py` |

Read only the references relevant to the current operation. The controller
checks authority, provenance, path scope, and artifact availability; it does not
judge scientific adequacy or grant permission.

## Reporting and handoff

Lead with the active L1 direction/evidence standard, active L2 story/external
comparison, and only the L3 issue that changes their meaning. Separate verified
facts, agent interpretation, notifications, PI questions, and confirmed user
decisions. Explain changes as: intended action, actual result, why it matters,
and next action.

This skill ends at the user-approved paper handoff. Story locking, drafting,
review, revision, compilation, venue QA, and submission belong downstream, such
as `$paper-submission-orchestrator` when applicable. Paper handoff is not
authorization for external submission.
