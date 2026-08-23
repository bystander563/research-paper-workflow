---
name: research-paper-workflow
description: Coordinate paper-oriented problem and dataset scouting, method exploration, experiment iteration, monitoring, failure-driven pivots, and asynchronous PI decisions. Use when the user wants Codex to explore or continue an active research project autonomously while explaining major changes plainly and preserving user-frozen choices. Do not use for ordinary one-off paper drafting or to invent project-specific data and evaluation protocols.
---

# Research Paper Workflow

Run the research process autonomously inside the user's current authorization while keeping scientific ownership with the user.

Project instructions, `AGENTS.md`, frozen contracts, and the user's latest message override this skill. Do not turn examples or failures from one project into universal scientific rules. In particular, this skill does not create generic rules for test sets, sealed sets, external labels, intermediate-result access, metrics, or validation protocols.

## Activate the workflow

Ordinary discussion remains analysis-only. Enter execution when the user clearly asks to start, continue, run, iterate, or monitor research.

For a long-running or multi-stage task, read [references/collaboration-policy.md](references/collaboration-policy.md) and [references/research-ledger.md](references/research-ledger.md). When project writes are authorized, use the project-local queue and research ledger described there, or an existing equivalent that preserves the same information.

For problem, dataset, or method exploration, first obtain a user-confirmed submission window and/or target venue plus the research domain. A starting concept is optional. Then read [references/exploration-policy.md](references/exploration-policy.md). Treat the confirmed venue/time and domain as the research compass; treat a starting concept as a seed unless the user explicitly freezes it.

## Operating phases

- **Exploration:** starting from the user-confirmed venue/time, domain, and optional concept, jointly search for a meaningful task and a matching dataset with useful headroom; audit nearest work; derive a problem-driven intuition and a mathematically aligned method. Choose and revise candidates autonomously. Use available GPU by default. Explain material changes plainly, but do not turn notifications into approval requests.
- **Confirmed project:** preserve every item the user explicitly marked `FROZEN_BY_PI`. Continue autonomously on everything else. Changing a frozen task, dataset, or other frozen item is a macro decision for the user.
- **Paper-ready:** assess the evidence against the current project's recorded paper-ready criteria. If it appears sufficient, ask the user whether to enter writing and what the headline claim should be. Ask about the venue only when it was tentative, must change, or the evidence no longer fits the frozen target. Continue evidence organization while waiting, but do not silently finalize the paper direction.

## Decisions and notifications

Treat these as macro decisions:

- changing an item explicitly frozen by the user;
- renting compute or creating new paid cost;
- entering a paper-writing route, fixing the headline claim, or choosing or changing an unfixed venue;
- submitting, publishing, or sending material externally.

Everything else is normally autonomous within project scope. Important events are notifications, not questions. Notifications do not count toward the macro-decision queue.

Tie every material downstream decision back to the research compass: venue/time fit, domain, task meaning, task-dataset correspondence, benchmark headroom, nearest-work novelty, observed problem, solution intuition, and mathematical fit. Do not justify a pivot only because a score increased.

Use plain language in every material notification:

1. 原来想做什么；
2. 实际发生了什么；
3. 为什么准备改变；
4. 接下来做什么。

When the method's meaning is easy to misunderstand, add one concrete sample-level example. Define unavoidable technical terms immediately.

## Iteration rules

- Screen candidates before spending on tuning. If a method has a coherent mechanism and a credible preliminary signal, tune it with the available compute to estimate its current-project ceiling, then report the starting result, best result, cost, remaining weakness, and paper potential in plain language.
- A method with no credible potential may be closed or followed by another method without PI approval. Record the reason internally; do not tune it or report it individually unless its failure changes the research direction, removes a serious candidate, or affects a frozen choice.
- Notify a gate pass or fail only when it belongs to a promising method, changes the project-level interpretation, or materially affects the next direction. A cheap screen for a low-potential candidate stays in the internal ledger.
- In exploration, a candidate dataset may be changed with notification. If the dataset or task is `FROZEN_BY_PI`, queue the change for the user instead.
- Model changes require a notification. Metric and hyperparameter changes need no individual notification; record them and summarize their effect in a ceiling report when the method is promising.
- Lowering or replacing a gate is autonomous unless that gate is explicitly `FROZEN_BY_PI`. Preserve the old failure, record the new rule as a new version, and never rewrite the old run as a pass.
- Fix deterministic crashes, ignored arguments, paths, and parsing errors automatically. Preserve invalid outputs as `PROTOCOL_ERROR`. If a fix changes a user-frozen item, queue it instead.
- Use an available GPU by default. Use CPU or no-GPU mode when the user requests it or the current environment requires it. Never rent paid compute without a macro decision.

## Twenty-minute asynchronous policy

Send material notices and PI decision questions as soon as they arise. Continue independent authorized work immediately. If a question remains unanswered after 20 minutes, keep it queued and batch it with later PI decisions while continuing work that does not depend on it. Twenty minutes grants no new permission: never use it to change `FROZEN_BY_PI`, spend money, commit the paper route, or create an external side effect.

Accumulate at most five unanswered macro decisions. When the fifth is recorded, set `PAUSED_FOR_PI` and stop the workflow at the next safe checkpoint. Do not launch, iterate, poll, or monitor further work. Do not kill an already-running process unless the user explicitly requests a hard stop. Resume automatically when the unanswered macro count falls below five, unless the user asks to remain paused.

## Reporting discipline

Separate:

- observed facts;
- the agent's interpretation;
- notifications about autonomous actions;
- macro decisions awaiting the user;
- the user's confirmed decisions.

Do not label an agent recommendation as the user's decision. Do not make routine progress sound like scientific success. When the user returns, lead with the queued macro decisions, then summarize what continued and what changed.
