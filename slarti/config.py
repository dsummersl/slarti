from __future__ import annotations

import tomllib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

CONFIG_NAME = "slarti.toml"
PYPROJECT_NAME = "pyproject.toml"

DEFAULTS: dict[str, str] = {
    "likec4": "docs/slarti/likec4",
    "linkml": "docs/slarti/linkml",
    "shacl": "docs/slarti/shacl",
    "constraints": "docs/slarti/constraints.yaml",
    "shacl_valid": "docs/slarti/data/valid",
    "shacl_invalid": "docs/slarti/data/invalid",
    "diagrams": "docs/diagrams",
}

DOCUMENTS_DEFAULT: list[str] = ["docs/architecture.md"]


class ConfigError(Exception):
    """Raised when slarti.toml is missing or malformed."""


@dataclass(frozen=True)
class Config:
    """Resolved project paths. Paths only — no settings are mirrored (I6)."""

    root: Path
    paths: dict[str, str] = field(default_factory=lambda: dict(DEFAULTS))
    documents: list[str] = field(default_factory=lambda: list(DOCUMENTS_DEFAULT))

    def path(self, key: str) -> Path:
        return self.root / self.paths[key]

    def document_paths(self) -> list[Path]:
        return [self.root / d for d in self.documents]

    def rel(self, target: Path) -> str:
        try:
            return str(target.resolve().relative_to(self.root.resolve()))
        except ValueError:
            return str(target)

    def schema_files(self) -> list[Path]:
        return sorted(self.path("linkml").glob("*.yaml"))

    def shape_files(self) -> list[Path]:
        return sorted(self.path("shacl").glob("*.ttl"))


def find_root(start: Path) -> Path | None:
    """Walk upward looking for the directory holding slarti.toml."""
    for candidate in [start.resolve(), *start.resolve().parents]:
        if (candidate / CONFIG_NAME).is_file():
            return candidate
    return None


def _merge(raw: dict[str, Any], source_label: str) -> tuple[dict[str, str], list[str]]:
    configured = raw.get("paths", {})
    unknown = sorted(set(configured) - set(DEFAULTS) - {"documents"})
    if unknown:
        raise ConfigError(f"Unknown path keys in {source_label}: {', '.join(unknown)}")
    docs = _merge_documents(configured.get("documents"))
    path_keys = {k: str(v) for k, v in configured.items() if k != "documents"}
    paths = dict(DEFAULTS) | path_keys
    return paths, docs


def _merge_documents(raw: Any) -> list[str]:
    if raw is None:
        return list(DOCUMENTS_DEFAULT)
    if isinstance(raw, list):
        return [str(item) for item in raw]
    return [str(raw)]


def _find_pyproject_root(start: Path) -> Path | None:
    for candidate in [start, *start.parents]:
        pyproject = candidate / PYPROJECT_NAME
        if pyproject.is_file():
            raw = tomllib.loads(pyproject.read_text(encoding="utf-8"))
            if "paths" in raw.get("tool", {}).get("slarti", {}):
                return candidate
    return None


def _load_toml(root: Path, name: str, source_label: str) -> Config:
    raw: dict[str, Any] = tomllib.loads((root / name).read_text(encoding="utf-8"))
    paths, docs = _merge(raw, source_label)
    return Config(root=root, paths=paths, documents=docs)


def _load_pyproject(root: Path) -> Config:
    raw: dict[str, Any] = tomllib.loads((root / PYPROJECT_NAME).read_text(encoding="utf-8"))
    paths, docs = _merge(raw["tool"]["slarti"], f"{PYPROJECT_NAME} [tool.slarti]")
    return Config(root=root, paths=paths, documents=docs)


def load(start: Path | None = None) -> Config:
    start = (start or Path.cwd()).resolve()

    root = find_root(start)
    if root is not None:
        return _load_toml(root, CONFIG_NAME, CONFIG_NAME)

    root = _find_pyproject_root(start)
    if root is not None:
        return _load_pyproject(root)

    raise ConfigError(
        f"No {CONFIG_NAME} or [tool.slarti] section in {PYPROJECT_NAME} found. "
        f"Run 'slarti init' first."
    )
