# Exploration policy

Read this reference when scouting a paper direction, selecting a task and dataset, or turning an observed failure into a method.

## Start from the PI brief

Before open-ended exploration, establish:

1. a target submission window and/or conference;
2. the research domain;
3. an optional starting concept from the user.

The first two belong only to the typed research-compass checkpoint; do not also
copy them into `frozen_by_pi`. A starting concept is inspiration, not a novelty
claim and not automatically frozen. If the user says the concept itself must
remain central, record that as a distinct project-specific concept constraint
rather than creating a second copy of the compass field.

When updating only the venue/window or domain, carry the current optional
starting concept forward. Clear it only with the user's explicit instruction;
the controller exposes `--clear-starting-concept` for that distinction.
Changing or clearing only this optional seed leaves an already confirmed L1/L2
contract intact; it is inspiration, not a hidden direction replacement.

Verify current venue timing and scope before spending heavily, because conference dates and calls change. Do not silently redirect the work to a different venue or domain merely because another benchmark is easier.

## Keep one research compass

All later task, dataset, baseline, method, and experiment decisions should answer one or more of these research-compass checks. These are scientific judgment axes, not PI decision questions and never count toward the five-question pause:

1. **Venue and timing:** Can the project reach the required evidence level in the available time, and does the contribution fit the target venue?
2. **Meaningful task:** Does the task expose a real scientific or practical failure rather than create a benchmark trick?
3. **Task-data correspondence:** Do the data, labels, sample unit, and evaluation setup actually measure the proposed task?
4. **Benchmark headroom:** Is the dataset still capable of distinguishing better ideas, or have comparable methods already saturated it?
5. **Nearest-work novelty:** Has the same problem, information pattern, or mechanism already been solved under another name?
6. **Observed problem:** What concrete failure, contradiction, or missing capability motivates a new method?
7. **Solution intuition:** In plain language, why should the proposed change repair that failure?
8. **Mathematical fit:** Does the mathematical object encode that intuition without introducing unrelated machinery?

When making a material pivot, state which compass item triggered it, what evidence changed, and what remains fixed.

## Explore tasks and datasets as a pair

Do not choose a task and then attach any convenient dataset, or choose a dataset and invent a loosely related task. Evaluate the pair together.

A task is promising when:

- its failure matters to a real use case or scientific claim;
- success and failure can be measured;
- the task is not already solved by a simple protocol-matched baseline;
- improving it would add knowledge, capability, reliability, efficiency, or another defensible contribution.

A dataset is promising for that task when:

- its inputs and labels directly support the task;
- its prediction unit matches the claimed output unit;
- its standard or defensible split tests the intended behavior;
- the necessary metadata and baselines are usable;
- it has enough difficulty and variation to expose the target problem.

Reject or narrow a task when the dataset supplies only a proxy label that cannot support the claim.

Always search for at least one credible dataset that has not previously been
used or exposed in the project, and report the candidate, task fit, access,
labels, likely protocol comparability, and cost. If none is credible, report the
search boundary and blocker. The search is mandatory; using the candidate as a
second dataset, generalization test, or paper requirement is an L1 decision.
Do not invent a universal sealed-set, external-label, or evaluation protocol.

Keep a small ranked L1 shortlist rather than silently choosing one pair. Once
meaning, fit, headroom, nearest-work risk, external-baseline feasibility, and
cost are known well enough to compare the candidates, ask the user to select
the active task-dataset direction and project evidence standard. The standard
covers the competitive target, novelty sufficiency, generalization or
second-dataset expectation, and any additional project-specific paper-ready
requirements. Those requirements may tighten but never lower the canonical
numeric paper floor. Cheap inspection and feasibility work may precede this
choice; sustained method search and broad tuning may not.

## Prefer useful headroom over saturated benchmarks

Prefer datasets where strong comparable methods still leave meaningful room for improvement. Scores above roughly 90 on percentage-like primary metrics are a warning sign when most recent methods cluster there, but `90` is not a universal cutoff: metric scale, uncertainty, subgroup failures, calibration, and task difficulty matter.

