# Research Paper Workflow

[![skills.sh](https://skills.sh/b/bystander563/research-paper-workflow)](https://skills.sh/b/bystander563/research-paper-workflow)

A Codex skill for autonomous, PI-in-the-loop paper research: scout meaningful task–dataset pairs, compare against real external methods, derive problem-driven methods, tune promising candidates toward their current-project ceiling, and preserve scientific decisions across long experiment cycles.

The skill keeps scientific ownership with the user. It distinguishes ordinary autonomous work from the small set of decisions that genuinely require PI approval.

## Core behavior

- starts exploration from a user-confirmed venue or timeline, domain, and optional idea;
- evaluates task meaning, task–dataset fit, benchmark headroom, nearest-work novelty, observed failure, intuition, and mathematical fit;
- keeps three linked layers: durable L1 task/dataset direction, durable L2 scientific story/evidence, and agent-managed L3 code/execution;
- requires the user to confirm the L1 direction and project evidence standard, then later promote the L2 problem, core mechanism, and innovation claim;
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
- protects frozen choices from silent replacement and preserves material L1/L2 decision history;
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

The JSON helper tracks PI questions, confirmed L1/L2 checkpoints, notifications, pause state, and frozen-field history. L1 and L2 retain the scientific state and user decisions. L3 may point to native experiment tracking, be compacted, or be omitted when it adds no value; active L2 claims must still identify adequate supporting evidence.

Existing projects may retain `.codex/research-ledger.md` as read-only history and create the layered files at the next material checkpoint.

## Architecture

- `SKILL.md` is the entry point, authority boundary, and shortest end-to-end flow.
- `references/workflow.md` is the canonical phase and gate specification.
- `references/exploration-policy.md` defines task–dataset, literature, baseline, method, and ceiling-search judgment.
- `references/collaboration-policy.md` defines notifications, PI questions, the 20-minute batch rule, and the five-question pause.
- `references/research-state.md` defines the L1/L2 durable record and discretionary L3 layer.
- `scripts/research_queue.py` records PI questions, confirmations, and pause state; it does not grant authority or run experiments.

The content layers and execution phases are intentionally separate: L1/L2/L3 say what information exists, while `exploration`, `confirmed_project`, and `paper_ready_pending_pi` say when the workflow is operating.

## Queue helper

```powershell
python scripts/research_queue.py init STATE --project NAME --phase exploration
python scripts/research_queue.py question STATE --layer direction --priority high --text "..." --reason "..." --recommendation "..." --continue-plan "..."
python scripts/research_queue.py answer STATE --id Q001 --decision "..."
python scripts/research_queue.py confirm STATE --layer direction --id D001 --summary "task=...; dataset=..." --decision-id Q001
python scripts/research_queue.py confirm STATE --layer science --id S001 --summary "problem=...; mechanism=...; claim=..." --pi-decision "把这个作为主线"
python scripts/research_queue.py freeze STATE --key dataset --value "..." --pi-decision "用户确认这个数据集"
python scripts/research_queue.py status STATE
```

## Validation

```powershell
python -X utf8 path\to\quick_validate.py .
python -X utf8 scripts\research_queue.py --help
```
