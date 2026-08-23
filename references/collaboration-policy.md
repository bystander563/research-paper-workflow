# Collaboration policy

Read this reference for long-running research execution, especially when the user may be away while experiments continue.

## Scope

This policy governs collaboration and execution state. It does not define scientific validity for a domain and does not add rules for test sets, sealed sets, external labels, intermediate-result access, metrics, or validation. Read those rules from the active project's own instructions.

## State model

Use these workflow states:

- `DISCUSSION`: analyze and explain; do not start research execution.
- `EXPLORATION`: autonomously search and iterate inside the active project.
- `CONFIRMED_PROJECT`: preserve fields explicitly listed under `FROZEN_BY_PI`; iterate on unfrozen choices.
- `PAPER_READY_PENDING_PI`: evidence may support a paper route; organize evidence and wait for the user to choose the paper direction.
- `PAUSED_FOR_PI`: five unanswered PI decision questions exist; stop at a safe checkpoint.

Do not infer that a project is confirmed merely because files or old experiments exist. The user confirms a task or dataset through an explicit instruction such as “按这个做”, “这个数据集定了”, or equivalent context. Record only the fields actually fixed.

## What is frozen

`FROZEN_BY_PI` is an explicit map rather than a predefined research template. Typical fields may include a task, dataset, claim boundary, or resource constraint, but include only what the user actually fixed.

When a proposed action conflicts with a frozen field:

1. keep working on independent parts of the active project;
2. create one PI decision question explaining the conflict;
3. do not change that frozen field until the user answers;
4. do not switch to an unrelated old project merely to stay busy.

## Notifications versus PI decision questions

### Notifications

Notifications describe autonomous work and never count toward the five-question cap. Examples include:

- a serious candidate failed in a way that changes the research direction or materially narrows the candidate pool;
- a promising method completed a ceiling search and its result is ready to report;
- a gate for a promising method passed or failed, or a gate result changed the project-level interpretation;
- the next method or model will change;
- a gate was lowered or replaced for a new exploratory version;
- a candidate dataset changed during exploration;
- a protocol error was repaired and rerun;
- a long-running job completed or failed.

Use this plain-language format:

```text
原来想做什么：
实际发生了什么：
为什么准备改变：
接下来做什么：
```

Avoid unexplained abbreviations. Translate numbers into their consequence. For example, for a material direction change say “这个候选原本是主要方向，但上限搜索后仍没有超过最简单的对照，因此我准备换方向”, not only “3/3 gate fail”.

### PI decision questions

Create a PI decision question only when the user must choose among materially different outcomes:

- change a `FROZEN_BY_PI` field;
- approve paid compute or a rental;
- decide that evidence is good enough to enter paper writing;
- decide the headline claim, or choose or change a venue that was not already frozen;
- authorize submission, publication, or an external send.

Each question should contain:

```text
需要你决定什么：
为什么现在需要决定：
选项和影响：
我的建议：
你没回复时我还能继续什么：
```

Do not ask the user to approve ordinary metrics, hyperparameters, model debugging, clear failures, or routine pivots.

Narrowing an exploratory interpretation after a clear failure is a notification only when it materially changes the project direction. Choosing the final headline claim becomes a PI decision question only when entering the paper route.

## Twenty-minute behavior

The 20-minute window is a batching rule, not a permission boundary and not an instruction to idle.

1. Timestamp the notice or question when sent.
2. Continue independent authorized work immediately.
3. Do not use a blocking sleep. Check elapsed time at natural experiment or reporting boundaries.
4. If a PI decision question is still unanswered after 20 minutes, keep it queued and batch it with later questions rather than repeating it.
5. Continue work that does not depend on the unanswered decision. Never treat elapsed time as permission to take the dependent action.

When the user replies, apply the answer to future work. Preserve any provisional branch that the user rejects, but mark it `PI_REJECTED_BRANCH` and exclude it from formal evidence or claims unless the user later restores it.

## Five-question stop

Only unanswered PI decision questions count. Research-compass checks and notifications do not count. Notifications are unlimited.

When the fifth unanswered PI decision question is added:

1. set state to `PAUSED_FOR_PI`;
2. launch nothing new;
3. stop further iteration, polling, monitoring, and analysis at the next safe checkpoint;
4. allow an already-running atomic command or training process to reach a safe end rather than killing it;
5. report the five questions in priority order.

When the user answers enough questions to reduce the count below five, resume automatically unless the user explicitly keeps the workflow paused.

## Exploration behavior

Within the current project and current authorization:

- use available GPU by default;
- screen for potential before broad tuning;
- for promising methods, iterate over metrics and hyperparameters to estimate the current-project ceiling, then report the result plainly;
- for methods without credible potential, skip broad tuning and keep only an internal failure note unless the failure changes the research direction;
- notify model changes in plain language;
- close low-potential or clear failures and choose another method autonomously;
- change candidate datasets during exploration with notification;
- preserve the configuration, result, failure reason, and evidence needed to understand or reproduce failed versions and protocol errors; retaining every large checkpoint or temporary artifact is not required unless the project says otherwise;
- if a non-frozen gate changes, create a new version and keep the old verdict intact.

If the user has explicitly frozen a dataset or task, the corresponding change becomes a PI decision question even if the current candidate failed.

## Paper-ready transition

Treat “good enough to write” as a PI decision, not an automatic state change. Judge it against the project-specific paper-ready criteria in the research ledger rather than a universal requirement. Present:

- the narrowest supported result in plain language;
- the strongest remaining failure or reviewer objection;
- what additional work is necessary versus optional;
- one or more plausible paper positions.

While waiting, verify artifacts and organize evidence. Do not silently select the final claim or title. Preserve a venue already frozen by the user; ask again only when it was tentative or a change is proposed.

## Durable state

For long-running projects, use `scripts/research_queue.py` for collaboration state and maintain the research ledger defined in [research-ledger.md](research-ledger.md) when writes are authorized. Existing project state conventions may replace either file only when they preserve the same information. Conventional paths are:

```text
<project>/.codex/research-paper-workflow.json
<project>/.codex/research-ledger.md
```

Do not create a state file for a read-only review or a short discussion. Existing project state conventions take precedence.

Useful commands:

```text
python scripts/research_queue.py init STATE --project NAME --phase exploration
python scripts/research_queue.py question STATE --priority high --text "..." --reason "..." --recommendation "..." --continue-plan "..."
python scripts/research_queue.py notify STATE --text "..."
python scripts/research_queue.py status STATE
python scripts/research_queue.py answer STATE --id Q001 --decision "..."
python scripts/research_queue.py phase STATE --set confirmed_project
python scripts/research_queue.py freeze STATE --key dataset --value "..." --pi-decision "用户确认这个数据集"
python scripts/research_queue.py freeze STATE --key dataset --value "..." --decision-id Q001
python scripts/research_queue.py unfreeze STATE --key dataset --decision-id Q002
```

The helper refuses a sixth pending PI decision question. Freezing, replacing, or unfreezing a field requires a recorded direct PI instruction or an answered decision ID; replacements remain in frozen history. The agent remains responsible for obeying the recorded pause.
