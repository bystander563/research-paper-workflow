# Collaboration policy

Read this reference for long-running research execution, especially when the
user may be away while experiments continue. The canonical phase and gate model
is [workflow.md](workflow.md); the layered retention contract is
[research-state.md](research-state.md).

## Authority

The user makes these decisions:

- confirm or change the research compass: venue/submission window and domain;
- select or change the L1 task-dataset direction and project evidence standard;
- promote or replace the L2 problem, core mechanism, and innovation claim;
- change another field explicitly frozen by the user;
- approve paid compute or rental;
- accept the project-specific risk of reporting favorably selected seeds;
- approve a semantic change to stable project instructions when it changes
  authority, scope, protocol, permissions, or required validation and is not
  merely reflecting an already recorded owning decision;
- enter paper writing or select the headline claim;
- authorize submission, publication, or an external send.

Everything else is normally autonomous inside the confirmed project scope.
Before broad tuning, the agent locks the primary metric, its scale, and
directionality. Setting or replacing that evaluation anchor does not need
approval, nor do aggregation details, hyperparameters, routine debugging, clear
failures, or individual candidate methods. A replacement anchor applies
prospectively: evidence tied only to an older anchor cannot pass the paper gate.

Direct user decisions must be captured in the state file even if no queued
question preceded them. If an existing project is still doing active method
research and lacks L1 or L2, report the missing decision and create the next
proper checkpoint instead of inferring consent from history. If its task,
method, experiment package, and manuscript direction are already substantially
fixed, route downstream without reconstructing retrospective checkpoints.

Every reply is typed as `select`, `approve`, `reject`, `defer`, or
`informational` internally; do not require the user to write these English
labels. `select`, `approve`, and `reject` resolve the active question.
`informational` records useful context but leaves the question active. `defer`
moves the question to a visible deferred queue, removes it from the active
five-question count, and requires a concrete revisit condition. Only `select`
and `approve` can confirm a compass, L1, L2, paper, or additional frozen choice.

Give every PI question a stable decision target such as `direction:D001` or
`science:S001`. A queued approval must match the checkpoint layer and target and
is consumed once. One user message may explicitly decide several matters, but
record a separate scoped receipt for each; never reuse a generic “同意继续” as
authority for unrelated gates.

`FROZEN_BY_PI` is reserved for project-specific choices beyond the compass,
L1, L2, and paper fields. Never duplicate venue, domain, task, dataset, evidence
standard, scientific story, or headline claim there. Include only fields the
user actually fixed. When work conflicts with one:

1. continue independent in-scope work;
2. create one PI question explaining the conflict;
3. do not change the frozen item until the user answers;
4. do not switch to an unrelated project merely to stay busy.

## Notifications versus PI questions

Notifications do not count toward the five-question cap. Notify material events
such as:

- the candidate pool materially narrowed;
- a promising method completed ceiling tuning;
- evidence changed the project-level interpretation;
- the next model family will change;
- a routine implementation repair changed or invalidated scientific evidence;
- a mechanical repair or meaning-preserving compaction changed the effective
  project instructions;
- a long-running job completed or failed.

Use plain language:

```text
原来想做什么：
实际发生了什么：
为什么准备改变：
接下来做什么：
```

Translate metrics into their consequence. Do not send only run names or
unexplained abbreviations.

New controller states keep a bounded recent notification window rather than an
ever-growing history. Legacy histories remain untouched until an explicit
`compact-notifications` command.

Create a PI question only when the user must choose among materially different
outcomes. Each question contains:

```text
需要你决定什么：
为什么现在需要决定：
选项和影响：
我的建议：
你没回复时我还能继续什么：
```

Do not ask the user to approve routine implementation work or an obviously
failed branch.

One exception is a headline result formed by selecting favorable seeds from a
larger pool. Before using that result for the paper gate, disclose the total
seed pool, the selection rule, and the project-specific risk to the user in the
current conversation and obtain a scoped approval. Those disclosure details
must not be copied into L1/L2, result cards, the paper-decision report,
`AGENTS.md`, `README.md`, or a manuscript. Durable state keeps only the minimum
approval receipt needed to show that the risk was accepted for the current
scientific story and evaluation-anchor revision.

## In-progress drift check

When the user asks to understand the current work, questions why a method is
being tried, or says the agent may be off course, treat that exchange as a
read-only alignment audit. Do not interpret questions, suggestions, or partial
understanding as permission to pass a gate.

Answer in plain language with:

1. the confirmed compass and L1 direction being served;
2. the active L2 problem, or the exploratory problem if L2 is not confirmed;
3. the exact hypothesis and predicted observable change of the current run;
4. why the implementation is the minimum useful test of that hypothesis;
5. the current evidence, uncertainty, and condition that would stop or redirect
   this branch.

If the current action cannot be traced through that chain, mark it as suspected
drift and stop only the dependent branch at a safe point. Continue unrelated
authorized work. Repair an implementation-level mismatch autonomously; create a
PI question when recovery requires changing confirmed compass, L1, or L2. A
user correction during this discussion becomes authority only when it clearly
selects, approves, rejects, or defers a scoped choice; record that decision in
the normal controller state.

## Twenty-minute behavior

The 20-minute window batches questions; it grants no authority and does not
instruct the workflow to idle.

1. Timestamp each notice or question.
2. Continue independent authorized work.
3. Check elapsed time at natural boundaries; do not use a blocking sleep.
4. After 20 minutes, leave an unanswered PI question queued and batch later
   questions with it.
5. Never take the dependent action merely because time elapsed.

