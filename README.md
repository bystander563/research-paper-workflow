# Research Paper Workflow

[![skills.sh](https://skills.sh/b/bystander563/research-paper-workflow)](https://skills.sh/b/bystander563/research-paper-workflow)

A Codex skill for autonomous, PI-in-the-loop paper research: scout meaningful task–dataset pairs, compare against real external methods, derive problem-driven methods, tune promising candidates toward their current-project ceiling, and preserve scientific decisions across long experiment cycles.

The skill keeps scientific ownership with the user. It distinguishes ordinary autonomous work from the small set of decisions that genuinely require PI approval.

## Core behavior

- starts exploration from a user-confirmed venue or timeline, domain, and optional idea;
- evaluates task meaning, task–dataset fit, benchmark headroom, nearest-work novelty, observed failure, intuition, and mathematical fit;
- keeps three linked layers: durable L1 task/adopted-dataset direction, durable
  L2 unresolved problem path/active leaf/leaf-linked method clusters/evidence, and
  agent-managed L3 engineering and execution;
- requires the user to confirm the L1 direction and project evidence standard,
  then later promote the L2 problem path, active leaf, method cluster, core mechanism, and
  innovation claim;
- binds each queued approval to one decision target, supersedes it when a newer decision for that target exists, and consumes it once;
- keeps informational replies active, while deferred decisions move to a visible queue with a required revisit condition and do not count toward the five-question pause;
- requires a dataset-origin reference, a recent top-conference comparable method, another published mechanism, and a strong simple baseline before paper-level claims;
- maintains one dataset-specific recent top-conference external-baseline row for every adopted dataset, explicitly tracks protocol-match status, and records dataset-origin, different-mechanism, and strong-simple comparison coverage or blockers;
- requires that roster before the evaluation anchor and reads its current
  revision at the paper gate, so a missing dataset or stale comparator cannot be
  supplied only at the end;
- separates external baselines, the proposed method, and internal variants instead of treating “ours versus ours” as competitiveness evidence;
- locks the problem path, active leaf, method cluster, falsifiable prediction, primary metric, scale, and direction before broad tuning, while allowing an agent-owned replacement to invalidate older paper-gate evidence prospectively;
- permits a paper-decision question only after the canonical [workflow G3](references/workflow.md) matched-baseline gain floor passes, includes project-appropriate stability evidence, and then generates a complete decision report before asking the user;
- admits only paper-grade active leaves and falsifiable scientific
  contributions; ordinary weighted fusion, heuristic ensembles, module stacks,
  runtime issues, and routine bugs stay in L3 or baselines unless the actual
  contribution is a distinct estimand/objective/constraint/mechanism/theory;
- notifies the user whenever the active problem path, leaf, or method cluster
  changes, and still requires PI approval to replace confirmed L2 science;
- uses existing GPU compute by default and never rents paid compute without approval;
- tunes only candidates with credible potential and reports their observed ceiling plainly;
- does not require an archive of every attempt, failed trial, tuning trace, or stopping rule;
- keeps L1/L2 scientific state and decisions durably while letting the agent decide how much L3 detail remains useful;
- gives the user a macro-only supervision surface: progress reports and
  discussions cover L1/L2 task, dataset, problem path/active leaf, method cluster, external
  comparison, representative result, current focus, and decisions; L3 jobs,
  commands, sessions, bugs, and tuning remain internal;
- keeps one replace-on-next-instruction current research window with keyed
  L1/L2 summary cards, so “what changed since I told you to run?” survives
  context compaction without becoming a full attempt archive;
- always searches for a credible dataset not previously exposed in the project, while leaving its adoption as a second-dataset or generalization requirement to the user;
- continues independent work while PI questions are unanswered;
- answers in-progress “what are you doing?” questions with a read-only compass→L1→L2→prediction drift trace instead of treating discussion as approval;
- pauses when five genuine PI decisions are pending;
- supports a separate direct PI pause/resume and a revocable paper-writing authorization without erasing L1/L2;
- rejects phase advancement, new instruction-maintenance mutations, new active jobs, and continued polling or advancement of existing jobs while paused; only safe terminal job updates remain allowed;
- content-locks both the paper-ready report file and its structured payload, requires the paper question to be created and answered after that report, and binds the approval to the current report receipt;
- keeps compass/L1/L2/paper fields as single sources of truth, protects additional frozen choices from silent replacement, and preserves material L1/L2 decision history;
- keeps `AGENTS.md` as a bounded stable contract and router, retains separate compare-only snapshots for audited scopes, and records instruction changes without copying dynamic research state into it;
- treats an edited `AGENTS.md` as next-run guidance because Codex loads the instruction chain once per run;
- routes semantic instruction changes through the same scoped five-question PI queue while treating verified path repairs and meaning-preserving compaction as notifications;
- audits legacy state instead of silently treating older unstructured approvals as complete;
- hands a user-approved research package to a separate submission workflow instead of mixing exploration with drafting and review.

The skill intentionally does not impose universal test-set, sealed-set,
external-label, aggregation, seed-count, significance-test, validation, or
second-dataset protocols. It does impose the paper-decision gain floor above
once a higher-is-better primary metric and matched protocol are selected. It
also requires an unexposed-dataset search during L1 scouting; the user decides
whether any candidate becomes part of the evidence standard.

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
<project>/.codex/research-paper-workflow.json.lock  # controller mutex; no research content
<project>/.codex/research/L1-directions.md
<project>/.codex/research/L2/D001.md
<project>/.codex/research/L3/D001.md  # optional agent/project-managed index
```

The schema-v15 controller tracks versioned PI decision targets, an explicit L1
adopted-dataset inventory, a revisioned per-dataset baseline roster with typed
protocol and comparison-role coverage, paper-grade
problem paths, active leaf and method-cluster IDs, active and deferred question queues,
research-compass/L1/L2/paper checkpoints, the evaluation anchor, legal phases,
structured paper-ready assessment and gain arithmetic, bounded invalidated-paper
receipts, recent typed notifications, resumable active jobs, per-job monitor
acknowledgements, pause state, frozen-field history, and bounded multi-scope
project-instruction receipts, and one non-authoritative current research window
whose L1/L2 cards are updated by stable identity. It serializes mutating commands with an adjacent
lock so scheduled and interactive tasks cannot silently overwrite state. `init`
creates the L1/L2 scaffold; confirmations refresh marked current-state blocks and
append receipts. The paper gate reads the current roster and anchor, requires
every adopted dataset to be matched, then generates and content-locks a readable
decision report before the user's paper decision. Checkpoint and assessment
records are project-local; external evidence references are read-only. L1/L2
retain selective science and user decisions; L3 owns engineering detail and may
use native experiment tracking, be compacted, or be omitted. `status --window`
omits all L3 detail and reports only the current macro research delta.

Existing projects may retain `.codex/research-ledger.md` as read-only history and create the layered files at the next material checkpoint.

## Architecture

- `SKILL.md` is the entry point, authority boundary, and shortest end-to-end flow.
- `references/workflow.md` is the canonical phase and gate specification.
- `references/exploration-policy.md` defines task–dataset, literature, baseline, method, and ceiling-search judgment.
- `references/collaboration-policy.md` defines the macro-only user supervision surface, research-window report, notifications, PI questions, state-aware unattended monitoring, the 20-minute batch rule, and the five-question pause.
- `references/research-state.md` defines the L1/L2 durable record, non-authoritative research window, and discretionary internal L3 layer.
- `references/agents-maintenance.md` defines bounded `AGENTS.md` content, precedence-aware audits, change classes, and how instruction decisions reuse the existing queue.
- `scripts/research_queue.py` initializes and control-audits state, enforces scoped typed checkpoints and legal transitions, records resumable active jobs, and audits/records project-instruction maintenance; it checks provenance and artifact availability, not scientific or semantic adequacy, and it does not grant authority, rewrite instructions, wake itself, or run experiments.

The content layers and execution phases are intentionally separate: L1/L2/L3 say what information exists, while `discussion`, `exploration`, `confirmed_project`, `paper_ready_pending_pi`, and `paper_handoff_approved` say when the workflow is operating.

## Queue helper

The commands below assume the repository root. When the skill is installed and
the active working directory is a research project, resolve the controller as
`scripts/research_queue.py` relative to the installed `SKILL.md`.

```powershell
python scripts/research_queue.py init STATE --project NAME
python scripts/research_queue.py init STATE --project NAME --phase exploration --venue-or-window "ICASSP" --domain "sMRI" --pi-decision "用户确认投稿目标和领域" --pi-outcome select
python scripts/research_queue.py audit STATE
python scripts/research_queue.py status STATE --window
python scripts/research_queue.py window-start STATE --instruction "用户明确要求继续跑当前研究方向"
python scripts/research_queue.py window-note STATE --layer L2 --kind method_cluster --subject-id M002 --title "..." --status PROMISING --verified-observation "..." --interpretation "..." --external-baseline-gap "..." --next-action "..." --starting-result "..." --best-result "..." --latest-result "..." --set-current --hypothesis "..." --current-action "..." --focus-latest-result "..."
python scripts/research_queue.py pause STATE --pi-decision "先暂停" --reason "..."
python scripts/research_queue.py resume STATE --pi-decision "继续"
python scripts/research_queue.py agents-audit STATE --cwd PROJECT_SUBDIRECTORY
python scripts/research_queue.py agents-scope-remove STATE --cwd RETIRED_DIRECTORY --reason "Directory was removed" --summary "清理已经不存在目录的说明审计范围。"
python scripts/research_queue.py agents-record STATE --path AGENTS.md --kind compaction --reason "Moved dynamic detail to L1/L2" --summary "删去项目说明中的动态研究记录，只保留稳定规则和来源链接。" --canonical-source .codex/research/L2/D001.md
python scripts/research_queue.py question STATE --layer direction --target direction:D001 --priority high --text "..." --reason "..." --recommendation "..." --continue-plan "..."
python scripts/research_queue.py answer STATE --id Q001 --decision "..." --outcome select
python scripts/research_queue.py answer STATE --id Q002 --decision "稍后决定" --outcome defer --revisit-condition "外部 baseline 复现完成"
python scripts/research_queue.py reopen STATE --id Q002 --reason "外部 baseline 复现已完成"
python scripts/research_queue.py confirm STATE --layer direction --id D001 --record L1_FILE --decision-id Q001 --task-type "..." --dataset "..." --primary-dataset "..." --supporting-dataset "..." --unexposed-dataset-search "..." --competitive-bar "..." --novelty-sufficiency "..." --generalization-requirement "..." --paper-ready-threshold "..." --minimum-paper-gain-points 1
python scripts/research_queue.py baseline-roster STATE --rows-file BASELINE_ROSTER.json --record L2_FILE --reason "source-checked every adopted dataset"
python scripts/research_queue.py evaluation-anchor STATE --problem-path PARENT_ID --problem-path ACTIVE_LEAF_ID --problem-id ACTIVE_LEAF_ID --method-cluster-id CLUSTER_ID --falsifiable-prediction "..." --primary-metric "..." --metric-scale unit_interval --metric-direction higher_is_better --reason "..."
python scripts/research_queue.py notify STATE --kind method_cluster_switch --from-id M001 --to-id M002 --text "原方法簇缺少潜力，切换到另一条可证伪机制；L1 不变。"
python scripts/research_queue.py confirm STATE --layer science --id S001 --record L2_FILE --pi-decision "把这个作为主线" --pi-outcome approve --direction-id D001 --problem-path PARENT_ID --problem-path ACTIVE_LEAF_ID --problem-id ACTIVE_LEAF_ID --method-cluster-id CLUSTER_ID --problem "..." --nearest-work-gap "..." --paper-grade-rationale "..." --core-mechanism "..." --falsifiable-prediction "..." --simple-combination-counterfactual "普通加权融合为什么不能解决该叶子问题" --contribution-type mechanism --innovation-claim "..." --external-baseline-status "..." --ceiling-summary "..." --problem-portfolio-record L2_FILE --nearest-work-record L2_FILE --baseline-record L2_FILE --result-record L2_FILE
python scripts/research_queue.py phase STATE --set paper_ready_pending_pi --assessment ASSESSMENT_FILE --competitive-bar-assessment "..." --novelty-assessment "..." --generalization-assessment "..." --paper-ready-threshold-assessment "..." --narrowest-supported-claim "..." --strongest-matched-comparison "..." --remaining-objection "..." --necessary-work "..." --optional-work "..." --specific-method "..." --final-results "..." --primary-comparison-dataset "..." --recent-top-conference-baseline "..." --baseline-venue-year "..." --baseline-search-scope "<venues> <year-range>; searched <YYYY-MM-DD>" --baseline-source "..." --protocol-match-evidence "..." --evaluation-anchor-evidence "..." --stability-evidence "..." --primary-metric "..." --metric-scale unit_interval --baseline-score 0.80 --our-score 0.81
python scripts/research_queue.py confirm STATE --layer paper --id P001 --record ASSESSMENT_FILE --decision-id Q003 --science-id S001 --headline-claim "..." --handoff-target "paper-submission-orchestrator"
python scripts/research_queue.py paper-revoke STATE --pi-decision "撤销本次写作授权" --reason "..."
python scripts/research_queue.py job-add STATE --id J001 --description "..." --command "..." --status running --next-poll "..." --next-action "..."
python scripts/research_queue.py status STATE --compact
python scripts/research_queue.py monitor-ack STATE --wakeup-fingerprint CURRENT --job-id J001 --artifact-fingerprint CURRENT_ARTIFACT
python scripts/research_queue.py status STATE
```

The controller cannot keep a Codex task alive by itself. When unattended
monitoring is explicitly requested, use the host scheduled-task mechanism as a
compact state-aware wakeup at the next meaningful time. Read `status --compact`
and use `wakeup_changed_since_ack` plus each job's saved artifact fingerprint before the full research state;
rescheduling alone does not change that fingerprint, while a pending question
crossing the 20-minute batching boundary changes it once. After successfully
processing a change, persist it with `monitor-ack`. Stop future wakeups at
workflow stop conditions. If scheduling is unavailable, the job registry makes
the work recoverable when a task resumes.

## Validation

```powershell
python -X utf8 path\to\quick_validate.py .
python -X utf8 scripts\research_queue.py --help
python -X utf8 -m unittest discover -s tests -v
```
