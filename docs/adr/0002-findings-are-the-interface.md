# 2. Findings are the interface

Date: 2026-07-25

## Status

Accepted

## Context

`slarti` has two consumers with different needs. A human wants to read what is
wrong; an LLM agent — which has no memory of the repository between sessions —
needs a stable identifier to reason about and a remedy it can act on. Exit codes
alone carry neither.

The tool also delegates every real validation to LikeC4, LinkML and pyshacl. Its
own output must therefore be clearly distinguishable from theirs, and phrased in
domain terms rather than tool terms: "class `Finding` has no owner", not
`KeyError: 'owner'`.

## Decision

Findings, not exit codes, are the interface. Every finding carries a stable rule
ID (`OWN-1`, `REG-2`, `DOC-1`, `ENV-1`), a file, a subject named in domain terms,
a message and a remedy sentence. The same findings render as text or as JSON;
`--json` changes the encoding, never the content. IDs are permanent — retired
checks are never reused — and `slarti explain <ID>` describes any of them.

Because the findings are the contract, the entities they are about are modelled
first-class: `Finding`, `Report`, `Constraint` and `Enforcer` are classes in
`model/schema/slarti.yaml`, with SHACL shapes over them (`D1`, `D2`, `D3`) and a
negative fixture per shape.

Diagnostics from the delegated tools are passed through unaltered and never
reformatted as findings.

## Consequences

- Agents can converge: run `slarti check --json`, apply the remedy, re-run.
- Message wording is part of the contract, and is covered by tests.
- Adding a check means adding an ID, a remedy sentence and an `explain` entry —
  slightly more work than raising an exception, deliberately.
- Rules that no model can enforce are recorded as `enforced_by: none` with a
  reason and surface in the unverified-invariants table rather than being silently
  absent.
