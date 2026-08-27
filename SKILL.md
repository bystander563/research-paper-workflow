---
name: research-paper-workflow
description: Coordinate paper-oriented problem and dataset scouting, literature-grounded method exploration, external-baseline comparison, experiment iteration, monitoring, and asynchronous PI decisions. Use when the user wants Codex to explore or continue an active research project autonomously while preserving user ownership of the research direction. Do not use for ordinary one-off paper drafting or to invent project-specific data and evaluation protocols.
---

# Research Paper Workflow

Run routine research work autonomously, but make the user choose the scientific
direction at explicit checkpoints. Experiments become useful only after the
task, dataset, scientific gap, and real comparison set are visible.

Project instructions, `AGENTS.md`, frozen contracts, and the user's latest
message override this skill. Do not turn one project's data or evaluation
protocol into a universal rule.

## At a glance

The shortest operational flow is:

```text
user confirms venue/time + domain (+ optional idea)
-> agent scouts task-dataset candidates
-> USER L1 DECISION: task + dataset + project evidence standard
-> agent maps nearest work, external baselines, failure, method, and evidence
-> agent tunes only promising methods to estimate their current-project ceiling
-> USER L2 DECISION: problem + core mechanism + innovation claim
-> agent completes evidence against the L1 standard
-> USER PAPER DECISION: enter writing + headline claim
-> hand off the fixed research package to a submission workflow
```

Use these files by purpose:

| Need | Read or run |
|---|---|
| Determine the current phase and next gate | [references/workflow.md](references/workflow.md) |
| Scout tasks, datasets, papers, baselines, and methods | [references/exploration-policy.md](references/exploration-policy.md) |
| Handle notifications, unanswered questions, and pause behavior | [references/collaboration-policy.md](references/collaboration-policy.md) |
| Create or update L1/L2/L3 project state | [references/research-state.md](references/research-state.md) |
| Record PI questions and confirmed checkpoints | `scripts/research_queue.py` |

## Authority and invariants

- The user owns the active task-dataset direction, the project-specific evidence
  standard, promotion or replacement of the scientific story, entry into paper
  writing, the headline claim, paid compute, and external submission.
- The agent may generate candidates, inspect data, reproduce baselines, run
  screens, tune promising methods, repair code, and close low-potential branches
  within the confirmed direction.
- Silence or a 20-minute timeout grants no new authority. Record direct user
  decisions; do not infer approval from existing code or experiments.
- L1 and L2 are durable scientific state. Keep their current facts, user
  decisions, replacements, and decision-relevant evidence. They are not
  chronological dumps of every attempt.
- L3 is an agent-managed execution layer. Keep, compact, or discard its logs,
  failed runs, tuning traces, and stop-rule notes according to current utility
  and project requirements. There is no universal requirement to archive every
  attempt or stopping rule.
- If an L3 bug or protocol repair invalidates an L2 result, update L2
  immediately. Never preserve a scientific conclusion merely because a corrected
  run is pending.
- This skill creates no generic test-set, sealed-set, external-label, metric,
  second-dataset, or unexposed-dataset protocol. Record such requirements in L1
  only when the user or active project adopts them.

## Activate and resume

Ordinary discussion remains analysis-only. Enter execution when the user asks
to start, continue, run, iterate, or monitor research.

Before open-ended exploration, obtain a user-confirmed submission window and/or
target venue plus the research domain. A starting concept is optional and is a
seed unless the user explicitly freezes it. For a long-running project, resume
from the durable L1/L2 state and PI queue rather than reconstructing decisions
from chat memory.

L1/L2/L3 describe **what information is maintained**. Exploration, confirmed
project, and paper-ready describe **when work happens**. Do not use a layer name
as a workflow phase or treat an implementation milestone as a scientific
approval. Follow the exact transitions in
[references/workflow.md](references/workflow.md).

## Mandatory PI checkpoints

### L1 direction

After scouting a small ranked shortlist, ask the user to select the active task
type and dataset or dataset bundle. The decision packet must also make the
project evidence standard explicit: competitive target, novelty sufficiency,
generalization or second-dataset expectation, and what would count as ready to
consider writing. “Not required” or “decide later” must be a user choice, not an
agent default.

Include task meaning, task-data fit, benchmark headroom, nearest-work collision
risk, external-baseline feasibility, cost, venue/time fit, and the agent's
recommendation. Cheap inspection and verification may continue while waiting,
but sustained method search and broad tuning require a confirmed L1 direction.

