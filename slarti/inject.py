from __future__ import annotations

import re

from slarti.domain import Region

BEGIN = "<!-- slarti:begin {region} -->"
END = "<!-- slarti:end {region} -->"
BEGIN_RE = re.compile(r"<!--\s*slarti:begin\s+(?P<region>[^\s>]+)\s*-->")
END_RE = re.compile(r"<!--\s*slarti:end\s+(?P<region>[^\s>]+)\s*-->")


class MarkerError(Exception):
    """Raised when generated-region markers are malformed."""


def _line_of(text: str, index: int) -> int:
    return text.count("\n", 0, index) + 1


def regions(text: str) -> list[Region]:
    """Every generated region in document order. Raises on unbalanced markers."""
    found: list[Region] = []
    position = 0
    while (begin := BEGIN_RE.search(text, position)) is not None:
        end = END_RE.search(text, begin.end())
        name = begin.group("region")
        if end is None or end.group("region") != name:
            raise MarkerError(f"Region '{name}' is opened but never closed with a matching marker.")
        found.append(
            Region(
                name=name,
                body=text[begin.end() : end.start()].strip("\n"),
                line=_line_of(text, begin.start()),
            )
        )
        position = end.end()
    return found


def replace(text: str, region: str, body: str) -> str:
    """Replace a region's body wholesale — no append path, idempotent by construction."""
    pattern = re.compile(
        re.escape(BEGIN.format(region=region)).replace(r"\ ", r"\s+")
        + r".*?"
        + re.escape(END.format(region=region)).replace(r"\ ", r"\s+"),
        re.DOTALL,
    )
    replacement = "\n".join([BEGIN.format(region=region), "", body, "", END.format(region=region)])
    updated, count = pattern.subn(lambda _: replacement, text)
    if count == 0:
        raise MarkerError(f"No region named '{region}' in the document.")
    return updated
