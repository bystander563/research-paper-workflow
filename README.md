# Research Paper Workflow

[![skills.sh](https://skills.sh/b/bystander563/research-paper-workflow)](https://skills.sh/b/bystander563/research-paper-workflow)

A Codex skill for paper-oriented research with the user in control of scientific
direction. It helps the agent find a meaningful problem, derive a defensible
method, compare real external baselines, and keep a useful research conversation
going across experiments and context changes.

It is not an automatic paper factory, a fixed multi-agent team, or another
experiment-tracking platform.

## The three-layer idea

| Layer | Question | Responsibility |
|---|---|---|
| L1: direction | What should we research? | Venue/time, task, datasets, evidence standard and user-selected constraints |
| L2: research reasoning | What is missing, how might we solve it, what does evidence show? | Nearest-work gap, problem path, method/innovation, comparisons, meaningful attempts and next test |
| L3: execution | How do we perform the experiment? | Code, runs, configurations, debugging and native artifacts |

These are not three sequential gates. L2 proposes tests, L3 returns evidence,
and L2 updates its understanding within L1. The user usually discusses L2 with
the agent and revisits L1 when direction changes.

L2 distinguishes confirmed selections, working hypotheses and supported
findings. A result update is neither automatic PI approval nor a reason to ask
the user to approve the same direction again.

## What it changes in daily use

- Start from venue/time and domain, then scout task-dataset pairs with meaningful headroom and nearest-work novelty.
- Find the deepest useful unresolved problem; do not keep re-justifying upstream choices the user already made.
- Let one method record grow from intuition to diagnostics, external comparison and ceiling search; avoid duplicate method tables.
- Tune promising mechanisms, not every idea. Score fusion or module stacking alone cannot stand in for core novelty.
- After dataset selection, maintain the strongest source-checked comparable external reference per dataset through every iteration and result report; internal improvements remain secondary and do not establish competitiveness.
- Answer progress questions with scientific changes/results, answer "why" with the relevant mechanism, and discuss corrections naturally.
- Keep engineering details internal by default, but explain them when explicitly asked.
- Preserve actual user choices while acting autonomously within the approved scope.

The project retains a configured numeric paper-decision floor over the strongest
recent top-conference protocol-matched baseline, plus its adopted evidence
requirements. The precise rule is in [workflow G3](references/workflow.md#g3-paper-decision-ready).
Before writing, the agent prepares a report covering task, data, nearest-work
problem, innovation, method, comparisons/results and remaining uncertainty;
the user decides whether to proceed.

## Install and use

```bash
npx skills add https://github.com/bystander563/research-paper-workflow --skill research-paper-workflow -g -a codex -y
```

Or ask Codex:

```text
$skill-installer install https://github.com/bystander563/research-paper-workflow
```

Start a new task/run after installation to load the updated instructions.

```text
用 $research-paper-workflow 继续这个论文项目。先理解我们已确定的任务和数据集，
围绕当前近邻工作的缺陷探索方法；需要我决定的宏观问题再问我。
```

Ordinary conversation does not require controller vocabulary:

```text
从上次让你跑开始，试过哪些问题和方法？当前结果与外部 baseline 差多少？
为什么你觉得这个机制能解决问题？
我怀疑问题不在这里，先讨论一下这个解释。
```

## Small durable state

```text
<project>/.codex/research/L1-directions.md
<project>/.codex/research/L2/<direction-id>.md
<project>/.codex/research-paper-workflow.json
```

Use existing project tools for L3; an extra L3 index is optional.
Keep decision-relevant L1/L2 evidence, not an archive of all failed runs.

Schema v16 adds a preferred `research-update` operation: write one keyed
research note, update its progress projection, and optionally record a
notification. The comparison roster remains the numeric source. A new reporting
boundary resets deltas while retaining scope-valid current focus as context.
Evidence updates preserve scientific selections; paper reports lock the
evidence versions on which the requested approval depends.

Partial research updates preserve scoped hypotheses and starting/best results
across reporting windows, and refresh the current focus automatically. Invalid
optional fields can be explicitly cleared. External references in update/status
views come from the baseline roster, not a hand-maintained narrative score.

Legacy `window-note` and `--simple-combination-counterfactual` remain compatible.
Prefer `research-update` and `--alternative-explanation` for new work.
Existing v15 selections do not need approval again; older paper packets need
a current evidence-bound report before a new paper decision.

## Optional support, not mandatory ceremony

Unanswered genuine decisions are batched after twenty minutes; silence never
grants authority. At five active decisions, stop new work safely. Deferred items
remain visible with revisit conditions. Direct pause/resume is separate.

When unattended monitoring is requested, use the host scheduler if available,
check state/results before full analysis, and stop future checks when needed.
Without a scheduler or available host, recovery is resume-on-open only.
The controller records state; it does not itself run experiments or kill jobs.

AGENTS.md contains stable execution rules and source pointers, not research
history. Its maintenance procedures are loaded only when relevant.
No universal sealed-set, external-label, aggregation, seed-count or significance
protocol is imposed. Unexposed-dataset scouting is required during L1 exploration;
adoption and second-dataset requirements belong to the user.

## Files and validation

- [SKILL.md](SKILL.md): short entry point and conditional routing.
- [workflow.md](references/workflow.md): phases, authority gates and paper floor.
- [exploration-policy.md](references/exploration-policy.md): scientific reasoning.
- [collaboration-policy.md](references/collaboration-policy.md): natural interaction, decisions and monitoring.
- [research-state.md](references/research-state.md): records, sources, CLI and migration.
- [agents-maintenance.md](references/agents-maintenance.md): conditional instruction maintenance.
- [research_queue.py](scripts/research_queue.py): deterministic state/authority checks and generated views, not a novelty judge.

```powershell
python -B -X utf8 -m unittest discover -s tests -p "test_*.py"
python scripts/research_queue.py --help
```

Tests check controller behavior, not whether an idea is publishable. Scientific
adequacy still depends on source verification, experiments and user judgment.
