# Workflow and gates

This file owns research phases and scientific approval gates.
[exploration-policy.md](exploration-policy.md) owns research judgment;
[collaboration-policy.md](collaboration-policy.md) owns interaction and monitoring;
[research-state.md](research-state.md) owns records and controller contracts.

## Layers are not phases

L1 is direction/constraints, L2 is evolving problem-method-evidence reasoning,
and L3 executes experiments. All remain available throughout research.
L2 contains both exploratory hypotheses and explicitly confirmed selections;
an update to one is not automatic authority over the other.

The controller's phases are `discussion`, `exploration`,
`confirmed_project`, `paper_ready_pending_pi`, and
`paper_handoff_approved`. Pause and reporting windows are overlays, not new
layers, research achievements or PI approvals. Do not expose phase machinery
when an ordinary explanation answers the user's question.

## Start or resume

Discussion remains analysis-only unless the user requests execution or clearly
directs a change. To begin exploration, obtain venue/submission window and domain.
An optional idea is a seed unless separately fixed. Changing only that seed
does not invalidate already confirmed L1/L2 choices. Preserve it when changing
venue/domain unless the user explicitly clears it.

For an existing state, run the control audit and read the current L1/L2 and
pending decisions. Check actual instruction conflicts before dependent work;
load instruction-maintenance procedures only for changed/conflicting instructions,
a changed scope, or deliberate maintenance. Do not run a maintenance ceremony
merely because a researcher asked to discuss a method.

For an existing project without state:

- active method research: establish the earliest genuinely missing choice;
- substantially fixed task/method/experiment/manuscript package: route directly to the submission workflow;
- ordinary non-paper work: do not activate this Skill.

Use explicit decisions already present in the conversation or durable evidence.
Do not infer consent from code or results, and do not ask the user to repeat
an unambiguous decision just to create a receipt.

## G1: selected task and datasets

Scout a small ranked shortlist and recommend a meaningful task-data pair.
Explain fit, headroom, nearest-work collision, external comparisons,
feasibility, and the unexposed-dataset search outcome.

The user selects the task and datasets and adopts the evidence standard:
competitive/novelty requirements, generalization or second-dataset requirements,
additional paper conditions and any stricter numeric gain floor. Explicit
"not required" or deferred expectations are valid where applicable; neither
waives the required dataset search nor lowers G3's numeric floor.

A typed L1 checkpoint binds the actual scoped approving/selecting decision to:

- task, dataset description and explicit adopted-dataset inventory;
- exactly one primary dataset and every adopted supporting dataset;
- unexposed-dataset search outcome;
- evidence standard and the numeric paper floor.

