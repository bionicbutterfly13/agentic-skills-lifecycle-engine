---
phase: 260924-tdp-chatclient-extra-headers-for-ccproxy-cod
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - src/asme/model_client.py
  - scripts/run_proposer.py
  - scripts/run_maintainer.py
  - tests/test_model_client.py
  - tests/test_run_proposer.py
  - tests/test_run_maintainer.py
  - .planning/quick/260924-tdp-chatclient-extra-headers-for-ccproxy-cod/260924-tdp-SMOKE.md
autonomous: true
requirements: [PAR-04]

estimate:
  tokens: 80000
  raw_tokens: 80000
  tasks: 3
  confidence: low

must_haves:
  truths:
    - "With no --header option and no extra_headers argument, ChatClient sends exactly the request it sent before this change: header set {Content-Type: application/json} plus Authorization: Bearer <key> only when an env API key is set, and the same JSON body bytes. A golden test pins both."
    - "A repeatable --header NAME:VALUE option on scripts/run_maintainer.py and scripts/run_proposer.py reaches the model endpoint as an HTTP request header on every chat-completions request, and a user-agent supplied this way replaces urllib's default Python-urllib User-Agent on the wire (loopback-server test)."
    - "An Authorization, Proxy-Authorization, or Content-Type header supplied through --header or ChatClient(extra_headers=...) is refused before any workspace access or network request: the driver exits with argparse status 2, ChatClient raises ModelClientError, and no error message echoes any user-supplied header text."
    - "Header values containing CR, LF, or NUL, header names that are not RFC 9110 tokens, and case-insensitive duplicate names are refused with ModelClientError."
    - "Extra headers never enter the request body, and ChatClient's response handling is unchanged: it neither synthesizes nor alters token usage."
    - "The full offline suite exits 0, measured by pytest's own exit code (appended to the suite log as EXIT=<code> and gated by Task 2's verify), with no new file left undeclared in MANIFEST.in."
    - "A live smoke against ccproxy 0.2.10 /codex/v1 with model gpt-6-luna and the three Codex identity headers ran one Maintainer call and one detective-mode Proposer run through the real driver CLIs. 260924-tdp-SMOKE.md records HTTP outcome, whether tool_calls came back, and usage exactly as the endpoint returned it (zeros stay zeros), and ccproxy is stopped afterwards. Task 3's verify fails if the driver outputs, the probe response, or the record is missing."
  artifacts:
    - path: src/asme/model_client.py
      provides: "ChatClient(extra_headers=...), parse_header_specs(), RESERVED_HEADER_NAMES, construction-time header validation"
      contains: "extra_headers"
    - path: scripts/run_proposer.py
      provides: "--header option parsed before workspace construction, passed to ChatClient"
      contains: "--header"
    - path: scripts/run_maintainer.py
      provides: "--header option parsed before workspace construction, passed to ChatClient"
      contains: "--header"
    - path: tests/test_model_client.py
      provides: "golden default-unchanged, pass-through, loopback wire, and refusal tests"
      contains: "test_default_request_headers_and_body_are_unchanged"
    - path: tests/test_run_proposer.py
      provides: "CLI header pass-through, default, and Authorization-refusal tests through run_proposer.main()"
      contains: "test_cli_header_reaches_the_chat_client"
    - path: tests/test_run_maintainer.py
      provides: "CLI header pass-through, default, and Authorization-refusal tests through run_maintainer.main()"
      contains: "test_cli_header_reaches_the_chat_client"
    - path: .planning/quick/260924-tdp-chatclient-extra-headers-for-ccproxy-cod/260924-tdp-SMOKE.md
      provides: "live-smoke record: one key: value line per observed field, no secrets"
      contains: "probe_usage: "
  key_links:
    - from: "scripts/run_proposer.py main()"
      to: "asme.model_client.parse_header_specs -> ChatClient(extra_headers=...)"
      via: "args.header parsed right after parse_args; ModelClientError -> parser.error (exit 2)"
      pattern: "parse_header_specs"
    - from: "scripts/run_maintainer.py main()"
      to: "asme.model_client.parse_header_specs -> ChatClient(extra_headers=...)"
      via: "args.header parsed right after parse_args; ModelClientError -> parser.error (exit 2)"
      pattern: "parse_header_specs"
    - from: "ChatClient._headers()"
      to: "urllib.request.Request(headers=...) in ChatClient._post"
      via: "validated extras appended after the unchanged Content-Type/Authorization logic"
      pattern: "_extra_headers"
---

<objective>
Let ChatClient (src/asme/model_client.py) send optional extra HTTP headers, configured
from the Maintainer and Proposer driver CLIs through a repeatable `--header NAME:VALUE`
option, so both drivers can reach gpt-6-luna through ccproxy's /codex/v1 route on the
ChatGPT subscription. Then prove it live with one Maintainer call and one detective-mode
Proposer run.

