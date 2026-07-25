from __future__ import annotations

from dataclasses import dataclass

from slarti import proc
from slarti.config import Config


@dataclass(frozen=True)
class Delegation:
    """One delegated validation and the exit code it returned."""

    tool: str
    argv: list[str]
    result: proc.Result

    @property
    def ok(self) -> bool:
        return self.result.code == 0


def likec4_validate(config: Config) -> Delegation:
    argv = proc.likec4(["validate", str(config.path("arch"))])
    return Delegation("likec4", argv, proc.run(argv, cwd=config.root))


def linkml_lint(config: Config) -> list[Delegation]:
    delegations = []
    for schema in config.schema_files():
        argv = ["linkml", "lint", str(config.rel(schema))]
        delegations.append(Delegation("linkml", argv, proc.run(argv, cwd=config.root)))
    return delegations


def run_all(config: Config) -> list[Delegation]:
    """Run every delegated validation; slarti reimplements none of them (I2)."""
    return [likec4_validate(config), *linkml_lint(config)]


def report(delegations: list[Delegation]) -> bool:
    """Pass every delegated diagnostic through unaltered; True if all passed."""
    ok = True
    for delegation in delegations:
        if not delegation.ok:
            ok = False
            proc.passthrough(delegation.result)
    return ok