Do not select a dataset merely because its scores are low. Low numbers caused by noisy labels, broken evaluation, tiny samples, or an impossible task are not useful headroom. Look for a dataset that is challenging for a diagnosable reason connected to the proposed task.

For each serious candidate, summarize:

- the strongest protocol-comparable recent result;
- how tightly recent methods cluster;
- whether remaining errors are systematic and relevant;
- whether the dataset can separate the proposed mechanism from a stronger baseline;
- the cost and time needed for a meaningful first result.

## Audit nearest work before claiming novelty

Search current primary literature and compare the closest methods by:

- exact task and prediction unit;
- dataset and split;
- training supervision and information available at inference;
- mathematical objective or mechanism;
- strongest baselines and native metrics;
- reported failure or limitation.

For every serious nearest-work claim, record the exact paper title, year or venue, stable URL or DOI, search date, and the evidence supporting the comparison. Mark whether each fact was verified from the primary source or inferred. Do not accept model memory, a search snippet, or a title-level resemblance as enough evidence for a novelty decision.

Novelty is not “this exact module combination was not found.” Require a meaningful gap: an unsolved problem, a different estimand, a new mechanism, a new guarantee, or a new empirical finding that changes what is known.

Actively search for alternative names for the same idea. If the nearest work already implements the same mechanism under different terminology, reject the novelty claim or redefine the problem honestly.

Use established field terms from primary literature, benchmark definitions, or other authoritative sources. Do not turn an internal nickname into a scientific concept or carry a novelty claim by renaming a known failure or mechanism. A provisional method name is acceptable only when the underlying difference is already substantive.

Cluster nearest work by the scientific problem it tries to solve, not only by
paper title or model family. For each cluster, state the shared limitation that
remains after its strongest methods. That unresolved limitation is the input to
problem selection; “nobody combined these modules” is not a problem.

## Establish external comparisons before multiplying methods

Nearest work and experimental baselines overlap but are not identical. A paper may be crucial for novelty even when it cannot be run, while a simple baseline may be essential experimentally without being the nearest conceptual work. Record both roles.

Before calling a method promising or giving it a broad tuning budget, identify and source-check a baseline roster from primary sources. Local reproduction of every item need not already be complete. The roster must include each applicable role below; when a role genuinely does not exist or cannot be used, record the blocker and the weaker claim that remains:

- the dataset paper's official reference result or method when available;
- the strongest recent protocol-comparable published method found for the task and dataset;
- at least one published method with a different mechanism;
- a strong simple baseline;
- internal variants and ablations in a separate category.

Index the competitive comparison by adopted dataset. For each primary or
generalization dataset, maintain the strongest recent top-conference
protocol-match found for that dataset, its venue/year/source/search scope, and
our result under the same protocol. Give the protocol its own typed status
rather than hiding match or mismatch inside prose. The same row records source
evidence or a concrete blocker for the dataset-origin result, recent
top-conference comparator, a different published mechanism, and a strong simple
baseline. A method may be the strongest comparator on several datasets, but
each dataset keeps its own evidence row; never reuse one dataset's number as
evidence for another.

Verify task, prediction unit, dataset version, split, supervision, information available at inference, metric definition, and evaluation date. A larger published number under a different protocol is historical context, not an apples-to-apples winner. Label it `REPORTED_NOT_MATCHED`; reproduce or adapt decision-critical baselines under the current protocol when feasible.

For the eventual paper decision, identify the strongest recent top-conference
baseline found that can be compared under the same protocol. Record its paper,
venue/year, primary source, score, literature search venues/year range/date, and why the task, data/split, labels,
supervision/inference information, metric, and evaluation procedure match. A
baseline that is merely recent, merely highly cited, or numerically larger under
a different protocol does not satisfy this role.

If the current result table contains only our own methods, the scientific comparison is incomplete regardless of how many internal variants were tried. Prioritize external comparison work before generating more variants. Before calling a result paper-worthy, obtain at least the key protocol-matched comparison. When a key implementation is unavailable or too costly, record the exact blocker and the weakest defensible claim that remains.

## Derive the method from the problem

Maintain a small paper-grade problem portfolio before multiplying methods. A
problem is admissible to L2 only when it:

- exposes a meaningful failure, contradiction, missing capability, estimand, or
  empirical fact rather than a code/runtime inconvenience;
