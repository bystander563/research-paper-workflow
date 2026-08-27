# Collaboration policy

Read this reference for long-running research execution, especially when the
user may be away while experiments continue. The canonical phase and gate model
is [workflow.md](workflow.md); the layered retention contract is
[research-state.md](research-state.md).

## Authority

The user makes these decisions:

- select or change the L1 task-dataset direction and project evidence standard;
- promote or replace the L2 problem, core mechanism, and innovation claim;
- change another field explicitly frozen by the user;
- approve paid compute or rental;
- enter paper writing, select the headline claim, or choose/change an unfixed
  venue;
- authorize submission, publication, or an external send.

Everything else is normally autonomous inside the confirmed project scope.
Metrics, hyperparameters, routine debugging, clear failures, and individual
candidate methods do not need approval.

Direct user decisions must be captured in the state file even if no queued
question preceded them. If an existing project has substantial work but lacks
an L1 or L2 checkpoint, report the missing decision and create the next proper
checkpoint instead of inferring consent from history.

`FROZEN_BY_PI` is reserved for project-specific choices beyond L1/L2. Include
only fields the user actually fixed. When work conflicts with one:

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

Only unanswered PI questions count. Notifications are unlimited.

When the fifth question is added:

1. set `PAUSED_FOR_PI`;
2. launch nothing new;
3. stop iteration, polling, monitoring, and analysis at the next safe checkpoint;
4. allow an already-running atomic process to reach a safe end;
5. report the five questions in priority order.

Resume the underlying phase when the pending count falls below five unless the
user keeps the workflow paused.

## Execution defaults

Within the current project and authorization:

- use an available GPU by default;
- identify and verify the external-baseline roster before broad ceiling tuning;
- tune a promising method to estimate its current-project ceiling;
- close low-potential methods after implementation, baseline, and diagnostic
  sanity checks;
- notify model-family changes;
- handle routine metrics, hyperparameters, code details, and ordinary debugging
  autonomously;
- apply changed non-frozen gates prospectively or by explicit re-evaluation,
  rather than relabeling old runs.

## Paper-ready decision

Treat “good enough to write” as a PI decision. It requires confirmed L1/L2 state
and assessment against the user-adopted evidence standard. Present:

- the narrowest supported result;
- the strongest matched external comparison;
- the strongest remaining reviewer objection;
- necessary versus optional additional work;
- plausible paper positions and the agent recommendation.

While waiting, verify artifacts and organize evidence. Do not silently choose
the final claim, title, or a new evidence standard.

## Durable control state

When project writes are authorized, use `scripts/research_queue.py` with the
layered files from [research-state.md](research-state.md):

```text
<project>/.codex/research-paper-workflow.json
<project>/.codex/research/
```

Useful commands:

```text
python scripts/research_queue.py init STATE --project NAME --phase exploration
python scripts/research_queue.py question STATE --layer direction --priority high --text "..." --reason "..." --recommendation "..." --continue-plan "..."
python scripts/research_queue.py answer STATE --id Q001 --decision "..."
python scripts/research_queue.py confirm STATE --layer direction --id D001 --summary "task=...; dataset=...; evidence_standard=..." --decision-id Q001
python scripts/research_queue.py confirm STATE --layer science --id S001 --summary "problem=...; mechanism=...; claim=..." --pi-decision "把这个作为主线"
python scripts/research_queue.py notify STATE --text "..."
python scripts/research_queue.py status STATE
```

Use `freeze` and `unfreeze` for additional user-fixed fields. Never use
`--pi-decision` to invent approval; it must quote or faithfully summarize an
actual user instruction. The helper records decisions and pause state. It does
not schedule or kill work.
