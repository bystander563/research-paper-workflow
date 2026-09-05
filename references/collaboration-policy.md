# Collaboration and conditional execution

Default to a research conversation, not a sequence of forms.
[workflow.md](workflow.md) owns scientific gates; [research-state.md](research-state.md)
owns state and commands. Read monitoring/job details only when they are needed.

## Answer the user's intent

- **Progress:** report L1/L2 changes since the last requested run, meaningful methods tried/retained/closed, representative results and external-baseline gap, current hypothesis and next action. State when evidence is not yet interpretable.
- **Why:** answer the specific question about the problem, intuition, mechanism or evidence. Keep the full reasoning chain available internally; do not recite the project charter every time.
- **Suggestion or challenge:** evaluate the idea and explain what would change. Do not turn tentative discussion into approval or force an immediate decision.
- **Explicit correction or decision:** acknowledge exactly what changes, record the scoped decision and execute its authorized consequences. Do not request a second confirmation merely to satisfy the controller.
- **Ambiguous consequential choice:** ask one concise clarification; continue independent authorized work.

Keep facts, interpretations and user decisions distinguishable without forcing
those headings into every reply. Use as much explanation as this exchange needs.

L3 details are omitted by default, not forbidden. If the user explicitly asks
for technical details, answer directly; subsequent routine reports return to
the macro default unless the user changes that preference. Translate an L3
event into its L2 consequence: for example, "the previous gain is not yet a
valid comparison", not just a stack trace or a process update. Resource,
permission, destructive-action and external-send questions are never hidden.

## Ownership and decisions

The user owns venue/window/domain, adopted L1 direction/evidence standard,
confirmed L2 problem/method/claim, separately frozen choices, paid compute,
semantic authority/scope changes, selected-seed risk acceptance, writing and
headline claims, direct pause/resume and external submission/publication/sends.

Before G2, exploratory problems and method clusters within confirmed L1 may
change autonomously with plain-language notification. After G2, a new candidate
does not overwrite the approved selection. Ordinary evidence updates, metrics,
hyperparameters, debugging and implementation choices need no new decision
unless the user explicitly fixed them. Apply the scientific gate rules in
[workflow.md](workflow.md), not a blanket "all L2 updates require approval" rule.

Capture explicit decisions even without a queued question. Internally,
`select`/`approve` authorize the matching scope, `reject` resolves a choice,
`defer` moves it to a visible queue with a revisit condition, and `informational`
records discussion without resolving the active question. The user need not
write these labels. One clear message may decide several matters; record scoped
receipts, not repeated questions. A generic "continue" cannot approve unrelated
direction changes or paper claims. New decisions supersede old unconsumed ones.

Use `frozen_by_pi` only for additional explicitly fixed choices. Do not duplicate
compass, task, dataset, L2 or paper fields there. A conflict stops only dependent
work; seek a scoped decision if resolution would change an approved choice.

## Notifications without ceremony

Notify changes of exploratory problem path/leaf or method cluster, a promising
method's ceiling result, a change in scientific interpretation or an invalidated
comparison. Describe what changed, why it matters and the next move in plain
language; short related updates can share one message without omitting changes.
Routine failures, individual trials and completed jobs are not automatically
macro notifications. Model-family changes matter when they change the science.

Use `research-update --notify-kind ...` to record a material change and its
notification together. For identity switches, preserve previous/new IDs
internally; a same-leaf refinement uses `problem_path_change`, not fake IDs.
Do not send a second message repeating a notification already communicated.

A genuine PI question states the actual choice, tradeoff, recommendation and
what can continue unanswered. Do not ask approval for an obviously failed
exploratory branch, record maintenance or an ordinary implementation step.

## Alignment without a mandatory audit speech

During explanation, trace the current experiment to the selected direction,
active problem and a prediction that evidence could contradict. If that trace
fails, stop the dependent branch safely and explain the suspected drift.
Repair implementation mismatches autonomously. Ask a scientific decision only
when the repair requires changing an approved direction or mechanism.

Respond to the user's scientific concern before proposing a workflow action.
A thoughtful exchange can change the hypothesis without instantly fixing the
paper story. An explicit scoped instruction, however, is actionable authority.

## Progress windows

Use `status STATE --window` for "现在怎么样" or "从上次开始发生了什么".
It is read-only and does not acknowledge monitor fingerprints.
Report the relevant changes, not every stored field or the entire job registry.
The current focus can be carried forward from the previous boundary; label it
as context when no new result exists.

