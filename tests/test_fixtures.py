from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from slarti import fixtures

SHAPES = """@prefix sh: <http://www.w3.org/ns/shacl#> .
@prefix example: <https://example.org/example/> .

example:TaskHasList
  a sh:NodeShape ;
  sh:targetClass example:Task ;
  sh:property [ sh:path example:list ; sh:minCount 1 ] .
"""

VIOLATING = """@prefix example: <https://example.org/example/> .

<https://example.org/example/data/t1> a example:Task .
"""

CONFORMING = """@prefix example: <https://example.org/example/> .

<https://example.org/example/data/t1> a example:Task ; example:list "inbox" .
"""

needs_pyshacl = pytest.mark.skipif(shutil.which("pyshacl") is None, reason="pyshacl not installed")


def write(config, name: str, text: str) -> Path:
    (config.path("shapes") / "invariants.ttl").write_text(SHAPES, encoding="utf-8")
    path = config.path("data_invalid") / name
    path.write_text(text, encoding="utf-8")
    return path


@needs_pyshacl
def test_a_violating_fixture_names_its_shape(config) -> None:
    outcome = fixtures.validate(config, write(config, "D1.ttl", VIOLATING))
    assert not outcome.conforms
    assert "example:TaskHasList" in outcome.shapes


@needs_pyshacl
def test_a_conforming_fixture_proves_nothing(config) -> None:
    outcome = fixtures.validate(config, write(config, "D2.ttl", CONFORMING))
    assert outcome.conforms
    assert outcome.shapes == frozenset()


def test_a_yaml_fixture_without_a_class_is_an_error(config) -> None:
    path = config.path("data_invalid") / "D3.yaml"
    path.write_text("id: t1\n", encoding="utf-8")
    outcome = fixtures.validate(config, path)
    assert outcome.error is not None
    assert "fixture_class" in outcome.error
