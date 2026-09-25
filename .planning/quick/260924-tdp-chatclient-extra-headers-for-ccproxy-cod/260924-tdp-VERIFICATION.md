---
phase: 260924-tdp-chatclient-extra-headers-for-ccproxy-cod
verified: 2026-09-25T02:30:00Z
status: passed
score: 7/7 must-haves verified
covered_files:
  - .planning/REQUIREMENTS.md
  - .planning/quick/260924-tdp-chatclient-extra-headers-for-ccproxy-cod/260924-tdp-PLAN.md
  - .planning/quick/260924-tdp-chatclient-extra-headers-for-ccproxy-cod/260924-tdp-SMOKE.md
  - .planning/quick/260924-tdp-chatclient-extra-headers-for-ccproxy-cod/260924-tdp-SUMMARY.md
  - scripts/run_maintainer.py
  - scripts/run_proposer.py
  - src/asme/model_client.py
  - tests/test_model_client.py
  - tests/test_run_maintainer.py
  - tests/test_run_proposer.py
covered_digest: "v1:sha256:4c20f3095efe2e02ce6d8ff7b554601ef25dfc3bb3d6fd54ab76e142d7e2cf70"
behavior_unverified: 0
overrides_applied: 0
coincidental_reliance_items:
  - truth: "The full offline suite exits 0, measured by pytest's own exit code, with no new file left undeclared in MANIFEST.in."
    reason: undeclared-precondition
    harden: "The full-suite log (mtime 21:50:23) was produced from the executor worktree's working tree before commits 07df998 (21:52:18) and cb3e09e (21:52:27) existed. Equivalence to main is inferred, not proven: collected count on main is 759 (= 758 passed + 1 skipped in the log), only three test files import the changed modules and all were re-run green on main 522fce5, and cb3e09e..522fce5 has zero code diff. Future quick tasks should run the full suite after the final commit, or record the tree hash in the log."
---

# Quick Task 260924-tdp: ChatClient extra headers for ccproxy /codex/v1 Verification Report

