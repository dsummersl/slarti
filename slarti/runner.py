from __future__ import annotations

from dataclasses import dataclass

from slarti import registry
from slarti.checks import delegated, doc_checks, ownership, registry_checks
from slarti.config import Config
from slarti.findings import Report
from slarti.models import Models
from slarti.registry import Constraint


@dataclass
class Context:
    """Everything a command needs: config, models and the registry."""

    config: Config
    models: Models
    constraints: list[Constraint]


def context(config: Config) -> Context:
    return Context(
        config=config,
        models=Models(config=config),
        constraints=registry.load(config.path("constraints")),
    )


def check(ctx: Context, include_docs: bool = True) -> tuple[Report, bool]:
    """Delegated validations first, then every slarti check."""
    report = Report()
    delegations = delegated.run_all(ctx.config)
    delegated_ok = delegated.report(delegations)
    report.extend(ownership.check(ctx.models))
    report.extend(registry_checks.check(ctx.config, ctx.models, ctx.constraints))
    if include_docs:
        report.extend(doc_checks.check(ctx.config, ctx.models, ctx.constraints))
    report.checked = _checked(ctx, len(delegations), include_docs)
    return report, delegated_ok


def _checked(ctx: Context, delegations: int, include_docs: bool) -> int:
    classes = len(ownership.owned_classes(ctx.models))
    elements = len(ctx.models.likec4.elements)
    docs_count = 4 if include_docs else 0
    seams = len(ctx.constraints) + len(ctx.models.shapes)
    return delegations + classes + elements + seams + docs_count


@dataclass(frozen=True)
class Dangling:
    """The registry seam in report form."""

    enforced: list[Constraint]
    unenforced: list[Constraint]
    orphaned: list[str]


def dangling(ctx: Context) -> Dangling:
    """Enforced rules, unenforced rules, and shapes no rule references."""
    ordered = sorted(ctx.constraints, key=lambda c: c.id)
    referenced = registry.referenced_shapes(ctx.constraints)
    return Dangling(
        enforced=[c for c in ordered if not c.enforcer.is_none],
        unenforced=[c for c in ordered if c.enforcer.is_none],
        orphaned=sorted(set(ctx.models.shapes) - referenced),
    )