- remains unresolved by the nearest-work cluster under the intended protocol;
- supports a falsifiable prediction and a defensible contribution type such as
  a mechanism, objective, estimand, diagnostic, theory, or empirical finding;
- plausibly admits a mathematical intervention that follows from the stated
  cause.

Runtime failures, data plumbing, performance optimization, ordinary model
configuration, hyperparameters, and bugs are L3 engineering work. Fix them
autonomously. Escalate them into L2 only when the repaired evidence changes the
scientific problem, mechanism conclusion, or active claim.

Use this order:

```text
observed problem
→ plain-language cause
→ solution intuition
→ predicted observable change
→ minimal mathematical formulation
→ minimal implementation
```

Before coding a serious candidate, explain one concrete example showing how the current baseline fails and how the new method would behave differently.

The mathematics should match the intuition:

- the optimized quantity should correspond to the claimed failure;
- required supervision must actually be available;
- inference must use information available in the intended setting;
- the formulation should predict a result that can fail;
- every added component should have a direct role in the mechanism.

Avoid method proposals whose identity is mainly a stack of adapters, routing,
fusion, auxiliary losses, thresholds, hand-selected weights, expert weighted
voting, or heuristic ensembles. Those may be L3 tools, controls, or baselines;
they are not the L2 problem, core mechanism, or innovation. Complexity is
acceptable only when each part follows from the same identified problem and can
be tested against a simpler alternative. Prefer one clear mechanism over a
collection of score-raising patches.

Do not choose mathematics merely because it looks novel. If the intuition cannot be explained without equations, or the equations do not change the predicted failure pattern, the method premise is not ready.

For each active problem, organize candidates into method clusters sharing one
solution intuition and mathematical mechanism. Test a representative minimal
member first. A different hyperparameter, backbone, implementation, or extra
module is normally the same cluster, not a new scientific idea. A new cluster
must change the causal intuition, optimized quantity, estimand, or falsifiable
prediction.

Close a method cluster only after implementation, baseline health, and a
mechanism-sensitive diagnostic have been checked. If one cluster fails, try
another paper-grade cluster for the same problem when justified. If the
credible clusters for that problem are exhausted or the problem itself proves
unimportant, mark the problem exhausted and choose another problem from the
portfolio. Do not keep patching an exhausted cluster for score alone.

Before G2, changing the active exploratory problem or method cluster within the
confirmed L1 is autonomous but always requires a plain-language notification to
the user with the previous and new stable IDs. After G2, replacing the confirmed
problem or core method cluster also requires a new scoped PI decision.

## Potential screen and ceiling search

Do not give every method cluster a full tuning budget. First decide whether its
representative candidate has enough potential to justify a ceiling search.
Before closing the cluster as low-potential, verify that the implementation runs
as intended, the comparison baseline is healthy, and at least one diagnostic
capable of detecting the proposed mechanism was inspected. A weak first
configuration alone is not enough to reject the idea.

Before broad tuning begins, lock the primary metric, its `0–1` or `0–100`
scale, and higher-is-better direction in the evaluation anchor. The agent owns
this technical choice, so it creates no PI question and imposes no universal
aggregation rule. If the anchor later changes, results tied only to its previous
revision remain exploratory until they are rerun or explicitly reassessed under
the new anchor.

Treat a method cluster as promising when most of the following hold:

- its mechanism directly addresses the observed problem;
- a preliminary result or diagnostic moves in the direction predicted by that mechanism;
- the signal is more than one lucky aggregate number, an obvious bug, or a data artifact;
- there is a plausible path from the current result to a competitive result;
- the expected scientific value justifies the remaining compute and time.

In addition, the baseline roster must exist and expose a plausible route to
competitiveness. A candidate can remain in `METHOD_CHEAP_SCREEN` while external
baselines are being verified, but it cannot be called paper-worthy from
internal comparisons alone. Apply the canonical G3 numeric floor and
protocol-matched comparison in [workflow.md](workflow.md); project-specific L1
requirements may be stricter but cannot lower that floor.

