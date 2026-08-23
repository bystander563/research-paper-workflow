# Research ledger

Read this reference for research that spans multiple runs, monitoring cycles, or context compactions. The ledger preserves the scientific reasoning chain; `research_queue.py` separately preserves collaboration state and PI decisions.

## When to maintain it

When project writes are authorized, maintain a project-local ledger at:

```text
<project>/.codex/research-ledger.md
```

Use an existing handoff, experiment index, or research log instead when it already preserves the fields below. Do not create a duplicate ledger for a short discussion, read-only review, or one-off experiment.

Update the ledger at material checkpoints: selecting or closing a serious candidate, changing a model, completing a potential screen or ceiling search, making a material pivot, verifying nearest work, or changing the next action. Do not create one entry for every routine hyperparameter trial.

## Required sections

### Research compass

Record:

- target submission window and/or venue, including whether it is frozen or tentative;
- domain;
- user-supplied starting concept and whether it is frozen;
- current task and dataset status;
- the active problem, solution intuition, and mathematical link;
- the project-specific paper-ready criteria.

Paper-ready criteria are local to the project. Derive them from the venue, contribution type, nearest work, available time, and the user's confirmed choices. Do not impose universal requirements such as SOTA or a second dataset, but record them when this project actually needs them.

### Candidate register

Keep a small ranked table of serious candidates with:

```text
ID | status | task and dataset | mechanism | potential evidence | best result | closure or next action
```

Use statuses that make the lifecycle explicit:

- `SCOUTING`
- `CHEAP_SCREEN`
- `PROMISING`
- `CEILING_SEARCH`
- `CLOSED_LOW_POTENTIAL`
- `CLOSED_NEAREST_WORK`
- `PAPER_READY_PENDING_PI`

Before using `CLOSED_LOW_POTENTIAL`, record the implementation sanity check, baseline health check, mechanism diagnostic, and short closure reason. A low-potential candidate does not require an individual user notification unless it changes the research direction or a frozen choice.

### Nearest-work evidence

For every paper that materially affects novelty or baseline selection, record:

```text
title | year or venue | stable URL or DOI | search date | exact task/data/information setting | overlap | remaining gap | verified facts | inference
```

Prefer the primary paper and official project source. Separate facts verified from the source from the agent's interpretation. A search snippet or model memory is not sufficient evidence for a novelty decision.

### Experiment evidence

For each decision-relevant experiment or grouped tuning round, record:

```text
candidate | intended test | predicted observable change | configuration or run reference | result | interpretation | artifact path | next consequence
```

Group routine hyperparameter trials into a compact summary. Preserve the configuration, result, failure reason, and artifact references needed to understand negative evidence. Do not retain every large checkpoint or temporary file unless the active project requires it.

### Ceiling report

For each promising method that receives tuning, record:

- why it qualified as promising;
- the ceiling-search budget and stop reason;
- starting and best result;
- strongest relevant baseline gap;
- stability and remaining failure cases;
- wall-clock and compute cost;
- estimated current-project ceiling;
- whether the project-specific paper-ready criteria now appear satisfied.

### Decision trail and next action

For every material pivot, record the research-compass check it addresses, the new evidence, what remains fixed, and whether the change is scientific or merely engineering. End the ledger with one concrete next action and any independent work that can continue while PI decisions are pending.

## Separation of records

Keep these categories distinct:

- verified observation;
- agent interpretation;
- autonomous action or notification;
- PI decision question;
- confirmed PI decision.

Never rewrite a failed result as a pass after changing a gate. Add a new version and preserve the previous verdict.
