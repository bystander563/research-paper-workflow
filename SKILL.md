---
name: research-paper-workflow
description: Coordinate paper-oriented task and dataset scouting, problem-driven method exploration, external-baseline comparison, experiments, and asynchronous user decisions. Use for starting or continuing active research while the user owns its direction; not for ordinary one-off drafting or inventing evaluation protocols.
---

# Research Paper Workflow

Help the user and agent understand the research, not administer a process.
Keep scientific choices explicit, pursue useful experiments autonomously, and
make the current problem, method, evidence and next move easy to discuss.
The user's latest explicit instruction and scoped project contracts govern;
do not silently substitute a new direction or infer approval from silence.

## Three layers, one research loop

| Layer | Purpose | Working content |
|---|---|---|
| L1: direction and constraints | What is worth studying? | Venue/time, domain, task, datasets, adopted evidence standard, user decisions |
| L2: problem, method and evidence | What is missing, why might our idea work, what have we learned? | Nearest-work gap, unresolved problem path, mechanism, innovation, external comparisons, meaningful attempts and next test |
| L3: execution | How do we perform the test reliably? | Code, configurations, jobs, debugging and native experiment artifacts |

These are content responsibilities, not sequential stages or automatic approval
levels. Inside L1, L2 proposes a test, L3 produces evidence, and L2 revises the
understanding. Return to L1 only when the direction actually needs changing.
In L2, separate **PI-confirmed choices**, **exploratory hypotheses**, and
**supported findings**. A new result updates evidence; it does not confirm a
story or revoke the user's existing selection.

The working loop is:

1. Confirm venue/submission window and domain; an optional idea is a seed unless frozen.
2. Scout meaningful task-dataset pairs and ask the user to select L1; then establish each dataset's strongest source-checked, protocol-comparable external baseline as the continuing reference.
3. Find the deepest defensible unresolved problem in nearest work; derive a mechanism and a discriminating experiment.
4. Screen a minimal candidate, tune promising candidates, and change the leaf/problem when its credible approaches are exhausted.
5. Promote an evidence-backed L2 selection with the user. Complete external comparison and the adopted evidence requirements.
6. When the canonical paper gate is met, produce the report and ask whether to enter writing and which claim to use.

Use [exploration-policy.md](references/exploration-policy.md) for scientific
judgment and [workflow.md](references/workflow.md) for gates. Do not front-load
a paper-length justification onto a tentative idea. Let one research record
mature as evidence arrives; do not create parallel tables for the same method.

## Discuss naturally; preserve decisions

Default to plain-language L1/L2 communication. Keep routine L3 details internal,
but answer an explicit user request for technical details. If an execution
problem changes scientific meaning, explain its consequence, not just the error.

- **Progress:** what changed since the last requested run, what was tried and learned, results against the maintained external baseline first, and the next move. Improvement over our previous version is secondary, not evidence of external competitiveness.
- **Why / discussion:** answer the specific scientific question first; show only the problem-to-evidence chain needed to explain it.
- **Correction / suggestion:** assess the substance, explain the implications, and distinguish a proposed test from an explicit change of direction.
- **Explicit decision:** acknowledge the scoped meaning, record it, and act. Do not ask the same question again to fill an internal form.

Discussion is analysis-only unless the user also requests execution or clearly
directs a change. Do not turn every exchange into an audit or approval packet.
If work cannot be traced to the current direction and hypothesis, stop that
branch, explain the drift, and resolve the actual scope conflict.

Before L2 confirmation, problem-path/leaf/method switches within L1 are
notification-only. Replacing confirmed L1/L2 choices requires a scoped user
decision. Routine metrics, hyperparameters, debugging and implementation remain
autonomous unless explicitly frozen. Paid compute, semantic permission/scope
changes, writing, headline claims and external sends retain user authority.
See [collaboration-policy.md](references/collaboration-policy.md) when a genuine
decision, pause, correction, or unattended monitor needs handling.

## Keep the evidence that changes decisions

- L1/L2 retain current facts, user decisions, source links and meaningful replacements. Do not require an archive of all attempts, negative results or stopping rules. L3 retention follows project utility; this is not permission to delete existing artifacts.
- The problem path starts at the first unresolved layer; one node is valid. Do not manufacture ancestors already fixed by L1. Innovation attaches to the active leaf, not a broad motivation.
- A core contribution must explain a relevant nearest-work gap and distinguish a meaningful simpler alternative. Fusion/stacking cannot carry novelty merely by scoring better; legitimate weighted mechanisms are not rejected by keywords.
- Each adopted dataset has its own source-checked recent strong external comparator and matched results. Keep that reference across iterations and reporting windows; update it when stronger comparable evidence is verified, with a notification explaining the change. Nearest conceptual work and experimental baselines have different roles; internal variants do not replace external evidence.
- Before broad tuning, the agent locks the scientific hypothesis and primary metric/scale/direction. Changed anchors require new or explicitly reassessed evidence; they do not create an extra PI question.
- The paper gate follows [workflow G3](references/workflow.md#g3-paper-decision-ready). Preserve its numeric floor and project-specific stability evidence. No universal aggregation, seed count, significance test, sealed-set or external-label protocol is introduced.
- During L1 scouting, search for a credible dataset not previously exposed in the project, or explain why none is feasible. Adoption remains the user's choice.

## Resume with a small working context

Resolve `<controller>` as `scripts/research_queue.py` relative to this Skill;
state lives at `<project>/.codex/research-paper-workflow.json`.
For active research, read the current direction, active L2 record and pending
decisions, and run the control audit on startup/recovery. An audit concerns
authority and artifacts, not whether an idea is good. Do not reopen already
explicit decisions merely because a new context starts.

Use `research-update` for a decision-relevant progress update: it maintains a
keyed L1/L2 note and its reporting view in one operation, optionally with a
notification. Extend the same note as the candidate matures. Use the baseline
roster as the numeric comparison source; do not manually mirror scores into
several tables. [research-state.md](references/research-state.md) defines the
record layout, command contract, legacy compatibility and paper evidence lock.

At an explicit request to start/continue research, open a reporting boundary
with `window-start`; status queries and automatic wakeups do not reset it.
Report the old window first if asked for status and continuation together.
Carried focus is context, not new progress. Research facts stay in L1/L2.

## Load peripheral mechanisms only when needed

- **Long-running jobs:** reuse native experiment tools; register only what must survive context loss. Use available GPU by default; never rent without permission.
- **Unanswered decisions:** keep independent authorized work moving. Twenty minutes batches questions, not consent. At five active questions, or a direct pause, stop new work and reach a safe endpoint. Deferred decisions stay visible with a revisit condition.
- **Unattended monitoring:** when requested, use the host's scheduled task as a state-aware wakeup. Check compact state/results first, reason only on meaningful changes, and stop future wakeups when required. Without scheduling, preserve recovery information and state the limitation. The controller itself does not schedule or kill processes. Details belong only in [collaboration-policy.md](references/collaboration-policy.md#unattended-monitoring).
- **AGENTS.md:** keep stable execution rules and source pointers, not research history. Read [agents-maintenance.md](references/agents-maintenance.md) only when instructions change, conflict, or need maintenance; no second scientific approval system.
- **Writing:** hand off the selected L1/L2 evidence and paper report to the available submission workflow. Reuse content, but do not treat writing approval as approval of a different story or external submission.

Do not pin a model, introduce a fixed agent team, or add a new research layer.
Use host capabilities only when they remove concrete work from this loop.
