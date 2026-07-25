from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from slarti import generate, inject
from slarti.config import Config
from slarti.models import Models
from slarti.registry import Constraint


@dataclass(frozen=True)
class Rendered:
    """The document as it should be, plus the region names it declares."""

    text: str
    regions: tuple[str, ...]
    unknown: tuple[str, ...]


def render(
    config: Config, constraints: list[Constraint], models: Models, diagrams: dict[str, str]
) -> Rendered:
    """Regenerate every region of the document from its sources."""
    text = config.path("document").read_text(encoding="utf-8")
    names = [region.name for region in inject.regions(text)]
    unknown = []
    for name in names:
        body = generate.region_content(name, constraints, models, diagrams)
        if body is None:
            unknown.append(name)
            continue
        text = inject.replace(text, name, body)
    return Rendered(text=text, regions=tuple(names), unknown=tuple(unknown))


def write(config: Config, constraints: list[Constraint], models: Models) -> Rendered:
    """`slarti docs`: regenerate diagrams and inject every region."""
    diagrams, _ = generate.diagrams_for(config)
    rendered = render(config, constraints, models, diagrams)
    document = config.path("document")
    if rendered.text != document.read_text(encoding="utf-8"):
        document.write_text(rendered.text, encoding="utf-8")
    return rendered


def committed_diagrams(config: Config) -> dict[str, str]:
    directory: Path = config.path("diagrams")
    return {p.stem: p.read_text(encoding="utf-8").strip() for p in sorted(directory.glob("*.mmd"))}
