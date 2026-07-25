from __future__ import annotations

from slarti import docs, generate, inject
from slarti.config import Config
from slarti.findings import Finding
from slarti.models import Models
from slarti.registry import Constraint


def _doc3(config: Config, message: str, subject: str, remedy: str) -> Finding:
    return Finding(
        id="DOC-3",
        severity="error",
        file=config.paths["document"],
        subject=subject,
        message=message,
        remedy=remedy,
    )


def _marker_findings(config: Config, unknown: tuple[str, ...]) -> list[Finding]:
    return [
        _doc3(
            config,
            f"the document declares a generated region named '{name}', which slarti cannot fill.",
            name,
            "Use one of: constraints, unverified, ownership, diagram:<view>.",
        )
        for name in unknown
    ]


def _stale(config: Config, region: str) -> Finding:
    return Finding(
        id="DOC-1",
        severity="error",
        file=config.paths["document"],
        subject=region,
        message=f"generated region '{region}' no longer matches the model it came from.",
        remedy="Run 'slarti docs' and commit the result.",
    )


def _hand_edited(config: Config, name: str) -> Finding:
    return Finding(
        id="DOC-2",
        severity="error",
        file=f"{config.paths['diagrams']}/{name}.mmd",
        subject=name,
        message=f"generated diagram '{name}' differs from what the model generates.",
        remedy="Never hand-edit files under the diagrams directory; run 'slarti docs' instead.",
    )


def _doc4(config: Config, constraint_id: str) -> Finding:
    return Finding(
        id="DOC-4",
        severity="error",
        file=config.paths["document"],
        subject=constraint_id,
        message=(
            f"constraint {constraint_id} is in the registry but has no row in the document tables."
        ),
        remedy="This is a generation bug in slarti; please report it with the registry entry.",
    )


def _bodies(text: str) -> dict[str, str]:
    return {r.name: r.body for r in inject.regions(text)}


def _region_findings(config: Config, current: str, rendered: docs.Rendered) -> list[Finding]:
    if current == rendered.text:
        return []
    before, after = _bodies(current), _bodies(rendered.text)
    return [_stale(config, name) for name in sorted(after) if before.get(name) != after[name]]


def _diagram_findings(config: Config, fresh: dict[str, str]) -> list[Finding]:
    committed = docs.committed_diagrams(config)
    names = sorted(set(fresh) | set(committed))
    return [_hand_edited(config, name) for name in names if fresh.get(name) != committed.get(name)]


def _table_findings(config: Config, constraints: list[Constraint], text: str) -> list[Finding]:
    tables = "".join(r.body for r in inject.regions(text) if r.name in generate.TABLE_REGIONS)
    return [_doc4(config, c.id) for c in constraints if f"| {c.id} |" not in tables]


def check(config: Config, models: Models, constraints: list[Constraint]) -> list[Finding]:
    """DOC-1..DOC-4: the document seam — drift, hand-edits, markers, coverage."""
    document = config.path("document")
    if not document.is_file():
        return [
            _doc3(
                config,
                "the architecture document does not exist.",
                "-",
                "Run 'slarti init', or point slarti.toml at the document.",
            )
        ]
    current = document.read_text(encoding="utf-8")
    try:
        fresh = generate.diagrams_temp(config)
        rendered = docs.render(config, constraints, models, fresh)
    except inject.MarkerError as exc:
        return [_doc3(config, str(exc), "-", "Balance the slarti:begin and slarti:end markers.")]
    return [
        *_marker_findings(config, rendered.unknown),
        *_region_findings(config, current, rendered),
        *_diagram_findings(config, fresh),
        *_table_findings(config, constraints, rendered.text),
    ]
