# Layered research state

Read this reference for research spanning multiple runs, monitoring cycles, or
context compactions. It defines the durable scientific state, not a chronological
ledger of all activity. `research_queue.py` separately records typed PI
questions, structured checkpoints, phase state, resumable active jobs, and a
bounded project-instruction maintenance receipt.

## Retention contract

- **L1 and L2 are required durable records.** Preserve their current state,
  verified evidence, user decisions, and material replacements.
- **L1/L2 are selective.** They retain decision-relevant scientific information,
  not every candidate, run, tuning trial, failed branch, or stopping rule.
- **L3 retention is discretionary.** The agent or active project may create,
  compact, replace, or remove L3 indexes and native logs according to their
  usefulness, storage cost, reproducibility needs, and existing project policy.
- Before discarding L3 evidence cited by an active L2 claim, either preserve an
  adequate supporting artifact or update L2 to mark the claim/result unsupported
  or invalidated. Link integrity matters; exhaustive archival does not.
- This policy does not authorize deletion of existing project artifacts merely
  because the skill would not have required creating them.

## Preferred project layout

When project writes are authorized, use:

```text
<project>/.codex/research/
  L1-directions.md
  L2/
    D001.md
    D002.md
  L3/                       # optional; agent/project managed
    D001.md
    D002.md
<project>/.codex/research-paper-workflow.json
```

`research_queue.py init` creates `L1-directions.md` and the `L2/` directory.
After L1 confirmation it creates `L2/<direction-id>.md` when that file does not
already exist. It never overwrites an existing scientific record. When a
checkpoint is confirmed, it refreshes a marked current-state block and appends
a compact receipt containing the typed
outcome, user decision, and structured payload to the supplied L1/L2/paper
record, then stores that record's hash in the controller. Checkpoint and
paper-ready assessment records must stay inside the project. Evidence references
may point to external files, but the controller reads and hashes them without
modifying them.

For evidence stored outside the live L2 record, a later hash change invalidates
the confirmed scientific checkpoint until the evidence is reassessed and L2 is
reconfirmed. Evidence sections embedded in the L2 record itself remain a live
document and are exempt from self-hash comparison.

The paper-ready assessment file and its structured payload are content-locked
when the project enters its paper gate. The controller refuses to consume a
paper decision if either later changes. When the paper checkpoint receipt is
appended to the same file, the controller records the post-handoff hash so later
edits remain visible to `status` and `audit`.

One L2 file belongs to one L1 direction ID. L3 may be a local index, native
experiment tracker, result cards, handoff, or nothing beyond the artifacts
already used by the project. Do not duplicate large logs.

Checkpoint IDs are short path-safe identifiers: 1-64 ASCII letters, digits,
dots, underscores, or hyphens, beginning with a letter or digit. Human-readable
titles and explanations belong in the records, not in filenames.

For an existing project with `.codex/research-ledger.md`, keep it as legacy
history unless the user authorizes cleanup. At the next material checkpoint,
create the layered files, copy only current state and source links, and link to
the legacy file. Do not mechanically rewrite its full history.

## Project instructions are outside the research layers

`AGENTS.md` and `AGENTS.override.md` are stable execution contracts and routers;
they are not L1, L2, L3, or a replacement for the controller. They may tell an
agent which active L1/L2 files or project truth sources to read, but must not
copy their changing contents.

The schema-v10 controller stores one project-local instruction-chain snapshot per
audited working-directory scope plus a bounded set of update receipts containing
paths, hashes, sizes, change classes, canonical compaction sources, reasons, and
decision provenance. Scope-removal receipts are bounded separately; a missing
directory may be pruned autonomously, while removing a scope that still exists
requires PI approval. It stores no instruction contents. See
[agents-maintenance.md](agents-maintenance.md) for content, budgets, change
classes, and authority.

## L1: direction portfolio

`L1-directions.md` is the compact page the user can decide from. Put the active
direction and adopted evidence standard at the top. Pending questions remain in
the controller queue; do not duplicate live queue state in L1.

Record the research compass:

