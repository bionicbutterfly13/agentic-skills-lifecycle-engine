"""Content-safety refusals for the skill files a delivery admits into staging.

It owns no lifecycle, network, or install behavior. It reads candidate file bytes
and refuses three structural dangers a staged skill must never carry: fetching and
executing remote code, depending on an unpinned package resolved at run time, and
writing to the agent memory or configuration files that survive skill removal.
"""

from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Iterable, Mapping

from .canonical import ContractError


SKILL_SAFETY_SCHEMA = "asme.skill-safety.v1"

REMOTE_CODE_EXECUTION = "remote_code_execution"
UNPINNED_DEPENDENCY = "unpinned_dependency"
AGENT_STATE_WRITE = "agent_state_write"

_PROTECTED_AGENT_STATE = (
    "AGENTS.md",
    "CLAUDE.md",
    "GEMINI.md",
    "MEMORY.md",
    "SOUL.md",
    "settings.json",
    "settings.local.json",
    "mcp.json",
)

_DOWNLOAD_INTO_SHELL = re.compile(
    r"\b(?:curl|wget)\b[^\n|]*\|\s*(?:sudo\s+)?(?:sh|bash|zsh|dash|python[0-9.]*)\b"
)
_SUBSTITUTED_DOWNLOAD = re.compile(r"(?:\$\(|`)\s*(?:curl|wget)\b")
_REMOTE_INSTALL = re.compile(
    r"\bpip[0-9.]*\s+install\b[^\n]*\b(?:https?://|git\+|file://)"
)
_REMOTE_RUNNER = re.compile(r"\b(?:uvx|uv\s+run|uv\s+tool\s+run)\b[^\n]*\bhttps?://")
_NPX = re.compile(r"\bnpx\b")

_PIP_INSTALL = re.compile(r"\bpip[0-9.]*\s+install\b([^\n]*)")
_UV_WITH = re.compile(r"--with(?:-editable)?[=\s]+([^\s]+)")

_WRITE_INDICATOR = re.compile(
    r">>?|\btee\b|\bsed\s+-i\b|\bwrite_text\b|\bwrite_bytes\b|\bopen\s*\("
    r"|\bcp\b|\bmv\b|\bdd\b|\btruncate\b"
)


class UnsafeSkillContent(ContractError):
    """One staged skill file carries a refused execution or persistence pattern."""


@dataclass(frozen=True)
class SafetyFinding:
    member: str
    rule: str
    line: int
    evidence: str

    def __post_init__(self) -> None:
        if not self.member:
            raise ContractError("safety finding requires a member path")
        if self.rule not in {REMOTE_CODE_EXECUTION, UNPINNED_DEPENDENCY, AGENT_STATE_WRITE}:
            raise ContractError(f"unknown skill safety rule: {self.rule}")
        if self.line < 1:
            raise ContractError("safety finding line numbers start at 1")


def scan_skill_files(files: Mapping[str, bytes]) -> tuple[SafetyFinding, ...]:
    """Return every refused pattern in the candidate files, sorted by member and line."""

    findings: list[SafetyFinding] = []
    for member, content in sorted(files.items()):
        if not isinstance(content, bytes):
            raise ContractError(f"skill safety input must be bytes: {member}")
        try:
            text = content.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise ContractError(f"skill file must be UTF-8 to scan: {member}") from exc
        for number, line in enumerate(text.splitlines(), start=1):
            for rule in _line_rules(line):
                findings.append(SafetyFinding(member, rule, number, line.strip()[:200]))
    return tuple(findings)


def require_safe_skill_files(files: Mapping[str, bytes]) -> Mapping[str, bytes]:
    """Return the candidate files unchanged, or refuse the first offending member."""

    findings = scan_skill_files(files)
    if findings:
        head = findings[0]
        raise UnsafeSkillContent(
            f"staged skill refused by {head.rule}: {head.member}:{head.line} "
            f"({len(findings)} finding(s))"
        )
    return files


def _line_rules(line: str) -> Iterable[str]:
    stripped = line.strip()
    if not stripped:
        return ()
    rules: list[str] = []
    if _is_remote_execution(stripped):
        rules.append(REMOTE_CODE_EXECUTION)
    elif _is_unpinned_dependency(stripped):
        rules.append(UNPINNED_DEPENDENCY)
    if _is_agent_state_write(stripped):
        rules.append(AGENT_STATE_WRITE)
    return tuple(rules)


def _is_remote_execution(line: str) -> bool:
    return bool(
        _DOWNLOAD_INTO_SHELL.search(line)
        or _SUBSTITUTED_DOWNLOAD.search(line)
        or _REMOTE_INSTALL.search(line)
        or _REMOTE_RUNNER.search(line)
        or _NPX.search(line)
    )


def _is_unpinned_dependency(line: str) -> bool:
    match = _PIP_INSTALL.search(line)
    if match is not None and _has_unpinned_requirement(match.group(1).split()):
        return True
    return any(
        _is_unpinned_requirement(value)
        for value in _UV_WITH.findall(line)
    )


def _has_unpinned_requirement(arguments: list[str]) -> bool:
    skip_next = False
    for argument in arguments:
        if skip_next:
            skip_next = False
            continue
        if argument in {"-r", "--requirement", "-c", "--constraint"}:
            skip_next = True
            continue
        if argument.startswith("-"):
            continue
        if _is_unpinned_requirement(argument):
            return True
    return False


def _is_unpinned_requirement(argument: str) -> bool:
    if not argument or argument.startswith("-"):
        return False
    if argument in {".", ".."} or argument.startswith(("./", "../", "/")):
        return False
    if argument.endswith((".txt", ".toml", ".whl", ".tar.gz")):
        return False
    return "==" not in argument


def _is_agent_state_write(line: str) -> bool:
    if not _WRITE_INDICATOR.search(line):
        return False
    if ">=" in line or "<=" in line or "->" in line:
        cleaned = line.replace(">=", " ").replace("<=", " ").replace("->", " ")
        if not _WRITE_INDICATOR.search(cleaned):
            return False
    lowered = line.lower()
    if any(name.lower() in lowered for name in _PROTECTED_AGENT_STATE):
        return True
    return ".claude/" in lowered or ".codex/" in lowered or ".hermes/" in lowered