Purpose: the route is verified (2026-09-24, ccproxy 0.2.10, `[plugins.codex]
model_mappings = []`, `inject_detection_payload = false`). Without Codex identity
headers it answers HTTP 400 "The 'gpt-6-luna' model is not supported when using Codex
with a ChatGPT account". With `originator: codex_cli_rs`, `version: 0.155.1`, and
`user-agent: codex_cli_rs/0.155.1 (probe)` it answers HTTP 200 (content "LUNA_OK",
model gpt-6-luna, usage prompt_tokens=0 and completion_tokens=0). ChatClient._headers
(src/asme/model_client.py:77) sends only Content-Type and Authorization today, so
neither driver can reach the model.

Output: ChatClient `extra_headers` keyword with construction-time validation, a
`parse_header_specs()` helper, `--header` on both drivers, offline tests, a green full
suite, and a live-smoke record in the SUMMARY.

Design choices (Claude's discretion, no CONTEXT.md exists for this quick task):
- The option carries header names and values only. The API key stays env-only through
  `--api-key-env` / LIFECYCLE_MODEL_API_KEY. Authorization and Proxy-Authorization
  (RFC 9110 credential headers) and Content-Type (owned by the client, which always
  sends JSON) are reserved and refused.
- No Codex or ccproxy identity values are hardcoded anywhere in src/ or scripts/. They
  are supplied only at the command line, so default behavior stays byte-identical.
- Usage: ChatClient returns only content, tool_calls, and finish_reason, and drops
  `usage`. This task does not change response handling. The live smoke observes `usage`
  from one raw probe on the same route and headers and reports it verbatim.

Out of scope (orchestrator-scoped, recorded as follow-ups in the SUMMARY):
scripts/run_rollout.py and adapters/direct (DirectAdapter has its own `_headers`, so the
Inference role cannot reach gpt-6-luna through ccproxy yet); persisting per-call token
usage into run evidence.

Source coverage audit (GOAL / REQ / RESEARCH / CONTEXT):

| Source item | Covered by |
|---|---|
| GOAL: drivers reach gpt-6-luna via ccproxy /codex/v1 | Tasks 1, 2 (code), Task 3 (live proof) |
| REQ PAR-04: Maintainer/Proposer drivers against a live model | Tasks 1-3 (extends the PAR-04 drivers; PAR-04 stays `[x]`, no REQUIREMENTS.md edit) |
| Constraint: no secrets via CLI values; Authorization refused | Task 1 (validation + Proposer CLI), Task 2 (Maintainer CLI) |
| Constraint: default byte-identical headers and body | Task 1 golden test |
| Constraint: do not fabricate token counts | Task 1 (response handling unchanged), Task 3 (verbatim usage) |
| Constraint: minimal repeatable `--header NAME:VALUE`, argparse style | Tasks 1, 2 |
| Acceptance: pass-through, default-unchanged, Authorization-refusal unit tests | Tasks 1, 2 |
| Acceptance: full suite exit 0 via pytest's own exit code, no extra -q, timeout 2400 | Task 2 |
| Acceptance: MANIFEST.in declares any new file | Task 2 (no new files planned; distribution test re-run) |
| Live smoke: ccproxy start, one Maintainer + one detective Proposer call, tool_calls + usage report, ccproxy stopped | Task 3 |
| RESEARCH / CONTEXT D-XX | none exist for this quick task |
</objective>

<execution_context>
@~/.claude/gsd-core/workflows/execute-plan.md
@~/.claude/gsd-core/templates/summary.md
</execution_context>

<context>
@AGENTS.md
@src/asme/model_client.py
@scripts/run_proposer.py
@scripts/run_maintainer.py
@tests/test_model_client.py
@tests/test_run_proposer.py
@tests/test_run_maintainer.py
@tests/test_terminal_paths.py

<interfaces>
Verified at planning time (2026-09-24, main 835e853):
- ChatClient.__init__(*, base_url, model_id, api_key=None, timeout_seconds=1800.0, temperature=0.0, transport=None). All keyword-only.
- ChatClient._headers() returns {"Content-Type": "application/json"} and adds "Authorization": f"Bearer {api_key}" only when api_key is truthy. ChatClient._post builds urllib.request.Request(url, data=json.dumps(body).encode("utf-8"), headers=self._headers(), method="POST").
- Default request body for complete(messages) without tools: {"model", "messages", "temperature", "stream": False} in that insertion order; "tools" is added only when tools is not None.
- ModelClientError(ContractError) is the module's error type.
- urllib.request.Request stores header names capitalized ("Content-type", "Originator", "User-agent"). Compare headers case-insensitively in tests, e.g. {name.lower(): value for name, value in request.header_items()}.
- On the wire, a supplied "user-agent" replaces urllib's default "Python-urllib/3.x" User-Agent (verified with a loopback server). Request() itself does NOT reject CR/LF in values; http.client only fails later at send time with a raw ValueError that ChatClient._send does not catch.
- scripts/run_maintainer.py main() builds its argparse parser inline, then DomainWorkspace, EvolutionWorkflow, ChatClient, then calls workflow.sample_train(), reads maintainer-input.json, and calls module-global run_maintainer_loop(workflow=..., client=..., run_dir=..., payload=...).
- tests/test_run_maintainer.py::test_api_key_is_read_from_environment_not_a_cli_flag inspects inspect.getsource(run_maintainer.main) for "--api-key-env". The parser MUST stay inside main().
- scripts/run_proposer.py main() calls build_arg_parser().parse_args(), then build_workspace_and_client(args), then run_dir_for(workspace), then module-global run_detective(workflow, client, run_dir, max_turns=...) or run_single_shot(workflow, client, run_dir).
- tests/test_run_maintainer.py::_harness(tmp_path) already calls sample_train(), so it cannot feed run_maintainer.main(), which calls sample_train() itself. For main() tests, build TerminalHarness(tmp_path, case_id=..., max_iterations=2), then .baseline(0.25) and .run_phase("train", 1.0), and do not call sample_train.
- tests/test_run_proposer.py::_harness_at_needs_proposal(tmp_path) returns a harness at NEEDS_PROPOSAL with domain_id "terminal-run-proposer" and workspace root tmp_path / "workspace".
- TerminalHarness domain_id is f"terminal-{case_id.lower()}" (DomainWorkspace.domain_id), workspace root is root / "workspace".
- pyproject.toml: addopts = "-q", pythonpath = ["src"], testpaths = ["tests"].
- Tooling present: ccproxy 0.2.10 at /Users/manisaintvictor/.local/bin/ccproxy; GNU timeout at /usr/local/bin/timeout; python3 3.14.6 with pytest 9.1.1; no listener on port 8765 at planning time.
</interfaces>
</context>

<tasks>

<!-- planner-discipline-allow: codex_cli_rs -->

<task type="tracer" tdd="true">
  <name>Task 1: End-to-end --header on the Proposer driver: CLI -> parse_header_specs -> ChatClient(extra_headers) -> request headers on the wire</name>
  <files>src/asme/model_client.py, scripts/run_proposer.py, tests/test_model_client.py, tests/test_run_proposer.py</files>
  <behavior>
    tests/test_model_client.py (extend FakeTransport to also record "headers" as a lower-cased-name dict from request.header_items() and "data" as the raw request.data bytes; existing tests keep reading only "url"/"body"):
    - test_default_request_headers_and_body_are_unchanged: a client built without extra_headers, and one built with extra_headers=None, and one with extra_headers={}, each send headers exactly {"content-type": "application/json"}; with api_key="k" exactly {"content-type": "application/json", "authorization": "Bearer k"}; request.data equals json.dumps({"model": MODEL, "messages": msgs, "temperature": 0.0, "stream": False}).encode("utf-8") byte for byte.
    - test_extra_headers_are_sent_and_body_is_unchanged: extra_headers {"originator": "codex_cli_rs", "version": "0.155.1", "user-agent": "codex_cli_rs/0.155.1 (probe)"} all appear with exact values; the request body is identical to the no-extras body; no "authorization" appears when api_key is None.
    - test_extra_headers_reach_the_wire_and_override_default_user_agent: a stdlib http.server.ThreadingHTTPServer bound to 127.0.0.1 port 0 (daemon thread, shut down in finally) records the received headers and returns a canned chat-completion JSON. The real urllib path (no transport, timeout_seconds=5) delivers originator, version, and User-Agent "codex_cli_rs/0.155.1 (probe)" (not Python-urllib). A second call without extras shows the default Python-urllib User-Agent and no Authorization. Loopback only, no external network.
    - test_extra_headers_reject_reserved_names (parametrized over "Authorization", "authorization", "AUTHORIZATION", "Proxy-Authorization", "Content-Type"): ChatClient(extra_headers={name: "sk-should-not-echo"}) raises ModelClientError and "sk-should-not-echo" is not in str(exc).
    - test_extra_headers_reject_line_breaks_and_invalid_names: values containing "\r", "\n", or "\x00", and names that are empty, contain a space, or contain ":", raise ModelClientError whose message does not contain the offending user text.
    - test_extra_headers_reject_case_insensitive_duplicates: {"Originator": "a", "originator": "b"} raises ModelClientError.
    - test_parse_header_specs_*: None -> {}; ["originator: codex_cli_rs"] -> {"originator": "codex_cli_rs"} (split on the FIRST colon, name and value whitespace-stripped); a value containing colons survives intact ("x-url: http://h:1/p"); a spec with no colon raises ModelClientError without echoing the spec; a repeated name (any case) raises; a reserved name raises.
    tests/test_run_proposer.py (monkeypatch.delenv("LIFECYCLE_MODEL_API_KEY", raising=False) in each):
    - test_cli_header_reaches_the_chat_client: harness from _harness_at_needs_proposal(tmp_path); monkeypatch sys.argv to run run_proposer.main() with --domain terminal-run-proposer --domain-root tmp_path/"workspace" --model test-model and three --header options; monkeypatch run_proposer.run_detective with a recorder that captures the client and returns None; main() returns 0; the captured client's _headers(), compared case-insensitively, contain the three extras and no authorization.
    - test_cli_without_header_keeps_default_client_headers: same path with no --header; the captured client's _headers() == {"Content-Type": "application/json"}.
    - test_cli_refuses_authorization_header_without_echoing_value: --header "Authorization: Bearer sk-test-should-not-echo" makes main() raise SystemExit with code 2; capsys stderr contains "usage:" and names the reserved header (case-insensitive "authorization"), and does not contain "sk-test-should-not-echo"; run_detective is never called.
  </behavior>
  <action>
RED first: add the behavior tests above and run them to confirm they fail. Then implement.

In src/asme/model_client.py:
- Add module constant RESERVED_HEADER_NAMES = frozenset of lower-case "authorization", "proxy-authorization", "content-type". Comment it: credentials stay env-only via the driver's --api-key-env; Content-Type is owned by this client because it always sends JSON.
- Add a private validator, e.g. _validated_extra_headers(headers: Mapping[str, str]) -> dict[str, str]. It returns a NEW plain dict that preserves insertion order and refuses the following with ModelClientError: non-str names or values; names that do not fully match the RFC 9110 token grammar (the characters !#$%&'*+-.^_`|~, digits, and ASCII letters, one or more); values containing "\r", "\n", or "\x00"; a name whose lower-case form is in RESERVED_HEADER_NAMES; and a name whose lower-case form repeats an earlier one. Error messages identify the offending header ONLY by its 1-based position ("extra header #2 ...") and, for reserved names, by the canonical reserved name taken from RESERVED_HEADER_NAMES. They never interpolate any user-supplied name, value, or spec text, because a mistyped secret could otherwise reach stderr or logs. For reserved Authorization, the message says the API key comes only from the environment via --api-key-env.
- Add public parse_header_specs(specs: Sequence[str] | None) -> dict[str, str]. None or empty returns {}. Each spec splits on its FIRST ":" into name and value, and both are whitespace-stripped. A spec without ":" raises ModelClientError by position without echoing the spec. The resulting mapping passes through _validated_extra_headers. Build it so an exact-duplicate name is caught: collect pairs and detect repeats before collapsing into a dict.
- ChatClient.__init__ gains keyword-only extra_headers: Mapping[str, str] | None = None, stored as self._extra_headers = _validated_extra_headers(extra_headers or {}). It is validated at construction, before any request exists, which gives defense in depth for Python API callers who bypass the CLI.
- ChatClient._headers(): keep the existing two statements byte-for-byte (Content-Type, then Authorization only when api_key is truthy), then apply self._extra_headers via headers.update(...) before returning. With no extras, update is a no-op, so the default dict is identical to today's. Do not touch complete(), the request body, _post, or _send. Response handling, including the absence of usage in the returned mapping, stays unchanged, so no token counts are synthesized.
- Update the module docstring with one sentence: callers may pass extra request headers (for endpoints that gate on client identity), and credentials never travel through them.

In scripts/run_proposer.py:
- Import parse_header_specs and ModelClientError from asme.model_client.
- build_arg_parser(): add "--header" with action="append", default=None, metavar="NAME:VALUE", and a help string saying it is an extra HTTP header sent with every model request and may be repeated; that values are visible in the process list and shell history, so never pass secrets; and that Authorization is refused because the key comes only from --api-key-env.
- build_workspace_and_client(args, *, extra_headers: Mapping[str, str] | None = None): pass extra_headers through to ChatClient(...).
- main(): parser = build_arg_parser(); args = parser.parse_args(); then, BEFORE build_workspace_and_client, compute extra_headers = parse_header_specs(args.header) inside try/except ModelClientError and call parser.error(str(exc)) on failure (argparse exit status 2). Then call build_workspace_and_client(args, extra_headers=extra_headers). Never print or log header values anywhere in the driver.
- Add one Usage example line to the module docstring showing repeated --header options in the generic form --header "NAME: VALUE". Do not put real client-identity values in the docstring: the shipped-code gate in <verification> requires zero occurrences of the Codex originator value under src/ and scripts/, and those values drift by Codex release.

Do not add any Codex/ccproxy header name or value as a default, constant, or example in src/ or scripts/. Do not create new files; all tests go in the existing test modules, so MANIFEST.in needs no change.
  </action>
  <verify>
    <automated>PYTHONPATH=src python3 -m pytest tests/test_model_client.py tests/test_run_proposer.py -x -p no:cacheprovider</automated>
  </verify>
  <done>ChatClient accepts validated extra_headers. Default headers and body are byte-identical (golden test). Extras reach the wire and override the default User-Agent (loopback test). Reserved, malformed, and duplicate headers are refused without echoing user text. run_proposer.py --header flows from the CLI to the ChatClient used by run_detective, and an Authorization header exits 2 before workspace construction. All tests in tests/test_model_client.py and tests/test_run_proposer.py pass.</done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: Maintainer driver --header wiring, then the full offline suite</name>
  <files>scripts/run_maintainer.py, tests/test_run_maintainer.py</files>
  <behavior>
    tests/test_run_maintainer.py (monkeypatch.delenv("LIFECYCLE_MODEL_API_KEY", raising=False) in each):
    - test_cli_header_reaches_the_chat_client: TerminalHarness(tmp_path, case_id="RUN-MAINTAINER-CLI", max_iterations=2), then .baseline(0.25) and .run_phase("train", 1.0), with NO sample_train, because main() performs it. Monkeypatch sys.argv for run_maintainer.main() with --domain harness.workspace.domain_id --domain-root tmp_path/"workspace" --model test-model and the three --header options. Monkeypatch run_maintainer.run_maintainer_loop with a keyword-arg recorder that captures client and returns 1. main() returns 0, and the captured client's _headers(), compared case-insensitively, contain the three extras and no authorization.
    - test_cli_without_header_keeps_default_client_headers: same path without --header; the captured client's _headers() == {"Content-Type": "application/json"}.
    - test_cli_refuses_authorization_header_without_echoing_value: --header "Authorization: Bearer sk-test-should-not-echo" makes main() raise SystemExit with code 2; stderr contains "usage:" and (case-insensitive) "authorization" and not "sk-test-should-not-echo"; run_maintainer_loop is never called.
    - The existing test_api_key_is_read_from_environment_not_a_cli_flag passes unchanged.
  </behavior>
  <action>
RED first: add the three tests and confirm they fail.

In scripts/run_maintainer.py:
- Import parse_header_specs and ModelClientError from asme.model_client.
- Inside main()'s existing inline parser, add the same "--header" argument as run_proposer.py: action="append", default=None, metavar="NAME:VALUE", and the same help text. Keep the parser inside main() because test_api_key_is_read_from_environment_not_a_cli_flag inspects main()'s source. Do not add any flag whose literal is the bare api-key flag.
- Right after args = parser.parse_args() and BEFORE DomainWorkspace is constructed, compute extra_headers = parse_header_specs(args.header) inside try/except ModelClientError and call parser.error(str(exc)). Pass extra_headers=extra_headers to ChatClient(...). Never print header values.
- Add one Usage example line to the module docstring with repeated --header options in the same generic --header "NAME: VALUE" form as run_proposer.py, with no real client-identity values.

Then run the full offline suite, which takes more than 10 minutes. Use the fixed log path LOG="${TMPDIR:-/tmp}/lifecycle-260924-tdp/full-suite.log", outside the repo, so Task 2's verify can read it. mkdir -p its directory and rm -f any earlier LOG first, so a stale log cannot pass the gate. Launch with the Bash tool's run_in_background: PYTHONPATH=src timeout 2400 python3 -m pytest -p no:cacheprovider > "$LOG" 2>&1; echo "EXIT=$?" >> "$LOG". That makes the log's last line pytest's own exit code (or 124 on timeout). Wait for that EXIT= line to appear. Do NOT add -q, because pyproject addopts already has it. Do NOT pipe pytest through tee, tail, or grep, because that replaces pytest's exit code. The known slow test test_hf_a18_route_hash_drift_alone_hits_dedicated_route_refusal needs the 2400 s budget. Record the final pytest line (passed/skipped counts). The pre-change baseline was 730 passed, 1 skipped. If any test fails, determine whether this change caused it before touching anything. If the cause is clear, make one targeted fix. Otherwise stop and report.

Confirm that no new file was created (git status shows only modified tracked files among the six planned). Re-run tests/test_distribution.py explicitly, since it enforces MANIFEST.in family completeness.
  </action>
  <verify>
    <automated>PYTHONPATH=src python3 -m pytest tests/test_run_maintainer.py tests/test_distribution.py -x -p no:cacheprovider && grep -qx 'EXIT=0' "${TMPDIR:-/tmp}/lifecycle-260924-tdp/full-suite.log" && echo FULL_SUITE_EXIT_0</automated>
  </verify>
  <done>run_maintainer.py --header flows from the CLI to the ChatClient passed to run_maintainer_loop. An Authorization header exits 2 without echoing its value. The pre-existing api-key test passes unchanged. The full-suite log ends with EXIT=0 from pytest's own exit code, which the verify gates on, and its passed/skipped counts are recorded for the SUMMARY. git status shows no untracked source or test file.</done>
</task>

<task type="auto">
  <name>Task 3: Live smoke through ccproxy /codex/v1 with gpt-6-luna: one Maintainer call, one detective-mode Proposer run, one raw usage probe</name>
  <files>.planning/quick/260924-tdp-chatclient-extra-headers-for-ccproxy-cod/260924-tdp-SMOKE.md (the only repo file; raw smoke artifacts stay outside the repo)</files>
  <precondition>ccproxy 0.2.10 is on PATH with working ChatGPT-subscription Codex credentials (verified by the orchestrator's 2026-09-24 probe), port 8765 has no listener, and Tasks 1-2 are committed with the suite green.</precondition>
  <action>
Raw artifacts go in the fixed throwaway directory SMOKE="${TMPDIR:-/tmp}/lifecycle-260924-tdp/smoke", outside the repository. Use this exact path because Task 3's verify reads it. rm -rf that one smoke directory first and then mkdir -p it, so no earlier run's outputs can pass the gate. Nothing from SMOKE is committed.

1. Write SMOKE/ccproxy.toml containing only a [plugins.codex] table with model_mappings = [] and inject_detection_payload = false, the two settings the orchestrator verified. Confirm port 8765 is free with lsof -nP -iTCP:8765 -sTCP:LISTEN. If anything is listening, stop and report. Do not kill a process this task did not start.

2. Start ccproxy serve --config SMOKE/ccproxy.toml --port 8765 in the background, with stdout and stderr redirected to SMOKE/ccproxy.log, and record its PID. Startup takes about 45 s: poll for a listener on 8765 for up to 120 s. Never cat or paste ccproxy.log. If diagnosis is needed, show only lines that survive grep -v -i -E 'authorization|bearer|token|cookie'. If no listener appears within 120 s, kill the recorded PID, report the failure, and stop this task.

3. Prepare two independent throwaway domains with a short Python prep script written into SMOKE (not the repo), run from the repo root with PYTHONPATH=src:tests:scripts:
   - Domain M: create SMOKE/maintainer, then build TerminalHarness(SMOKE/maintainer, case_id="LUNA-M", max_iterations=2) from test_terminal_paths, then call .baseline(0.25) and .run_phase("train", 1.0). Do NOT call sample_train, because run_maintainer.main() performs it.
   - Domain P: create SMOKE/proposer and call test_run_proposer._harness_at_needs_proposal(SMOKE/proposer). It reaches NEEDS_PROPOSAL with 4 train traces.
   - Print each domain_id and workspace root (root/"workspace"). Use the printed values below rather than guessing.
   Separate domains mean a Maintainer validation failure cannot block the Proposer check.

4. Maintainer call through the real CLI, run from the repo root with LIFECYCLE_MODEL_API_KEY unset (env -u LIFECYCLE_MODEL_API_KEY), matching the verified probe, which sent no Authorization. Wrap it in timeout 900: PYTHONPATH=src python3 scripts/run_maintainer.py --domain <M domain_id> --domain-root <M workspace root> --base-url http://127.0.0.1:8765/codex/v1 --model gpt-6-luna --header "originator: codex_cli_rs" --header "version: 0.155.1" --header "user-agent: codex_cli_rs/0.155.1 (probe)". Keep the header values exactly as verified. Capture stdout/stderr to SMOKE/maintainer.out, then append the exit code to it as a final line EXIT=<code>. Record: exit code; the "attempt n/3 succeeded|failed" lines; whether maintainer-attempt-1.txt under the M runs directory is non-empty (non-empty means the route returned HTTP 200 with content); and for failures, the first line of the error. A ModelClientError "HTTP <code>" is a route/transport result. A ContractError after 3 attempts is a model-output validation result. Report both kinds verbatim, and do not change code to chase either.

5. Proposer detective run through the real CLI, with the same env, timeout, base URL, model, and three headers, plus --domain <P domain_id> --domain-root <P workspace root> --mode detective. Capture output to SMOKE/proposer.out, then append the exit code to it as a final line EXIT=<code>. A successful detective run prints nothing, so the EXIT line is what proves the run happened. Locate proposer-reads-log.json under the P runs directory (find SMOKE/proposer -name proposer-reads-log.json). Record: exit code; the final error line if any (turn cap, finish refused, or HTTP code); the number of reads-log entries and how many are refused; and whether the run finished with an applied proposal. Tool_calls came back on this route if and only if the reads log has one or more entries or the run finished. An empty reads log with a turn-cap error means no tool_calls came back.

6. Raw usage probe. This is observation only, because ChatClient intentionally drops usage and the drivers therefore cannot show it. Use python3 to write SMOKE/probe-body.json with model gpt-6-luna, stream false, one user message asking the model to call read_file with path wiki/index.md, and tools set to [run_proposer.READ_FILE_TOOL_SCHEMA]. POST it with curl -sS to http://127.0.0.1:8765/codex/v1/chat/completions, with Content-Type application/json and the same three headers and no Authorization, writing the body to SMOKE/probe.json and printing the HTTP code. Extract with python3: the HTTP code; whether choices[0].message.tool_calls is present, with its count and function names; finish_reason; and the usage object printed verbatim with json.dumps. Record it exactly as returned: zeros stay zeros, and nothing is estimated or back-filled.

7. Stop ccproxy: kill the recorded PID, wait for it to exit, and confirm lsof shows no listener on 8765. Do this even when an earlier step failed.

8. After step 7, write the record file .planning/quick/260924-tdp-chatclient-extra-headers-for-ccproxy-cod/260924-tdp-SMOKE.md. It has a one-line heading "Live smoke (ccproxy 0.2.10, gpt-6-luna)", followed by exactly one line per key, each starting at column 0 as "key: value": smoke_dir (the absolute SMOKE path), ccproxy_version, maintainer_exit, maintainer_outcome (the attempt lines, or the first error line), proposer_exit, proposer_outcome, proposer_reads_log (entry count and refused count), tool_calls_driver (yes or no, with the basis), probe_http, tool_calls_probe (yes with count and function names, or no), probe_finish_reason, probe_usage (the usage object as verbatim JSON, followed by "(as reported by the endpoint; not measured, not estimated)"), and ccproxy_stopped (yes, once lsof confirms no listener). Include no ccproxy log lines and no bearer values. The SUMMARY's "Live smoke" section links this record and restates its findings. The SUMMARY also carries a Follow-ups list: header support for scripts/run_rollout.py / adapters/direct (the Inference role still cannot reach this route), and persisting per-call usage into run evidence.
  </action>
  <verify>
    <automated>R=.planning/quick/260924-tdp-chatclient-extra-headers-for-ccproxy-cod/260924-tdp-SMOKE.md; S="${TMPDIR:-/tmp}/lifecycle-260924-tdp/smoke"; grep -q '^EXIT=' "$S/maintainer.out" && grep -q '^EXIT=' "$S/proposer.out" && test -s "$S/probe.json" && grep -q '^maintainer_exit: ' "$R" && grep -q '^proposer_exit: ' "$R" && grep -q '^tool_calls_driver: ' "$R" && grep -q '^probe_http: ' "$R" && grep -q '^tool_calls_probe: ' "$R" && grep -q '^probe_usage: ' "$R" && grep -q '^ccproxy_stopped: yes' "$R" && ! grep -Eqi 'bearer [A-Za-z0-9._~+/-]{12,}' "$R" && ! lsof -nP -iTCP:8765 -sTCP:LISTEN >/dev/null 2>&1 && echo SMOKE_RECORDED</automated>
  </verify>
  <done>Both driver CLIs were run live against ccproxy /codex/v1 with gpt-6-luna and the three headers; their outputs end in EXIT= lines. The raw probe response is saved. 260924-tdp-SMOKE.md holds every required key, with usage verbatim and no bearer material. ccproxy is stopped and port 8765 has no listener. A route refusal (HTTP 4xx/5xx) is a recorded result: the drivers still wrote their EXIT lines and probe.json holds the error body. If ccproxy cannot start, the smoke did not execute, so the verify fails by design and the task is reported as blocked, with the filtered status and ccproxy confirmed stopped.</done>
</task>

</tasks>

<threat_model>
ASVS level 1; block on high. No package installs in this plan, so the supply-chain row is not applicable.

## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| operator CLI -> driver | `--header` specs are operator input. They are visible in the process list and shell history, so they must never carry credentials. |
| driver -> model endpoint | Extra headers leave the process on every chat-completions request. In the smoke, the endpoint is loopback ccproxy, which forwards to the ChatGPT backend under the operator's subscription. |
| model endpoint -> driver / evidence | Response content, tool_calls, and usage are untrusted reports. Usage zeros from the Codex route are the endpoint's claim, not a measurement. |
| ccproxy process -> smoke artifacts | ccproxy logs may contain upstream bearer tokens. Smoke artifacts must not carry them into the SUMMARY or the repo. |

## STRIDE Threat Register

| Threat ID | Category | Component | Severity | Disposition | Mitigation Plan |
|-----------|----------|-----------|----------|-------------|-----------------|
| T-260924-01 | Information Disclosure | `--header` carrying an API key (Authorization / Proxy-Authorization) | high | mitigate | parse_header_specs and ChatClient._validated_extra_headers refuse RESERVED_HEADER_NAMES case-insensitively, before workspace access or any request. The key stays env-only via --api-key-env. Help text warns that values are visible in the process list. Tests in all three test modules assert the refusal (exit 2 at the CLI). |
| T-260924-02 | Information Disclosure | error messages echoing a mistyped secret | high | mitigate | Validation errors identify headers only by 1-based position and canonical reserved name and never interpolate user text. Tests assert the sentinel secret string is absent from str(exc) and from argparse stderr. |
| T-260924-03 | Information Disclosure | vendor-specific key headers (e.g. x-api-key) passed via `--header` | medium | accept | Name-based detection of arbitrary vendor key headers is unreliable. The help text states that header values are visible and must never be secrets, and the supported key path is --api-key-env. |
| T-260924-04 | Tampering | CR/LF/NUL header injection or non-token names | medium | mitigate | Values with \r, \n, or \x00 and names outside the RFC 9110 token grammar are refused at construction with ModelClientError, instead of surfacing later as an uncaught http.client ValueError. Covered by test_extra_headers_reject_line_breaks_and_invalid_names. |
| T-260924-05 | Tampering | extra header overriding client-owned Content-Type or colliding by case | medium | mitigate | Content-Type is reserved, and case-insensitive duplicates are refused, so the JSON request contract and header determinism hold. Covered by the reserved and duplicate tests. |
| T-260924-06 | Spoofing | Codex client-identity headers presented to ccproxy / the ChatGPT backend | medium | accept | This is Dr. Mani's settled routing choice (gpt-6-luna via the subscription route). The identity values are opt-in CLI input only, and no Codex/ccproxy identity is hardcoded or defaulted in src/ or scripts/, so default traffic is byte-identical to today (golden test). |
| T-260924-07 | Repudiation | fabricated or back-filled token usage in evidence | medium | mitigate | ChatClient response handling is unchanged and synthesizes no usage. The smoke reports the raw probe's usage object verbatim, labeled as endpoint-reported, with zeros kept as zeros. |
| T-260924-08 | Information Disclosure | ccproxy debug log bearer tokens leaking into SUMMARY or chat | high | mitigate | ccproxy output goes to a file outside the repo and is never pasted whole. Any diagnostic view is filtered with grep -v -i on authorization/bearer/token/cookie. The smoke record and the SUMMARY hold only status codes and parsed fields. Task 3's verify and the verification grep refuse any bearer-token-shaped string in the record and the SUMMARY. |
| T-260924-09 | Denial of Service | ccproxy left running or port 8765 occupied after the smoke | low | mitigate | The PID is recorded at start, killed in step 7 even on earlier failure, and the Task 3 automated check confirms no listener on 8765. A foreign process on 8765 is never killed; the task stops and reports instead. |
</threat_model>

<verification>
Targeted, after Tasks 1-2:

```
PYTHONPATH=src python3 -m pytest tests/test_model_client.py tests/test_run_proposer.py tests/test_run_maintainer.py tests/test_distribution.py -x -p no:cacheprovider
```

Full offline suite (background; more than 10 minutes; pytest's own exit code; no extra -q):

```
LOG="${TMPDIR:-/tmp}/lifecycle-260924-tdp/full-suite.log"; mkdir -p "$(dirname "$LOG")"; rm -f "$LOG"
PYTHONPATH=src timeout 2400 python3 -m pytest -p no:cacheprovider > "$LOG" 2>&1; echo "EXIT=$?" >> "$LOG"
```

The log's last line must be EXIT=0 (Task 2's verify gates on it with grep -qx).

Default-unchanged guard (the two original _headers() statements are still present):

```
grep -v '^\s*#' src/asme/model_client.py | grep -c 'headers\["Authorization"\] = f"Bearer {self._api_key}"'
```

Must print 1.

No hardcoded Codex identity in shipped code:

```
grep -rn --include='*.py' 'codex_cli_rs' src scripts | wc -l
```

Must print 0.

SUMMARY secret hygiene (after the SUMMARY is written):

```
grep -Eci 'bearer [A-Za-z0-9._~+/-]{12,}' .planning/quick/260924-tdp-chatclient-extra-headers-for-ccproxy-cod/260924-tdp-SUMMARY.md
```

Must print 0.
</verification>

<success_criteria>
- ChatClient(extra_headers=...) and parse_header_specs() exist in src/asme/model_client.py. Reserved (Authorization, Proxy-Authorization, Content-Type), malformed, and duplicate headers are refused at construction without echoing user text.
- With no extras, the header dict and request body bytes match the pre-change golden values exactly.
- scripts/run_maintainer.py and scripts/run_proposer.py accept a repeatable --header NAME:VALUE, parse it before any workspace access, exit 2 on refusal, and pass the headers to ChatClient.
- New tests live in the existing test modules, and MANIFEST.in needs no change; tests/test_distribution.py passes.
- The full offline suite prints EXIT=0 from pytest's own exit code.
- 260924-tdp-SMOKE.md and the SUMMARY hold the live-smoke record (Maintainer outcome, detective Proposer outcome with reads-log counts, tool_calls yes/no, usage verbatim) and the follow-ups (run_rollout.py/DirectAdapter headers; persisting usage). ccproxy is stopped.
</success_criteria>

<output>
Create `.planning/quick/260924-tdp-chatclient-extra-headers-for-ccproxy-cod/260924-tdp-SUMMARY.md` when done.
</output>
