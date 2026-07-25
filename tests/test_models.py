from __future__ import annotations

from pathlib import Path

from slarti import models as models_module
from slarti.explain import CHECKS, explain

PAYLOAD = {
    "elements": {
        "todo.db": {
            "id": "todo.db",
            "title": "DB",
            "kind": "container",
            "metadata": {"owns": "Task, TodoList"},
        },
        "todo": {"id": "todo", "title": "Todo", "kind": "system"},
    },
    "relations": {
        "r1": {
            "id": "r1",
            "title": "reads",
            "source": {"model": "todo"},
            "target": {"model": "todo.db"},
        },
    },
    "views": {"index": {}},
}

SHAPE = """@prefix sh: <http://www.w3.org/ns/shacl#> .
@prefix todo: <https://example.org/todo/> .

todo:UniqueMembership
  a sh:NodeShape ;
  sh:targetClass todo:Membership ;
  sh:property [ sh:path todo:list ; sh:minCount 1 ] .
"""


def test_export_payload_is_parsed_and_sorted() -> None:
    model = models_module.parse_likec4(PAYLOAD)
    assert list(model.elements) == ["todo", "todo.db"]
    assert model.elements["todo.db"].owns == ("Task", "TodoList")
    assert model.has_relation("todo", "todo.db")
    assert not model.has_relation("todo.db", "todo")
    assert model.views == ("index",)


def test_owners_of_reads_the_seam_backwards() -> None:
    model = models_module.parse_likec4(PAYLOAD)
    assert model.owners_of("Task") == ["todo.db"]
    assert model.owners_of("Ghost") == []


def test_shape_names_are_curies(tmp_path: Path) -> None:
    path = tmp_path / "invariants.ttl"
    path.write_text(SHAPE, encoding="utf-8")
    found = models_module.shape_names([path])
    assert list(found) == ["todo:UniqueMembership"]
    assert models_module.shape_line(path, "todo:UniqueMembership") == 4


def test_every_check_id_can_be_explained() -> None:
    for identifier in CHECKS:
        assert "Remedy" in explain(identifier) or "remedy" in explain(identifier)
    assert explain("own-1") is not None
    assert explain("NOPE-9") is None