**Task Goal:** Let ChatClient send optional extra HTTP headers, configurable from the Maintainer and Proposer driver CLIs, so the drivers can reach gpt-6-luna through ccproxy's /codex/v1 route on a ChatGPT subscription. No secrets via CLI; default request byte-identical; usage recorded as reported; full suite passes; live smoke of one Maintainer call and one Proposer detective call.
**Verified:** 2026-09-25T02:30:00Z (against main at 522fce5)
**Status:** passed
**Re-verification:** No, initial verification

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | Default request unchanged with no --header / no extra_headers (headers and body bytes pinned by golden test) | VERIFIED | `_headers()` keeps its two original statements, then `headers.update(self._extra_headers)` (no-op when empty). `complete()`, `_post`, `_send` untouched in `git diff 835e853 522fce5`. `test_default_request_headers_and_body_are_unchanged` (parametrized omitted/None/{}) asserts exact header dict and byte-equal body; passes on main. Plan guard grep for the Authorization statement prints 1. |
| 2 | Repeatable --header on both drivers reaches the endpoint on every request; user-agent replaces Python-urllib on the wire | VERIFIED | Both parsers add `--header` (action=append). CLI tests through `main()` capture the ChatClient and find all three extras. `test_extra_headers_reach_the_wire_and_override_default_user_agent` uses a real loopback ThreadingHTTPServer: extras arrive, UA is `codex_cli_rs/0.155.1 (probe)`, the plain client still sends `Python-urllib/`. `_headers()` is called from `_post` on every request. Live corroboration: without identity headers the route answers 400; the Proposer detective run made 8+ successful calls through it. |
| 3 | Authorization / Proxy-Authorization / Content-Type refused before workspace access or network; exit 2; ModelClientError; no echo | VERIFIED | `RESERVED_HEADER_NAMES` checked case-insensitively in `_validated_header_pairs`, messages use position + canonical name only. Both drivers call `parse_header_specs` right after `parse_args()` and before `DomainWorkspace`. Spot-check on main: `--header "Proxy-Authorization: Basic zz..."` and `"content-type: zz..."` exit 2 on both drivers with zero sentinel echo, while a valid header with the same nonexistent domain-root reaches the later `domain workspace is not initialized` error (exit 1), proving the refusal precedes workspace access. pytest covers Authorization via CLI (exit 2, `usage:`, no sentinel, loop never called) and all three names via ChatClient. |
| 4 | CR/LF/NUL values, non-token names, case-insensitive duplicates refused with ModelClientError | VERIFIED | `_HEADER_NAME_TOKEN` fullmatch on RFC 9110 tchar set; `_FORBIDDEN_VALUE_CHARACTERS`; `seen` set on lower-cased names. `test_extra_headers_reject_line_breaks_and_invalid_names` (6 cases, asserts no "sentinel" in message), `test_extra_headers_reject_case_insensitive_duplicates`, `test_parse_header_specs_rejects_repeated_names` all pass. |
| 5 | Extra headers never enter the body; response handling unchanged, no synthesized usage | VERIFIED | Body built only in unchanged `complete()`; `test_extra_headers_are_sent_and_body_is_unchanged` asserts body bytes equal the golden body with extras present. Response mapping code (content, tool_calls, finish_reason) is outside the diff; no `usage` key is produced anywhere in model_client.py. |
| 6 | Full offline suite exits 0 by pytest's own exit code; no new file undeclared in MANIFEST.in | VERIFIED (coincidental-reliance) | Log `/var/folders/dt/s_wcpb612fg7l96x7r3fpwm80000gn/T/lifecycle-260924-tdp/full-suite.log` ends `758 passed, 1 skipped, 1 warning in 1028.52s` then `EXIT=0`. `git diff --name-status 835e853 522fce5` shows only 6 `M` files; no untracked files under src/scripts/tests. Targeted re-run on main (model_client, run_maintainer, run_proposer, distribution): 130 passed, exit 0. See advisory: the log predates the final two commits. |
| 7 | Live smoke via ccproxy 0.2.10 /codex/v1, gpt-6-luna: one Maintainer call and one detective Proposer run through the real CLIs; SMOKE.md records HTTP outcome, tool_calls, usage verbatim; ccproxy stopped | VERIFIED | Raw artifacts inspected directly (not via SUMMARY): `maintainer.out` ends `EXIT=1` with `attempt 1/3 failed: maintainer input hash mismatch` then `ModelClientError: HTTP 502`; `maintainer-attempt-1.txt` is 950 bytes of model JSON; `proposer.out` is `EXIT=0`; `probe.json` gives model gpt-6-luna, tool_calls [read_file], finish_reason tool_calls, usage `{"completion_tokens": 0, "prompt_tokens": 0, "total_tokens": 0}`, matching SMOKE.md verbatim. `lsof -iTCP:8765 -sTCP:LISTEN` returns nothing now. Smoke ran from the worktree at cb3e09e, whose code tree is identical to 522fce5. |

**Score:** 7/7 truths verified (0 present, behavior-unverified)

### Maintainer smoke failure assessment

The Maintainer result does not leave a must-have unmet. The must-have requires the call to run and its HTTP outcome to be recorded, both of which hold. The two failures have different causes, and neither points at the header change:

- **Attempt 1:** HTTP 200 with content, so the identity headers worked and the Maintainer driver reached gpt-6-luna. Validation then failed in `src/asme/wiki.py:151`, because the model wrote `attestation.input_hash` as three semicolon-joined hashes instead of the single input hash. That is a model-output contract failure, and the plan says to record it rather than fix it.
- **Attempt 2:** HTTP 502 from ccproxy. The filtered ccproxy log shows `codex_format_chain_response_failed` from `ccproxy.plugins.codex.adapter` with a pydantic `ResponseObject ... Field required` error. The adapter failed to convert the upstream reply. The same headers had just produced a 200, so this is a ccproxy route limitation, and it is correctly recorded as a follow-up.

Residual risk: no complete Maintainer iteration has been shown on this route yet. That was never a must-have, but it should be treated as unproven before any long Maintainer run through ccproxy.

### Sentinel concatenation deviation (commit 07df998)

The deviation does not weaken either check:

