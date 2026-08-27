# Layered research record

Read this reference for research spanning multiple runs, monitoring cycles, or context compactions. The record is a live scientific state, not a chronological dump. `research_queue.py` separately preserves PI questions and confirmed checkpoints.

## Preferred project layout

When project writes are authorized, use:

```text
<project>/.codex/research/
  L1-directions.md
  L2/
    D001.md
    D002.md
  L3/
    D001.md
    D002.md
<project>/.codex/research-paper-workflow.json
```

One L2 and L3 file belongs to one L1 direction ID. Native experiment trackers, result cards, or handoffs may replace L3 when they preserve the required evidence and are linked from L2. Do not duplicate large logs.

For an existing project with `.codex/research-ledger.md`, keep it as historical evidence. At the next material checkpoint, create the layered files, copy only the current state and source links, and link back to the legacy ledger. Do not mechanically rewrite a large history.

## L1: direction portfolio

`L1-directions.md` is the compact page the user can actually decide from. Put the active direction and pending decision at the top.

Record the research compass:

- target submission window and/or venue, including whether frozen or tentative;
- domain;
- user-supplied starting concept and whether it is frozen;
- project-specific paper-ready criteria.

Maintain a ranked table:

```text
ID | status | task type | dataset or bundle | why meaningful | task-data fit | headroom | nearest-work risk | external-baseline feasibility | cost/time | next action
```

Use these statuses:

- `SCOUTING`
- `SHORTLISTED`
- `PENDING_PI_DIRECTION`
- `ACTIVE_PI_CONFIRMED`
- `PI_REJECTED`
- `CLOSED_EVIDENCE`

After a small shortlist is grounded, create the direction checkpoint. The user must select the task type and dataset or dataset bundle before sustained method search or broad tuning. Cheap data inspection, literature verification, and baseline-feasibility work may continue while the question waits.

The L1 decision packet must state, in plain language:

1. what each task would teach or enable;
2. why the proposed dataset measures that task;
3. how much credible headroom remains;
4. the nearest-work collision and external-baseline situation;
5. time, compute, and data risks;
6. the recommended direction and why.

Record the exact PI instruction in the queue checkpoint. Do not infer a selection from the fact that a candidate has code or early results.

## L2: scientific story for one direction

Each `L2/<direction-id>.md` begins with:

```text
Direction ID:
L1 task and dataset:
L1 confirmation source:
L2 status:
Active problem + method decision source:
Last material update:
```

Use these L2 statuses:

- `MAPPING_NEAREST_WORK`
- `BASELINE_INCOMPLETE`
- `METHOD_CHEAP_SCREEN`
- `METHOD_PROMISING`
- `CEILING_SEARCH`
- `PENDING_PI_SCIENCE`
- `ACTIVE_PI_CONFIRMED`
- `PAPER_READY_PENDING_PI`

Closed low-potential or nearest-work-collided candidates may be removed from the live L2 file. This skill does not require an archive of closed candidates.

### Problem-to-method chain

Maintain one explicit chain:

```text
observed problem
-> plain-language cause
-> solution intuition
-> predicted observable change
-> minimal mathematical formulation
-> minimal implementation
-> innovation claim
```

Add one concrete example showing how a strong baseline fails and how the proposed method should behave differently. If a component cannot be traced to the same problem, treat it as an engineering addition rather than part of the scientific contribution.

### Nearest-work matrix

For every paper that affects novelty, problem selection, or baseline choice, record:

```text
paper | year/venue | stable URL/DOI | search date | task/data/split | supervision and inference information | mechanism | result used | overlap | remaining gap | VERIFIED or INFERENCE
```

Use primary papers and official project sources. A search snippet, title resemblance, or model memory is not enough for a novelty decision.

### Mandatory external-baseline roster

The roster is created before a method is marked `METHOD_PROMISING` or receives broad ceiling tuning. It normally contains:

