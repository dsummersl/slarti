from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Literal

from slarti import __version__

Severity = Literal["error", "warning"]


@dataclass(frozen=True)
class Finding:
    """A single machine-readable check result."""

    id: str
    severity: Severity
    file: str
    subject: str
    message: str
    remedy: str
    line: int | None = None

    def as_dict(self) -> dict[str, Any]:
        data: dict[str, Any] = {
            "id": self.id,
            "severity": self.severity,
            "file": self.file,
            "subject": self.subject,
            "message": self.message,
            "remedy": self.remedy,
        }
        if self.line is not None:
            data["line"] = self.line
        return data


@dataclass
class Report:
    """A run's findings plus the count of checks performed."""

    findings: list[Finding] = field(default_factory=list)
    checked: int = 0

    def add(self, finding: Finding) -> None:
        self.findings.append(finding)

    def extend(self, findings: list[Finding]) -> None:
        self.findings.extend(findings)

    @property
    def errors(self) -> int:
        return sum(1 for f in self.findings if f.severity == "error")

    @property
    def warnings(self) -> int:
        return sum(1 for f in self.findings if f.severity == "warning")

    def sorted_findings(self) -> list[Finding]:
        return sorted(self.findings, key=lambda f: (f.id, f.file, f.subject))

    def as_json(self) -> str:
        payload = {
            "seam_version": __version__,
            "findings": [f.as_dict() for f in self.sorted_findings()],
            "summary": {
                "errors": self.errors,
                "warnings": self.warnings,
                "checked": self.checked,
            },
        }
        return json.dumps(payload, indent=2, sort_keys=False)

    def as_text(self) -> str:
        if not self.findings:
            return f"No findings ({self.checked} checks)."
        lines = []
        for f in self.sorted_findings():
            where = f.file if f.line is None else f"{f.file}:{f.line}"
            lines.append(f"{f.severity}: [{f.id}] {where}: {f.message}")
            lines.append(f"  remedy: {f.remedy}")
        lines.append(f"{self.errors} error(s), {self.warnings} warning(s), {self.checked} checks.")
        return "\n".join(lines)
