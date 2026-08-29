# Layered research state

Read this reference for research spanning multiple runs, monitoring cycles, or
context compactions. It defines the durable scientific state, not a chronological
ledger of all activity. `research_queue.py` separately records typed PI
questions, structured checkpoints, phase state, resumable active jobs, and a
bounded project-instruction maintenance receipt. Schema v15 also carries one
replace-on-next-instruction macro reporting window and binds experiments to the
active L2 problem path.

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

## Current research window: non-authoritative reporting cache

`research_window` answers one user question: what changed at L1/L2 since the
latest explicit request to run research? It is an overlay, not L4, not a full
ledger, and not evidence or approval for a scientific gate. Starting the next
window replaces its cards without archiving the previous window.

The state contains:

```text
sequence, id, status, started_at, instruction, start_snapshot, revision
cards[]
current_focus
```

`start_snapshot` contains only the phase, checkpoint IDs/statuses,
baseline-roster revision/hash, and evaluation-anchor revision. It does not copy
L1/L2 payloads. Cards are keyed by `(layer, kind, subject_id)` and updated in
place. Allowed identities are:

- `L1 / task_dataset`;
- `L2 / problem`;
- `L2 / method_cluster`;
- `L2 / baseline_comparison` for one adopted dataset.

Each card separates verified observation from agent interpretation and records
status, representative starting/best/latest results when available, the current
dataset-specific external-baseline gap or blocker, disposition reason when
useful, and the next macro action. It must not create one card per run, variant,
hyperparameter, seed, bug, or stopping rule. `current_focus` references an
existing non-terminal card and gives the active hypothesis, current macro test,
latest interpretable result, and next macro action.
An `L2 / problem` card may additionally carry the ordered unresolved
`problem_path`; it must end at that card's `subject_id`. This is a projection of
L2, never a second authoritative problem tree.

L3 is never copied into this cache. The controller rejects L3 cards. Jobs,
commands, sessions, raw errors, debugging, and engineering repairs stay in the
job registry, native logs, or optional L3 index. If they change scientific
meaning, update the affected L1/L2 card with only the consequence, such as an
invalidated result or a baseline gap that must be remeasured.

The window cannot confirm or replace compass, L1, L2, paper, baseline-roster,
evaluation-anchor, evidence-record, or PI-decision state. Its revision enters
the semantic monitoring fingerprint so a scheduled wakeup can detect new macro
evidence, while compact status exposes only the window ID/revision, not card
text. `status --window` is read-only and omits active jobs and all L3 detail.

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
<project>/.codex/research-paper-workflow.json.lock  # controller mutex; no research content
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
modifying them. Never reuse the workflow JSON, its lock/temp files, or a project
`AGENTS.md`/`AGENTS.override.md` as a scientific checkpoint or assessment record.

The adjacent lock file serializes mutating controller commands from interactive
and scheduled tasks. It contains no scientific state and may remain present
between runs. A busy lock means another controller command is active; retry
after it finishes instead of bypassing the controller.

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

The schema-v15 controller stores one project-local instruction-chain snapshot per
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
- user-supplied starting concept and any separately named user-frozen
  constraint that makes it central;
- mandatory unexposed-dataset search result, feasibility, and recommendation;
- competitive target, such as SOTA, near-SOTA, or another user-defined bar;
- novelty sufficiency standard;
- generalization, second-dataset, or other evidence requirement, including an
  explicit “not required” when that is the user's decision;
- additional project-specific paper-ready requirements, which may tighten but
  never lower the numeric gain floor;
- numeric paper-gain floor: at least 1 percentage point over the strongest
  recent top-conference protocol-matched baseline; a project may set it higher.
- explicit adopted-dataset inventory: exactly one `primary` dataset plus every
  user-adopted `supporting` dataset. A descriptive bundle name is not a
  substitute for this list.

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

The schema-v15 L1 checkpoint separately stores the selected task type, dataset,
explicit adopted-dataset inventory,
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

## External-baseline roster and evaluation anchor

After L1 confirmation, maintain the structured controller roster with
`baseline-roster`. It has exactly one row for every adopted dataset and the same
primary/supporting role. Each row stores baseline identity, venue/year, primary
source, search scope, protocol evidence, typed protocol status, comparison-role
coverage, metric/scale, score slots, and one of:

- `IDENTIFIED`: the strongest eligible comparator has been source-checked;
- `BLOCKED`: the comparator or protocol cannot currently be matched, with the
  blocker retained in the L2 record;
- `MATCHED`: baseline and our result are available under the stated protocol.

Protocol status is `PENDING_MATCH`, `BLOCKED`, or `VERIFIED_MATCH` and must agree
with the row status. A paper-gate row must be both `MATCHED` and
`VERIFIED_MATCH`; explicit mismatch language cannot be labeled verified. Each
row also contains exactly these comparison roles:

- `dataset_origin`;
- `recent_top_conference`;
- `different_published_mechanism`;
- `strong_simple`.

Each role is `COVERED` with source evidence or `BLOCKED` with a concrete
blocker. The recent top-conference role must be covered at G3; other genuine
blockers narrow the claim and remain visible rather than disappearing.

The JSON row accepted by `baseline-roster` uses this shape (scores may be
`null` until the row becomes `MATCHED`):

```json
{
  "dataset": "Dataset-A",
  "role": "primary",
  "baseline": "Method and paper identity",
  "venue_year": "SIGIR 2026",
  "source": "primary URL or project evidence reference",
  "search_scope": "venues, years, and search date",
  "protocol_match": "task/split/labels/input/metric/evaluation evidence",
  "protocol_status": "PENDING_MATCH",
  "comparison_roles": {
    "dataset_origin": {"status": "COVERED", "evidence": "paper/source"},
    "recent_top_conference": {"status": "COVERED", "evidence": "paper/source"},
    "different_published_mechanism": {"status": "COVERED", "evidence": "paper/source"},
    "strong_simple": {"status": "COVERED", "evidence": "method/result"}
  },
  "metric": "primary metric",
  "metric_scale": "unit_interval",
  "baseline_score": null,
  "our_score": null,
  "status": "IDENTIFIED"
}
```

The roster may be revised when literature search finds a stronger eligible
comparator or evidence changes. Each revision invalidates a pending paper packet
but not routine L2 implementation work.

Only after the roster exactly covers the adopted datasets, and before broad
tuning, the controller stores an agent-owned evaluation anchor containing the
active direction ID, ordered problem path, active leaf ID, method-cluster ID,
falsifiable prediction, primary metric, `0–1` or `0–100` scale,
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
Active problem + method-cluster decision source:
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

### Active problem path and alternatives

Group nearest work into clusters that share a scientific problem. L1 already
owns the task/dataset scope; L2 starts at the first unresolved layer and retains
the ordered path to the deepest defensible active leaf. A one-node path is valid
and fixed or irrelevant ancestors are not fabricated. Maintain:

```text
path position | problem ID | parent problem ID | status | nearest-work cluster | unresolved problem | scientific value | failure evidence | paper-grade rationale | next action
```

Useful statuses include `SCOUTING`, `ACTIVE_SCREEN`, `PROMISING`, `EXHAUSTED`,
`CLOSED`, and `CONFIRMED_BY_PI`. Retain the active path plus only alternatives
that determine the next choice or received a user decision. The active leaf must
concern knowledge, capability, estimand, mechanism, diagnosis, or another paper
contribution. Runtime, data plumbing, memory use, ordinary bugs, hyperparameters,
and implementation inconvenience belong to L3.

### Problem-linked method clusters

For the active leaf, group methods by shared solution intuition and
mathematical mechanism:

```text
active leaf problem ID | method-cluster ID | status | shared intuition | mathematical mechanism | simple-combination counterfactual | falsifiable prediction | representative evidence | external-baseline gap | next action
```

Useful statuses include `HYPOTHESIS`, `CHEAP_SCREEN`, `PROMISING`,
`CEILING_SEARCH`, `EXHAUSTED`, and `CONFIRMED_BY_PI`. A hyperparameter,
backbone, code path, or extra module does not create a new cluster unless the
scientific mechanism or falsifiable prediction changes. Every core candidate
states what an ordinary average, weighted fusion, heuristic ensemble, or module
stack cannot capture about the leaf. Those combinations may be baselines or L3
tools; weighting remains eligible only when the contribution is a distinct
estimand, objective, constraint, mechanism, or theory rather than fusion itself.