Cheap feasibility checks may continue while a choice is pending. Sustained
method search and broad tuning require confirmed L1. Replacing an adopted
task/dataset or evidence standard needs a scoped decision, not a timeout.
After selection, establish the external comparison reference for each adopted
dataset as described in [exploration-policy.md](exploration-policy.md#nearest-work-and-external-comparisons).
Incomplete reproduction may coexist with cheap diagnostics; it does not turn
our own starting model into the competitive reference.

## Work inside L1: hypotheses before a fixed story

Use nearest-work evidence to locate the deepest defensible unresolved leaf.
Fixed upstream scope is background; one problem node can be sufficient.
Derive the method from a suspected cause and test a representative minimal
candidate. Grow one record through hypothesis, diagnostics, external comparison,
ceiling search and interpretation rather than duplicating templates.

Before broad tuning:

- source-check the external-baseline roster for every adopted dataset;
- lock problem path/leaf, method cluster, falsifiable prediction, primary metric,
  scale and direction in the agent-owned evaluation anchor.

A baseline row may still be `IDENTIFIED` or `BLOCKED` during exploration.
Full matched reproduction need not precede a cheap diagnostic. The roster must
not be fabricated from our own variants, and unmatched scores cannot justify
paper-readiness. Numeric/structural validation is not scientific verification.

Switching exploratory problems or methods within L1 is autonomous with a
plain-language notification. Changing the anchor needs no extra PI question;
old-anchor results require new evaluation or an explicit evidence reassessment.
Before closing a mechanism, check implementation, baseline health and an
informative diagnostic. If credible clusters fail, reconsider the leaf.

## G2: promote the scientific selection

When a ceiling summary and meaningful external comparison exist, discuss the
current problem, mechanism, innovation, evidence and remaining weakness. Ask
whether to adopt that scientific selection, keep it exploratory, or close it.
An internal best score does not decide this for the user.

The checkpoint records a scoped explicit PI decision and binds the current L1
to problem path/leaf, method cluster, mechanism, falsifiable prediction, relevant
alternative explanation, innovation and source-linked evidence. Its problem,
method and prediction match the active evaluation anchor.

This promotes a **selection**, not every future sentence or evidence-file byte.
New results and literature can update the working record without repeating G2.
When evidence contradicts the premise, mark the conclusion unsupported, stop
using it, and discuss the consequence. Replacing the confirmed problem,
mechanism, prediction or innovation still needs a scoped decision.

An exploratory branch may coexist with confirmed L2 when authorized. Keep that
distinction explicit: the exploratory anchor never silently overwrites the
confirmed story, and only a matching confirmed selection can pass G3.
Do not block all independent exploration just because an older story is no
longer the current hypothesis.

## G3: paper decision ready

This gate means "ready to ask the user", not automatic writing approval.

Require:

- valid L1/L2 selections and an evaluation anchor matching the scored scientific hypothesis;
- one `MATCHED`, `VERIFIED_MATCH` comparison row per adopted dataset, with source-checked recent top-conference coverage;
- explicit coverage or a concrete blocker for dataset-origin, recent top-conference, different published mechanism and strong-simple roles; a missing essential comparison blocks the claim;
- task/data/split, labels, inference information, metric and evaluation comparability checked from primary sources;
- current, interpretable results and project-appropriate repeat/uncertainty/stability evidence;
- assessment against every adopted L1 requirement, a narrow supported claim and strongest remaining objection.

The primary metric is higher-is-better on a `0-1` or `0-100` scale.
Let `gain_points = (ours - baseline) * 100` for `unit_interval`, or
`gain_points = ours - baseline` for `percentage`. It must be at least
`minimum_paper_gain_points >= 1.0` over the strongest recent top-conference
protocol-matched baseline found for the primary dataset. Use the configured
stricter floor when present. Free-text `paper_ready_threshold` supplies only
additional requirements; it cannot redefine or lower the numeric field.
Do not silently convert an incompatible metric to satisfy this gate.

Generate a readable project-local paper report from the existing L1/L2 and
comparison evidence, adding only the missing decision synthesis. Include task,
datasets, active problem and nearest-work gap, innovation, concrete method,
per-dataset comparisons, primary baseline identity/venue/source/search scope,
metric/scale, scores and computed gain, stability, remaining objections,
necessary versus optional work, and proposed headline claim.

The report and its structured payload are locked at G3, together with current
science-evidence versions. Evidence changes after G3 require a rebuilt report;
they do not automatically revoke L1/L2 selections. Embedded and separately
stored evidence follow the same principle. The controller verifies structure,
arithmetic, provenance and version consistency; the agent verifies science.

If the headline selects favorable seeds from a larger pool, disclose the total
pool, selection rule and scientific risk to the user in the decision conversation
and obtain scoped acceptance. Keep those details out of L1/L2, result cards,
the report, AGENTS.md, README and downstream manuscript artifacts; retain only
the minimal controller acceptance receipt. No universal seed count, aggregation
or significance test is added by this workflow.

Only after the current report exists, ask whether to write and which claim to
use. Bind the decision to that exact report. Older/pre-report questions cannot
authorize a rebuilt report; silence or a high score cannot pass this gate.

## Writing handoff

A typed paper checkpoint records the current report, confirmed science, chosen
headline claim and handoff target, entering `paper_handoff_approved`.
Reuse that package downstream rather than rewriting the same story. Respect the
submission workflow's actual approval contract; writing approval does not
approve a different story or any external submission.

If declined or deferred, continue only authorized research. If the user revokes
writing, `paper-revoke` retains L1/L2, withdraws paper authorization and requires
a new report/decision before re-entry. Do not create retrospective approvals.

## Reporting and recovery overlays

A new explicit start/continue/run/iterate/monitor request opens a reporting
window; a status query, discussion or automatic wakeup does not. For a combined
status-and-continue message, report the previous window before starting another.
A new boundary clears the delta view, not durable research notes. Carry the
previous focus only when its scientific scope remains unchanged and label it
as context, not newly performed work.

Use `research-update` once per meaningful research development to update its
keyed L1/L2 note and reporting projection. Numeric comparisons come from the
roster. Retain selected intermediate conclusions, including branches tried and
closed within a window, without a trial-by-trial archive.
Controller-generated checkpoint/baseline/switch projections need no manual copy.

Pause does not erase phase or scientific choices. The user can pause directly;
five active unanswered PI decisions also stop new work at a safe endpoint.
Deferred items are visible but do not count. For precise queue semantics, safe
job recovery and unattended scheduling, read
[collaboration-policy.md](collaboration-policy.md).

## Control audit

Audit on startup/recovery, after migration and before paper handoff. It checks
typed authority, scoped decision receipts, required records, baseline/anchor
consistency and paper evidence locks. It does not certify novelty or baseline
comparability. A missing/changed artifact should block its dependent claim or
gate, not manufacture a new scientific choice.

AGENTS maintenance and job recovery are conditional execution support. Their
procedures are not additional scientific stages. Do not repeatedly run a full
audit during ordinary discussion or unchanged monitoring.
