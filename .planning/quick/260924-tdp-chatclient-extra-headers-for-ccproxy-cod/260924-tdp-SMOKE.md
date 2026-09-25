# Live smoke (ccproxy 0.2.10, gpt-6-luna)

smoke_dir: /private/var/folders/dt/s_wcpb612fg7l96x7r3fpwm80000gn/T/lifecycle-260924-tdp/smoke
ccproxy_version: ccproxy 0.2.10 (serve --config smoke/ccproxy.toml --port 8765; [plugins.codex] model_mappings = [], inject_detection_payload = false)
maintainer_exit: 1
maintainer_outcome: attempt 1/3 failed: maintainer input hash mismatch (HTTP 200 with content; maintainer-attempt-1.txt is 950 bytes; model-output validation result). Attempt 2 then ended the run with ModelClientError: HTTP 502 from http://127.0.0.1:8765/codex/v1/chat/completions (route/transport result; ccproxy logged codex_format_chain_response_failed, pydantic "1 validation error for ResponseObject: output Field required", i.e. ccproxy's Codex adapter could not convert the upstream reply). No code was changed to chase either result.
proposer_exit: 0
proposer_outcome: detective run finished with an applied proposal (action no_action, trace_ids train-1..train-4); workspace state moved NEEDS_PROPOSAL -> NEEDS_TRAIN_RUN; no error line
proposer_reads_log: 8 entries, 1 refused (wiki/skill-impact.md, absent from the virtual filesystem); turns 1-8; reads: wiki/index.md, wiki/skill-impact.md, wiki/log.md, wiki/patterns/pattern-1.md, traces/train-1, traces/train-2, traces/train-3, traces/train-4
tool_calls_driver: yes (the reads log has 8 entries and the run finished via finish())
probe_http: 200
tool_calls_probe: yes (1: read_file)
probe_finish_reason: tool_calls
probe_usage: {"completion_tokens": 0, "prompt_tokens": 0, "total_tokens": 0} (as reported by the endpoint; not measured, not estimated)
ccproxy_stopped: yes (recorded PID 42587 killed with SIGTERM and exited; lsof shows no listener on 8765)
