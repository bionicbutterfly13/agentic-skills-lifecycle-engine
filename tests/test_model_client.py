"""Offline contract tests for the core stateless chat-completions client."""

from __future__ import annotations

import http.server
import json
import threading
from typing import Any, Mapping
import urllib.error
import urllib.request

import pytest

from asme.model_client import ChatClient, ModelClientError, parse_header_specs

MODEL = "test-model:4b"


class FakeTransport:
    """One scripted OpenAI-compatible endpoint, with a recorded request log."""

    def __init__(
        self,
        *,
        content: str = "hello",
        tool_calls: list[dict[str, Any]] | None = None,
        finish_reason: str = "stop",
        raise_error: Exception | None = None,
    ) -> None:
        self.content = content
        self.tool_calls = tool_calls
        self.finish_reason = finish_reason
        self.raise_error = raise_error
        self.requests: list[dict[str, Any]] = []

    def __call__(self, request: urllib.request.Request) -> Mapping[str, Any]:
        body = json.loads(request.data) if request.data else None
        self.requests.append(
            {
                "url": request.full_url,
                "body": body,
                "headers": {name.lower(): value for name, value in request.header_items()},
                "data": request.data,
            }
        )
        if self.raise_error is not None:
            raise self.raise_error
        message: dict[str, Any] = {"role": "assistant", "content": self.content}
        if self.tool_calls is not None:
            message["tool_calls"] = self.tool_calls
        return {
            "choices": [{"message": message, "finish_reason": self.finish_reason}]
        }


def _client(transport: FakeTransport) -> ChatClient:
    return ChatClient(base_url="http://endpoint.invalid/v1", model_id=MODEL, transport=transport)


def test_complete_plain_content_has_no_tool_calls_key() -> None:
    transport = FakeTransport(content="a plain answer")
    result = _client(transport).complete([{"role": "user", "content": "hi"}])
    assert result["content"] == "a plain answer"
    assert "tool_calls" not in result


def test_complete_surfaces_tool_calls_unmodified() -> None:
    tool_calls = [{"id": "call_1", "type": "function", "function": {"name": "read", "arguments": "{}"}}]
    transport = FakeTransport(content="", tool_calls=tool_calls)
    result = _client(transport).complete([{"role": "user", "content": "hi"}])
    assert result["tool_calls"] == tool_calls


def test_complete_places_tools_in_request_body() -> None:
    transport = FakeTransport()
    tools = [{"type": "function", "function": {"name": "read", "parameters": {}}}]
    _client(transport).complete([{"role": "user", "content": "hi"}], tools=tools)
    assert transport.requests[0]["body"]["tools"] == tools


def test_complete_without_tools_omits_tools_key() -> None:
    transport = FakeTransport()
    _client(transport).complete([{"role": "user", "content": "hi"}])
    assert "tools" not in transport.requests[0]["body"]


def test_complete_transport_failure_raises_model_client_error() -> None:
    transport = FakeTransport(raise_error=urllib.error.URLError("connection refused"))
    with pytest.raises(ModelClientError):
        _client(transport).complete([{"role": "user", "content": "hi"}])


# ---------------------------------------------------------------------------
# Extra request headers (quick task 260924-tdp)
# ---------------------------------------------------------------------------

IDENTITY_HEADERS = {
    "originator": "codex_cli_rs",
    "version": "0.155.1",
    "user-agent": "codex_cli_rs/0.155.1 (probe)",
}
MESSAGES = [{"role": "user", "content": "hi"}]


def _golden_body() -> bytes:
    return json.dumps(
        {"model": MODEL, "messages": MESSAGES, "temperature": 0.0, "stream": False}
    ).encode("utf-8")


def _send_once(**kwargs: Any) -> dict[str, Any]:
    transport = FakeTransport()
    client = ChatClient(
        base_url="http://endpoint.invalid/v1", model_id=MODEL, transport=transport, **kwargs
    )
    client.complete(MESSAGES)
    return transport.requests[0]


@pytest.mark.parametrize("extras", ["omitted", None, {}])
def test_default_request_headers_and_body_are_unchanged(extras: Any) -> None:
    extra_kwargs = {} if extras == "omitted" else {"extra_headers": extras}

    anonymous = _send_once(**extra_kwargs)
    assert anonymous["headers"] == {"content-type": "application/json"}
    assert anonymous["data"] == _golden_body()

    keyed = _send_once(api_key="k", **extra_kwargs)
    assert keyed["headers"] == {"content-type": "application/json", "authorization": "Bearer k"}
    assert keyed["data"] == _golden_body()


