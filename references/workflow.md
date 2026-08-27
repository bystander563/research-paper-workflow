# Workflow and gates

This file is the canonical stage model for research exploration and iteration.
It answers three questions: where the work is now, what may continue, and what
must be true before the next phase.

## Layers are not phases

- **L1 direction** and **L2 scientific story** are durable content layers whose
  material state and user decisions must be retained.
- **L3 implementation** is an execution layer whose retention is chosen by the
  agent or active project.
- `DISCUSSION`, `EXPLORATION`, `CONFIRMED_PROJECT`, and
  `PAPER_READY_PENDING_PI` are temporal workflow phases.
- `PAUSED_FOR_PI` is a pause status that can overlay an execution phase; it is
  not a scientific stage and does not erase the underlying phase.

Use these exact phase names in documentation and `research_queue.py`.

## Stage 0: DISCUSSION -> EXPLORATION

Ordinary explanation, critique, and idea discussion remain read-only. Enter
`EXPLORATION` only when the user asks to start, continue, run, iterate, or
monitor research.

Establish the research compass:

- target submission time and/or venue;
- research domain;
- optional user concept and whether it is only a seed or explicitly frozen.

Gate `G0 EXPLORATION_READY`:

- the domain is user-confirmed;
- a venue or submission window is user-confirmed;
- project instructions and existing state have been located;
- execution is authorized.

## Stage 1: EXPLORATION -> CONFIRMED_PROJECT

Scout a small ranked set of task-dataset candidates. For each, check:

- why the task matters;
- whether the dataset genuinely measures that task;
- whether credible performance headroom remains;
- nearest-work collision risk;
- availability of meaningful published comparators;
- time, data, and compute feasibility;
- fit to the venue or submission window.

Cheap dataset inspection, literature verification, and baseline-feasibility
work may continue while the choice is pending. Do not start sustained method
search or broad tuning for an unconfirmed direction.

Prepare an L1 decision packet containing:

1. the ranked candidates and agent recommendation;
2. the proposed task type and dataset or dataset bundle;
3. the project evidence standard, stated as user choices:
   - required competitive bar, such as SOTA, near-SOTA, or another explicit bar;
   - novelty sufficiency standard;
   - whether generalization, a second dataset, or another evidence axis is
     required;
   - what result would justify considering paper writing;
4. unresolved risks and what can continue while the user decides.

Gate `G1 L1_CONFIRMED`:

- task type and dataset are explicitly selected by the user;
- the evidence standard is recorded, including explicit “not required”,
  tentative, or deferred choices where applicable;
- the exact user decision is linked from L1 and the queue checkpoint;
- no unresolved contradiction exists with another user-frozen field.

Only then enter `CONFIRMED_PROJECT`. Replacing the task, dataset, or adopted
evidence standard invalidates G1 and requires another user decision.

## Stage 2: CONFIRMED_PROJECT -> L2 scientific story

Within the confirmed L1 direction:

1. map the nearest conceptual work from primary sources;
2. identify the concrete failure or limitation to improve;
3. build the external-baseline roster;
4. derive a problem -> intuition -> predicted change -> mathematics -> minimal
   implementation chain;
5. run a cheap falsifiable screen;
6. give broad tuning only to candidates with credible potential;
7. compare the resulting ceiling summary with real external methods.

The baseline roster must be identified and source-checked before broad tuning.
The full matched local reproduction need not be complete at that moment. Before
calling a result paper-worthy, however, at least the key protocol-matched
comparison must exist or remain explicitly `BLOCKED`/`BASELINE_INCOMPLETE`.

Prepare an L2 decision packet containing:

- the observed problem and plain-language cause;
- one concrete example of how a strong baseline fails;
- solution intuition, predicted diagnostic, mathematical mechanism, and minimal
  implementation;
- proposed innovation claim and exact difference from nearest work;
- external-baseline roster and comparability status;
- our decision-relevant results and current-project ceiling summary;
- remaining evidence gap, paper potential, and agent recommendation.

The packet records the selected scientific evidence, not every trial, tuning
trajectory, failed branch, or stopping rule.

Gate `G2 L2_CONFIRMED`:

- an explicit user decision promotes the identified problem + core mechanism +
  innovation claim;
- L2 links to its L1 direction, verified nearest work, external comparison, and
  decision-relevant result evidence;
- unsupported or blocked comparisons are labeled rather than treated as wins;
- the exact user decision is linked from L2 and the queue checkpoint.

An implementation win or internally best variant never passes G2 by itself.
Replacing the confirmed problem, core mechanism, or innovation claim invalidates
G2 and requires another user decision.

## Stage 3: Evidence completion -> PAPER_READY_PENDING_PI

Continue experiments inside the confirmed L1/L2 contract. Hyperparameters,
routine metrics, implementation details, diagnostics, and bug repair remain
agent-owned unless the user froze them. Notify model-family changes and any L3
event that changes L1/L2 meaning.

Assess the current package against the L1 evidence standard. Do not silently
replace that standard because results are inconvenient. If a requirement is no
longer sensible, present a proposed L1 change for user decision.

Gate `G3 PAPER_DECISION_READY`:

- G1 and G2 remain valid;
- the narrowest supported claim is explicit;
- the strongest protocol-matched external comparison is explicit;
- the remaining reviewer-level objection is explicit;
- necessary and optional additional work are separated;
- the package is assessed against every recorded L1 evidence criterion.

Enter `PAPER_READY_PENDING_PI` and ask whether to start paper writing and what
headline claim to use. This is a real user decision even when the agent strongly
recommends proceeding.

If approved, this research workflow ends with the durable L1/L2 package as the
handoff. Route story locking, drafting, review, revision, compilation, venue QA,
and submission to a downstream paper-submission workflow. If declined, continue
only within the confirmed research direction or obtain the needed L1/L2 change.
Approval to enter writing does not approve an arbitrary later story packet or
submission action; downstream approval gates remain separate.

## Pause overlay: PAUSED_FOR_PI

Only unanswered PI decisions count toward the cap. Notifications do not.

At five unanswered PI decisions:

1. set `PAUSED_FOR_PI`;
2. launch nothing new;
3. stop iteration, polling, monitoring, and analysis at the next safe checkpoint;
4. allow an already-running atomic process to reach a safe end;
5. present the five questions in priority order.

Resume the underlying phase when the unanswered count falls below five unless
the user asks to remain paused. A 20-minute timeout only batches questions; it
never passes a gate.
