# WikiSkill paper notes

Primary source: [arXiv:2608.27454v1](https://arxiv.org/abs/2608.27454).

## Retained paper method

- Keep three layers distinct: immutable training traces, a persistent wiki, and active
  procedural skills.
- Start with empty skills and wiki, run a baseline, then iterate over train tasks.
- Sample at most five failures and three successes, truncating each trace view to 15,000
  characters.
- Run Wiki Maintainer before Skill Proposer.
- Give the Proposer train outcomes and train ground truth, while keeping validation and
  test answers outside its input.
- Permit one create, patch, or no-action proposal per iteration.
- Accept only strict aggregate improvement. On rejection, keep the wiki and roll back the
  candidate skill.
- Keep train, validation, and test splits disjoint.
- Preserve skill-impact history.

## Local architecture rules

The paper does not specify the transaction journal, exact snapshot hash, provider lock,
confirmation run, visibility-safe observation seed, route latch, staging archive, or
runtime adapter contract used here. Those are labelled `ARCHITECTURE` or `GATE_A` in
code and records.

Local acceptance requires two fresh strict wins. The accepted score is the lower of the
validation and confirmation scores. This reduces lucky promotion but is not presented as
a paper rule.

## Evidence limits

The paper evaluates specific benchmark suites and reports aggregate results and
ablations. This implementation does not reproduce those experiments. A local accepted
candidate is not a paper-comparable result. Public comparative claims require three
complete runs and paired-bootstrap evidence under the claim policy.

The paper reports that prompts, model behavior, and trace quality affect results. A final
answer or visible transcript cannot be relabelled as hidden reasoning. This package uses
the narrower label that the runtime can prove.

## Paper result reference

These are paper results, not results reproduced by this package.

- In the Gemini-3.5-Flash ablation, disabling wiki access for both the Inference Agent
  and Skill Proposer produced a 48.7 average. The paper's default, no Inference Agent
  wiki access and Skill Proposer wiki access, produced 63.7. Giving both roles wiki
  access produced 60.9. Paper Table 3, Section 5.1.
- Table 4 reports average evolved-skill lengths from 45.1 to 128.6 markdown lines by
  model and from 84.6 to 142.5 by benchmark. Average wiki-pattern lengths range from
  18.1 to 48.2 lines by model and from 26.9 to 40.6 by benchmark.
- The main paper text names the chronological file `logs.md`, while Appendix E.2 names
  `wiki/log.md`. This implementation chooses `wiki/log.md` as a local architecture rule;
  the filename is not presented as an unambiguous paper requirement.

## Paper limitations retained

The paper does not evaluate skill retrieval or triggering because it injects active
skills directly. Strict-improvement gating excludes neutral proposals that might enable
later gains. The wiki has no automated pruning mechanism. The benchmark suite does not
cover executions spanning hundreds of environment actions or multiple hours. This
package does not claim to resolve those limitations.
