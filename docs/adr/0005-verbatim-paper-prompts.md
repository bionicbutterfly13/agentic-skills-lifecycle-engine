# ADR-0005: Verbatim paper prompts

Status: accepted 2026-09-22

## Context

Adding Lifecycle-specific fields directly into the paper's Appendix E.1-E.3 prompts
risks silently drifting from what the paper actually specifies.

## Decision

Copy the paper's prompts (Appendix E.1-E.3) verbatim into references/paper-prompts/ with
CC BY 4.0 attribution. Local additions, such as the attestation field and hash checks,
live in a separate wrapper layer and are never edited into the paper text.

## Consequences

Any future prompt change must go into the wrapper layer, not the verbatim files. The
verbatim files carry attribution matching arXiv 2608.27454's CC BY 4.0 license.
