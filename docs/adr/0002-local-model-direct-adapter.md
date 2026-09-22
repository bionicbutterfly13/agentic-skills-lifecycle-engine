# ADR-0002: Local-model direct adapter

Status: accepted 2026-09-22

## Context

The prior ASME implementation routes exclusively through OpenAI; this is inherited
history, not Lifecycle authority. The development machine (Intel i7, 16 GB, CPU-only)
needs a no-paid-provider path for the first Inference Agent runtime. Two local models
are available via Ollama on this machine: hermes3 (4.7 GB) and deepseek-r1 (5.2 GB).

## Decision

Build a new direct adapter for a bare local model (Ollama) as the first Inference Agent
runtime. Host adapters for Hermes, Codex, and Claude Code follow after the loop is
proven on this direct adapter.

## Consequences

DAED-0x host-adapter work is sequenced after this direct adapter, not before it. ASME's
OpenAI-only routing control does not carry forward as Lifecycle authority.
