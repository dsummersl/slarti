from __future__ import annotations

import pytest

from slarti import inject

DOCUMENT = """# Doc

<!-- slarti:begin constraints -->
old body
<!-- slarti:end constraints -->

tail
"""


def test_regions_are_found_in_order() -> None:
    regions = inject.regions(DOCUMENT)
    assert [r.name for r in regions] == ["constraints"]
    assert regions[0].body == "old body"
    assert regions[0].line == 3


def test_unbalanced_markers_are_an_error() -> None:
    with pytest.raises(inject.MarkerError):
        inject.regions("<!-- slarti:begin constraints -->\nno close\n")


def test_mismatched_close_is_an_error() -> None:
    text = "<!-- slarti:begin a -->\n<!-- slarti:end b -->\n"
    with pytest.raises(inject.MarkerError):
        inject.regions(text)


def test_replace_is_idempotent() -> None:
    once = inject.replace(DOCUMENT, "constraints", "new body")
    twice = inject.replace(once, "constraints", "new body")
    assert once == twice
    assert "old body" not in once
    assert inject.regions(once)[0].body == "new body"


def test_replace_keeps_the_prose() -> None:
    updated = inject.replace(DOCUMENT, "constraints", "x")
    assert updated.startswith("# Doc")
    assert updated.endswith("tail\n")


def test_replace_of_an_unknown_region_is_an_error() -> None:
    with pytest.raises(inject.MarkerError):
        inject.replace(DOCUMENT, "ownership", "x")