When a cluster is exhausted, keep its compact representative conclusion only if
it affects the next scientific choice. Try another justified cluster for the
same leaf, or mark it exhausted and activate another justified leaf. Record every
problem-path, leaf, or method-cluster switch in plain language. Stable previous
and new IDs are required when identity changes; a same-leaf path refinement is
described directly. Replacing an already confirmed L2 selection also needs
scoped PI approval.

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
must contain every applicable role below; record an explicit blocker and the
weaker remaining claim when a role genuinely does not exist or cannot be run:

1. **Dataset-origin anchor:** the dataset paper's official result or method.
2. **Recent top-conference comparator:** the strongest recent top-conference
   method found for the same task under a directly comparable or matchable
   protocol. Record venue/year and a primary source.
3. **Different published mechanism:** an external method not merely another
   version of the proposed approach.
4. **Strong simple baseline:** a conventional model testing whether the added
   mechanism is needed.
5. **Internal controls:** variants and ablations in a separate block.

Maintain the decision-relevant external comparisons by dataset, not only by
method. Every adopted primary or generalization dataset gets one current row:

```text
dataset | role | strongest recent top-conference baseline | venue/year | primary source | venues/year range/search date | protocol evidence/status | comparison-role coverage/blockers | metric/scale | baseline result | our matched result | IDENTIFIED, BLOCKED, or MATCHED
```

Use `IDENTIFIED`, `BLOCKED`, or `MATCHED` for the controller roster. The
baseline attached to one dataset does not establish competitiveness on
another. Update the row when literature search finds a stronger eligible
comparator or when a protocol repair changes either score.

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
numbers. Apply the canonical numeric rule from
[workflow G3](workflow.md).

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

### Method-cluster and ceiling summary

Maintain only a small set of decision-relevant method clusters:

```text
active leaf problem ID | method-cluster ID | status | mechanism | predicted diagnostic | simple-combination counterfactual | representative cheap-screen evidence | external-baseline gap | best result | next action
```

For each promising method cluster that receives broad tuning, retain the scientific
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
scientific-story checkpoint. Ask whether to promote the problem path + active
leaf + method cluster
+ core mechanism + innovation claim, keep it exploratory, or close it. The agent does not promote
it merely because it is the best internal variant.

The schema-v15 L2 checkpoint stores the active direction ID, ordered problem
path, active leaf ID, method-cluster ID, problem, nearest-work gap, paper-grade
rationale, core mechanism, simple-combination counterfactual, falsifiable
prediction, contribution type, innovation claim,
external-baseline status, ceiling summary,
approving outcome, durable-record path, and hashed references to the nearest-
work, problem-portfolio, external-baseline, and result records used for the
decision. A queued
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

1. current task, descriptive dataset bundle, and explicit adopted datasets;
2. compact problem path, active leaf ID, and problem in current/nearest work;
3. innovation, core mechanism, and method-cluster ID;
4. concrete method;
5. final decision-relevant results;
6. the current baseline-roster revision/hash and a per-dataset matrix linking every adopted dataset to its own strongest
   recent top-conference baseline and our matched result, plus the dataset used
   for the headline numeric comparison;
7. strongest recent top-conference protocol-matched baseline, venue/year,
   primary source, and literature-search venues/year range/date for that primary row;
8. protocol-match evidence covering task, data/split, labels,
   supervision/inference information, metric, and evaluation procedure;
9. current evaluation-anchor revision and evidence that the scored result was
   produced or reassessed under it;
10. higher-is-better primary metric and scale (`0–1` or `0–100`), baseline score,
   our score, computed percentage-point gain, and required L1 floor;
11. project-appropriate repeat, uncertainty, or stability evidence, without a
    universal seed count, aggregation method, or significance test;
12. competitive, novelty, generalization, and additional paper-ready assessments;
13. narrowest supported claim, remaining objection, and necessary versus
    optional work.

The controller copies L1 task/adopted datasets and L2 problem path/active leaf/
method-cluster/innovation/mechanism into
the report receipt, checks numeric arithmetic and the floor, ties it to the
active checkpoint IDs, and content-locks both the file and structured payload.
A queued paper decision must be created and answered after this receipt; the
paper checkpoint stores its structured-payload hash and generation time in the
decision source. The agent remains responsible for verifying top-conference
status and protocol comparability from primary sources. A report that passes
these mechanical checks is still evidence for the user's paper decision, not
the decision itself.

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