1. **Dataset-origin anchor:** the dataset paper's official reference result or method when one exists.
2. **Recent strongest comparable:** the strongest recent published method found under the same task and a protocol that is directly comparable or can be matched.
3. **Different published mechanism:** at least one external method that is not merely another version of our approach.
4. **Strong simple baseline:** a conventional model that tests whether the added mechanism is needed.
5. **Internal controls:** our variants and ablations, kept in a separate block.

Use this table:

```text
method | external/internal | source | role | task/split | supervision/input | metric | reported result | matched local result | evidence status | comparability | code/checkpoint | blocker
```

Allowed evidence statuses:

- `CITATION_VERIFIED`: the primary source and reported value were checked.
- `REPORTED_NOT_MATCHED`: useful historical context but not apples-to-apples.
- `OFFICIAL_REPRODUCED`: official implementation reproduced under its stated protocol.
- `MATCHED_ADAPTATION`: implemented or adapted under the current project's protocol.
- `INTERNAL_CONTROL`: our baseline, ablation, or variant; never presented as external evidence.
- `BLOCKED`: important comparison is currently unavailable, with a concrete reason.
- `INVALIDATED_BY_BUG`: a prior value lost support after an implementation or protocol defect.

Do not call a row “SOTA” only because it has the largest published number. Check task, split, labels, supervision, inference information, metric, and evaluation date. If exact comparison is impossible, separate the historical reported table from the matched local table.

### Result matrix

Keep three visibly separate blocks:

```text
A. protocol-matched external baselines
B. our proposed method
C. internal variants and ablations
```

For every decision-relevant result, record:

```text
method | version/run | protocol identity | main metric(s) | uncertainty/seeds | status | artifact | interpretation
```

An “ours versus ours” table may diagnose the mechanism, but it cannot satisfy the external-baseline gate or support a competitive claim.

### Candidate and ceiling register

Maintain a small method table:

```text
method ID | status | mechanism | predicted diagnostic | cheap-screen evidence | external-baseline gap | best result | next action
```

For each promising method that receives tuning, record:

- why it qualified as promising;
- tuning budget and stop reason;
- starting and best result;
- gap to the strongest protocol-matched external baseline;
- stability and failure cases;
- wall-clock and compute cost;
- estimated current-project ceiling;
- remaining evidence needed for a paper.

After the ceiling report and external comparison are available, create the L2 scientific-story checkpoint. Ask whether to promote the problem + core mechanism + innovation claim, keep it exploratory, or close it. The agent does not promote it merely because it is the best internal variant.

## L3: implementation and execution

Each `L3/<direction-id>.md` is an engineering index, not a scientific narrative. Record:

```text
component/run | code commit or path | config | data/environment identity | hardware | status | result artifact | bug/protocol note | next technical action
```

Use statuses such as:

- `QUEUED`
- `RUNNING`
- `VALID`
- `FAILED_IMPLEMENTATION`
- `PROTOCOL_ERROR`
- `SUPERSEDED`

Group routine hyperparameter trials. Link to native logs rather than pasting them. Bugs and repairs are autonomous unless they require changing L1/L2 or another frozen item.

The L3 index tracks current execution state, not a mandatory failure archive. Resolved failed runs, superseded exploratory runs, and protocol-error artifacts may be removed unless the user or project requires retention.

Propagate upward when L3 changes scientific meaning:

- invalidate affected L2 result rows when a bug changes their support;
- notify model-family changes in plain language;
- update L2 when a repair changes the baseline gap or mechanism conclusion;
- create a PI question only when the repair requires changing confirmed L1/L2;
- do not treat a crash or protocol error as evidence that a scientific idea failed.

## Decision trail

The queue is the authority for current PI decisions. L1/L2 should link to the relevant question or direct-decision record. For every material pivot, record:

- which L1 or L2 item it affects;
- the new verified evidence;
- what remains confirmed;
- whether the change is scientific or engineering;
- the next independent action.

Keep verified observation, agent interpretation, autonomous action, PI question, and confirmed PI decision separate. Do not describe a failed result as a pass under a gate it was not evaluated against; retaining the superseded run is not required.
