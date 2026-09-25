# API Coverage — OpenAI-compatible chat completions via ccproxy /codex/v1

> Full coverage by default. Opt-outs are explicit, reasoned decisions.
> Surface = what ChatClient (src/asme/model_client.py) and the Maintainer/Proposer
> drivers can use on this route. This task adds request headers; every other row
> records whether the existing client already covers the capability.

| capability | decision | reason |
|---|---|---|
| chat-completions-post | INTEGRATE | |
| request-extra-headers | INTEGRATE | |
| bearer-auth-from-env | INTEGRATE | |
| tools-in-request | INTEGRATE | |
| tool-calls-in-response | INTEGRATE | |
| finish-reason | INTEGRATE | |
| temperature | INTEGRATE | |
| streaming-sse | OPT-OUT | explicitly out of scope: ChatClient is deliberately non-streaming (stream false), one complete response per call |
| usage-in-client-result | OPT-OUT | not needed yet: ChatClient drops usage by design; the live smoke reads usage from a raw probe; persisting usage is a recorded follow-up |
| multiple-choices-n | OPT-OUT | explicitly out of scope: ChatClient contract reads choices[0] only |
| extra-sampling-params | OPT-OUT | not needed: top_p, max_tokens, seed, response_format are not used by the Maintainer or Proposer drivers |
| models-list | OPT-OUT | not needed: drivers take --model explicitly |
| responses-api | OPT-OUT | explicitly out of scope: drivers are built on chat completions, and the route is verified on /chat/completions |
| embeddings | OPT-OUT | not needed: no Lifecycle role uses embeddings |
| inference-role-headers-direct-adapter | OPT-OUT | explicitly out of scope per orchestrator: scripts/run_rollout.py and adapters/direct are a recorded follow-up |
