"""Offline contract tests for the core stateless chat-completions client."""

from __future__ import annotations

import json
from typing import Any, Mapping
import urllib.error
import urllib.request

import pytest

from asme.model_client import ChatClient, ModelClientError

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
        self.requests.append({"url": request.full_url, "body": body})
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
