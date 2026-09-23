"""A pure, stateless OpenAI-compatible chat-completions transport.

ChatClient sends one request per call and returns the raw first-choice message
mapping. It carries no retry logic and no role awareness; callers (such as
scripts/run_maintainer.py) own retry policy and role-specific interpretation.
"""

from __future__ import annotations

import json
from typing import Any, Callable, Mapping
import urllib.error
import urllib.request

from .canonical import ContractError

DEFAULT_TIMEOUT_SECONDS = 1800.0


class ModelClientError(ContractError):
    """One chat-completions request could not be completed or parsed."""


class ChatClient:
    """Dispatch one stateless chat-completions request per call."""

    def __init__(
        self,
        *,
        base_url: str,
        model_id: str,
        api_key: str | None = None,
        timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
        temperature: float = 0.0,
        transport: Callable[[urllib.request.Request], Mapping[str, Any]] | None = None,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._model_id = model_id
        self._api_key = api_key
        self._timeout = float(timeout_seconds)
        self._temperature = float(temperature)
        self._transport = transport

    def complete(
        self,
        messages: list[dict[str, Any]],
        *,
        tools: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        """Send one chat-completions request and return the raw first message."""

        body: dict[str, Any] = {
            "model": self._model_id,
            "messages": messages,
            "temperature": self._temperature,
            "stream": False,
        }
        if tools is not None:
            body["tools"] = tools
        payload = self._post("/chat/completions", body)
        choices = payload.get("choices")
        if not isinstance(choices, list) or not choices:
            raise ModelClientError("completion payload has no choices")
        first = choices[0]
        if not isinstance(first, Mapping):
            raise ModelClientError("completion choice is malformed")
        message = first.get("message")
        if not isinstance(message, Mapping):
            raise ModelClientError("completion choice has no message")
        result: dict[str, Any] = {"content": message.get("content") or ""}
        if "tool_calls" in message and message["tool_calls"] is not None:
            result["tool_calls"] = message["tool_calls"]
        if first.get("finish_reason"):
            result["finish_reason"] = first["finish_reason"]
        return result

    def _headers(self) -> dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if self._api_key:
            headers["Authorization"] = f"Bearer {self._api_key}"
        return headers

    def _post(self, path: str, body: Mapping[str, Any]) -> Mapping[str, Any]:
        data = json.dumps(body).encode("utf-8")
        request = urllib.request.Request(
            f"{self._base_url}{path}", data=data, headers=self._headers(), method="POST"
        )
        return self._send(request)

    def _send(self, request: urllib.request.Request) -> Mapping[str, Any]:
        if self._transport is not None:
            try:
                return self._transport(request)
            except ModelClientError:
                raise
            except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError, OSError) as exc:
                raise ModelClientError(f"transport failure: {exc}") from exc
        try:
            with urllib.request.urlopen(request, timeout=self._timeout) as response:
                raw = response.read()
        except urllib.error.HTTPError as exc:
            raise ModelClientError(f"HTTP {exc.code} from {request.full_url}") from exc
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            raise ModelClientError(f"transport failure: {exc}") from exc
        try:
            decoded = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise ModelClientError("endpoint returned malformed JSON") from exc
        if not isinstance(decoded, Mapping):
            raise ModelClientError("endpoint returned a non-object payload")
        return decoded