- target submission window and/or venue, including whether frozen or tentative;
- domain;
- user-supplied starting concept and whether it is frozen;
- mandatory unexposed-dataset search result, feasibility, and recommendation;
- competitive target, such as SOTA, near-SOTA, or another user-defined bar;
- novelty sufficiency standard;
- generalization, second-dataset, or other evidence requirement, including an
  explicit “not required” when that is the user's decision;
- additional project-specific paper-ready requirements, which may tighten but
  never lower the numeric gain floor;
- numeric paper-gain floor: at least 1 percentage point over the strongest
  recent top-conference protocol-matched baseline; a project may set it higher.

Maintain a ranked table:

```text
ID | status | task type | dataset or bundle | why meaningful | task-data fit | headroom | nearest-work risk | external-baseline feasibility | unexposed-data option | cost/time | next action
```

Use these statuses:

- `SCOUTING`
- `SHORTLISTED`
- `PENDING_PI_DIRECTION`
- `ACTIVE_PI_CONFIRMED`
- `PI_REJECTED`
- `CLOSED_EVIDENCE`

The shortlist is compact; weak ideas that never become decision-relevant need
not be retained. Preserve the selected direction, alternatives actually shown
to the user, the decision source, and later replacements.

The L1 decision packet states, in plain language:

1. what each task would teach or enable;
2. why the proposed dataset measures that task;
3. how much credible headroom remains;
4. the nearest-work collision and external-baseline situation;
5. time, compute, and data risks;
6. the proposed evidence standard;
7. the recommended direction and why.

Record the exact PI instruction in the controller decision receipt. Code or early results
do not imply selection.

The schema-v10 L1 checkpoint separately stores the selected task type, dataset,
mandatory unexposed-dataset search result, four descriptive evidence-standard
fields plus the numeric paper-gain floor,
approving outcome, durable-record path, and the record hash at confirmation. A
queued approval is also bound to this direction ID and consumed once. The hash
is provenance for the approved snapshot; L1 remains a live file and may later
change through recorded decisions.

When a compass change invalidates L1, the controller replaces the visible
current-direction and evidence-standard blocks with
`STALE_AFTER_COMPASS_CHANGE`; it must not leave the old contract looking
active.

## Evaluation anchor

Before broad tuning, the controller stores an agent-owned evaluation anchor
containing the active direction ID, primary metric, `0–1` or `0–100` scale,
higher-is-better directionality, revision, reason, and lock time. It deliberately
does not define a universal aggregation rule. Setting or replacing this anchor
does not require a PI decision.

Replacement archives the prior anchor and applies prospectively. Evidence tied
only to an older revision may remain useful for exploration, but it cannot pass
the paper gate until rerun or explicitly reassessed under the current anchor.

## L2: scientific story for one direction

Each `L2/<direction-id>.md` begins with:

```text
Direction ID:
L1 task, dataset, and evidence standard:
Unexposed-dataset search:
L1 confirmation source:
L2 status:
Active problem + method decision source:
Last material update:
```

Use these statuses:

- `MAPPING_NEAREST_WORK`
- `BASELINE_INCOMPLETE`
- `METHOD_CHEAP_SCREEN`
- `METHOD_PROMISING`
- `CEILING_SEARCH`
- `PENDING_PI_SCIENCE`
- `ACTIVE_PI_CONFIRMED`
- `PAPER_READY_PENDING_PI`

L2 is durable at the level of scientific decisions and evidence. A low-potential
idea that never became decision-relevant need not enter L2. Once a candidate is
presented for L2 confirmation, affects the active scientific interpretation, or
receives a user decision, retain its compact conclusion even if implementation
attempts are later discarded.

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

Add one concrete example showing how a strong baseline fails and how the
proposed method should behave differently. If a component cannot be traced to
the same problem, treat it as an engineering addition rather than part of the
scientific contribution.

### Nearest-work matrix

For every paper that affects novelty, problem selection, or baseline choice,
record:

```text
paper | year/venue | stable URL/DOI | search date | task/data/split | supervision and inference information | mechanism | result used | overlap | remaining gap | VERIFIED or INFERENCE
```

Use primary papers and official project sources. A search snippet, title
resemblance, or model memory is not enough for a novelty decision.

### External-baseline roster