Engineering problems are resolved here autonomously: crashes, data loading,
memory/runtime performance, ordinary model configuration, hyperparameters,
metrics plumbing, and routine bug repair. Do not elevate them into L2 to create
an innovation story. If a repair changes the sample, label, estimand, model
family, baseline gap, mechanism conclusion, or another scientific meaning,
propagate that effect upward and notify the user only of the resulting L1/L2
consequence, not the L3 repair.

Long-running jobs that must survive context compaction should also be registered
in the controller with a command or session ID, status, meaningful next check,
and concrete next action. Active records missing either scheduling field fail
the control audit. This job registry is live recovery state and may be pruned
after a job finishes; it is not a required experiment archive.

Regardless of retention, propagate changes in scientific meaning upward:

- invalidate affected L2 result rows when a bug changes their support;
- notify a model-family change only when it changes the L2 mechanism,
  comparability, or conclusion boundary, and describe that macro consequence;
- notify every problem-path, active-leaf, or method-cluster switch in plain language;
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

Schema-v1 through schema-v14 states are readable. Unstructured L1/L2 approvals,
unscoped decision questions, or schema-v4 L2 checkpoints without evidence
references are marked for audit and do not satisfy current gates. Schema-v5
scientific checkpoints retain their meaning while receiving an instruction-
maintenance state during migration. Schema-v6 instruction snapshots migrate to
the matching scope, and decision questions receive ordered target revisions so
an older unconsumed approval cannot override a newer decision. Schema-v7 states
receive bounded scope-removal history, and a confirmed direction without the
mandatory unexposed-dataset search result requires reconfirmation. A schema-v8
confirmed direction without the numeric paper-gain floor also requires
reconfirmation. Schema-v9 paper assessments receive a legacy evaluation-anchor
receipt and explicit missing-evidence markers during migration. That legacy
anchor cannot pass the paper gate: return to `confirmed_project`, lock the
metric again, and rebuild the assessment with actual stability evidence.
Schema-v10 paper packets without the per-dataset baseline matrix return to
`confirmed_project`. Schema-v11 states migrate their monitor artifact receipt to
a legacy unscoped field. A valid locked per-dataset paper matrix may seed the
schema-v12 adopted-dataset inventory and baseline roster; otherwise the L1
inventory must be normalized only when unambiguous or reconfirmed by the PI.
Legacy L2 science must be reconfirmed with a paper-grade problem ID,
method-cluster ID, falsifiable prediction, contribution type, and
problem-portfolio evidence. Any obsolete paper packet leaves a bounded
invalidation receipt containing its durable path and gate hashes rather than
silently disappearing.
Schema-v12 baseline rows did not structurally separate protocol status from
free text or enumerate comparison-role coverage. Migration labels those fields
`LEGACY_UNVERIFIED`, archives any pending paper packet, and requires a revised
roster before the evaluation anchor or G3 can be used again.
Existing scoped approvals
already linked from a checkpoint are migrated as consumed by that checkpoint;
do not silently turn an unrelated old summary into new user approval. Run
`research_queue.py audit STATE` after migration.

New states retain only a bounded recent notification window. Legacy notification
history is preserved until `compact-notifications` is explicitly run, so a
migration does not silently delete existing project material.

Schema-v13 states receive an empty `research_window` with status `NOT_STARTED`.
Migration never infers a past execution boundary or attempts from jobs,
notifications, logs, checkpoint timestamps, or file modification times. The
first later explicit user run instruction starts the first trustworthy window.

Schema-v14 science migrates conservatively to `problem_path=[problem_id]`; no
ancestor is inferred. Its old evaluation anchor is archived as scientifically
unscoped and cannot pass G3. Relocking the exact same leaf, method cluster, and
falsifiable prediction may also add a plain-language simple-combination
counterfactual to the durable L2 record without a new PI question. That
agent-owned enrichment must leave the existing problem, nearest-work gap, core
mechanism, prediction, contribution type, and innovation claim unchanged; any
semantic change follows the normal scoped L2 decision rule.