For a promising method cluster, choose a project-appropriate ceiling-search budget
based on the venue timeline, available compute, and the number of viable
alternatives. Tune hyperparameters and other permitted implementation choices
using available compute, including an existing GPU by default. Continue until
results saturate, gains show clear diminishing returns, the budget is reached,
or the candidate loses its promise. Gather repeat, uncertainty, or stability
evidence appropriate to this project when the method approaches the paper gate;
do not impose one seed count, aggregation method, or significance test on every
project. The resulting "ceiling" is the best observed development-side result
under the current project contract, not a universal upper bound or proof of
generalization. Report the decision-relevant summary; do not require an archive
of every attempt or the stopping rule.

After the ceiling report and external comparison exist, ask the user whether
this problem + method cluster + core mechanism + innovation claim should become
the active L2 scientific story. The tuning itself does not silently make that
decision.

Report a ceiling search to the user in plain language with:

1. the problem and method being tested;
2. why the method looked promising;
3. what was tuned;
4. the locked metric and the starting and best results under its current revision;
5. the gap to the strongest relevant baseline;
6. stability, failure cases, and remaining weaknesses;
7. compute cost, estimated ceiling, and whether the evidence now looks paper-worthy.

The ceiling summary may say “promising but not paper-decision ready” when the
external comparison is incomplete or the gain is below the floor. Do not turn a
promising internal result into a paper recommendation by wording alone.

If a method cluster has no credible potential, stop before broad tuning and move
to another justified cluster or problem; no individual negative-result record
is required. Notify every problem or method-cluster switch. Surface additional
failure detail only when it changes the research compass, exhausts or materially
narrows the portfolio, invalidates a serious premise, or affects an item marked
`FROZEN_BY_PI`.

## Candidate records by layer

Before L1 confirmation, keep task-dataset candidates only in the compact L1
shortlist. Each row or attached note covers meaning, task-data fit, headroom,
nearest-work risk, external-baseline feasibility, cost, and recommendation. Do
not create an L2 file for an unselected task-dataset pair. The shortlist also
states the mandatory unexposed-dataset search result or its current blocker.

After L1 confirmation, maintain two compact L2 maps inside that direction:

```text
problem ID | status | nearest-work cluster | shared unresolved problem | scientific value | failure evidence | paper-grade rationale | next action
problem ID | method-cluster ID | status | shared intuition | mathematical mechanism | falsifiable prediction | representative evidence | external-baseline gap | next action
```

These are selective scientific maps, not trial logs. Keep the active problem,
credible alternatives, exhausted problem/cluster conclusions that affect the
next choice, and anything shown to or decided by the user. L3 owns bugs,
implementation variants, tuning runs, and routine repair notes.

For a decision-relevant problem/method card, cover:

```text
L1 已确认方向 reference：
最接近的工作、来源、检索日期与未解决点：
外部 baseline roster、协议可比性与复现状态：
观察到的具体问题与基线失败例子：
解决直觉、预测诊断与最小数学方法：
候选创新点及与近邻工作的差异：
第一个可证伪实验及潜力筛选证据：
调参起点、当前最好结果与外部 baseline 差距（如适用）：
问题 ID、方法簇 ID、状态及更换通知（如发生）：
L2 科学主线决策来源（如已确认）：
剩余论文证据缺口、预计时间和算力：
```

Keep a small ranked set rather than a long idea dump. Cheap data and baseline
feasibility work may precede L1, but sustained method work starts only after L1
confirmation. Preserve L2 cards that received a user decision or materially
support the active scientific interpretation; L3 trial detail remains
discretionary. When a whole problem or method cluster is closed, retain only
the compact conclusion needed to justify the next scientific choice, not every
attempt or stopping rule.

## Downstream decision rule

Every later decision should cite the candidate card and answer:

1. Which research-compass check does this decision address?
2. What new evidence requires the decision?
3. Does it preserve the target venue/time and domain?
4. Does it strengthen task meaning, task-data fit, headroom, novelty, or the problem-to-method link?
5. Is it a scientific repair or only another engineering patch?

If none of these answers is clear, do not make the change merely because it may raise the score.

Report conclusions in plain language. Technical names and metric tables may follow, but they cannot replace the explanation of what problem was found and why the proposed method should solve it.