Changing the confirmed task, dataset, or evidence standard requires another PI
decision.

### L2 scientific story

Inside the confirmed L1 direction, the agent may derive methods, run cheap
screens, and tune a promising method to estimate its current-project ceiling.
After a ceiling summary and external comparison exist, ask whether to promote
that **problem + core mechanism + innovation claim** into the active paper line,
keep it exploratory, or close it.

The L2 packet must show nearest work, the observed problem, the problem-to-method
chain, the strongest defensible external comparison, our result, remaining
evidence gaps, and the agent's recommendation. The best internal variant does
not become the scientific story automatically. Replacing a confirmed L2 story
requires another PI decision.

### Paper decision

When the confirmed L2 story appears to meet the L1 evidence standard, report the
narrowest supported claim, strongest matched comparison, remaining objection,
and necessary versus optional work. Ask whether to enter writing and what the
headline claim should be. If approved, hand off the fixed L1/L2 evidence package
to a paper-submission workflow; do not silently start a different scientific
story during writing.

## External-baseline gate

“External baseline” means another published method or conventional comparator,
not a second or newly collected dataset.

Before a method receives broad ceiling tuning, identify and source-check the
baseline roster. Before a result is called paper-worthy, obtain at least the key
protocol-matched comparison or mark the comparison explicitly blocked. The
roster should normally include:

- the dataset paper's official reference result or method, when one exists;
- the strongest recent protocol-comparable published method found for that task;
- another published method from a meaningfully different mechanism family;
- a strong simple or conventional baseline;
- internal variants and ablations, kept separate from external methods.

Verify task, split, labels, supervision, inference information, metric, and
evaluation date. Label unmatched published numbers `REPORTED_NOT_MATCHED`.
Reproduced or adapted comparisons are `OFFICIAL_REPRODUCED` or
`MATCHED_ADAPTATION`. If a decision-critical method cannot be run or compared,
record `BLOCKED` or `BASELINE_INCOMPLETE`; do not fill the gap with more internal
variants.

## Iteration rules

- Start from an observed problem: plain-language cause, solution intuition,
  predicted change, minimal mathematical formulation, and minimal
  implementation. Prefer one testable mechanism over an engineering-heavy stack.
- Before broad tuning, require a coherent mechanism, a diagnostic moving as
  predicted, a healthy baseline, and a plausible path to competitiveness.
- For a promising method, use available compute to estimate its current-project
  ceiling. Report the starting and best result, external-baseline gap, resource
  cost, weakness, and paper potential in plain language. A ceiling summary does
  not require an archive of every tuning attempt or its stopping rule.
- Close low-potential branches autonomously after implementation, baseline, and
  diagnostic sanity checks. Notify only when closure changes the project-level
  interpretation or a confirmed choice.
- Model-family changes require notification. Routine metrics, hyperparameters,
  implementation choices, and debugging do not require individual approval.
- Fix deterministic crashes, ignored arguments, paths, and parsing errors
  automatically. Exclude invalid output from scientific evidence.
- Use an available GPU by default. Use CPU or no-GPU mode when requested or
  required by the environment. Never rent paid compute without a PI decision.

## Decisions, notifications, and asynchronous work

PI decisions include L1 selection or change, L2 promotion or replacement,
changes to another user-frozen item, paid cost, the paper decision, and external
submission. Everything else is normally autonomous within project scope.

Important events are notifications rather than questions. Explain them as:

1. 原来想做什么；
2. 实际发生了什么；
3. 为什么准备改变；
4. 接下来做什么。

Send questions as they arise and continue independent authorized work. After 20
minutes, keep an unanswered question queued and batch it with later questions;
do not infer consent. At five unanswered PI decisions, set `PAUSED_FOR_PI` and
stop at the next safe checkpoint. Do not kill an already-running atomic process
unless the user requests a hard stop.

## Reporting and downstream handoff

Lead status reports with:

1. active L1 direction, evidence standard, and any L1 decision needed;
2. active L2 story, external-baseline coverage, and any L2 decision needed;
3. only the L3 issue that changes L1/L2 meaning.

Separate verified facts, agent interpretations, notifications, questions, and
confirmed user decisions. Do not make the user reconstruct scientific state
from run names or call an internally best method competitive.

This skill ends at the user-approved paper handoff. Story locking, drafting,
independent review, revision, compilation, venue-format QA, and submission
belong to a downstream workflow such as `$paper-submission-orchestrator` when it
is installed and applicable. The paper decision authorizes that handoff, not an
arbitrary downstream story packet or external submission.
