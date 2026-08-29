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
-> map nearest-work problem clusters + adopted-dataset baseline roster
-> retain the unresolved problem path to the deepest defensible active leaf
-> bind paper-grade method clusters to that leaf
-> agent locks the scientific scope + metric before broad tuning
-> screen clusters; tune only promising ones; change problem when exhausted
-> USER L2: promote problem path + active leaf + method cluster + core mechanism + innovation
-> complete the L1 evidence standard
-> clear the canonical G3 matched-baseline gain floor
-> generate the paper-decision report
-> USER PAPER: enter writing + select headline claim
-> hand off the fixed package to the submission workflow
```

L1/L2/L3 describe what information is maintained. `discussion`, `exploration`,
`confirmed_project`, `paper_ready_pending_pi`, and
`paper_handoff_approved` describe when work happens. Instruction maintenance
and `PAUSED_FOR_PI`/`PAUSED_BY_PI` are overlays, not scientific layers or
approvals.

## User authority

The user decides:

- confirmation or change of the venue/submission window and research domain;
- L1 task-dataset direction and its evidence standard;
- confirmed L2 problem path, active leaf, method cluster, core mechanism, and
  innovation claim;
- any additional explicitly frozen project choice;
- semantic changes to stable project instructions;
- paid compute or rental;
- project-specific acceptance of favorable-seed selection risk;
- entry into paper writing and the headline claim;
- direct pause/resume and withdrawal of an approved paper handoff;
- external submission, publication, or sending.

The agent may scout candidates, inspect data, reproduce baselines, run cheap
screens, tune promising methods, repair code, and close low-potential branches
within the confirmed direction. Metrics, hyperparameters, implementation
choices, and routine debugging do not need approval and remain internal L3.
User-facing supervision is macro-only: report model-family changes only when
they change L2 meaning, every problem-path/active-leaf or method-cluster switch, and
the L1/L2 consequence—not the engineering details—when a repair changes
scientific meaning. Before L2 confirmation,
problem-path/leaf/method-cluster switches inside confirmed L1 are notification-only;
replacing an already confirmed L2 selection still requires a scoped user
decision. Resolve engineering problems autonomously in L3.

Silence or a 20-minute timeout grants no authority. Record direct user decisions
even when no question was queued. A newer decision for the same target
supersedes every older unconsumed approval.

## Core invariants

- L1 and L2 are durable, selective scientific state. Preserve current facts,
  decision-relevant evidence, user decisions, and material replacements—not
  every attempt.
- L1 is the user-confirmed task/dataset scope. L2 retains only the unresolved
  problem path needed to reach the deepest defensible active leaf; one node is
  valid, and fixed or irrelevant ancestors must not be fabricated. The method,
  falsifiable prediction, and innovation attach to that leaf. If its credible
  clusters fail, activate another justified leaf rather than accumulating
  engineering patches.
- Each L2 core candidate explains why an ordinary average, weighted fusion,
  heuristic ensemble, or module stack cannot solve the active leaf. Such devices
  may be L3 tools, controls, or baselines; weighting is not rejected when the
  actual contribution is a new estimand, objective, constraint, mechanism, or
  theory and the mechanism-sensitive evidence tests that scientific object.
- L3 is agent/project-managed. Keep or discard logs, failed runs, tuning traces,
  and stop notes according to current utility and project rules. Never delete
  existing artifacts merely because this skill would not have required them.
- A corrected bug or protocol invalidation must propagate to L2 immediately.
- L3 never becomes the user's supervision interface. Jobs, commands, sessions,
  raw errors, debugging, and implementation detail stay internal. If an L3
  event changes evidence or scientific meaning, expose only its translated
  L1/L2 consequence. Paid compute, permissions, destructive actions, data
  safety, and external sends remain macro authorization matters.
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
- Maintain a dataset-indexed external-baseline row for every adopted dataset:
  identify the strongest recent top-conference protocol-match found for that
  dataset and keep its venue/year/source/search scope. Each row explicitly
  records protocol status and coverage or a concrete blocker for the dataset
  paper, recent top-conference comparator, a different published mechanism, and
  a strong simple baseline. Rows may be `IDENTIFIED` or `BLOCKED` during
  exploration; every row must be `MATCHED` and its protocol status must be
  `VERIFIED_MATCH` at G3.
  Never carry one dataset's score or comparator across to another dataset.
- Before broad tuning, the agent must lock the ordered problem path, active leaf,
  method cluster, falsifiable prediction, higher-is-better primary metric, its
  `0–1` or `0–100` scale, and its direction in the controller. This is an
  agent-owned scientific-and-metric anchor, not a new PI question. Replacing any
  anchored field invalidates the previous anchor for the paper gate; earlier
  results remain exploratory until evidence is produced or explicitly
  reassessed under the new anchor.
- Do not impose a universal aggregation rule, seed count, or significance test.
  The paper report must contain project-appropriate repeat, uncertainty, or
  stability evidence.
- “Ready for a paper decision” must clear the canonical numeric floor in
  [workflow G3](references/workflow.md).
  L1 may set a stricter floor, never a lower one.
- Project checkpoint and assessment records must be project-local. External
  literature or evidence artifacts may be referenced read-only.
- `AGENTS.md` is a bounded stable contract and router, not research state.
- Project instructions are discovered once per Codex run. After changing an
  `AGENTS.md` file, keep following the instruction chain already loaded for the
  current run; treat the recorded file as active guidance from the next run.

## Activate or resume

Ordinary discussion is analysis-only. Enter execution when the user asks to
start, continue, run, iterate, or monitor.

Before open-ended exploration, obtain a user-confirmed venue/submission window
and domain. An optional idea is a seed unless the user explicitly freezes an
additional constraint around it. When changing only venue/domain, preserve the
current optional idea unless the user explicitly clears it. Changing or clearing
only that optional seed does not invalidate an already confirmed L1/L2 story.

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

For every explicit user instruction to start, continue, run, iterate, or begin
monitoring, start the replace-on-next-instruction reporting window with
`window-start` before scientific execution. Initialization directly into
`exploration` creates the first window. Scheduled wakeups continue the same
window and never create one. A progress query is read-only and never resets it.
If one message asks for status and then continuation, report the old window
first and start the new window second. See the canonical lifecycle in
[workflow.md](references/workflow.md).

## PI checkpoints

### L1 direction

Scout a small ranked shortlist. Show task meaning, task-data fit, headroom,
nearest-work collision risk, external-baseline feasibility, cost, venue/time
fit, the result of the unexposed-dataset search, and a recommendation. Ask the
user to select the task-dataset pair and set the competitive bar, novelty
sufficiency, generalization/second-dataset expectation, and additional
paper-ready requirements. These descriptive requirements may add conditions
but cannot lower the separately stored canonical G3 numeric paper-gain floor.
“Not required” and “decide later” are user choices for
adoption, not permission to skip the search or lower this competitive floor.

Cheap verification may continue while waiting. Sustained method search and
broad tuning require confirmed L1. Changing L1 requires a new scoped decision.

### L2 scientific story

Inside L1, cluster current primary literature by the unresolved problem and keep
an ordered active path ending at the deepest defensible paper-grade leaf. Start
the path at the first unresolved layer; do not restate fixed L1 scope, and allow
a one-node path. Maintain a source-checked external-baseline roster for every
adopted dataset and organize solutions as leaf-linked method clusters with a
shared intuition, mathematics, falsifiable prediction, and simple-combination
counterfactual. Screen a representative minimal method, tune only promising
clusters, and move to another leaf when credible clusters are exhausted. Notify
each problem-path, active-leaf, or method-cluster change in plain language.
After a ceiling summary and external
comparison exist, ask whether to promote the problem path, active leaf, method
cluster, core mechanism, and innovation claim.

Before broad ceiling tuning, record the full adopted-dataset baseline roster,
then lock the ordered problem path, active leaf, method cluster, falsifiable
prediction, primary metric, scale, and direction in the agent-owned evaluation
anchor. Replacing any anchored scientific or metric field needs no extra PI
question during exploration, but old-anchor results cannot directly satisfy the
paper gate. G2 confirmation and G3 evidence must match the current anchor.

L2 must link resolvable problem-portfolio, nearest-work, external-baseline, and
result evidence. Its baseline record maintains one row per adopted dataset and
keeps the external comparator and our matched result together.
The best internal variant never becomes the story automatically. Changing L2
requires a new scoped decision.

### Paper decision

When L2 appears to meet L1, verify from primary sources that the comparison is
the strongest recent top-conference baseline found under the same task,
dataset/split, labels, inference information, metric, and evaluation procedure.
Do not ask for a paper decision unless the primary result clears the configured
gain floor.

First create a project-local paper-decision report containing the current task,
dataset, compact problem path and active leaf, problem in current/nearest work,
innovation, concrete method, final
results, a per-dataset baseline matrix, the primary comparison dataset,
baseline identity/venue/year/source and literature-search scope,
protocol-match evidence, the locked metric and scale, evidence tied to the
current anchor, baseline and our score, computed point gain, required floor,
project-appropriate stability evidence, every other L1 criterion, the narrowest
supported claim, strongest remaining objection, and necessary versus optional
work. Then ask whether to enter writing and which headline claim to use. Only a
typed paper checkpoint may enter `paper_handoff_approved`. If the assessment
changes after this gate, reassess it before seeking or consuming the paper
decision. A queued paper question must be created and answered after the current
report; never reuse approval from an earlier or pre-report packet.

If the proposed headline result selects `n` favorable seeds from a larger pool,
show the user the total pool, selection rule, and scientific risk in the
decision conversation. This is a real scoped PI risk decision. Do not copy that
detailed disclosure into L1/L2, result cards, the paper-decision report,
`AGENTS.md`, README, or downstream manuscript artifacts. Keep only the minimal
controller receipt needed to prove that the project-specific risk was accepted.

## Execution and collaboration

Before broad ceiling tuning, source-check the external comparison roster and
ensure a plausible path to competitiveness. Prefer one testable mechanism over
an engineering-heavy stack. Keep runtime, data plumbing, hyperparameters,
ordinary bugs, and implementation repairs in L3. Use available GPU compute by default; use CPU or
no-GPU mode when requested or required. Never rent paid compute without a user
decision.

For a promising method cluster, report its starting and best result, matched-baseline
gap, stability, cost, weakness, and paper potential in plain language. Close a
well-checked low-potential branch autonomously and notify only when the closure
changes project-level interpretation or a confirmed choice.

Questions use stable targets. `select`/`approve` authorize the matching target;
`reject` resolves it; `informational` leaves it active; `defer` moves it to a
visible deferred queue with a revisit condition. A queued approval is consumed
once. Notifications never count toward the cap.

Continue independent authorized work while questions are unanswered. At five
active PI decisions, set `PAUSED_FOR_PI` and stop at the next safe checkpoint.
The user may explicitly pause all execution without filling the five-question
queue; use the controller's `pause`/`resume` commands and do no active work while
`PAUSED_BY_PI`. If an approved paper handoff is withdrawn, use `paper-revoke`;
retain L1/L2, clear the paper authorization, and require a rebuilt report and a
new paper decision.

Register long-running work that must survive context compaction with a
reproducible command or session, a meaningful next-check time, and a concrete
next action. When the user explicitly requests unattended monitoring and the
host supports scheduled
tasks, use a scheduled task only as a state-aware wakeup: choose the next
meaningful check time from job progress or the 20-minute question window, read
`status STATE --compact` first, compare `wakeup_changed_since_ack`, and compare
each current job/result artifact fingerprint with that job's entry in
`acknowledged_artifact_fingerprints`.
Avoid loading the full scientific state or reasoning when neither changed.
After successfully processing a change, persist it with
`monitor-ack --job-id JOB --artifact-fingerprint VALUE`; omission preserves
other jobs and explicit clearing affects only the named job. Do not
acknowledge before the resulting state is safely recorded. If processing
changed workflow state, read compact status again and acknowledge the new
fingerprint, not the pre-processing one. A mere reschedule
changes the exact state hash but not this semantic
wakeup fingerprint; an unanswered question crossing the 20-minute batching
boundary changes it once.
Pause or stop future wakeups before costly work when the user stops, five PI
questions are active, L1/L2 is invalid, a macro choice or paid compute is
required, or the paper gate is reached. If scheduled tasks are unavailable,
fall back to the job registry and resume when a task is opened again. For a
desktop-local project, monitoring also depends on the computer and app
remaining available; use the narrowest permissions that can run the known
project command and update its scoped state. The controller records recovery
state but does not itself schedule or poll.

When the user asks what the agent is doing, challenges the rationale, or wants
to discuss an in-progress method, run a read-only drift check. Trace the current
action through compass -> L1 -> active L2 problem path/leaf -> tested prediction and state what evidence
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

For “窗口现在什么情况”, “跑到哪了”, “从上次开始有什么变化”, or an equivalent
progress request, read `status STATE --window`. Lead with the window boundary,
then L1 task/dataset changes, L2 problem-path/active-leaf and method-cluster attempts and their
representative external-baseline gaps, the current macro focus and next action,
and finally notifications and real PI questions. Do not expose L3 jobs,
commands, sessions, bugs, raw errors, or engineering summaries. Translate any
scientifically material L3 event into its L1/L2 consequence. Separate verified
facts, agent interpretation, notifications, PI questions, and confirmed user
decisions. The canonical user-facing boundary and report semantics are in
[collaboration-policy.md](references/collaboration-policy.md).

This skill ends at the user-approved paper handoff. Story locking, drafting,
review, revision, compilation, venue QA, and submission belong downstream, such
as `$paper-submission-orchestrator` when applicable. Paper handoff is not
authorization for external submission.
