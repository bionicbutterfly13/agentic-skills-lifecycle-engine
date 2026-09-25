"""A pure, stateless OpenAI-compatible chat-completions transport.

ChatClient sends one request per call and returns the raw first-choice message
mapping. It carries no retry logic and no role awareness; callers (such as
scripts/run_maintainer.py) own retry policy and role-specific interpretation.
Callers may pass extra request headers (for endpoints that gate on client
identity); credentials never travel through them.
"""

from __future__ import annotations

import json
import re
from typing import Any, Callable, Mapping, Sequence
import urllib.error
import urllib.request

from .canonical import ContractError

DEFAULT_TIMEOUT_SECONDS = 1800.0

# Header names an extra header may never set (compared lower-case). Credentials
# stay env-only via the driver's --api-key-env, so Authorization and
# Proxy-Authorization are refused; Content-Type is owned by this client because
# it always sends JSON.
RESERVED_HEADER_NAMES = frozenset({"authorization", "proxy-authorization", "content-type"})

# RFC 9110 section 5.6.2 token: one or more tchar.
_HEADER_NAME_TOKEN = re.compile(r"[!#$%&'*+\-.^_`|~0-9A-Za-z]+")
_FORBIDDEN_VALUE_CHARACTERS = ("\r", "\n", "\x00")


class ModelClientError(ContractError):
    """One chat-completions request could not be completed or parsed."""


def _validated_header_pairs(pairs: Sequence[tuple[Any, Any]]) -> dict[str, str]:
    """Validate (name, value) pairs and return a new insertion-ordered dict.

    Errors identify a header only by its 1-based position (and, for reserved
    names, the canonical reserved name). They never interpolate user-supplied
    text, because a mistyped secret could otherwise reach stderr or logs.
    """

    validated: dict[str, str] = {}
    seen: set[str] = set()
    for position, (name, value) in enumerate(pairs, start=1):
        if not isinstance(name, str) or not isinstance(value, str):
            raise ModelClientError(f"extra header #{position} must have a string name and value")
        if not _HEADER_NAME_TOKEN.fullmatch(name):
            raise ModelClientError(
                f"extra header #{position} has an invalid name (RFC 9110 token required)"
            )
        lowered = name.lower()
        if lowered in RESERVED_HEADER_NAMES:
            # Name the header by the canonical constant, not the user's spelling.
            reserved = next(item for item in RESERVED_HEADER_NAMES if item == lowered)
            if reserved == "authorization":
                raise ModelClientError(
                    f"extra header #{position} is reserved ({reserved}): the API key comes "
                    "only from the environment via --api-key-env"
                )
            raise ModelClientError(f"extra header #{position} is reserved ({reserved})")
        if any(character in value for character in _FORBIDDEN_VALUE_CHARACTERS):
            raise ModelClientError(
                f"extra header #{position} value contains a CR, LF, or NUL character"
            )
        if lowered in seen:
            raise ModelClientError(
                f"extra header #{position} repeats an earlier header name (case-insensitive)"
            )
        seen.add(lowered)
        validated[name] = value
    return validated


def _validated_extra_headers(headers: Mapping[str, str]) -> dict[str, str]:
    """Validate an extra-header mapping; see _validated_header_pairs."""

    return _validated_header_pairs(list(headers.items()))


def parse_header_specs(specs: Sequence[str] | None) -> dict[str, str]:
    """Parse repeatable ``NAME:VALUE`` specs into a validated header mapping.

    Each spec splits on its first colon; name and value are whitespace-stripped.
    Repeated names (any case), reserved names, and malformed specs raise
    ModelClientError without echoing the spec text.
    """

    if not specs:
        return {}
    pairs: list[tuple[str, str]] = []
    for position, spec in enumerate(specs, start=1):
        if not isinstance(spec, str) or ":" not in spec:
            raise ModelClientError(f"extra header #{position} must have the form NAME:VALUE")
        name, value = spec.split(":", 1)
        pairs.append((name.strip(), value.strip()))
    return _validated_header_pairs(pairs)


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
        extra_headers: Mapping[str, str] | None = None,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._model_id = model_id
        self._api_key = api_key
        self._timeout = float(timeout_seconds)
        self._temperature = float(temperature)
        self._transport = transport
        # Validated at construction, before any request exists, so Python API
        # callers who bypass the driver CLIs get the same refusals.
        self._extra_headers = _validated_extra_headers(extra_headers or {})

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
        headers.update(self._extra_headers)
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
