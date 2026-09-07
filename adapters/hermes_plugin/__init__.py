"""Thin Hermes adapter for Agent Skill Mastery Engine.

This user plugin does not patch Hermes internals, observe ambient sessions, or
dispatch a role through a provider fallback it cannot lock.  It exposes the
runtime's currently defensible capability report.  Staging is performed by the
runtime-neutral core outside live skill roots.
"""

from __future__ import annotations

from dataclasses import asdict
from functools import partial
import json
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from asme.contract import CapabilityReport


ADAPTER_ID = "hermes"
ADAPTER_VERSION = "0.2.0"
_LIFECYCLE_METHODS = ("launch", "status", "wait", "cancel", "result", "reconnect")

CAPABILITIES_SCHEMA = {
    "name": "wikiskill_capabilities",
    "description": (
        "Report measured Agent Skill Mastery Engine adapter capabilities. This is read-only and "
        "does not run evolution, inspect session history, stage files, or install skills."
    ),
    "parameters": {"type": "object", "properties": {}, "additionalProperties": False},
}


def capability_report(context: Any | None = None) -> CapabilityReport:
    """Return the conservative report supported by current public Hermes APIs."""

    from asme.contract import CapabilityEvidence, CapabilityReport

    try:
        from hermes_cli import __version__ as runtime_version
    except Exception:
        runtime_version = "unknown"
    lifecycle = None
    if context is not None:
        try:
            lifecycle = getattr(context, "subagent_lifecycle", None)
        except Exception:
            lifecycle = None
    lifecycle_surface_available = lifecycle is not None and all(
        callable(getattr(lifecycle, method, None)) for method in _LIFECYCLE_METHODS
    )
    return CapabilityReport.conservative(
        runtime_id=ADAPTER_ID,
        runtime_version=str(runtime_version or "unknown"),
        adapter_version=ADAPTER_VERSION,
        provider="unknown",
        model_id="unknown",
        openai_backed=False,
        captured_events=(),
        evidence=(
            CapabilityEvidence(
                kind="public_plugin_context",
                detail="manifest v2 and PluginContext registration surface",
                passed=True,
            ),
            CapabilityEvidence(
                kind="fresh_child_lifecycle",
                detail=(
                    "active PluginContext exposes the public lifecycle service surface; "
                    "fresh launch was not exercised"
                    if lifecycle_surface_available
                    else "active PluginContext does not expose the required lifecycle surface"
                ),
                passed=lifecycle_surface_available,
            ),
            CapabilityEvidence(
                kind="fail_closed_provider_route_lock",
                detail=(
                    "public child launch has no atomic provider allowlist or no-fallback token; "
                    "dispatch is disabled before any model request"
                ),
                passed=False,
            ),
            CapabilityEvidence(
                kind="ambient_transcript_capture",
                detail="not registered; declared task sets are the only evidence source",
                passed=False,
            ),
        ),
    )


def _handle_capabilities(
    args: dict[str, Any], *, context: Any | None = None, **_: Any
) -> str:
    if args:
        return json.dumps(
            {"ok": False, "error": "wikiskill_capabilities accepts no arguments"},
            sort_keys=True,
        )
    report = capability_report(context)
    return json.dumps(
        {
            "ok": True,
            "status": "staging_only_dispatch_disabled",
            "reason": "fail_closed_provider_route_lock_unavailable",
            "capability_report": asdict(report),
            "capability_report_sha256": report.digest,
            "live_mutation": False,
        },
        sort_keys=True,
        default=str,
    )


def register(ctx: Any) -> None:
    """Register one read-only capability tool with no ambient hooks."""

    ctx.register_tool(
        name="wikiskill_capabilities",
        toolset="asme",
        schema=CAPABILITIES_SCHEMA,
        handler=partial(_handle_capabilities, context=ctx),
        description="Read-only Agent Skill Mastery Engine capability report.",
        emoji="🧪",
    )
