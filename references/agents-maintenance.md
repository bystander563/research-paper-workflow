# Conditional project-instruction maintenance

Use this reference only when creating, changing, compacting or resolving a
conflict in AGENTS.md / AGENTS.override.md. Routine research progress does not
require updating these files or loading this maintenance procedure.

## What belongs here

AGENTS.md is a stable execution contract and router, not another research layer.
Keep only:

- a brief repository scope;
- canonical source paths and when to read them;
- stable setup/run/test commands;
- durable authority, safety, data/protocol invariants;
- completion checks not already reliably enforced by tooling;
- pointers to genuinely distinct directory-local rules.

Do not copy current hypotheses, datasets under consideration, results,
literature, experiment history, jobs, question queues or dated progress.
Their source is L1/L2 or native execution tools. If no stable project-specific
rule/router is needed, do not create AGENTS.md just because this Skill is active.

## Maintain meaning, not an append-only log

Prefer replacement and compaction. Remove duplicate statements or replace
dynamic content with a source pointer; do not append a new rule after every bug.
A root target of 8 KiB, review point of 12 KiB and effective project-local target
of 16 KiB are soft maintenance heuristics, not runtime permissions or research
gates. The official default project-document budget is a comparison point,
not a size to fill. [Official AGENTS.md guide](https://learn.chatgpt.com/docs/agent-configuration/agents-md)

Scientific choices stay in their owning checkpoint. An instruction edit that
merely reflects an already authorized choice must not manufacture another
scientific decision. A genuine change of authority, project scope, permission,
protocol or required validation still needs scoped user authority.

## When action is necessary

1. Read the effective project-local instructions for the actual working scope.
2. Inspect the intended diff and distinguish mechanical repair, meaning-preserving compaction and semantic change.
3. Use the existing controller audit/receipt support for that scope; do not bootstrap unrelated directory scopes.
4. Apply the authorized edit, record it and perform the relevant validation.

Mechanical fixes are autonomous. Compaction is autonomous after checking that
the surviving canonical source exists and meaning is preserved. Semantic
changes require an actual scoped instruction or decision, using the same PI
queue rather than a second approval system. The user need not approve internal
classification or see file-maintenance jargon.

If rules conflict, stop only the dependent action, identify the conflicting
meaning and resolve it with the current instruction/owning decision. Do not
silently discard a rule merely because it is old or inconvenient.
For a first large migration of an oversized file, show the keep/move/remove
meaning and obtain any needed semantic decisions before rewriting.

Project instructions are discovered once per Codex run. A file edit does not
reload the active prompt. Follow the already loaded chain for this run; rely on
the user's current instruction when a permitted change matters immediately,
and treat the saved file as guidance for the next run.

## Compatible controller support

```powershell
python <controller> agents-audit STATE --cwd PROJECT_SUBDIRECTORY
python <controller> agents-record STATE --path AGENTS.md --kind mechanical --reason "..." --summary "..."
python <controller> agents-record STATE --path AGENTS.md --kind compaction --reason "..." --summary "..." --canonical-source PATH
python <controller> agents-record STATE --path AGENTS.md --kind semantic --reason "..." --summary "..." --decision-id Q001
```

An existing scope audit is compare-only: rerunning it does not accept an
unrecorded change. Record one instruction-file content change at a time;
creation uses `--before-absent`, deletion `--after-absent`. The controller keeps
bounded receipts, not contents or a change log inside AGENTS.md.
Compaction verifies smaller size and resolvable source paths; the agent verifies
semantic equivalence. Direct explicit instructions can be recorded without
first queuing a question.

If Codex uses configured fallback filenames, pass them in precedence order with
`--fallback-name`. Empty files are ignored for effective guidance. Existing
advanced per-directory snapshots and scope-removal commands remain available
for compatibility, not required daily work. A retired missing directory can be
pruned autonomously; removing audit coverage for an existing scope retains its
scoped approval requirement. Never use maintenance to silently remove protections.

Pause applies to maintenance too: do not mutate or add audit scopes while
execution is paused. Read-only inspection remains available. The helper cannot
judge scientific adequacy or rewrite instructions by itself.
