# Workflow and gates

This file is the canonical stage model for research exploration and iteration.
It answers three questions: where the work is now, what may continue, and what
must be true before the next phase.

## Layers are not phases

- **L1 direction** and **L2 scientific story** are durable content layers whose
  material state and user decisions must be retained.
- **L3 implementation** is an execution layer whose retention is chosen by the
  agent or active project.
- `discussion`, `exploration`, `confirmed_project`,
  `paper_ready_pending_pi`, and `paper_handoff_approved` are temporal workflow
  phases.
- `PAUSED_FOR_PI` is a pause status that can overlay an execution phase; it is
  not a scientific stage and does not erase the underlying phase.
- Project-instruction maintenance is another overlay. It keeps stable repository
  instructions usable but neither creates a research layer nor advances a
  scientific phase.

Use these exact phase names in documentation and `research_queue.py`.

## Existing-project intake

Run `research_queue.py audit STATE` before resuming any project with workflow
state. Run `agents-audit STATE --cwd WORKING_DIRECTORY` as well when project
instructions exist, the working directory changed, or the controller has no
snapshot for that scope. An existing-scope audit compares against its saved
snapshot and never accepts changed content; use `agents-record` after classifying
an intentional change. If an audited working-directory scope no longer exists,
remove that stale scope with `agents-scope-remove`; removing a scope whose
directory still exists requires PI approval. Legacy approvals without the current structured payload
or scoped decision receipt are reported as needing audit; existing code and
results do not waive that decision. Follow
[agents-maintenance.md](agents-maintenance.md) for instruction content and
change authority.

If no workflow state exists, inspect the active project authority and evidence
before initializing:

- active method research -> initialize or bootstrap the earliest missing
  research checkpoint;
- substantially fixed task, method, experiment package, and manuscript route ->
  hand off to a submission workflow without reconstructing retrospective L1/L2;
- non-paper work -> do not activate this workflow.

## Stage 0: discussion -> exploration

Ordinary explanation, critique, and idea discussion remain read-only. Enter
`exploration` only when the user asks to start, continue, run, iterate, or
monitor research.

Establish the research compass:

- target submission time and/or venue;
- research domain;
- optional user concept and whether it is only a seed or explicitly frozen.

Gate `G0 EXPLORATION_READY`:

- the domain is user-confirmed;
- a venue or submission window is user-confirmed;
- project instructions and existing state have been located;
- the effective project-local instruction chain has been audited when present;
- execution is authorized.

Initialize in `discussion` by default. Starting directly in `exploration` is
allowed only when the venue/window, domain, and actual user instruction are
provided together. Initialization cannot select a later phase. The controller
creates the L1 file and L2 directory rather than relying on each agent to invent
its own layout.

## Stage 1: exploration -> confirmed_project

Scout a small ranked set of task-dataset candidates. For each, check:

- why the task matters;
- whether the dataset genuinely measures that task;
- whether credible performance headroom remains;
- nearest-work collision risk;
- availability of meaningful published comparators;
- at least one credible dataset not previously exposed in the project, or a
  documented search boundary and blocker;
- time, data, and compute feasibility;
- fit to the venue or submission window.

Cheap dataset inspection, literature verification, and baseline-feasibility
work may continue while the choice is pending. Do not start sustained method
search or broad tuning for an unconfirmed direction.

Prepare an L1 decision packet containing:

1. the ranked candidates and agent recommendation;
2. the proposed task type and dataset or dataset bundle;
3. the mandatory unexposed-dataset search result and whether the agent
   recommends adopting it;
4. the project evidence standard, stated as user choices:
   - required competitive bar, such as SOTA, near-SOTA, or another explicit bar;
   - novelty sufficiency standard;
   - whether generalization, a second dataset, or another evidence axis is
     required;
   - what result would justify considering paper writing;
5. unresolved risks and what can continue while the user decides.

Gate `G1 L1_CONFIRMED`:

- task type and dataset are explicitly selected by the user;
- the evidence standard is recorded, including explicit “not required”,
  tentative, or deferred choices where applicable;
- the exact user decision is linked from L1 and its controller decision receipt;
- the decision outcome is `select` or `approve`, not merely “answered”;
- a queued approval is scoped to this direction ID and consumed only here;
- the structured checkpoint contains task, dataset, competitive bar, novelty
  sufficiency, generalization requirement, paper-ready threshold, and the
  unexposed-dataset search result;
- the numeric paper-gain floor is at least 1 percentage point over the strongest
  recent top-conference protocol-matched baseline; a project may raise but not
  lower it;
- no unresolved contradiction exists with another user-frozen field.

Only then enter `confirmed_project`. Replacing the task, dataset, or adopted
evidence standard invalidates G1 and requires another user decision.

## Stage 2: confirmed_project -> L2 scientific story

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
The full matched local reproduction need not be complete at that moment. A
`BLOCKED` or `BASELINE_INCOMPLETE` key comparison may coexist with L2 method
work, but it cannot support a paper-worthy judgment or pass G3.

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
- the controller stores resolvable references to the nearest-work,
  external-baseline, and result records used for the decision;
- unsupported or blocked comparisons are labeled rather than treated as wins;
- the exact user decision is linked from L2 and its controller decision receipt.
- the decision outcome is `select` or `approve`; `reject`, `defer`, and
  `informational` cannot pass G2.
