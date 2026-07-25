from __future__ import annotations

import tempfile
from pathlib import Path

from slarti import proc, resolvers
from slarti.checks.ownership import owned_classes
from slarti.config import Config
from slarti.models import Models
from slarti.registry import Constraint, is_unenforced, kind_text

DIAGRAM_PREFIX = "diagram:"
TABLE_REGIONS = ("constraints", "unverified", "ownership")


def _row(cells: list[str]) -> str:
    return "| " + " | ".join(cells) + " |"


def _table(headers: list[str], rows: list[list[str]], empty: str) -> str:
    if not rows:
        return f"_{empty}_"
    lines = [_row(headers), _row(["---"] * len(headers))]
    lines.extend(_row(cells) for cells in rows)
    return "\n".join(lines)


def constraints_table(constraints: list[Constraint]) -> str:
    """The enforced-rules table: every rule and the enforcer that holds it."""
    rows = [
        [
            c.id,
            c.statement,
            str(c.enforced_by.layer or "-"),
            f"{kind_text(c.enforced_by)} {resolvers.describe(c.enforced_by)}",
            c.decision or "-",
        ]
        for c in sorted(constraints, key=lambda c: c.id)
        if not is_unenforced(c.enforced_by)
    ]
    return _table(["ID", "Rule", "Layer", "Enforced by", "Decision"], rows, "No enforced rules.")


def unverified_table(constraints: list[Constraint]) -> str:
    """The honest table: rules stated but not mechanically enforced."""
    rows = [
        [c.id, c.statement, c.reason or "-"]
        for c in sorted(constraints, key=lambda c: c.id)
        if is_unenforced(c.enforced_by)
    ]
    return _table(["ID", "Rule", "Why unenforced"], rows, "Every rule is enforced.")


def ownership_table(models: Models) -> str:
    """The ownership seam, rendered: which container owns which entity."""
    elements = models.likec4.elements
    rows = []
    for name in owned_classes(models):
        owner = models.class_annotation(name, "owner")
        title = (elements[owner].title or "-") if owner in elements else "-"
        rows.append([name, f"`{owner}`" if owner else "-", title])
    return _table(["Entity", "Owner", "Owner title"], rows, "No entities are owned.")


def render_diagrams(config: Config, outdir: Path) -> dict[str, str]:
    """Delegate diagram generation to `likec4 codegen mermaid` (I2, §6)."""
    argv = proc.likec4(["codegen", "mermaid", "-o", str(outdir), str(config.path("likec4"))])
    result = proc.run(argv, cwd=config.root)
    if result.code != 0:
        raise RuntimeError(f"likec4 codegen mermaid failed:\n{result.stderr or result.stdout}")
    return {p.stem: p.read_text(encoding="utf-8").strip() for p in sorted(outdir.glob("*.mmd"))}


def diagram_block(name: str, diagrams: dict[str, str]) -> str:
    if name not in diagrams:
        return f"_View `{name}` is not in the model._"
    return "```mermaid\n" + diagrams[name] + "\n```"


def region_content(
    region: str, constraints: list[Constraint], models: Models, diagrams: dict[str, str]
) -> str | None:
    """Generated body for a named region, or None if the name is unknown."""
    if region == "constraints":
        return constraints_table(constraints)
    if region == "unverified":
        return unverified_table(constraints)
    if region == "ownership":
        return ownership_table(models)
    if region.startswith(DIAGRAM_PREFIX):
        return diagram_block(region[len(DIAGRAM_PREFIX) :], diagrams)
    return None


def diagrams_for(config: Config) -> tuple[dict[str, str], Path]:
    """Regenerate diagrams into the configured directory, returning their bodies."""
    outdir = config.path("diagrams")
    outdir.mkdir(parents=True, exist_ok=True)
    return render_diagrams(config, outdir), outdir


def diagrams_temp(config: Config) -> dict[str, str]:
    """Regenerate diagrams into a temp tree, touching nothing in the project (I1)."""
    with tempfile.TemporaryDirectory() as tmp:
        return render_diagrams(config, Path(tmp))
