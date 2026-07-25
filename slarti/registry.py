from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


class RegistryError(Exception):
    """Raised when the constraint registry cannot be read."""


@dataclass(frozen=True)
class Enforcer:
    """How a constraint is enforced, or the honest absence of enforcement."""

    layer: int | None
    kind: str | None
    ref: str | None
    fixture: str | None
    fixture_class: str | None

    @property
    def is_none(self) -> bool:
        return self.kind is None


@dataclass(frozen=True)
class Constraint:
    """One rule in the registry, with its enforcer and provenance."""

    id: str
    statement: str
    enforcer: Enforcer
    reason: str | None
    decision: str | None
    line: int | None = None


def _enforcer(raw: Any) -> Enforcer:
    if raw in (None, "none"):
        return Enforcer(None, None, None, None, None)
    if not isinstance(raw, dict):
        raise RegistryError(f"enforced_by must be a mapping or 'none', got: {raw!r}")
    return Enforcer(
        layer=raw.get("layer"),
        kind=raw.get("kind"),
        ref=raw.get("ref"),
        fixture=raw.get("fixture"),
        fixture_class=raw.get("fixture_class"),
    )


def _constraint(raw: dict[str, Any]) -> Constraint:
    if "id" not in raw or "statement" not in raw:
        raise RegistryError(f"Constraint needs an 'id' and a 'statement': {raw!r}")
    return Constraint(
        id=str(raw["id"]),
        statement=str(raw["statement"]).strip(),
        enforcer=_enforcer(raw.get("enforced_by")),
        reason=None if raw.get("reason") is None else str(raw["reason"]).strip(),
        decision=None if raw.get("decision") is None else str(raw["decision"]),
    )


def _locate_ids(path: Path, constraints: list[Constraint]) -> list[Constraint]:
    lines = path.read_text(encoding="utf-8").splitlines()
    located = []
    for constraint in constraints:
        needle = f"id: {constraint.id}"
        number = next(
            (i for i, t in enumerate(lines, 1) if t.strip() in (needle, f"- {needle}")), None
        )
        located.append(
            Constraint(
                constraint.id,
                constraint.statement,
                constraint.enforcer,
                constraint.reason,
                constraint.decision,
                number,
            )
        )
    return located


def referenced_shapes(constraints: list[Constraint]) -> set[str]:
    """Every SHACL shape the registry points at."""
    refs = (c.enforcer.ref for c in constraints if c.enforcer.kind == "shacl_shape")
    return {ref for ref in refs if ref}


def load(path: Path) -> list[Constraint]:
    """Read model/constraints.yaml in document order."""
    if not path.is_file():
        raise RegistryError(f"No constraint registry at {path}.")
    return _locate_ids(path, [_constraint(item) for item in _raw_constraints(path)])


def _raw_constraints(path: Path) -> list[dict[str, Any]]:
    payload = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    raw = payload.get("constraints") or []
    if not isinstance(raw, list):
        raise RegistryError("'constraints' must be a list.")
    return raw
