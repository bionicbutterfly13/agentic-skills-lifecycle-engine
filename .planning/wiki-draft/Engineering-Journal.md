# Engineering journal

A dated record of obstacles met while building Lifecycle, how each was diagnosed, and how
it was resolved. Each entry names its evidence and the commit that closed it. Entries are
factual records, not narrative; published articles draw on this page as source material.

## 2026-09-22 to 2026-09-23: first live runs of the WikiSkill loop

### 1. The engine had never run a model

**Obstacle.** A parity audit against the WikiSkill paper (arXiv 2608.27454) found the
engine faithful to the paper's loop in structure: sampling limits, the Maintainer and
Proposer output shapes, the strict gate, skill rollback with a persistent wiki. But every
rollout in the repository came from recorded fixtures. The Hermes adapter had dispatch
disabled, and one evaluation path used a scripted responder that answered correctly
whenever the skill's name appeared in the prompt.

**Resolution.** A direct adapter (`adapters/direct`) that sends a prepared job to any
OpenAI-compatible endpoint, such as a local Ollama server or a GPU behind a tunnel. The
first live run scored 1.0 on an easy smoke domain and the engine stopped immediately,
which is the paper's early-stop rule acting on real output. Commit `1c80646`.

### 2. The capability report changed its own fingerprint on every probe

**Obstacle.** A prepared job binds the digest of the capability report it was prepared
against. The report embeds its observation time, so each fresh probe produced a new digest
and every dispatch would have been refused as bound to a different report.

**Resolution.** The adapter measures once and reuses that report for the dispatches bound
to it; a caller can force a fresh measurement. Covered by
`test_probe_is_cached_so_the_job_digest_stays_stable`.

### 3. The development laptop was too slow to run the study

**Obstacle.** Estimates were first based on remembered throughput. Measured on the actual
machine (Intel i7-9750H, no usable GPU), `qwen3.5:4b` generated 1.5 tokens per second. A
40-token prompt took 73 seconds, and one research-level question ran 26 minutes.

**Resolution.** Treat the laptop as wiring-only and serve the model from a Colab GPU. On a
T4, `qwen3.5:9b` generated 24.8 and read prompts at 202.3 tokens per second, warm.
Lesson: measure throughput on the target hardware before planning iterations.

### 4. A model spent its whole budget reasoning and never answered

**Obstacle.** On a real LiveMathematicianBench item the model used all 3,072 output tokens
inside its reasoning and emitted no answer tag, after 1,598 seconds.

**What went right.** The engine did not score it. The adapter recorded the termination as
truncated, extraction failed, the manifest was invalid, and the state machine refused to
advance. A non-answer never became a zero.

**Resolution.** One added sentence in the inference prompt tells the model to commit to
its best current choice rather than run out of room. This deviates from the paper's
prompt, so paper-comparable runs must use the verbatim text instead. Commit `cf15267`.

### 5. The packaging gate refused quoted paper text

**Obstacle.** The distribution checker treats every markdown link as a file dependency. An
example link inside the paper's quoted Maintainer prompt looked like a missing file, and a
wiki-style link in a draft did the same.

**Resolution.** Wiki drafts live under `.planning/`, which the distribution excludes by
design. The quoted paper prompts were first moved there too, which was wrong: see entry 11.

### 6. A new adapter broke an architecture rule on main

**Obstacle.** The direct adapter imported two core modules. Governance rule HF-A03 allows
adapters to import only `asme.contract`, so that no adapter can fork core behavior. Only
the tests next to the change were run before pushing, so main carried one failing test
until the next task's baseline check stopped and reported it.

**Resolution.** The adapter now duck-types the job and builds its evidence record from the
contract module alone, with behavior unchanged. Full suite afterwards: 688 passed, 1
skipped, 0 failed. Commit `0e38c8c`. Lesson: run the full suite before every push.

### 7. A green test run that proved nothing

**Obstacle.** The project configuration already passes `-q` to pytest. Passing it again
hid the summary line, and piping the output into `tail` meant the recorded exit status
belonged to `tail`, not pytest.

**Resolution.** Capture pytest's own exit status directly, and count outcomes from the
progress line when the summary is absent.

### 8. The confirmation switch loosened a history check

**Obstacle.** Letting a study promote on a single validation win (PAR-03) required an
accepted history entry to carry one score instead of two. The entry type cannot see its
domain's mode, so a one-score accepted entry would have read back clean even in a domain
that requires confirmation. The independent verifier confirmed this.

**Resolution.** The history reader now takes the domain's confirmation setting and refuses
an accepted entry whose score count does not match it. Four test cases cover both
mismatches and both matches. Full suite: 704 passed, 1 skipped, 0 failed. Commit `5992e82`.

### 9. The Colab install cell failed

**Obstacle.** The Ollama install script exited with status 1 in two seconds. The notebook
discarded the script's error output, so the cause was invisible.

**Resolution.** Rerunning with the output visible showed "This version requires zstd for
extraction." The notebook now installs `zstd` first. Commit `481ae2f`.

### 10. The model server's context window was too small

**Obstacle.** `ollama ps` showed a 4,096-token context. The Wiki Maintainer receives up to
eight traces of 15,000 characters each, roughly 30,000 tokens.

**Resolution.** The notebook starts the server with a 32,768-token context. Not yet
verified on a live runtime; the next run's `ollama ps` will show the effective value.

### 11. A requirement was ticked before it was true

**Obstacle.** PAR-05 says the paper's prompts ship with the package. It was marked done
while the prompts sat under `.planning/`, which never ships. The planner for the next task
found the contradiction by reading the distribution tests.

**Resolution.** The prompts move to `references/paper-prompts/` as `.txt` files. The
distribution's link checker reads only `.md` files, so the example links inside the quoted
text no longer look like missing dependencies, and not one byte of the paper text changes.
A test compares each moved file with its original bytes in git history. Commits `b241b84`
and `f95d71f`. Lesson: tick a
requirement only after checking the shipped artifact, not the intent.
