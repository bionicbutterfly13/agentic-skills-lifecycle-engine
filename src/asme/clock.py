"""Canonical system or fixed clock values for transaction intent records."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

from .canonical import ContractError


@dataclass(frozen=True)
class CanonicalClock:
    """Read timezone-aware UTC timestamps, optionally fixed for conformance tests."""

    _fixed: datetime | None = None

    @classmethod
    def system(cls) -> "CanonicalClock":
        return cls()

    @classmethod
    def fixed(cls, value: str | datetime) -> "CanonicalClock":
        try:
            parsed = datetime.fromisoformat(value) if isinstance(value, str) else value
        except ValueError as exc:
            raise ContractError("fixed clock must be an ISO-8601 timestamp") from exc
        if not isinstance(parsed, datetime) or parsed.tzinfo is None:
            raise ContractError("fixed clock must include a timezone")
        return cls(parsed.astimezone(timezone.utc))

    def now(self) -> datetime:
        return self._fixed or datetime.now(timezone.utc)

    def read(self) -> str:
        return self.now().astimezone(timezone.utc).isoformat()
