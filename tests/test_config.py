from __future__ import annotations

from pathlib import Path

import pytest

from slarti import config as config_module


def test_defaults_apply_when_unstated(tmp_path: Path) -> None:
    (tmp_path / "slarti.toml").write_text('[paths]\narch = "src/arch"\n', encoding="utf-8")
    cfg = config_module.load(tmp_path)
    assert cfg.paths["arch"] == "src/arch"
    assert cfg.paths["schema"] == "model/schema"


def test_config_is_found_from_a_subdirectory(tmp_path: Path) -> None:
    (tmp_path / "slarti.toml").write_text("[paths]\n", encoding="utf-8")
    nested = tmp_path / "a" / "b"
    nested.mkdir(parents=True)
    assert config_module.load(nested).root == tmp_path


def test_missing_config_is_an_error(tmp_path: Path) -> None:
    with pytest.raises(config_module.ConfigError):
        config_module.load(tmp_path)


def test_unknown_keys_are_rejected(tmp_path: Path) -> None:
    (tmp_path / "slarti.toml").write_text('[paths]\ntheme = "dark"\n', encoding="utf-8")
    with pytest.raises(config_module.ConfigError, match="theme"):
        config_module.load(tmp_path)


def test_rel_is_relative_to_the_root(tmp_path: Path) -> None:
    cfg = config_module.Config(root=tmp_path)
    assert cfg.rel(tmp_path / "model" / "x.yaml") == "model/x.yaml"
