# Scientific exploration

Use this reference when choosing a task, problem, method or next experiment.
It owns scientific judgment; [workflow.md](workflow.md) owns approval gates and
[research-state.md](research-state.md) owns the record format.

## Start from the research brief

Confirm venue/submission window and domain before open-ended exploration.
Preserve a user-supplied idea as a seed unless its scope is explicitly fixed.
Existing code and convenient data are evidence about feasibility, not authority
to decide the research direction.

Scout a small ranked shortlist of task-dataset pairs. Consider:

- meaningful capability, failure or unanswered question and who/what benefits;
- task-data fit in both directions: prediction unit, labels, metadata and evaluation;
- nearest-work collision risk and space for a defensible contribution;
- usable external comparisons, achievable headroom, cost and time to evidence;
- fit to the user's venue/window and research interests.

During L1 scouting, actively search for at least one credible dataset not
previously exposed in this project, or give a concrete reason none is feasible.
Adopting it, requiring a second dataset, and generalization standards remain
the user's L1 choices. Do not create a sealed-set or new-label protocol.

Prefer useful headroom, not just a low number. A benchmark at 90+ is not
automatically solved; a low score may reflect bad labels, mismatched protocols
or a broken baseline rather than opportunity. Inspect errors and whether the
task/data can distinguish the proposed scientific mechanism.

## Nearest work and external comparisons

Verify decision-critical claims from primary sources. Keep title, year/venue,
stable URL/DOI, search date/scope, relevant protocol and the passage/table/code
supporting the claim. Separate verified facts from inference. Model memory,
search snippets and title similarity do not establish novelty.

Nearest work answers **what has already been explained or solved**; an
experimental baseline answers **what we must compare against**. A single paper
can serve both roles; share its source record, not two independently maintained
descriptions. Include conceptual neighbors even when they are not runnable.

As soon as L1 datasets are selected, establish the dataset-indexed external
comparison roster; do not postpone it until several rounds of internal tuning.
The target is the strongest comparable external result supported by the search,
not whichever method is easiest to reproduce. State search scope/date and what
is still unverified rather than promise a globally exhaustive "best".
Before broad ceiling tuning, source-check that roster.
For each adopted dataset, find the strongest recent top-conference comparator
under the relevant protocol; record venue/year/source and search scope. Cover
the dataset-origin result, a recent top-conference method, a different published
mechanism, and a strong simple baseline when applicable. Record an explicit
blocker for unavailable roles; do not invent comparators or count our variants.

Check task, dataset version/split, prediction unit, labels/supervision,
inference information, metric and evaluation procedure. Published numbers
under different conditions are context, not wins. Reproduce/adapt the
decision-critical comparison when feasible. Identity/source verification is
needed before broad tuning; complete matched evidence is needed for the paper
gate. Do not duplicate the roster's numbers in a second hand-maintained table.

Carry the external reference through screening, ceiling search and reporting.
Our previous model, base model and ablations explain a mechanism; none becomes
the main competitive baseline just because it is convenient. A valid new result
updates our score in the matching roster row without changing the external
opponent. If comparability is unresolved, report the limitation and external
target, not a win. A failed reproduction is a reproduction gap, not grounds to
lower a published score. Source-checked stronger comparators replace the target
with a plain-language explanation; a correction or protocol mismatch also needs
an explanation. Do not ignore known stronger comparable work outside the recent
top-conference set; retain it as an additional scientific challenge in L2 while
preserving G3's existing top-conference requirement.

## Find the problem before multiplying methods

Retain only the unresolved path needed to reach the active leaf. Fixed upstream
choices are context, not research tasks to rediscover. A one-node path is valid.
The leaf must identify a meaningful failure, contradiction, missing capability
or empirical fact left unresolved by nearest work, not an implementation nuisance.

Reason through:

```text
observed problem -> suspected cause -> solution intuition
-> predicted difference -> suitable mathematics -> discriminating test
```

The suspected cause is a hypothesis, not a fact merely because it sounds
plausible. Use a concrete failure example and an experiment that can distinguish
it from the strongest relevant alternative explanation. Mathematics should
formalize the proposed mechanism, use available information, and imply a
prediction that could fail; novelty-looking equations are not evidence.

A lightweight idea need only identify the gap, intuition and next useful test.
Do not demand a complete paper packet before a cheap diagnostic. Before serious
method implementation, articulate the mechanism and relevant simpler
alternative; add the full innovation argument as evidence matures.

Engineering combinations such as score fusion, voting, extra losses, routing or
module stacks may be controls or implementation tools. They cannot carry the
core novelty merely because they improve a metric. Conversely, words such as
"weighted" do not disqualify a new objective, estimand, constraint, mechanism or
theory. Judge the scientific object and evidence, not its vocabulary.

Ask **why the nearest relevant simpler alternative cannot account for the
claimed improvement**. Do not require an unrelated argument against averaging
for every candidate. The legacy `simple_combination_counterfactual` field now
stores this relevant-alternative explanation (`--alternative-explanation`).

Group candidates by shared mechanism, not configuration. A different backbone,
seed, hyperparameter or code path is usually the same method cluster. Keep one
evolving record per decision-relevant cluster, including its problem link,
mechanism, evidence and next action; no separate problem-to-method, method-cluster
and ceiling tables repeating the same facts.

## Choose experiments that change our understanding

For the next scientific test, be able to explain:

1. What important uncertainty are we resolving?
2. Which explanations or methods will this evidence distinguish?
3. What would the different outcomes imply for the next research move?

These are reasoning prompts, not three new required records or PI questions.
Choose the smallest informative test before multiplying candidates or tuning.
Resolve implementation problems in L3. If a repair changes the validity of a
result, update the L2 conclusion immediately and stop using the invalid claim.

Do not reject a mechanism solely because its first configuration is weak.
Check implementation sanity, baseline health and a diagnostic sensitive to the
proposed mechanism. A promising cluster has a credible predicted signal, an
intact comparison, a plausible path to competitiveness, and enough expected
scientific value to justify the remaining time/compute.

Before broad tuning, record the comparison roster and lock the active
problem/path, method, prediction and primary metric/scale/direction. This is an
agent-owned evaluation anchor, not an extra approval. Old-anchor evidence must
be rerun or explicitly reassessed before supporting a new claim.

Tune only promising clusters. Use the available GPU unless the user says
otherwise; paid rental still requires permission. Bound the search by the
project's timeline, compute and diminishing returns. Its "ceiling" is the best
observed development-side result, not a universal upper bound.

Summarize starting/best results, matched external gap, stability, failure cases
and remaining evidence in the same research record. Explain scientific meaning
to the user, not a trial-by-trial parameter log. Apply the canonical
[G3 floor](workflow.md#g3-paper-decision-ready); never reword an internal win as
paper-ready. No universal seed count, aggregation rule or significance test.

If credible approaches to a leaf are exhausted, change the problem rather than
accumulate patches. Before G2 this is autonomous within L1 with a plain-language
notification; changing a confirmed selection needs a scoped decision.
Retain only conclusions that affect the next choice or were discussed with the
user. Do not require every failed attempt or stopping rule to be archived.