For result-bearing progress and ceiling updates, lead with the maintained
external opponent, its dataset/metric/score, our comparable result and gap (or
why the gap is not yet valid). Read `current_external_baselines` even when no
baseline changed in this window. Our starting/best/latest values and ablation
gains are secondary. An internal improvement while still below the external
reference must be described that way. Do not repeat a result table in an
unrelated explanation or discussion. Explain any external-reference replacement;
never silently downgrade it to make a candidate appear successful.

A missing legacy window means the since-start history is unavailable, not that
no work happened. Report current verified L1/L2, and only dated, source-supported
changes when their boundary can be established; do not invent a trajectory from
run names or file modification times. Research notes, not job logs, own
decision-relevant scientific conclusions.

## Unanswered decisions and pause

Twenty minutes is a batching window, not consent and not an instruction to
sleep. Timestamp genuine questions, deliver them through the host's asynchronous
input mechanism when available, and continue independent authorized work.
At natural boundaries, group unanswered questions; elapsed time never permits
the dependent action.

At five active unanswered decisions:

1. set `PAUSED_FOR_PI` and launch nothing new;
2. stop iteration, analysis and future polling/wakeups at a safe checkpoint;
3. allow an already-running atomic process to reach a safe end;
4. present the five choices in priority order.

Notifications and deferred items do not count. Deferred items remain visible;
when their stated condition is met, reopen the question instead of inferring an
answer. Resume when active questions fall below five unless the user maintains
a manual pause. A direct `pause` sets `PAUSED_BY_PI`; only an explicit resume
clears it, not silence or an unrelated answer.

While paused, read-only status, answering questions and recording an existing
job's safe terminal outcome remain possible. Do not claim a process was killed
merely because the workflow state says paused.

## Long-running job recovery

Reuse project-native experiment tools and existing terminal sessions.
Register only jobs whose command/session and next action must survive context
loss. Store stable ID, purpose, command/session, status, meaningful next check
and resumable next action. Terminal jobs may be removed when no longer useful;
this is not a mandatory archive. Preserve artifacts needed by active claims.

Prefer native completion/wait mechanisms for a job already running in the
current turn. A state-file lock serializes controller writes, not experiment
launches. Before launching, verify the project does not already have that
active job. Do not let concurrent agents/wakeups own the same scientific state;
use a single responsible executor and no fixed multi-agent team.

## Unattended monitoring

Only when requested, use the available host scheduled-task mechanism. Prefer
the existing conversation's monitor where supported; do not silently create a
new task per check. Keep the actual scheduler handle with the project's recovery
information. No scheduler or available machine/app means resume-on-open only;
tell the user this limitation.

A wakeup should:

1. read `status STATE --compact` and relevant job/result fingerprints;
2. when neither semantic state nor artifacts changed, avoid full L1/L2/literature analysis and remain quiet;
3. when evidence changes, assess it, persist the research update and run at most one authorized next batch;
4. after successful writes, read compact status again and use `monitor-ack --job-id JOB --artifact-fingerprint VALUE` with the new fingerprint;
5. choose the next meaningful check from job progress or an actual decision boundary.

Omitting an artifact update preserves other jobs' acknowledgements; explicit
clearing applies only to the named job. A reschedule is not scientific progress.
An unanswered question crosses its twenty-minute batching boundary only once.
Light checks reduce repeated analysis; a model wakeup is not zero-token work.

Stop future wakeups when the user stops, five questions are active, no authorized
action remains, a required decision/cost blocks all useful work, or the paper
decision gate is reached. A failed experiment alone does not stop an authorized
alternative. An exploratory project without G2 is not an invalid project;
a stale confirmed claim blocks dependent conclusions, not every independent test.

Use the actual host cancellation/pause controls and safe process endpoints.
Distinguish "no new work", "scheduler disabled", and "running job ended".
The controller records recovery/acknowledgements; it does not schedule or kill.

## Conditional instruction and paper work

Read [agents-maintenance.md](agents-maintenance.md) for changed/conflicting
project instructions. Stable rules and source pointers do not need rewriting
after each experiment. Reflecting an already authorized choice does not require
a duplicate scientific decision.

At paper readiness use the existing research record and comparison evidence to
build the report defined by [G3](workflow.md#g3-paper-decision-ready), then ask
the actual writing/claim decision. Selected-seed disclosure and its minimal
private acceptance receipt follow that gate; do not propagate disclosure details
into project or manuscript documents.
