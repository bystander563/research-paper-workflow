# Research records and controller contract

Maintain a small working research record, not a chronological experiment ledger.
[workflow.md](workflow.md) owns gate meaning; this file owns records, sources and
CLI compatibility. Schema v16 separates evolving evidence from PI-selected scope
and provides one write for research notes and progress views.

## Three responsibilities, not three copies

| Owner | Contents |
|---|---|
| L1 direction | Selected task/datasets, venue/time/domain, evidence standard and actual PI decisions |
| L2 research record | Active problem and mechanism, nearest-work gap, evolving hypotheses, evidence, comparison links and meaningful alternatives |
| L3 project tools | Code/configurations, execution and useful native artifacts; optional indexes only |
| Controller JSON | Typed authority, numeric comparison/anchor receipts, pending decisions and recovery/report projections |

L1/L2 retain current facts, meaningful replacements, source links and user
decisions. L3 retention is discretionary. Neither rejection nor this Skill
requires every failed attempt, tuning trajectory, negative result or stopping
rule to be archived. Existing artifacts are not authorized for deletion merely
because the Skill would not have created them. Preserve evidence supporting
active claims or explicitly mark those claims unsupported.

Do not copy dynamic research state into AGENTS.md. Do not require four separate
files for problem, literature, baselines and results: the same L2 record can
contain those evidence sections, with external primary artifacts linked read-only.

## Layout and sources

```text
<project>/.codex/research/
  L1-directions.md
  L2/<direction-id>.md
  L3/                      # optional; native logs may be sufficient
<project>/.codex/research-paper-workflow.json
```

Resolve the controller relative to the invoked Skill, not the research project.
The JSON's adjacent lock serializes controller writes only. It does not prevent
two independent executors from launching the same experiment.

Initialization creates L1 and L2 scaffolding without overwriting existing
scientific records. Existing research-ledger.md remains legacy history; link to
it and move only current decision-relevant content when needed, not its full log.

Checkpoint and paper-report records are project-local files, not controller
JSON, lock/temp files or AGENTS files. IDs are path-safe 1-64-character ASCII
identifiers starting with a letter/digit; descriptive titles belong in content.
External evidence files are referenced without modifying them.

Typed checkpoint receipts are generated from the actual decision and structured
payload, and marked current blocks are updated by the controller. Those blocks
are generated views: do not hand-edit them or duplicate their authority in prose.
The JSON owns structured decisions and comparison arithmetic; surrounding L2
prose supplies the scientific explanation and source artifacts.

## L1 direction record

Keep the active direction and constraints at the top:

- venue/submission window, domain and optional starting idea;
- selected task, dataset description and explicit adopted inventory;
- one primary dataset and every user-adopted supporting dataset;
- task meaning, data fit, headroom and nearest-work risk;
- unexposed-dataset search outcome and adoption recommendation;
- competitive/novelty standard, generalization/second-dataset expectation;
- additional paper requirements and numeric gain floor;
- actual selection/approval source and material later changes.

A small ranked shortlist is sufficient. Weak ideas that never affect a decision
need not persist. Pending questions live in the controller queue, not a second
live checklist in L1. Core fields are owned by their typed checkpoint;
`frozen_by_pi` is only for additional explicit choices.

