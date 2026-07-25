from __future__ import annotations

import tomllib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

CONFIG_NAME = "slarti.toml"

DEFAULTS: dict[str, str] = {
    "arch": "model/arch",
    "schema": "model/schema",
    "shapes": "model/shapes",
    "constraints": "model/constraints.yaml",
    "data_valid": "model/data/valid",
    "data_invalid": "model/data/invalid",
    "document": "docs/architecture.md",
    "diagrams": "docs/diagrams",
    "build": "build",
}


class ConfigError(Exception):
    """Raised when slarti.toml is missing or malformed."""


@dataclass(frozen=True)
class Config:
    """Resolved project paths. Paths only — no settings are mirrored (I6)."""

    root: Path
    paths: dict[str, str] = field(default_factory=lambda: dict(DEFAULTS))

    def path(self, key: str) -> Path:
        return self.root / self.paths[key]

    def rel(self, target: Path) -> str:
        try:
            return str(target.resolve().relative_to(self.root.resolve()))
        except ValueError:
            return str(target)

    def schema_files(self) -> list[Path]:
        return sorted(self.path("schema").glob("*.yaml"))

    def shape_files(self) -> list[Path]:
        return sorted(self.path("shapes").glob("*.ttl"))


def find_root(start: Path) -> Path | None:
    """Walk upward looking for the directory holding slarti.toml."""
    for candidate in [start.resolve(), *start.resolve().parents]:
        if (candidate / CONFIG_NAME).is_file():
            return candidate
    return None


def load(start: Path | None = None) -> Config:
    root = find_root(start or Path.cwd())
    if root is None:
        raise ConfigError(f"No {CONFIG_NAME} found. Run 'slarti init' first.")
    raw: dict[str, Any] = tomllib.loads((root / CONFIG_NAME).read_text(encoding="utf-8"))
    paths = dict(DEFAULTS)
    configured = raw.get("paths", {})
    unknown = sorted(set(configured) - set(DEFAULTS))
    if unknown:
        raise ConfigError(f"Unknown path keys in {CONFIG_NAME}: {', '.join(unknown)}")
    paths.update({k: str(v) for k, v in configured.items()})
    return Config(root=root, paths=paths)
