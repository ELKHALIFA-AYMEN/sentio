# 1. Record architecture decisions

- **Status:** Accepted
- **Date:** 2026-11-09

## Context

Sentio is built in small steps over a long period. Many technical choices (broker client, event format,
service boundaries, models) will be made along the way. Without a written trace, the reasons behind these
choices are forgotten, and later contributors cannot tell whether a decision is deliberate or accidental.

## Decision

We record every important technical decision as an **Architecture Decision Record** (ADR) in `docs/adr/`,
following the lightweight format popularised by Michael Nygard.

- One decision per file, named `NNNN-short-title.md` with a zero-padded sequence number.
- Each ADR contains: **Status**, **Date**, **Context**, **Decision**, **Consequences**.
- Status values: `Proposed`, `Accepted`, `Superseded by NNNN`, `Deprecated`.
- ADRs are never rewritten once accepted. A changed decision gets a new ADR that supersedes the old one.
- An ADR is added in the same change as the code that implements the decision.

## Consequences

- The reasoning behind the architecture is versioned with the code and easy to review.
- Writing an ADR adds a small cost to each important change, which is acceptable for the clarity it brings.
- [`docs/adr/README.md`](README.md) keeps an index and a template.