The canonical numeric formula is in [G3](workflow.md#g3-paper-decision-ready).
`minimum_paper_gain_points` is a number with minimum 1.0;
`paper_ready_threshold` is additional free-text requirements only.
No alternative wording may lower the numeric field.

## L2: one evolving record

Start with a short separation of:

- **Confirmed selection:** what the PI actually adopted; it may still lack evidence.
- **Working hypothesis:** what we are currently testing, possibly different from the selected story.
- **Supported finding:** what the available evidence demonstrates and its limits.

Use one compact entry per decision-relevant mechanism, with links instead of
copies. Let it grow when necessary:

```text
Problem / active leaf (only unresolved ancestry needed)
Nearest work and the specific remaining gap
Suspected cause -> intuition -> predicted difference
Mechanism / necessary mathematics
Relevant simpler alternative and discriminating experiment
Observed evidence / interpretation / uncertainty
External comparison reference and starting/best/latest result when relevant
Next scientific action or reason for changing direction
```

This is a content guide, not a form that every idea must fill.
Tentative ideas may remain conversational. A cheap test does not need a complete
paper claim. One node is a valid problem path; do not invent fixed ancestors.
Methods with the same scientific mechanism share a cluster even when code,
backbone or hyperparameters differ. Keep the path and meaningful alternatives,
not a full ontology. Exhausted clusters need only the conclusion that changes
the next decision.

Keep one source record for each decision-relevant paper: title, venue/year,
URL/DOI, search scope/date, pertinent protocol, mechanism/result, exact overlap
and gap, and verified fact versus inference. A paper may serve both a conceptual
and experimental role, but these roles must remain distinguishable.

Keep experimental evidence in three recognizable categories: external matched
methods, our proposed mechanism, and internal variants/ablations. They can share
one table or tracker. Link run/version, protocol, metric, stability evidence and
supporting artifact; do not copy a baseline score into several hand-maintained
tables. A ceiling summary extends the same method entry rather than adding a
parallel method-cluster summary.

### One research update

For a meaningful L1/L2 development, prefer:

```powershell
python <controller> research-update STATE --layer L2 --kind method_cluster --subject-id M001 --title "Mechanism being tested" --status SCREENING --observation "What was observed; cite the evidence path" --interpretation "What this does and does not support" --next-action "Next discriminating test" --set-current --hypothesis "Predicted scientific difference" --current-action "Current scientific test"
```

This updates one keyed note in the active L1/L2 Markdown record and the window
projection together. Optional `--record` selects another existing project-local
record. Optional `--starting-result`, `--best-result`, `--latest-result` and
`--disposition-reason` enrich the same entry rather than creating trial records.
For a problem entry, `--problem-path` repeats ordered IDs ending at its subject.

Within the same recorded scientific scope, omitted optional fields keep their
existing values across reporting windows. The same managed note contains a
generated recovery payload, not a separate ledger. Updating the current subject
refreshes its latest-result/next-action view without repeating `--set-current`;
updating another subject does not make it current. Existing hypothesis and test
descriptions remain in the note. Use `--clear-field best_result` (repeatable for
optional fields) to remove invalid or superseded information; omission is not
deletion. Changed scientific scope does not inherit old evidence automatically.
Legacy unscoped notes are retained for review, not assigned fabricated validity.

Use `--notify-kind` and optional `--notification` for a material notification in
the same operation. For `problem_switch` or `method_cluster_switch`, `--from-id`
is the old identity and `--subject-id` is the new one; notify-kind must match the
entry kind. `problem_path_change` is for same-leaf refinement. No extra question
or notification copy is required. Scientific switches still need to be
communicated in the actual conversation, not merely stored.

L2 updates require confirmed L1, not confirmed G2. They cannot promote a
selection, authorize writing or change a verified baseline score. A missing
numeric comparison is explicitly unresolved. Use `baseline-roster` to record
numeric evidence; its reporting projection is generated automatically.
An approved writing handoff must be revoked before resuming research updates.

For L2, the update receipt and status view generate their external reference
from the canonical roster; the durable method note keeps a pointer, not a second
baseline score. The optional legacy `--external-baseline-gap` is an additional
comparison note and cannot replace that reference. Free-text latest/best values
are not automatically treated as protocol-matched scores: after checking the
dataset/protocol, update `our_score` in the appropriate roster row. Status always
includes the external rows, source and search scope, even after a new window.

Generated research blocks are keyed by layer/kind/subject and updated in place.
Keep genuinely decision-relevant alternatives as separate entries. A reporting
boundary clears the window projection, not these durable notes. File writes
precede the derived state save; if a write is interrupted, inspect the durable
note and repair the projection rather than infer a new approval.

## Comparison roster and evaluation anchor

`baseline-roster` is the numeric comparison source with exactly one row per
adopted dataset. A row contains:

```json
{
  "dataset": "Dataset-A", "role": "primary",
  "baseline": "Published method", "venue_year": "Venue year",
  "source": "Primary source", "search_scope": "Sources/dates examined",
  "protocol_match": "Task/split/input/metric match evidence",
  "protocol_status": "PENDING_MATCH", "status": "IDENTIFIED",
  "comparison_roles": {
    "dataset_origin": {"status": "COVERED", "evidence": "Source"},
    "recent_top_conference": {"status": "COVERED", "evidence": "Source"},
    "different_published_mechanism": {"status": "BLOCKED", "evidence": "Concrete reason"},
    "strong_simple": {"status": "COVERED", "evidence": "Comparator"}
  },
  "metric": "Primary metric", "metric_scale": "unit_interval",
  "baseline_score": null, "our_score": null
}
```

Check exact field/enum names with `baseline-roster --help` and current parser.
Exploration permits `IDENTIFIED`/`BLOCKED`; paper comparisons require
`MATCHED` and `VERIFIED_MATCH`. Each comparison role has coverage or a concrete
blocker; recent top-conference coverage is required at the paper gate.
Rows cannot borrow scores or roles across datasets. Narrative protocol evidence
must actually support the typed status; the controller is not a literature reviewer.

The roster has a direction ID, revision, payload hash and durable receipt.
Changes invalidate stale paper packets, not the user's task selection.
Existing matched comparisons stay visible while other evidence is gathered.

Before broad tuning, `evaluation-anchor` records ordered problem path, active
leaf, method cluster, falsifiable prediction, primary metric, scale and
higher-is-better direction. It has its own revision linked to L1. Scientific
changes apply prospectively; earlier results must be rerun or explicitly
reassessed before supporting a new anchor. This does not impose an aggregation
rule or ask the PI to approve metric details.
Replacing an existing anchor with a changed scientific/metric scope keeps the
external reference and its published score, but clears current `our_score` and
returns completed rows to `IDENTIFIED`. Previous comparisons remain in roster
history. After a rerun or documented reassessment, register the valid comparison
with `baseline-roster`; changing a method cannot borrow its predecessor's score.

## Confirmed choices versus evidence versions

`confirm --layer science` records the scoped PI selection and evidence links:
problem portfolio, nearest work, external comparisons and results. The links
may point to the same L2 file; no extra dossiers are required.
The CLI accepts `--alternative-explanation`; the persisted legacy field name
`simple_combination_counterfactual` remains for compatibility.
Scientific adequacy must be reviewed by the agent; a keyword is not a veto.

A later evidence edit does not withdraw PI approval. Missing evidence makes
dependent claims unusable; new or contradictory evidence must be interpreted
in the working L2 record. Do not keep using a result invalidated by an L3 repair.
A genuine replacement of the approved problem, mechanism or claim still needs
the corresponding scoped decision.

At G3, the controller snapshots current science-evidence hashes into
`science_evidence_at_gate`, alongside the content-locked report and structured
payload. Subsequent changes block consuming the old report's approval.
Evidence embedded in the report is protected by the report's own hash, avoiding
a self-hash cycle. Rebuild/reassess the paper report, not the same L2 selection,
when only evidence changes.

## Reporting window

The `research_window` is a replace-on-next-explicit-execution projection, not a
second scientific authority. Its start snapshot contains checkpoint and
baseline/anchor revisions. Keyed cards are updated from research updates,
checkpoint changes, roster changes and scientific switch notifications.

`current_focus` states the hypothesis, current scientific test, latest
interpretable result and next move. A new window may carry that focus only
across unchanged scientific scope. The reported
`context_origin=carried_forward_not_new_progress` distinguishes it from work
performed in the new window. Closed/exhausted candidates cannot remain current.
Evidence-only roster updates do not change that scope. Changed task, scientific
selection or hypothesis/metric anchor prevents stale focus from being carried
or reported as current. Legacy focus without a trustworthy scope must be
refreshed from the current research record, not guessed from job history.

`status --window` is read-only, excludes L3 jobs/errors and does not acknowledge
monitor state. If a historical boundary is absent, say so; do not fabricate
since-start activity. Current verified L1/L2 remain reportable.
The user need not know card IDs or controller phase names.

## Decisions, jobs and optional maintenance

Questions have stable targets; approving/selecting decisions apply only to the
matching target and latest revision, are consumed once and cannot be inferred
from a filename, good score or timeout. Direct instructions can be recorded
without creating a synthetic question. `reject`, `defer` and `informational`
do not authorize a gate. Deferred questions need a revisit condition.

The controller retains bounded notification and instruction receipts. This is
not a requirement to retain every experiment. Jobs store command/session, next
check and next action only when needed for recovery; use existing L3 trackers.
The controller never schedules or kills a process. Monitoring and pause semantics
are in [collaboration-policy.md](collaboration-policy.md).

AGENTS snapshots are conditional maintenance metadata, not research content.
Existing advanced `agents-*` commands remain compatible; do not create audit
scopes for every directory during normal research. Read
[agents-maintenance.md](agents-maintenance.md) when that work is actually needed.

## Compatibility and migration

- Schema v16 preserves v15 scientific selections, IDs and queued decisions; merely upgrading does not require repeating G1/G2.
- A pre-v16 paper packet lacks the new evidence-version binding and must be rebuilt before it can support a new paper decision. Do not fabricate historical evidence hashes.
- Earlier migrations retain their legacy-unverified flags. Unscoped approvals, unknown dataset inventories or missing scientific anchors require evidence-based recovery, not guessing.
- Pre-v14 states have no trustworthy reporting boundary; do not reconstruct one automatically.
- The old `window-note` command remains a projection-only compatibility path. Prefer `research-update` for durable progress; do not invoke both for the same event.
- The legacy counterfactual field/flag accepts the relevant-alternative explanation. No mandatory anti-averaging essay or novelty keyword classifier remains.
- Read-only load/status migrates in memory; authorized state writes persist the current schema. Do not run old controllers against a newly written state.