External means another published method or conventional comparator, not a new
dataset. Identify and source-check the roster before broad ceiling tuning. It
normally contains:

1. **Dataset-origin anchor:** the dataset paper's official result or method.
2. **Recent top-conference comparator:** the strongest recent top-conference
   method found for the same task under a directly comparable or matchable
   protocol. Record venue/year and a primary source.
3. **Different published mechanism:** an external method not merely another
   version of the proposed approach.
4. **Strong simple baseline:** a conventional model testing whether the added
   mechanism is needed.
5. **Internal controls:** variants and ablations in a separate block.

Use:

```text
method | external/internal | source | role | task/split | supervision/input | metric | reported result | matched local result | evidence status | comparability | code/checkpoint | blocker
```

Allowed evidence statuses:

- `CITATION_VERIFIED`
- `REPORTED_NOT_MATCHED`
- `OFFICIAL_REPRODUCED`
- `MATCHED_ADAPTATION`
- `INTERNAL_CONTROL`
- `BLOCKED`
- `INVALIDATED_BY_BUG`

Before broad tuning, roster identity and source verification are required; not
every local reproduction must already be complete. Before a paper-worthy claim,
the strongest recent top-conference protocol-matched comparison must exist;
`BLOCKED` means the paper gate cannot pass. Check task, split, labels,
supervision, inference information, metric, and evaluation date before ranking
numbers. On the higher-is-better primary metric, our result must exceed it by at
least the L1 point floor, never below 1 percentage point.

### Result matrix

Keep three visibly separate blocks:

```text
A. protocol-matched external baselines
B. our proposed method
C. internal variants and ablations
```

For every decision-relevant result, record:

```text
method | version/run | protocol identity | main metric(s) | uncertainty/seeds | status | supporting artifact or availability | interpretation
```

An “ours versus ours” table may diagnose the mechanism, but it cannot satisfy
the external-baseline gate or support a competitive claim.

### Candidate and ceiling summary

Maintain only a small set of decision-relevant methods:

```text
method ID | status | mechanism | predicted diagnostic | cheap-screen evidence | external-baseline gap | best result | next action
```

For each promising method that receives broad tuning, retain the scientific
summary:

- why it qualified as promising;
- starting and best decision-relevant result;
- gap to the strongest protocol-matched external baseline;
- stability, failure cases, and estimated current-project ceiling;
- aggregate wall-clock or compute cost when useful for planning;
- remaining evidence needed for the L1 paper threshold.

Do not require a list of every tuning attempt, the complete search trajectory,
or a recorded stopping rule. Those are L3 details and may be retained or
discarded at agent discretion.

After the ceiling summary and external comparison exist, create the L2
scientific-story checkpoint. Ask whether to promote the problem + core mechanism
+ innovation claim, keep it exploratory, or close it. The agent does not promote
it merely because it is the best internal variant.

The schema-v10 L2 checkpoint stores the active direction ID, problem, core
mechanism, innovation claim, external-baseline status, ceiling summary,
approving outcome, durable-record path, and hashed references to the nearest-
work, external-baseline, and result records used for the decision. A queued
approval is bound to this scientific-story ID and consumed once. A question
with outcome `reject`, `defer`, or `informational` cannot be used as
confirmation.

When a compass or L1 change invalidates L2, the controller replaces the visible
L2 current-state block with the matching `STALE_AFTER_*` status and replacement
checkpoint. Historical evidence remains in the file, but it is no longer
presented as the active story.

## Paper-decision report

Do not ask the user whether to write the paper until a project-local report has
been generated and the configured gain floor passes. The report is a readable
decision packet, not just a pointer to experiment logs. It must contain:

1. current task and dataset;
2. problem in current/nearest work;
3. innovation and core mechanism;
4. concrete method;
5. final decision-relevant results;
6. strongest recent top-conference protocol-matched baseline, venue/year,
   primary source, and literature-search venues/year range/date;
7. protocol-match evidence covering task, data/split, labels,
   supervision/inference information, metric, and evaluation procedure;
8. current evaluation-anchor revision and evidence that the scored result was
   produced or reassessed under it;
9. higher-is-better primary metric and scale (`0–1` or `0–100`), baseline score,
   our score, computed percentage-point gain, and required L1 floor;
