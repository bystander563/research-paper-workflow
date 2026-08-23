# Exploration policy

Read this reference when scouting a paper direction, selecting a task and dataset, or turning an observed failure into a method.

## Start from the PI brief

Before open-ended exploration, establish:

1. a target submission window and/or conference;
2. the research domain;
3. an optional starting concept from the user.

The first two are the research compass and should normally be recorded as `FROZEN_BY_PI`. A starting concept is inspiration, not a novelty claim and not automatically frozen. If the user says the concept itself must remain central, record that explicitly.

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

## Derive the method from the problem

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

Avoid method proposals whose identity is mainly a stack of adapters, routing, fusion, auxiliary losses, thresholds, or hand-selected weights. Complexity is acceptable only when each part follows from the same identified problem and can be tested against a simpler alternative. Prefer one clear mechanism over a collection of score-raising patches.

Do not choose mathematics merely because it looks novel. If the intuition cannot be explained without equations, or the equations do not change the predicted failure pattern, the method premise is not ready.

## Potential screen and ceiling search

Do not give every candidate a full tuning budget. First decide whether the method has enough potential to justify a ceiling search. Before closing a method as low-potential, verify that the implementation runs as intended, the comparison baseline is healthy, and at least one diagnostic capable of detecting the proposed mechanism was inspected. A weak first configuration alone is not enough to reject the idea.

Treat a candidate as promising when most of the following hold:

- its mechanism directly addresses the observed problem;
- a preliminary result or diagnostic moves in the direction predicted by that mechanism;
- the signal is more than one lucky aggregate number, an obvious bug, or a data artifact;
- there is a plausible path from the current result to a competitive result;
- the expected scientific value justifies the remaining compute and time.

For a promising candidate, choose a project-appropriate ceiling-search budget based on the venue timeline, available compute, and the number of viable alternatives. Tune hyperparameters and other permitted implementation choices using available compute, including an existing GPU by default. Continue until results saturate, gains show clear diminishing returns, the budget is reached, or the candidate loses its promise. Record why the ceiling search stopped. The resulting "ceiling" is the best observed development-side result under the current project contract, not a universal upper bound or proof of generalization.

Report a ceiling search to the user in plain language with:

1. the problem and method being tested;
2. why the method looked promising;
3. what was tuned;
4. the starting result and best result;
5. the gap to the strongest relevant baseline;
6. stability, failure cases, and remaining weaknesses;
7. compute cost, estimated ceiling, and whether the evidence now looks paper-worthy.

If a candidate has no credible potential, stop before broad tuning and record a short internal reason. Do not send an individual report merely to enumerate weak candidates. Surface the failure only when it changes the research compass, exhausts or materially narrows the candidate pool, invalidates a serious premise, or affects an item marked `FROZEN_BY_PI`.

## Candidate card

For each serious task-dataset-method candidate, keep a compact card:

```text
目标投稿时间/会议：
领域：
用户给的初始构想（如有）：
任务为什么有意义：
任务与数据集为什么匹配：
数据集为什么还有提升空间：
最接近的工作及未解决点：
近邻工作来源、检索日期与已验证事实：
观察到的具体问题：
解决问题的直觉：
对应的最小数学方法：
最强简单对照：
第一个可证伪实验：
潜力筛选状态与证据：
低潜力关闭原因（如适用）：
调参起点、当前最好结果与停止原因（如适用）：
本项目的论文就绪条件：
预计时间和算力：
```

Keep a small ranked set of candidates rather than a long idea dump. A candidate may enter cheap exploratory testing when the pair is plausible; it becomes a confirmed project only when the user fixes the task or dataset.

## Downstream decision rule

Every later decision should cite the candidate card and answer:

1. Which research-compass check does this decision address?
2. What new evidence requires the decision?
3. Does it preserve the target venue/time and domain?
4. Does it strengthen task meaning, task-data fit, headroom, novelty, or the problem-to-method link?
5. Is it a scientific repair or only another engineering patch?

If none of these answers is clear, do not make the change merely because it may raise the score.

Report conclusions in plain language. Technical names and metric tables may follow, but they cannot replace the explanation of what problem was found and why the proposed method should solve it.