- a queued approval is scoped to this scientific-story ID and consumed only
  here.

An implementation win or internally best variant never passes G2 by itself.
Replacing the confirmed problem, core mechanism, or innovation claim invalidates
G2 and requires another user decision.

## Stage 3: Evidence completion -> paper_ready_pending_pi

Continue experiments inside the confirmed L1/L2 contract. Hyperparameters,
routine metrics, implementation details, diagnostics, and bug repair remain
agent-owned unless the user froze them. Notify model-family changes and any L3
event that changes L1/L2 meaning.

Assess the current package against the L1 evidence standard. Do not silently
replace that standard because results are inconvenient. If a requirement is no
longer sensible, present a proposed L1 change for user decision.

Gate `G3 PAPER_DECISION_READY`:

- G1 and G2 remain valid;
- a primary source identifies the strongest recent top-conference baseline found
  for the same protocol, and the report explains the task, dataset/split, labels,
  supervision/inference information, metric, and evaluation match;
- on a higher-is-better primary metric, our result exceeds that baseline by at
  least the L1 floor, which can never be below 1 percentage point (`0.01` on a
  `0–1` scale or `1.0` on a `0–100` scale);
- the narrowest supported claim is explicit;
- the strongest protocol-matched external comparison is explicit;
- the remaining reviewer-level objection is explicit;
- necessary and optional additional work are separated;
- the package is assessed against every recorded L1 evidence criterion.

Before asking the user, generate a readable project-local paper-decision report
covering the current task, dataset, problem in current/nearest work, innovation, concrete
method, final results, baseline identity/venue/year/source and search scope,
protocol-match evidence, metric scale, baseline score, our score, computed point gain, required floor,
and the remaining G3 assessments. Only after that report exists may the workflow
enter `paper_ready_pending_pi` and ask whether to start paper writing and what
headline claim to use. This is a real user decision even when the agent strongly
recommends proceeding.

The transition into `paper_ready_pending_pi` requires that project-local durable
report and a structured receipt covering its scientific and numeric fields. The
controller checks completeness, arithmetic, the configured floor, provenance,
and artifact locking. It cannot determine whether a venue is genuinely top-tier
or whether two protocols are scientifically matched; the agent must verify and
source those claims before invoking the gate. The phase cannot be set at
initialization or reached without complete typed L1/L2 checkpoints.

The assessment is content-locked at this gate. If it changes before the PI
decision is consumed, rebuild the assessment and present the changed meaning;
the old decision must not authorize the rewritten evidence.

If approved, record a typed `paper` checkpoint containing the confirmed science
checkpoint, headline claim, durable record, and handoff target. Only then enter
`paper_handoff_approved`. This research workflow ends with the durable L1/L2
package as the handoff. Route story locking, drafting, review, revision,
compilation, venue QA, and submission to a downstream paper-submission workflow.
If declined or deferred, continue only within the confirmed research direction
or obtain the needed L1/L2 change. Approval to enter writing does not approve an
arbitrary later story packet or submission action; downstream approval gates
remain separate.

## Pause overlay: PAUSED_FOR_PI

Only active unanswered PI decisions count toward the cap. Notifications and
user-deferred decisions do not. A deferred item remains visible with a recorded
revisit condition and returns to the active queue when that condition is met.

At five unanswered PI decisions:

1. set `PAUSED_FOR_PI`;
2. launch nothing new;
3. stop iteration, polling, monitoring, and analysis at the next safe checkpoint;
4. allow an already-running atomic process to reach a safe end;
5. present the five questions in priority order.

Resume the underlying phase when the unanswered count falls below five unless
the user asks to remain paused. A 20-minute timeout only batches questions; it
never passes a gate.

The controller rejects phase advancement, new active-job registration, and
active-to-active polling or advancement while paused. It also rejects new
project-instruction audit scopes and instruction-maintenance mutations.
Answering questions, recording notifications, read-only status/audit checks, and
marking an already-running job with a safe terminal status remain allowed.

## Active-job recovery

Register every long-running process that must survive context compaction with:

- stable job ID and plain-language purpose;
- reproducible command and/or terminal/session ID;
- `queued` or `running` state;
- next poll time and next action.

Update it to `completed`, `failed`, `blocked`, or `cancelled` when appropriate,
then remove the record when it no longer helps recovery. This is a live L3
index, not a mandatory run archive. The controller records resumability; it does
not schedule, poll, or terminate the process by itself.

## Control audit

`research_queue.py audit STATE` is a control-state audit. It fails when the
current phase lacks a complete typed checkpoint, a decision receipt is unscoped
or incorrectly reused, a core field has conflicting authorities, a required
evidence reference or durable record is missing, a paper-ready assessment is
incomplete or changed after its gate, a project checkpoint record is outside the project, a legacy
approval needs audit, any audited instruction scope changed without a receipt,
non-self-referential L2 evidence changed after confirmation, or an active job
cannot be resumed. It verifies provenance
and availability, not scientific adequacy. `agents-audit` separately reports
instruction precedence and size without treating an oversized file as a
scientific checkpoint failure. Run the control audit at startup, after
migration, and before paper handoff.
