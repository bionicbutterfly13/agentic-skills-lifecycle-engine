# Pitfalls Research

**Status:** Risks extracted from the reviewed primary sources and Daedalus operating
experience

## Static files mistaken for a lifecycle

**Warning sign:** The project can generate `SKILL.md` but cannot show a paired test,
decision record, rollback path, or retirement state.

**Prevention:** Make lifecycle transitions and their evidence part of the minimum
vertical slice.

## Self-judgment controls promotion

**Warning sign:** A model's score or explanation is the final acceptance criterion.

**Prevention:** Use deterministic correctness gates and treat model judgment as
diagnostic evidence only.

## Evaluation leakage

**Warning sign:** The proposer or maintainer can inspect held-out tasks, validation
traces, or acceptance thresholds during candidate creation.

**Prevention:** Freeze packets, separate roles, hide validation data, and record every
artifact access.

## Mutable identity

**Warning sign:** A skill changes after review while retaining the same approval.

**Prevention:** Hash the complete candidate. Any byte change invalidates earlier
inspection, admission, and evaluation.

## Retrieval confused with permission

**Warning sign:** A relevant skill is executed without a compatible capability grant.

**Prevention:** Keep retrieval, trust, license, policy, compatibility, and runtime
admission as separate gates.

## Host neutrality asserted too early

**Warning sign:** The core is described as cross-runtime after only the Daedalus adapter
exists.

**Prevention:** Describe runtime neutrality as a design property until a second adapter
passes the same contract suite.

## Synthetic success inflated into a product claim

**Warning sign:** Passing fixtures are described as proof that Lifecycle improves real
agents.

**Prevention:** Label evidence by class and scope. The first study can validate the
experimental machinery without validating broad utility.

## Lost work during ASME retirement

**Warning sign:** The old repository is deleted after copying visible source files.

**Prevention:** Audit code, contracts, tests, provenance, licenses, unique evidence,
history, and untracked material immediately before any authorized deletion.

