# Research Paper Workflow

[![skills.sh](https://skills.sh/b/bystander563/research-paper-workflow)](https://skills.sh/b/bystander563/research-paper-workflow)

A Codex skill for autonomous, PI-in-the-loop paper research: scout meaningful task–dataset pairs, compare against real external methods, derive problem-driven methods, tune promising candidates toward their current-project ceiling, and preserve scientific decisions across long experiment cycles.

The skill keeps scientific ownership with the user. It distinguishes ordinary autonomous work from the small set of decisions that genuinely require PI approval.

## Core behavior

- starts exploration from a user-confirmed venue or timeline, domain, and optional idea;
- evaluates task meaning, task–dataset fit, benchmark headroom, nearest-work novelty, observed failure, intuition, and mathematical fit;
- keeps three linked layers: durable L1 task/dataset direction, durable L2 scientific story/evidence, and agent-managed L3 code/execution;
- requires the user to confirm the L1 direction and project evidence standard, then later promote the L2 problem, core mechanism, and innovation claim;
- binds each queued approval to one decision target and consumes it once, so a generic queued answer cannot pass unrelated gates;
- keeps informational replies active, while deferred decisions move to a visible queue with a required revisit condition and do not count toward the five-question pause;
- requires a dataset-origin reference, a recent strong comparable method, another published mechanism, and a strong simple baseline before paper-level claims;
- separates external baselines, the proposed method, and internal variants instead of treating “ours versus ours” as competitiveness evidence;
- avoids engineering-heavy module stacks without a coherent mechanism;
- uses existing GPU compute by default and never rents paid compute without approval;
- tunes only candidates with credible potential and reports their observed ceiling plainly;
- does not require an archive of every attempt, failed trial, tuning trace, or stopping rule;
- keeps L1/L2 scientific state and decisions durably while letting the agent decide how much L3 detail remains useful;
- does not require a second, new, or previously unexposed dataset unless the user or project adopts that evidence standard;
- continues independent work while PI questions are unanswered;
- pauses when five genuine PI decisions are pending;
- rejects phase advancement and new active-job registration while paused;
- keeps compass/L1/L2/paper fields as single sources of truth, protects additional frozen choices from silent replacement, and preserves material L1/L2 decision history;
- audits legacy state instead of silently treating older unstructured approvals as complete;
- hands a user-approved research package to a separate submission workflow instead of mixing exploration with drafting and review.

The skill intentionally does not impose universal test-set, sealed-set, external-label, metric, validation, second-dataset, or unexposed-dataset protocols. Those remain project-specific.

## Install

```bash
npx skills add https://github.com/bystander563/research-paper-workflow --skill research-paper-workflow -g -a codex -y
```

Alternatively, ask Codex:

```text
$skill-installer install https://github.com/bystander563/research-paper-workflow
```

Restart Codex after installation, then invoke it with:

```text
Use $research-paper-workflow to scout or continue this paper project.
```

Chinese example:

```text
用 $research-paper-workflow 探索或继续这个论文项目。需要我拍板的问题最多积累五个，其余授权范围内继续推进。
```

## Durable project state

For long-running work, the skill can maintain:

```text
<project>/.codex/research-paper-workflow.json
<project>/.codex/research/L1-directions.md
<project>/.codex/research/L2/D001.md
<project>/.codex/research/L3/D001.md  # optional agent/project-managed index
```

The schema-v5 controller tracks scoped PI decisions, active and deferred question queues, research-compass/L1/L2/paper checkpoints, legal phases, structured paper-ready assessment, recent notifications, resumable active jobs, pause state, and additional frozen-field history. `init` creates the L1/L2 scaffold, and each confirmation appends a structured decision receipt to its durable record. L2 confirmation also records resolvable nearest-work, external-baseline, and result references. L1 and L2 retain the scientific state and user decisions. L3 may point to native experiment tracking, be compacted, or be omitted when it adds no value; active L2 claims must still identify adequate supporting evidence.

Existing projects may retain `.codex/research-ledger.md` as read-only history and create the layered files at the next material checkpoint.

## Architecture

- `SKILL.md` is the entry point, authority boundary, and shortest end-to-end flow.
- `references/workflow.md` is the canonical phase and gate specification.
- `references/exploration-policy.md` defines task–dataset, literature, baseline, method, and ceiling-search judgment.
- `references/collaboration-policy.md` defines notifications, PI questions, the 20-minute batch rule, and the five-question pause.
- `references/research-state.md` defines the L1/L2 durable record and discretionary L3 layer.
- `scripts/research_queue.py` initializes and control-audits state, enforces scoped typed checkpoints and legal transitions, and records resumable active jobs; it checks provenance and artifact availability, not scientific adequacy, and it does not grant authority, wake itself, or run experiments.

The content layers and execution phases are intentionally separate: L1/L2/L3 say what information exists, while `discussion`, `exploration`, `confirmed_project`, `paper_ready_pending_pi`, and `paper_handoff_approved` say when the workflow is operating.

## Queue helper

```powershell
python scripts/research_queue.py init STATE --project NAME
python scripts/research_queue.py init STATE --project NAME --phase exploration --venue-or-window "ICASSP" --domain "sMRI" --pi-decision "用户确认投稿目标和领域" --pi-outcome select
python scripts/research_queue.py audit STATE
python scripts/research_queue.py question STATE --layer direction --target direction:D001 --priority high --text "..." --reason "..." --recommendation "..." --continue-plan "..."
python scripts/research_queue.py answer STATE --id Q001 --decision "..." --outcome select
python scripts/research_queue.py answer STATE --id Q002 --decision "稍后决定" --outcome defer --revisit-condition "外部 baseline 复现完成"
python scripts/research_queue.py reopen STATE --id Q002 --reason "外部 baseline 复现已完成"
python scripts/research_queue.py confirm STATE --layer direction --id D001 --record L1_FILE --decision-id Q001 --task-type "..." --dataset "..." --competitive-bar "..." --novelty-sufficiency "..." --generalization-requirement "..." --paper-ready-threshold "..."
python scripts/research_queue.py confirm STATE --layer science --id S001 --record L2_FILE --pi-decision "把这个作为主线" --pi-outcome approve --direction-id D001 --problem "..." --core-mechanism "..." --innovation-claim "..." --external-baseline-status "..." --ceiling-summary "..." --nearest-work-record L2_FILE --baseline-record L2_FILE --result-record L2_FILE
python scripts/research_queue.py phase STATE --set paper_ready_pending_pi --assessment ASSESSMENT_FILE --competitive-bar-assessment "..." --novelty-assessment "..." --generalization-assessment "..." --paper-ready-threshold-assessment "..." --narrowest-supported-claim "..." --strongest-matched-comparison "..." --remaining-objection "..." --necessary-work "..." --optional-work "..."
python scripts/research_queue.py confirm STATE --layer paper --id P001 --record ASSESSMENT_FILE --decision-id Q003 --science-id S001 --headline-claim "..." --handoff-target "paper-submission-orchestrator"
python scripts/research_queue.py job-add STATE --id J001 --description "..." --command "..." --status running --next-action "..."
python scripts/research_queue.py status STATE
```

The controller cannot keep a Codex task alive by itself. Use the host task or automation mechanism for unattended wakeups; the job registry makes the work recoverable when a task resumes.

## Validation

```powershell
python -X utf8 path\to\quick_validate.py .
python -X utf8 scripts\research_queue.py --help
python -X utf8 -m unittest discover -s tests -v
```
