from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from pydantic import ValidationError

from slarti.domain import Constraint, Enforcer, EnforcerKind

__all__ = [
    "Constraint",
    "Enforcer",
    "EnforcerKind",
    "RegistryError",
    "is_unenforced",
    "kind_text",
    "load",
    "load_enforcer",
    "referenced_shapes",
]


class RegistryError(Exception):
    """Raised when the constraint registry cannot be read."""


def is_unenforced(enforcer: Enforcer) -> bool:
    """An enforcer with no kind is the honest record of a rule nothing enforces."""
    return enforcer.kind is None


def kind_text(enforcer: Enforcer) -> str:
    """The enforcer kind as it is written in the registry, or 'none'."""
    return "none" if enforcer.kind is None else str(enforcer.kind)


def load_enforcer(raw: Any) -> Enforcer:
    if raw in (None, "none"):
        return Enforcer()
    if not isinstance(raw, dict):
        raise RegistryError(f"enforced_by must be a mapping or 'none', got: {raw!r}")
    try:
        return Enforcer(
            layer=raw.get("layer"),
            kind=raw.get("kind"),
            ref=raw.get("ref"),
            fixture=raw.get("fixture"),
            fixture_class=raw.get("fixture_class"),
        )
    except ValidationError as exc:
        kinds = ", ".join(k.value for k in EnforcerKind)
        raise RegistryError(f"Invalid enforcer {raw!r}. Enforcer kinds are: {kinds}.") from exc


def _constraint(raw: dict[str, Any]) -> Constraint:
    if "id" not in raw or "statement" not in raw:
        raise RegistryError(f"Constraint needs an 'id' and a 'statement': {raw!r}")
    return Constraint(
        id=str(raw["id"]),
        statement=str(raw["statement"]).strip(),
        enforced_by=load_enforcer(raw.get("enforced_by")),
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
        located.append(constraint.model_copy(update={"line": number}))
    return located


def referenced_shapes(constraints: list[Constraint]) -> set[str]:
    """Every SHACL shape the registry points at."""
    shacl = EnforcerKind.shacl_shape
    refs = (c.enforced_by.ref for c in constraints if c.enforced_by.kind == shacl)
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
