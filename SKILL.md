---
name: research-paper-workflow
description: Coordinate paper-oriented problem and dataset scouting, literature-grounded method exploration, external-baseline comparison, experiment iteration, monitoring, and asynchronous PI decisions. Use when the user wants Codex to explore or continue an active research project autonomously while preserving user ownership of the research direction. Do not use for ordinary one-off paper drafting or to invent project-specific data and evaluation protocols.
---

# Research Paper Workflow

Run routine research work autonomously, but make the user choose the scientific direction at explicit checkpoints. A large number of experiments is useful only after the task, dataset, scientific gap, and comparison set are visible.

Project instructions, `AGENTS.md`, frozen contracts, and the user's latest message override this skill. Do not turn one project's protocol into a universal rule. In particular, this skill does not create generic rules for test sets, sealed sets, external labels, intermediate-result access, metrics, or validation protocols.

## Activate the workflow

Ordinary discussion remains analysis-only. Enter execution when the user asks to start, continue, run, iterate, or monitor research.

For a long-running or multi-stage task, read [references/collaboration-policy.md](references/collaboration-policy.md) and [references/research-ledger.md](references/research-ledger.md). When project writes are authorized, maintain the layered project record and PI queue described there, or an existing equivalent that preserves the same distinctions.

For task, dataset, or method exploration, first obtain a user-confirmed submission window and/or target venue plus the research domain. A starting concept is optional. Then read [references/exploration-policy.md](references/exploration-policy.md). Treat the confirmed venue/time and domain as the research compass; treat a starting concept as a seed unless the user explicitly freezes it.

## Maintain three layers

Never keep a long-running project only as a chronological experiment log.

1. **L1 direction — user-owned.** Maintain the candidate and active task type, dataset or dataset bundle, why the task matters, task-data fit, benchmark headroom, nearest-work collision risk, external-baseline availability, cost, and venue/time fit.
2. **L2 scientific story — jointly developed, user-confirmed.** For each serious L1 direction, maintain nearest work, the concrete problem to improve, cause, solution intuition, mathematical mechanism, innovation claim, external baseline roster, our results, published/reproduced baseline results, and remaining evidence gap.
3. **L3 implementation — agent-owned by default.** Maintain code and configuration references, data and environment identity, run status, bugs, protocol errors, diagnostics, compute, and artifact paths. Do not let implementation activity silently rewrite L1 or L2.

Every L2 claim must link upward to one L1 direction and downward to the literature, result, and implementation artifacts that support it. If a bug or protocol repair invalidates an L2 result, mark that result invalid immediately; do not preserve the scientific conclusion merely because the corrected run is pending.

## Mandatory PI checkpoints

The workflow must create real user decisions instead of waiting for a conflict with an already-frozen field.

### Direction checkpoint

After scouting a small ranked shortlist, ask the user to select the active **task type and dataset or dataset bundle**. Include meaning, headroom, nearest-work risk, baseline availability, cost, and your recommendation. Cheap dataset inspection, literature verification, and baseline-feasibility checks may continue while waiting, but do not begin sustained method search or broad tuning for an unconfirmed direction.

Record a direct instruction such as “按这个做” or “这个数据集定了” as the L1 decision even if it was not an answer to a queued question. Changing the confirmed L1 direction always requires another PI decision.

### Scientific-story checkpoint

The agent may generate methods, run cheap screens, and tune a promising method to estimate its ceiling without prior approval. Once a ceiling report and external-baseline comparison exist, ask the user whether to promote that **problem + core mechanism + innovation claim** into the active paper line, keep it exploratory, or close it. Do not treat the best internal variant as the project direction automatically.

Record the user's choice as the L2 decision. Replacing the confirmed problem, core mechanism, or innovation claim requires another PI decision. Routine implementation choices inside that story remain L3 work.

### Paper checkpoint

If the confirmed L2 story appears to meet the project's paper-ready criteria, ask whether to enter writing and what the headline claim should be. Ask about venue only when it is tentative, must change, or no longer fits.

## External-baseline gate

Before marking a method `PROMISING` or starting a broad ceiling search, build a baseline roster from primary sources. Before calling a result paper-worthy, the comparison must not consist only of the agent's own variants.

