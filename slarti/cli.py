from __future__ import annotations

import sys
from pathlib import Path

import typer

from slarti import config as config_module
from slarti import docs, env, resolvers, runner, scaffold
from slarti import explain as explain_module
from slarti.checks import doc_checks
from slarti.models import ModelError
from slarti.registry import RegistryError

app = typer.Typer(add_completion=False, help="Coordination CLI for validated architecture docs.")

EXIT_CLEAN = 0
EXIT_FINDINGS = 1
EXIT_ENVIRONMENT = 2

DIRECTORY_ARGUMENT = typer.Argument(Path("."), help="Project root.")
ID_ARGUMENT = typer.Argument(..., help="A check ID or a constraint ID.")


def _load() -> config_module.Config:
    try:
        return config_module.load()
    except config_module.ConfigError as exc:
        typer.secho(str(exc), fg="red", err=True)
        raise typer.Exit(EXIT_ENVIRONMENT) from exc


def _gate() -> None:
    probes = env.probe_all()
    failures = env.env_findings(probes)
    if failures:
        for finding in failures:
            typer.secho(f"[{finding.id}] {finding.message}", fg="red", err=True)
        raise typer.Exit(EXIT_ENVIRONMENT)


def _context() -> runner.Context:
    cfg = _load()
    _gate()
    try:
        return runner.context(cfg)
    except (RegistryError, ModelError) as exc:
        typer.secho(str(exc), fg="red", err=True)
        raise typer.Exit(EXIT_ENVIRONMENT) from exc


@app.command()
def init(directory: Path = DIRECTORY_ARGUMENT) -> None:
    """Scaffold the conventional layout. Never overwrites an existing file."""
    result = scaffold.init(directory)
    for name in result.written:
        typer.echo(f"created {name}")
    for name in result.skipped:
        typer.secho(f"kept    {name} (already exists)", fg="yellow")


@app.command()
def doctor() -> None:
    """Probe every delegated tool: version, location, supported range."""
    probes = env.probe_all()
    for probe in probes:
        typer.echo(_probe_line(probe))
        typer.echo(f"     {probe.detail}")
    raise typer.Exit(EXIT_CLEAN if all(p.ok for p in probes) else EXIT_ENVIRONMENT)


def _probe_line(probe: env.Probe) -> str:
    mark = "ok  " if probe.ok else "FAIL"
    return f"{mark} {probe.tool:8} {probe.version_text:10} {probe.location or '-'}"


@app.command()
def check(
    json_output: bool = typer.Option(False, "--json", help="Structured findings on stdout."),
    skip_docs: bool = typer.Option(False, "--no-docs", help="Skip the DOC-* checks."),
) -> None:
    """Run delegated validations, then every slarti check. The CI command."""
    ctx = _context()
    report, delegated_ok = runner.check(ctx, include_docs=not skip_docs)
    typer.echo(report.as_json() if json_output else report.as_text())
    failed = report.errors > 0 or not delegated_ok
    raise typer.Exit(EXIT_FINDINGS if failed else EXIT_CLEAN)


@app.command(name="docs")
def docs_command(
    check_only: bool = typer.Option(False, "--check", help="Fail if the committed tree drifts."),
) -> None:
    """Regenerate diagrams and registry tables, and inject them into the document."""
    ctx = _context()
    if check_only:
        _docs_check(ctx)
    rendered = docs.write(ctx.config, ctx.constraints, ctx.models)
    for name in rendered.regions:
        typer.echo(f"generated {name}")


def _docs_check(ctx: runner.Context) -> None:
    findings = doc_checks.check(ctx.config, ctx.models, ctx.constraints)
    for finding in findings:
        typer.secho(f"[{finding.id}] {finding.file}: {finding.message}", fg="red", err=True)
    raise typer.Exit(EXIT_FINDINGS if findings else EXIT_CLEAN)


@app.command()
def dangling() -> None:
    """Report enforced rules, unenforced rules and orphaned shapes."""
    ctx = _context()
    result = runner.dangling(ctx)
    typer.echo("Enforced:")
    for c in result.enforced:
        enforcer = resolvers.describe(c.enforcer)
        typer.echo(f"  {c.id}  {c.statement}  <- {c.enforcer.kind} {enforcer}")
    typer.echo("Unenforced (declared, with a reason):")
    for c in result.unenforced:
        typer.echo(f"  {c.id}  {c.statement}")
    typer.echo("Orphaned shapes (enforced, unreferenced):")
    for shape in result.orphaned:
        typer.echo(f"  {shape}")
    raise typer.Exit(EXIT_FINDINGS if result.orphaned else EXIT_CLEAN)


@app.command()
def explain(identifier: str = ID_ARGUMENT) -> None:
    """Describe a check or constraint ID, with its remedy. Primarily for agents."""
    text = explain_module.explain(identifier)
    if text is not None:
        typer.echo(f"{identifier.upper()}\n{text}")
        raise typer.Exit(EXIT_CLEAN)
    typer.echo(_explain_constraint(identifier))


def _explain_constraint(identifier: str) -> str:
    ctx = _context()
    for c in ctx.constraints:
        if c.id.lower() == identifier.lower():
            enforcer = resolvers.describe(c.enforcer)
            reason = f"\nUnenforced because: {c.reason}" if c.enforcer.is_none else ""
            kind = c.enforcer.kind or "none"
            return f"{c.id}\n{c.statement}\nEnforced by: {kind} {enforcer}{reason}"
    typer.secho(f"Unknown ID: {identifier}", fg="red", err=True)
    raise typer.Exit(EXIT_ENVIRONMENT)


def main() -> None:
    sys.exit(app())


__all__ = ["app", "main"]
