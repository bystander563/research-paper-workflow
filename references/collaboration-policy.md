# Collaboration policy

Read this reference for long-running research execution, especially when the user may be away while experiments continue.

## Scope

This policy governs collaboration state. It does not define a domain's test-set, sealed-set, external-label, metric, validation, second-dataset, or unexposed-dataset protocol. Read those from the active project. A new or previously unexposed dataset is not a universal requirement.

## State model

Use these workflow states:

- `DISCUSSION`: analyze and explain; do not start execution.
- `EXPLORATION`: scout L1 task-dataset directions and prepare a user decision.
- `CONFIRMED_PROJECT`: an L1 direction is confirmed; iterate on L2 candidates and L3 implementation.
- `PAPER_READY_PENDING_PI`: a user-confirmed L2 story may support a paper route.
- `PAUSED_FOR_PI`: five unanswered PI decisions exist; stop at a safe checkpoint.

Do not infer that a direction or scientific story is confirmed because code or experiments exist. Record an explicit instruction such as “按这个做”, “这个数据集定了”, or “把这个作为主线”.

## Two mandatory scientific checkpoints

### L1 direction

Once a small task-dataset shortlist is grounded, ask the user to select the active task type and dataset or dataset bundle. The user owns this decision. Before it is answered, continue cheap data inspection, nearest-work verification, and baseline-feasibility checks, but not sustained method search or broad tuning.

Changing a confirmed L1 direction is always a PI question.

### L2 scientific story

Inside a confirmed L1 direction, the agent may propose methods, run cheap screens, and tune promising candidates. After a ceiling report and external-baseline comparison exist, ask the user whether the problem + core mechanism + innovation claim becomes the active paper line.

Changing a confirmed L2 problem, core mechanism, or innovation claim is always a PI question. Hyperparameters, routine metrics, code details, and ordinary debugging remain autonomous L3 work.

Direct user decisions must be captured in the state file even if no queued question preceded them. If an existing project's state has no L1 or L2 checkpoint despite substantial work, report the missing decision explicitly and create the next appropriate checkpoint instead of assuming consent from history.

## Other frozen fields

`FROZEN_BY_PI` remains an explicit map for project-specific choices beyond L1/L2. Include only what the user actually fixed.

When an action conflicts with a frozen item:

1. keep working on independent in-scope work;
2. create one PI question explaining the conflict;
3. do not change the item until the user answers;
4. do not switch to an unrelated old project merely to stay busy.

## Notifications versus PI questions

### Notifications

Notifications do not count toward the five-question cap. Examples include:

- a serious candidate failed and the candidate pool materially narrowed;
- a promising method finished ceiling tuning;
- a gate result changed the project-level interpretation;
- the next model family will change;
- a non-frozen gate was versioned;
- a routine implementation or protocol error was repaired and rerun;
- a long-running job completed or failed.

Use:

```text
原来想做什么：
实际发生了什么：
为什么准备改变：
接下来做什么：
```

Translate metrics into their consequence. Do not send only run names or unexplained abbreviations.

### PI questions

Create a PI question when the user must choose among materially different outcomes:

- select or change the L1 task-dataset direction;
- promote or replace the L2 problem, mechanism, and innovation claim;
- change another `FROZEN_BY_PI` item;
- approve paid compute or rental;
- enter paper writing, select the headline claim, or choose/change an unfixed venue;
- authorize submission, publication, or an external send.

Each question contains:

```text
需要你决定什么：
为什么现在需要决定：
选项和影响：
我的建议：
你没回复时我还能继续什么：
```

Do not ask the user to approve ordinary metrics, hyperparameters, routine debugging, clear failures, or every candidate method.

## Twenty-minute behavior

The 20-minute window batches questions; it grants no authority and does not instruct the workflow to idle.

1. Timestamp each notice or question.
2. Continue independent authorized work.
3. Do not use a blocking sleep; check elapsed time at natural boundaries.
4. After 20 minutes, keep an unanswered PI question queued and batch later PI questions with it.
5. Never take the dependent action merely because time elapsed.

If the user rejects a provisional branch, stop using it in the active claim. No retained branch record is required unless the user or project asks for one.

## Five-question stop

Only unanswered PI questions count. Notifications are unlimited.

When the fifth question is added:

1. set `PAUSED_FOR_PI`;
2. launch nothing new;
3. stop iteration, polling, monitoring, and analysis at the next safe checkpoint;
4. allow an already-running atomic process to reach a safe end;
5. report the five questions in priority order.

Resume when the pending count falls below five unless the user keeps the workflow paused.

## Exploration and iteration

Within the current project and authorization:

- use available GPU by default;
- build the external-baseline roster before broad ceiling tuning;
- tune a promising method to estimate its current-project ceiling and report it plainly;
- close low-potential methods after implementation, baseline, and diagnostic sanity checks;
- notify model-family changes;
- keep routine metrics and hyperparameters in L3;
- apply changed non-frozen gates prospectively or by explicit re-evaluation rather than relabeling old runs;
- keep no default negative-result ledger; failed trials, rejected branches, superseded verdicts, and protocol-error artifacts may be discarded unless the user or project requires retention.

## Paper-ready transition

Treat “good enough to write” as a PI decision. It requires a confirmed L1 direction, a confirmed L2 scientific story, and the project-specific evidence criteria. Present:

- the narrowest supported result;
- the strongest matched external comparison;
- the strongest remaining reviewer objection;
- necessary versus optional additional work;
- plausible paper positions.

While waiting, verify artifacts and organize evidence. Do not silently choose the final claim or title.

The agent may explain that using only previously explored data limits the strength of a generalization or confirmation claim, but it must not convert that limitation into a mandatory search for a new or unexposed dataset. Such a requirement exists only when the user or project explicitly adopts it.

## Durable state

Use `scripts/research_queue.py` with the layered record from [research-ledger.md](research-ledger.md) when writes are authorized:

```text
<project>/.codex/research-paper-workflow.json
<project>/.codex/research/
```

Existing equivalents may replace these only when they preserve the same layer, evidence, and decision distinctions.

Useful commands:

```text
python scripts/research_queue.py init STATE --project NAME --phase exploration
python scripts/research_queue.py question STATE --layer direction --priority high --text "..." --reason "..." --recommendation "..." --continue-plan "..."
python scripts/research_queue.py answer STATE --id Q001 --decision "..."
python scripts/research_queue.py confirm STATE --layer direction --id D001 --summary "task=...; dataset=..." --decision-id Q001
python scripts/research_queue.py confirm STATE --layer science --id S001 --summary "problem=...; mechanism=...; claim=..." --pi-decision "把这个作为主线"
python scripts/research_queue.py notify STATE --text "..."
python scripts/research_queue.py status STATE
```

Use `freeze` and `unfreeze` for additional user-fixed fields. Never use `--pi-decision` to invent approval; it must quote or faithfully summarize an actual user instruction. The helper does not schedule or kill work; the operating agent obeys the pause state.