For each active task-dataset pair, the roster should normally include:

- the dataset paper's official reference result or method, when one exists;
- the strongest recent protocol-comparable published method found for that dataset and task;
- at least one other published method from a meaningfully different mechanism family;
- a strong simple or conventional baseline;
- internal variants and ablations, clearly separated from external baselines.

If an external result uses a different split, supervision, input, or metric, keep it as `REPORTED_NOT_MATCHED`; do not place it in an apples-to-apples ranking. Reproduce or adapt important baselines under the current protocol when feasible, and label them `OFFICIAL_REPRODUCED` or `MATCHED_ADAPTATION`. If no defensible external comparison is currently possible, set `BASELINE_INCOMPLETE`, explain the blocker, and work on the comparison gap before multiplying internal methods.

## Operating phases

- **Exploration:** search for meaningful task-dataset pairs, verify headroom and nearest work, and prepare the L1 shortlist. Candidate generation is autonomous; L1 activation is not.
- **Confirmed project:** preserve the confirmed L1 direction and any explicit `FROZEN_BY_PI` items. Develop and test L2 candidates autonomously, with the external-baseline gate. Promote one to the active scientific story only through the L2 checkpoint.
- **Paper-ready:** assess the confirmed L2 story against the project's recorded criteria, organize evidence, and wait for the paper checkpoint before finalizing the writing direction.

## Decisions and notifications

Treat these as PI decisions:

- selecting or changing the active L1 task-dataset direction;
- promoting or replacing the active L2 problem, core mechanism, or innovation claim;
- changing any other item explicitly frozen by the user;
- renting compute or creating new paid cost;
- entering a paper-writing route, fixing the headline claim, or choosing or changing an unfixed venue;
- submitting, publishing, or sending material externally.

Everything else is normally autonomous within project scope. Important events are notifications, not questions, and do not count toward the macro-decision queue.

Use plain language in every material notification:

1. 原来想做什么；
2. 实际发生了什么；
3. 为什么准备改变；
4. 接下来做什么。

When the method is easy to misunderstand, add one concrete sample-level example. Define unavoidable technical terms immediately.

## Iteration rules

- Screen candidates before broad tuning. A coherent mechanism, a diagnostic moving as predicted, baseline health, and a plausible competitive path are needed before `PROMISING`.
- For a promising method, use available compute to estimate its current-project ceiling, then report the start, best result, external-baseline gap, cost, weakness, and paper potential in plain language.
- Close low-potential methods autonomously after implementation and baseline sanity checks. Record the reason in L2/L3; notify only when the closure changes the project-level interpretation or a confirmed choice.
- Model-family changes require notification. Metric, ordinary implementation, and hyperparameter changes need no individual notification; record them in L3 and summarize material effects upward.
- Lowering or replacing a non-frozen gate is autonomous, but preserve the old failure and create a new version. Never rewrite an old run as a pass.
- Fix deterministic crashes, ignored arguments, paths, and parsing errors automatically. Preserve invalid outputs as `PROTOCOL_ERROR`. Propagate any invalidated L2 result upward.
- Use an available GPU by default. Use CPU or no-GPU mode when requested or required by the environment. Never rent paid compute without a PI decision.

## Twenty-minute asynchronous policy

Send material notices and PI questions as soon as they arise, then continue independent authorized work. If a question remains unanswered after 20 minutes, keep it queued and batch it with later PI decisions. Twenty minutes grants no new authority.

Accumulate at most five unanswered PI decisions. When the fifth is recorded, set `PAUSED_FOR_PI` and stop at the next safe checkpoint: launch, iterate, poll, and monitor nothing further. Do not kill an already-running process unless the user requests a hard stop. Resume when the unanswered count falls below five unless the user asks to remain paused.

## Reporting discipline

Separate observed facts, agent interpretation, autonomous notifications, PI questions, and confirmed PI decisions. Lead status reports with:

1. active L1 direction and any L1 decision needed;
2. active L2 scientific story, external-baseline coverage, and any L2 decision needed;
3. only the L3 implementation issue that changes L1/L2 meaning.

Do not make the user reconstruct the research state from run names. Do not label an agent recommendation as the user's decision. Do not call an internally best method competitive until the external-baseline gate is satisfied.
