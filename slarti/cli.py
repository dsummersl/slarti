from __future__ import annotations

import sys
from pathlib import Path

import typer

from slarti import config as config_module
from slarti import docs, env, report, runner, scaffold
from slarti.checks import doc_checks
from slarti.domain import Probe
from slarti.models import ModelError
from slarti.registry import RegistryError

app = typer.Typer(add_completion=False, help="Coordination CLI for validated architecture docs.")

EXIT_CLEAN = 0
EXIT_FINDINGS = 1
EXIT_ENVIRONMENT = 2

DIRECTORY_ARGUMENT = typer.Argument(Path("."), help="Project root.")


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


def _probe_line(probe: Probe) -> str:
    mark = "ok  " if probe.ok else "FAIL"
    return f"{mark} {probe.tool:8} {(probe.version or '-'):10} {probe.location or '-'}"


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


@app.command(name="report")
def report_command(
    json_output: bool = typer.Option(False, "--json", help="The whole report, fully detailed."),
) -> None:
    """Every rule, shape, owned class and check ID slarti knows about."""
    ctx = _context()
    result = report.build(ctx.models, ctx.constraints)
    typer.echo(result.as_json() if json_output else result.as_text())
    raise typer.Exit(EXIT_FINDINGS if result.orphaned else EXIT_CLEAN)


def main() -> None:
    sys.exit(app())


__all__ = ["app", "main"]