If the user rejects a provisional branch, stop using it in the active claim.
Apply the retention contract in `research-state.md`; rejection alone does not
create a requirement to archive every attempt.

## Five-question stop

Only active unanswered PI questions count. Notifications and deferred questions
are unlimited by this cap. Deferred questions remain visible with their revisit
conditions.

When the fifth question is added:

1. set `PAUSED_FOR_PI`;
2. launch nothing new;
3. stop iteration, polling, monitoring, and analysis at the next safe checkpoint;
4. allow an already-running atomic process to reach a safe end;
5. report the five questions in priority order.

Resume the underlying phase when the pending count falls below five unless the
user keeps the workflow paused.

When a defer condition becomes true, run `reopen` and present that question
again in the next decision packet. Do not silently answer it from the condition
itself.

Register long-running active work with `job-add` and update it with `job-update`
so another context can recover its command/session, next meaningful check, and
next action. Active records missing either scheduling field are incomplete. The
controller blocks a new active job and active-to-active polling or advancement
while paused. An existing job may only be recorded at a safe terminal status:
`completed`, `failed`, `cancelled`, or `blocked`. It does not itself schedule or
poll jobs. It also blocks bootstrapping, changing, or removing project-
instruction audit scopes until the active PI-question count falls below five.

Project-instruction questions use the same queue and count: set `layer` to
`instructions` and target the exact project-relative file, such as
`instructions:AGENTS.md`. Mechanical repairs and verified meaning-preserving
compaction are notifications, not questions. See
[agents-maintenance.md](agents-maintenance.md); do not create a second approval
system for instruction changes.

## Unattended monitoring

Use a host scheduled task only when the user explicitly asks for unattended
monitoring and the host supports it. Treat it as a state-aware wakeup, not as a
fixed 20-minute research loop:

1. choose the next meaningful wake time from expected job progress or a known
   decision boundary; the 20-minute mark is relevant only to an unanswered
   question's batching/revisit condition;
2. run `status STATE --compact`, compare its `wakeup_fingerprint`, then inspect
   the job and an artifact or process fingerprint before loading the full
   state, literature, or analysis; a next-check reschedule alone is not a
   meaningful change, while an unanswered question crossing the 20-minute
   batching boundary changes the fingerprint once;
3. if nothing changed, update the next useful check and exit without repeating
   reasoning or producing a report;
4. if evidence changed, analyze it and launch at most one next authorized
   experiment batch before scheduling another wakeup;
5. stop future wakeups before costly work when five PI questions are active, a
   required user decision blocks the branch, the paper gate is reached, the
   user pauses/stops, or no authorized promising action remains.

A failed experiment alone is not a stop condition when an already authorized,
promising alternative remains. If scheduled tasks are unavailable, keep the
job registry and next action current so a later task can resume safely.
Desktop-local monitoring requires the machine and app to remain available.
Use the narrowest permission mode that can run the known project command, read
its result fingerprint, and update the scoped workflow state.

## Execution defaults

Within the current project and authorization:

- use an available GPU by default;
- identify and verify the external-baseline roster before broad ceiling tuning;
- lock the primary metric, scale, and direction before broad ceiling tuning;
- tune a promising method to estimate its current-project ceiling;
- close low-potential methods after implementation, baseline, and diagnostic
  sanity checks;
- notify model-family changes;
- handle routine metrics, hyperparameters, code details, and ordinary debugging
  autonomously;
- apply changed non-frozen gates prospectively or by explicit re-evaluation,
  rather than relabeling old runs.

## Paper-ready decision

Treat “good enough to write” as a PI decision. It requires confirmed L1/L2
state and assessment against the user-adopted evidence standard. Before
creating that question, verify and source the strongest recent top-conference
protocol-matched baseline, clear the configured numeric gain floor, establish
project-appropriate repeat, uncertainty, or stability evidence, and generate
the project-local paper-decision report. Present:

- the current task, dataset, problem in current/nearest work, innovation, and concrete method;
- final results plus the baseline venue/year/source and search scope,
  protocol-match evidence, the current evaluation anchor and matching evidence,
  both scores, computed point gain, required floor, and stability evidence;
- the narrowest supported result;
- the strongest matched external comparison;
- the strongest remaining reviewer objection;
- necessary versus optional additional work;
- plausible paper positions and the agent recommendation.

Only then ask the user whether to enter writing and which claim to use. While
waiting, verify artifacts and organize evidence. Do not silently choose the
final claim, title, or a new evidence standard. Do not reuse a paper approval
question created for an earlier or not-yet-generated report; the controller
binds the approval to the current report receipt.

## Durable control state

When project writes are authorized, resolve the controller from the directory
containing the active `SKILL.md`, then use it with the layered files from
[research-state.md](research-state.md):

```text
<project>/.codex/research-paper-workflow.json
<project>/.codex/research/
```

Use `<controller> --help` for the complete CLI. The common collaboration
operations are:

```text
python <controller> status STATE
python <controller> status STATE --compact
python <controller> question STATE --layer direction --target direction:D001 --text "..."
python <controller> answer STATE --id Q001 --decision "..." --outcome select
python <controller> answer STATE --id Q002 --decision "稍后决定" --outcome defer --revisit-condition "..."
python <controller> job-add STATE --id J001 --description "..." --command "..." --status running --next-poll "..." --next-action "..."
```

Use `freeze` and `unfreeze` for additional user-fixed fields. Direct decisions
also require `--pi-outcome approve|select`. Never use `--pi-decision` to invent
approval; it must quote or faithfully summarize an actual user instruction.
The controller records decisions, phase, jobs, and pause state. It does not
schedule or kill work.