10. project-appropriate repeat, uncertainty, or stability evidence, without a
    universal seed count, aggregation method, or significance test;
11. competitive, novelty, generalization, and additional paper-ready assessments;
12. narrowest supported claim, remaining objection, and necessary versus
    optional work.

The controller copies L1 task/dataset and L2 problem/innovation/mechanism into
the report receipt, checks numeric arithmetic and the floor, ties it to the
active checkpoint IDs, and content-locks both the file and structured payload. The agent remains
responsible for verifying top-conference status and protocol comparability from
primary sources. A report that passes these mechanical checks is still evidence
for the user's paper decision, not the decision itself.

When the headline result uses favorable-seed selection, keep its detailed risk
disclosure in the current user conversation only. Do not copy it into L1/L2,
result cards, the paper-decision report, project instructions, repository
documentation, or a manuscript. The controller stores only a minimal scoped
receipt that the user accepted the risk for the active scientific story and
evaluation-anchor revision.

## L3: implementation and execution

L3 is an optional engineering aid rather than a mandatory archive. When useful,
an `L3/<direction-id>.md` index may contain:

```text
component/run | code commit or path | config | data/environment identity | hardware | status | result artifact | bug/protocol note | next technical action
```

Native experiment trackers may replace it. The agent decides the useful level
of detail, grouping, and retention. Routine hyperparameter trials, resolved
failures, superseded exploratory runs, protocol-error artifacts, and stopping
notes may be omitted or removed unless the user or project requires them.

Long-running jobs that must survive context compaction should also be registered
in the controller with a command or session ID, status, next poll, and next
action. This job registry is live recovery state and may be pruned after a job
finishes; it is not a required experiment archive.

Regardless of retention, propagate changes in scientific meaning upward:

- invalidate affected L2 result rows when a bug changes their support;
- notify model-family changes in plain language;
- update L2 when a repair changes the baseline gap or mechanism conclusion;
- create a PI question only when the repair requires changing confirmed L1/L2;
- do not treat a crash or protocol error as evidence that a scientific idea
  failed.

## Decision trail

The queue is the authority for current PI decisions. L1/L2 link to the relevant
question or direct-decision record. Retain material L1/L2 pivots with:

- the affected direction or scientific story;
- the new verified evidence;
- what remains confirmed;
- the user decision source;
- the next independent action.

Keep verified observation, agent interpretation, autonomous action, PI question,
and confirmed PI decision separate. This trail records scientific ownership; it
does not require preserving all underlying attempts or stop conditions.

Each PI question has a stable decision target. Keep its active, deferred,
informational, and consumed state only in the controller; follow
[collaboration-policy.md](collaboration-policy.md) for queue behavior.

Core fields have one authority: compass, L1, L2, or paper checkpoint state.
`frozen_by_pi` is only for additional project-specific constraints and must not
duplicate venue, domain, task, dataset, evidence standard, scientific story, or
headline claim.

## Legacy-state audit

Schema-v1 through schema-v9 states are readable. Unstructured L1/L2 approvals,
unscoped decision questions, or schema-v4 L2 checkpoints without evidence
references are marked for audit and do not satisfy schema-v10 gates. Schema-v5
scientific checkpoints retain their meaning while receiving an instruction-
maintenance state during migration. Schema-v6 instruction snapshots migrate to
the matching scope, and decision questions receive ordered target revisions so
an older unconsumed approval cannot override a newer decision. Schema-v7 states
receive bounded scope-removal history, and a confirmed direction without the
mandatory unexposed-dataset search result requires reconfirmation. A schema-v8
confirmed direction without the numeric paper-gain floor also requires
reconfirmation. Schema-v9 paper assessments receive a legacy evaluation-anchor
receipt and explicit missing-evidence markers during migration; they do not
become prospective locks retroactively. Existing scoped approvals
already linked from a checkpoint are migrated as consumed by that checkpoint;
do not silently turn an unrelated old summary into new user approval. Run
`research_queue.py audit STATE` after migration.

New states retain only a bounded recent notification window. Legacy notification
history is preserved until `compact-notifications` is explicitly run, so a
migration does not silently delete existing project material.
