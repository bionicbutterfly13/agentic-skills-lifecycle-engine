# Security model

Report suspected path traversal, symlink escape, provider fallback, answer leakage,
transaction replay, archive ambiguity, or credential exposure privately to the project
owner. No public reporting address has been approved yet.

The core rejects unsafe relative paths, symlinks in governed trees, private absolute paths
in staged files, credential-like content, provider/model drift, domain-seal drift, output
hash mismatch, candidate marker propagation, and non-identical replay targets.

The core does not provide an OS sandbox. Runtime isolation is measured and labelled. An
`unsandboxed` run may still be useful as local evidence, but it cannot support an unseen
or sandboxed claim.

