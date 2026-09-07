# Fidelity and capability labels

## Trace fidelity

- `paper_complete`: captured reasoning, tool calls, tool outputs, and final answer are all
  present. Provider-hidden reasoning is not reconstructed.
- `observable_transcript`: visible assistant and tool events are captured, without a
  claim about hidden reasoning.
- `final_only`: only the returned final answer is bound to the job.
- `unknown`: the adapter cannot prove even the narrower capture contract.

## Isolation labels

Conversation, filesystem, tool, held-out-answer, and wiki isolation are recorded
separately as `enforced`, `procedural`, `none`, or `unknown`.

`sandboxed` is allowed only if every relevant dimension is enforced. `unseen` is allowed
only if held-out answers and the wiki are inaccessible and that boundary has been
negatively tested. Otherwise the run is labelled `unsandboxed`.

## What markers prove

Literal markers can detect propagation into outputs or candidate files. They do not prove
that an agent could not read a source, and a marker-free paraphrase is not detected. A
correct prediction equal to an expected answer is legal; provenance markers, not answer
values, are the canary.

## Hermes default

The included Hermes plugin currently reports `unknown` and `unsandboxed`, then refuses
role dispatch. A future adapter may report a stronger label only after its exact runtime
version and negative isolation tests are recorded.