def test_extra_headers_are_sent_and_body_is_unchanged() -> None:
    sent = _send_once(extra_headers=dict(IDENTITY_HEADERS))
    for name, value in IDENTITY_HEADERS.items():
        assert sent["headers"][name] == value
    assert "authorization" not in sent["headers"]
    assert sent["headers"]["content-type"] == "application/json"
    assert sent["data"] == _golden_body()


class _RecordingHandler(http.server.BaseHTTPRequestHandler):
    received: list[dict[str, str]] = []

    def do_POST(self) -> None:  # noqa: N802 - stdlib handler name
        length = int(self.headers.get("Content-Length", "0"))
        self.rfile.read(length)
        type(self).received.append({name.lower(): value for name, value in self.headers.items()})
        payload = json.dumps(
            {
                "choices": [
                    {"message": {"role": "assistant", "content": "ok"}, "finish_reason": "stop"}
                ]
            }
        ).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def log_message(self, format: str, *args: Any) -> None:  # noqa: A002 - stdlib signature
        return


def test_extra_headers_reach_the_wire_and_override_default_user_agent() -> None:
    handler = type("Handler", (_RecordingHandler,), {"received": []})
    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        base_url = f"http://127.0.0.1:{server.server_address[1]}/v1"
        with_extras = ChatClient(
            base_url=base_url,
            model_id=MODEL,
            timeout_seconds=5,
            extra_headers=dict(IDENTITY_HEADERS),
        )
        assert with_extras.complete(MESSAGES)["content"] == "ok"
        plain = ChatClient(base_url=base_url, model_id=MODEL, timeout_seconds=5)
        assert plain.complete(MESSAGES)["content"] == "ok"
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)

    first, second = handler.received
    assert first["originator"] == "codex_cli_rs"
    assert first["version"] == "0.155.1"
    assert first["user-agent"] == "codex_cli_rs/0.155.1 (probe)"
    assert "authorization" not in first
    assert second["user-agent"].startswith("Python-urllib/")
    assert "originator" not in second
    assert "authorization" not in second


@pytest.mark.parametrize(
    "name",
    ["Authorization", "authorization", "AUTHORIZATION", "Proxy-Authorization", "Content-Type"],
)
def test_extra_headers_reject_reserved_names(name: str) -> None:
    with pytest.raises(ModelClientError) as caught:
        ChatClient(
            base_url="http://endpoint.invalid/v1",
            model_id=MODEL,
            extra_headers={name: "sk-should-not-echo"},
        )
    assert "sk-should-not-echo" not in str(caught.value)


@pytest.mark.parametrize(
    "headers",
    [
        {"x-ok": "sentinel-line\rbreak"},
        {"x-ok": "sentinel-line\nbreak"},
        {"x-ok": "sentinel-nul\x00byte"},
        {"": "sentinel-empty-name"},
        {"sentinel name": "sentinel-v"},
        {"sentinel:name": "sentinel-v"},
    ],
)
def test_extra_headers_reject_line_breaks_and_invalid_names(headers: dict[str, str]) -> None:
    with pytest.raises(ModelClientError) as caught:
        ChatClient(base_url="http://endpoint.invalid/v1", model_id=MODEL, extra_headers=headers)
    assert "sentinel" not in str(caught.value)


def test_extra_headers_reject_case_insensitive_duplicates() -> None:
    with pytest.raises(ModelClientError):
        ChatClient(
            base_url="http://endpoint.invalid/v1",
            model_id=MODEL,
            extra_headers={"Originator": "a", "originator": "b"},
        )


def test_parse_header_specs_none_and_empty_return_empty_mapping() -> None:
    assert parse_header_specs(None) == {}
    assert parse_header_specs([]) == {}


def test_parse_header_specs_splits_on_first_colon_and_strips() -> None:
    assert parse_header_specs(["originator: codex_cli_rs"]) == {"originator": "codex_cli_rs"}
    assert parse_header_specs(["x-url: http://h:1/p"]) == {"x-url": "http://h:1/p"}


def test_parse_header_specs_rejects_spec_without_colon_without_echo() -> None:
    # Assembled at runtime so this file's bytes do not trip the package
    # secret scanner (asme.package._SECRET_PATTERNS).
    sentinel = "sk-" + "secret-without-colon"
    with pytest.raises(ModelClientError) as caught:
        parse_header_specs([sentinel])
    assert sentinel not in str(caught.value)


def test_parse_header_specs_rejects_repeated_names() -> None:
    with pytest.raises(ModelClientError):
        parse_header_specs(["x-a: 1", "x-a: 2"])
    with pytest.raises(ModelClientError):
        parse_header_specs(["X-A: 1", "x-a: 2"])


def test_parse_header_specs_rejects_reserved_names() -> None:
    with pytest.raises(ModelClientError) as caught:
        parse_header_specs(["Authorization: Bearer sk-should-not-echo"])
    assert "sk-should-not-echo" not in str(caught.value)
