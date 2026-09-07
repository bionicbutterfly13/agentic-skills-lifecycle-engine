# Hermes adapter

This adapter is intentionally small and update-safe. It registers one read-only tool,
`wikiskill_capabilities`, through the public plugin context. It does not patch Hermes,
inspect ambient sessions, dispatch a model, stage a package, or install a skill.

Current status: `staging_only_dispatch_disabled`.

The development candidate passes Hermes Agent 0.20.5's official Plugin Doctor: runtime
discovery, manifest parsing, import, and registration completed with one tool and zero
hooks. In an uninstalled source checkout, Doctor also reports the declared
`asme` Python dependency as missing. This warning is expected and is not
silently resolved. The standalone loader uses this directory's `__init__.py`; a `tools.py`
`register_tools(ctx)` module is reserved for deferred platform plugins and is not part of
this adapter's contract.

Reason: the verified public child-launch surface does not provide an atomic exact-provider
allowlist with no fallback. The OpenAI-only rule therefore fails closed before any model
request.

The files are development artifacts. Do not copy them into a live Hermes plugin directory
without a separate installation approval. After an approved installation, probe and test
the exact Hermes version before updating compatibility metadata.
