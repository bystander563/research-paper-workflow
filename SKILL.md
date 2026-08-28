---
name: research-paper-workflow
description: Coordinate paper-oriented problem and dataset scouting, literature-grounded method exploration, external-baseline comparison, experiment iteration, monitoring, and asynchronous PI decisions. Use when the user wants Codex to explore or continue an active research project autonomously while preserving user ownership of the research direction. Do not use for ordinary one-off paper drafting or to invent project-specific data and evaluation protocols.
---

# Research Paper Workflow

Run routine research work autonomously inside a user-confirmed direction. The
user chooses the scientific direction at explicit checkpoints; elapsed time,
existing code, or a good result never substitutes for that decision.

The user's latest explicit instruction, confirmed project contracts, and scoped
project instructions (including `AGENTS.md`) govern this skill. Resolve any
conflict before dependent work. Do not turn one project's protocol into a
universal rule.

## Shortest flow

```text
user confirms venue/time + domain (+ optional idea)
-> scout meaningful task-dataset pairs
-> USER L1: select task + dataset + project evidence standard
-> map nearest work, external baselines, failure, method, and evidence
-> agent locks the primary metric, scale, and direction before broad tuning
-> tune only promising methods to estimate their current-project ceiling
-> USER L2: promote problem + core mechanism + innovation claim
-> complete the L1 evidence standard
-> beat the strongest recent top-conference protocol-matched baseline by >=1 point
-> generate the paper-decision report
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
- project-specific acceptance of favorable-seed selection risk;
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
- During L1 scouting, actively search for and report at least one credible
  dataset not previously exposed in the project, or report why none is
  currently feasible. This search is mandatory; adopting it as a second
  dataset or generalization requirement remains the user's L1 decision.
- No generic sealed-set, external-label, project-independent metric selection,
  or evaluation protocol is created by this skill. Put adopted requirements in
  L1 and the agent-owned project metric in the evaluation anchor.
- External baselines are published methods or conventional comparators, not
  another dataset. Keep them separate from internal variants.
- Before broad tuning, the agent must lock the higher-is-better primary metric,
  its `0–1` or `0–100` scale, and its direction in the controller. This is an
  agent-owned protocol anchor, not a new PI question. Replacing it invalidates
  the previous anchor for the paper gate; earlier results remain exploratory
  until evidence is produced or explicitly reassessed under the new anchor.
- Do not impose a universal aggregation rule, seed count, or significance test.
  The paper report must contain project-appropriate repeat, uncertainty, or
  stability evidence.
- “Ready for a paper decision” has a hard numeric floor: on the higher-is-better
  primary metric, the method must beat the strongest recent top-conference
  protocol-matched baseline by at least 1 percentage point. Interpret this as
  `0.01` on a `0–1` scale or `1.0` on a `0–100` scale. L1 may set a stricter
  floor, never a lower one.
- Project checkpoint and assessment records must be project-local. External
  literature or evidence artifacts may be referenced read-only.
- `AGENTS.md` is a bounded stable contract and router, not research state.

## Activate or resume

Ordinary discussion is analysis-only. Enter execution when the user asks to
start, continue, run, iterate, or monitor.

Before open-ended exploration, obtain a user-confirmed venue/submission window
and domain. An optional idea is a seed unless the user explicitly freezes an
additional constraint around it. When changing only venue/domain, preserve the
current optional idea unless the user explicitly clears it.

Resolve `<controller>` as `scripts/research_queue.py` relative to the directory
containing this `SKILL.md`, not the active research project's working
directory. Keep the state itself at
`<project>/.codex/research-paper-workflow.json`.

For an existing state, run `python <controller> audit STATE`. Audit the relevant
project-instruction scope when instructions exist or the working directory
changed. Instruction audit is compare-only for an existing scope; an unrecorded
change must be classified and recorded, not accepted by rerunning the audit.

If a project has no workflow state, classify it first. Route a substantially
fixed task, method, experiment package, and manuscript direction directly to a
submission workflow. For active method research, initialize the earliest
missing checkpoint; do not infer it from historical experiments.

## PI checkpoints

### L1 direction

Scout a small ranked shortlist. Show task meaning, task-data fit, headroom,
nearest-work collision risk, external-baseline feasibility, cost, venue/time
fit, the result of the unexposed-dataset search, and a recommendation. Ask the
user to select the task-dataset pair and set the competitive bar, novelty
sufficiency, generalization/second-dataset expectation, and additional
paper-ready requirements. These descriptive requirements may add conditions
but cannot lower the separately stored numeric paper-gain floor of at least 1
percentage point. “Not required” and “decide later” are user choices for
adoption, not permission to skip the search or lower this competitive floor.

Cheap verification may continue while waiting. Sustained method search and
broad tuning require confirmed L1. Changing L1 requires a new scoped decision.

### L2 scientific story

Inside L1, map current primary literature and real external baselines, diagnose
one concrete failure, derive a problem-to-intuition-to-mathematics mechanism,
run a falsifiable screen, and tune only promising candidates. After a ceiling
summary and external comparison exist, ask whether to promote the problem,
core mechanism, and innovation claim.

Before broad ceiling tuning, record the agent-owned evaluation anchor. Changing
the metric name, scale, or direction later does not require PI approval, but the
old anchor's results cannot directly satisfy the paper gate.

L2 must link resolvable nearest-work, external-baseline, and result evidence.
The best internal variant never becomes the story automatically. Changing L2
requires a new scoped decision.

### Paper decision

When L2 appears to meet L1, verify from primary sources that the comparison is
the strongest recent top-conference baseline found under the same task,
dataset/split, labels, inference information, metric, and evaluation procedure.
Do not ask for a paper decision unless the primary result clears the configured
gain floor.

First create a project-local paper-decision report containing the current task,
dataset, problem in current/nearest work, innovation, concrete method, final
results, baseline identity/venue/year/source and literature-search scope,
protocol-match evidence, the locked metric and scale, evidence tied to the
current anchor, baseline and our score, computed point gain, required floor,
project-appropriate stability evidence, every other L1 criterion, the narrowest
supported claim, strongest remaining objection, and necessary versus optional
work. Then ask whether to enter writing and which headline claim to use. Only a
typed paper checkpoint may enter `paper_handoff_approved`. If the assessment
changes after this gate, reassess it before seeking or consuming the paper
decision.

If the proposed headline result selects `n` favorable seeds from a larger pool,
show the user the total pool, selection rule, and scientific risk in the
decision conversation. This is a real scoped PI risk decision. Do not copy that
detailed disclosure into L1/L2, result cards, the paper-decision report,
`AGENTS.md`, README, or downstream manuscript artifacts. Keep only the minimal
controller receipt needed to prove that the project-specific risk was accepted.

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
Register long-running work that must survive context compaction. When the user
explicitly requests unattended monitoring and the host supports scheduled
tasks, use a scheduled task only as a state-aware wakeup: choose the next
meaningful check time from job progress or the 20-minute question window, read
compact durable state first, and avoid full reasoning when nothing changed.
Pause or stop future wakeups before costly work when the user stops, five PI
questions are active, L1/L2 is invalid, a macro choice or paid compute is
required, or the paper gate is reached. If scheduled tasks are unavailable,
fall back to the job registry and resume when a task is opened again. The
controller records recovery state but does not itself schedule or poll.

When the user asks what the agent is doing, challenges the rationale, or wants
to discuss an in-progress method, run a read-only drift check. Trace the current
action through compass -> L1 -> L2 -> tested prediction and state what evidence
would falsify it. The discussion is not approval. If the trace fails, stop only
that branch, report the suspected drift plainly, and obtain a scoped L1/L2
decision before changing the scientific direction.

## Routing

| Need | Read or run |
|---|---|
| Phase transitions and gates | [references/workflow.md](references/workflow.md) |
| Task/data/literature/baseline/method judgment | [references/exploration-policy.md](references/exploration-policy.md) |
| Questions, notifications, timeout, pause | [references/collaboration-policy.md](references/collaboration-policy.md) |
| L1/L2/L3 record content | [references/research-state.md](references/research-state.md) |
| Project `AGENTS.md` maintenance | [references/agents-maintenance.md](references/agents-maintenance.md) |
| State, checkpoints, jobs, and audits | `<skill-dir>/scripts/research_queue.py` |

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
