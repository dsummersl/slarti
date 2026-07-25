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


def _render_one(
    doc_path: Path, constraints: list[Constraint], models: Models, diagrams: dict[str, str]
) -> Rendered:
    if not doc_path.is_file():
        return Rendered(text="", regions=(), unknown=())
    text = doc_path.read_text(encoding="utf-8")
    names = [region.name for region in inject.regions(text)]
    unknown = []
    for name in names:
        body = generate.region_content(name, constraints, models, diagrams)
        if body is None:
            unknown.append(name)
            continue
        text = inject.replace(text, name, body)
    return Rendered(text=text, regions=tuple(names), unknown=tuple(unknown))


def render(
    config: Config, constraints: list[Constraint], models: Models, diagrams: dict[str, str]
) -> list[Rendered]:
    """Regenerate every region of every configured document from its sources."""
    return [_render_one(p, constraints, models, diagrams) for p in config.document_paths()]


def write(config: Config, constraints: list[Constraint], models: Models) -> list[Rendered]:
    """`slarti docs`: regenerate diagrams and inject every region."""
    diagrams, _ = generate.diagrams_for(config)
    rendered_docs = render(config, constraints, models, diagrams)
    for doc_path, rendered in zip(config.document_paths(), rendered_docs, strict=True):
        if rendered.text and rendered.text != doc_path.read_text(encoding="utf-8"):
            doc_path.write_text(rendered.text, encoding="utf-8")
    return rendered_docs


def committed_diagrams(config: Config) -> dict[str, str]:
    directory: Path = config.path("diagrams")
    return {p.stem: p.read_text(encoding="utf-8").strip() for p in sorted(directory.glob("*.mmd"))}