- **Scanner unchanged:** `git diff 835e853 522fce5 -- src/asme/package.py tests/test_distribution.py MANIFEST.in` is empty. `_SECRET_PATTERNS` still includes `\bsk-[A-Za-z0-9_-]{20,}\b`.
- **Assertions unchanged:** `"sk-" + "secret-without-colon"` and `"sk-" + "test-should-not-echo"` evaluate to the same strings as the old literals (20-char suffixes, which is why they tripped the scanner). Each test builds one `sentinel` variable, feeds it to the code under test, and asserts that same variable is absent from the output. Input and assertion cannot drift apart.
- **Established repo convention:** `tests/test_snapshot_package.py:210` already uses `secret = b"sk" + b"-" + b"a" * 24`. `package.py` itself builds its PEM pattern by concatenation.
- **Scanner still strict:** nothing was added to an allowlist. A real `sk-` literal committed anywhere in the sdist is still refused, and `test_distribution.py` passes on main.

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `src/asme/model_client.py` | extra_headers, parse_header_specs, RESERVED_HEADER_NAMES, construction-time validation | VERIFIED | All present; validated in `__init__`; imported by both drivers |
| `scripts/run_proposer.py` | --header parsed before workspace, passed to ChatClient | VERIFIED | `parse_header_specs` then `build_workspace_and_client(args, extra_headers=...)` |
| `scripts/run_maintainer.py` | --header parsed before workspace, passed to ChatClient | VERIFIED | Parser still inside `main()`; `test_api_key_is_read_from_environment_not_a_cli_flag` passes |
| `tests/test_model_client.py` | golden, pass-through, loopback, refusal tests | VERIFIED | Contains `test_default_request_headers_and_body_are_unchanged` and the others |
| `tests/test_run_proposer.py` | CLI pass-through, default, Authorization refusal | VERIFIED | Drives real `main()` |
| `tests/test_run_maintainer.py` | CLI pass-through, default, Authorization refusal | VERIFIED | Drives real `main()` without pre-calling sample_train |
| `260924-tdp-SMOKE.md` | one key: value per field, no secrets | VERIFIED | All 13 keys present, including `probe_usage:`; bearer-shape grep = 0 |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| run_proposer.main() | parse_header_specs -> ChatClient(extra_headers) | parser.error on ModelClientError | WIRED | Exit 2 observed in spot-check and tests |
| run_maintainer.main() | parse_header_specs -> ChatClient(extra_headers) | parser.error on ModelClientError | WIRED | Exit 2 observed in spot-check and tests |
| ChatClient._headers() | urllib.request.Request(headers=...) in _post | update after original two statements | WIRED | Loopback server receives the headers |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| Targeted test files on main | `PYTHONPATH=src python3 -m pytest tests/test_model_client.py tests/test_run_maintainer.py tests/test_run_proposer.py tests/test_distribution.py -p no:cacheprovider` | 130 passed, exit 0 | PASS |
| Collected count matches the log | `pytest --collect-only` | 759 collected (758 + 1 skipped) | PASS |
| Proxy-Authorization / Content-Type / no-colon refused on both CLIs, no echo, before workspace | driver runs with nonexistent domain root | exit 2, 0 sentinel echoes; the valid-header control reaches the workspace error | PASS |
| No hardcoded Codex identity | `grep -rn --include='*.py' codex_cli_rs src scripts` | 0 | PASS |
| Default Authorization statement intact | plan guard grep | 1 | PASS |
| ccproxy stopped | `lsof -nP -iTCP:8765 -sTCP:LISTEN` | no listener | PASS |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|-------------|-------------|--------|----------|
| PAR-04 | 260924-tdp-PLAN.md | Proposer detective mode by default, >=4 traces read before proposing | SATISFIED (extended) | Live detective run on gpt-6-luna read train-1..train-4 plus wiki files before an applied proposal |

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| (modified src/scripts files) | - | TBD/FIXME/XXX/TODO/HACK | none found | - |
| src/asme/model_client.py | `_validated_header_pairs` | Values outside latin-1 (such as `€`) pass validation, then raise a raw `UnicodeEncodeError` at send, which `_send` does not wrap. Confirmed on main. | Info | This is the same kind of late failure that T-260924-04 fixed for CR/LF. The must-have only lists CR/LF/NUL, so it does not block. |
| src/asme/model_client.py | `RESERVED_HEADER_NAMES` | Framing headers (Host, Content-Length, Transfer-Encoding, Connection) are not reserved, so an operator can override them and send a malformed request | Info | The input is operator-only and not a secret path. Not a must-have. |

### Human Verification Required

None.

### Gaps Summary

None. All 7 must-haves hold on main at 522fce5. Advisory notes for follow-up, none of which block:
1. A full Maintainer iteration on the ccproxy route is still unproven, because of the ccproxy adapter 502 (already in the SUMMARY follow-ups).
2. The full-suite log came from the worktree before the last two commits. Equivalence to main is inferred from the collected count, the targeted re-run, and the zero-diff merge.
3. Non-latin-1 header values and framing-header overrides are not validated (Info).

---

_Verified: 2026-09-25T02:30:00Z_
_Verifier: Claude (gsd-verifier)_
