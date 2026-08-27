# Project-instruction maintenance

Read this reference when creating, auditing, compacting, or semantically
changing a project `AGENTS.md` or `AGENTS.override.md`. These files are a stable
operating contract and router. They are not another research-state layer.

The canonical Codex discovery and precedence behavior is documented in the
[OpenAI AGENTS.md guide](https://developers.openai.com/codex/guides/agents-md).
This workflow audits the project-local portion of that chain; global Codex
instructions may consume additional instruction budget.

## Relationship to the research workflow

Project instructions and research state have different jobs:

- `AGENTS.md` says **how work in this repository must be performed**.
- L1 says **which task, dataset, and evidence standard the user selected**.
- L2 says **which problem, mechanism, innovation claim, comparison set, and
  decision-relevant results currently support the paper line**.
- L3 contains optional implementation and execution detail.
- `research-paper-workflow.json` records phase, scoped PI decisions, active
  jobs, notifications, and bounded instruction-maintenance receipts.

Instruction maintenance is an overlay, not L0/L1/L2/L3 and not a workflow
phase. It cannot confirm a scientific checkpoint, change the five-question
limit, or turn a notification into approval.

Never copy the current task, dataset shortlist, nearest-work table, result
matrix, experiment history, pending jobs, manuscript progress, or PI question
queue into `AGENTS.md`. Route an agent to the current canonical file instead.

## What belongs in project instructions

Keep only project-wide or directory-stable material that changes execution:

1. project scope in one or two sentences;
2. canonical truth-source paths and when each must be read;
3. stable setup, run, test, and validation commands;
4. durable authority, safety, data-handling, and protocol invariants;
5. definition-of-done checks that cannot be delegated to ordinary CI;
6. links to narrower directory instructions.

Do not put these in project instructions:

- current best results, leaderboard tables, or baseline gaps;
- candidate methods, literature summaries, or novelty arguments;
- trial histories, negative-result archives, tuning traces, or stop rules;
- dated handoffs, monitoring state, open questions, or job/session IDs;
- copied L1/L2 content or long copies of a protocol available elsewhere;
- formatting and lint rules already enforced reliably by repository tooling.

When no stable project-specific instruction or router is needed, do not create
an `AGENTS.md` merely because this workflow is active.

## Bounded structure

Prefer this compact shape at the project root:

```text
# Project scope
# Canonical truth sources
# Required setup and commands
# Stable invariants and authority
# Verification before completion
# Directory-specific instruction pointers
```

Use these workflow soft budgets:

- root target: 8 KiB;
- root review threshold: 12 KiB;
- effective project-local chain target: 16 KiB;
- Codex default project-document comparison point: 32 KiB.

The first three are workflow maintenance targets, not OpenAI hard limits. The
last is the default combined project-document budget described by OpenAI. Stay
well below it because global instructions and other discovered files may also
consume context.

Put genuinely different directory rules in a nested `AGENTS.md` close to their
scope. Use `AGENTS.override.md` only when its precedence is intentional; audit
the shadowed file so stale rules are not mistaken for active ones. Do not solve
growth by increasing the Codex limit before removing duplication and routing
dynamic detail to its canonical source.

If the active Codex configuration defines `project_doc_fallback_filenames`, pass
each configured basename to `agents-audit --fallback-name NAME` in the same
precedence order. Otherwise the helper intentionally checks only the standard
`AGENTS.override.md` and `AGENTS.md` names.

## Maintenance loop

Before changing project instructions:

1. run the normal workflow control audit;
2. run `agents-audit` for the directory where work will happen;
3. read every effective project-local instruction file reported by the audit;
4. classify proposed content as stable contract, canonical-source pointer,
   directory-local exception, dynamic research state, or stale duplication;
5. determine whether the change is mechanical, compaction, or semantic;
6. make one instruction-file content change at a time;
7. run `agents-record`, then rerun relevant repository validation.

Use replacement and compaction, not chronological appends. When adding a stable
rule, remove an obsolete rule or route displaced detail to an existing
canonical file where possible. Do not keep an AGENTS change log inside
`AGENTS.md`; Git and the bounded controller receipt provide provenance.

The controller stores hashes, sizes, reasons, and a user-readable notification,
not instruction contents. It retains only the 20 most recent update receipts
and counts compacted older receipts.

## Change classes and authority

### Mechanical

Examples: repair a verified path, update a command after a repository rename,
or correct an unambiguous typo without changing behavior. The agent may perform
and record this autonomously. Explain the consequence in plain language.

### Compaction

Examples: replace duplicated results with a pointer to L2, remove dated history
already preserved in a canonical artifact, or move a service-only rule into a
nested file. The agent may perform this autonomously only after verifying that
the surviving source exists and the effective meaning is unchanged.
`agents-record --kind compaction` requires the resulting file to be smaller.

### Semantic

Examples: change who may approve an action, alter a stable data or evaluation
protocol, add or remove a required validation, broaden project scope, or change
permission for cost or external actions. This needs user authority.

Reuse the normal question queue:

```text
layer: instructions
decision target: instructions:<project-relative-path>
```

The question counts toward the same five active PI decisions. A typed
`approve` or `select` can be consumed once by the matching instruction update.
`reject`, `defer`, and `informational` cannot authorize it. A direct user
instruction may be recorded without first manufacturing a queue question.

Do not use a semantic AGENTS update to bypass an L1 or L2 checkpoint. If the
underlying change is task, dataset, evidence standard, problem, mechanism,
innovation claim, or paper claim, update the owning checkpoint first. Usually
`AGENTS.md` should keep only the pointer and therefore needs no corresponding
semantic rewrite.

## Conflicts and stale instructions

If project instructions conflict with the user's latest message, a confirmed
checkpoint, or another effective instruction file:

1. identify the exact conflicting statements and their scopes;
2. stop only the dependent action;
3. continue unrelated authorized work when the five-question rule permits;
4. ask one scoped PI question if resolving the conflict changes meaning;
5. after resolution, update the canonical scientific state first and compact
   project instructions back to stable rules and pointers.

Do not silently declare an instruction stale because it is old or inconvenient.
Do not preserve a known conflict merely because the file has higher prompt
precedence.

## Controller commands

```powershell
python scripts/research_queue.py agents-audit STATE --cwd PROJECT_SUBDIRECTORY
python scripts/research_queue.py agents-record STATE --path AGENTS.md --kind mechanical --reason "..." --summary "..."
python scripts/research_queue.py agents-record STATE --path AGENTS.md --kind compaction --reason "..." --summary "..."
python scripts/research_queue.py question STATE --layer instructions --target instructions:AGENTS.md --text "..."
python scripts/research_queue.py answer STATE --id Q001 --decision "..." --outcome approve
python scripts/research_queue.py agents-record STATE --path AGENTS.md --kind semantic --reason "..." --summary "..." --decision-id Q001
```

For a newly created instruction file, audit its intended directory before
creation and pass `--before-absent` when recording it. The controller refuses to
record multiple changed instruction files as one receipt. It also reports an
unrecorded change through the normal control audit after an instruction snapshot
exists.

The helper does not rewrite project instructions or judge whether prose is
semantically equivalent. The agent must inspect the diff and the linked truth
sources. For a first large migration of an existing oversized file, present the
keep/move/remove map and proposed semantic changes to the user before applying
the rewrite.
