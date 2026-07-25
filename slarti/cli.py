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

app = typer.Typer(
    add_completion=False,
    no_args_is_help=True,
    help=(
        "Coordination CLI for validated architecture docs.\n"
        "\n"
        "Default paths (see 'slarti doctor' for actual):\n"
        "  docs/slarti/{likec4/*.c4, linkml/*.yaml, shacl/*.ttl, constraints.yaml}\n"
        "Config: slarti.toml (preferred) or the tool.slarti section of pyproject.toml.\n"
        "Typical workflow: init → doctor → check → docs, then report for details."
    ),
)

EXIT_CLEAN = 0
EXIT_FINDINGS = 1
EXIT_ENVIRONMENT = 2

DIRECTORY_ARGUMENT = typer.Argument(Path("."), help="Project root.")


def _load() -> config_module.Config:
    return _load_config()


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


_PATH_DESCRIPTIONS: dict[str, str] = {
    "likec4": "LikeC4 architecture model sources (*.c4)",
    "linkml": "LinkML domain entity schemas (*.yaml)",
    "shacl": "SHACL shape files (*.ttl)",
    "shacl_valid": "Fixtures that must pass SHACL validation",
    "shacl_invalid": "Fixtures that must violate rules (one per rule)",
    "constraints": "Rule registry connecting rules to enforcers",
    "documents": "Architecture documents to generate",
    "diagrams": "Generated diagram images",
}


@app.command()
def init(directory: Path = DIRECTORY_ARGUMENT) -> None:
    """Scaffold slarti.toml, docs/slarti/, and architecture doc. Never overwrites."""
    result = scaffold.init(directory)
    for name in result.written:
        typer.echo(f"created {name}")
    for name in result.skipped:
        typer.secho(f"kept    {name} (already exists)", fg="yellow")


def _load_config() -> config_module.Config:
    try:
        return config_module.load()
    except config_module.ConfigError as exc:
        typer.secho(str(exc), fg="red", err=True)
        raise typer.Exit(EXIT_ENVIRONMENT) from exc


def _show_paths(cfg: config_module.Config) -> None:
    typer.echo(f"root: {cfg.root}")
    for key, value in sorted(cfg.paths.items()):
        desc = _PATH_DESCRIPTIONS.get(key, "")
        typer.echo(f"  {key:16} {value:40} {desc}")
    if cfg.documents:
        desc = _PATH_DESCRIPTIONS.get("documents", "")
        typer.echo(f"  {'documents':16} {str(cfg.documents):40} {desc}")


@app.command()
def doctor() -> None:
    """Show resolved project paths and probe every delegated tool."""
    cfg = _load_config()
    _show_paths(cfg)
    typer.echo("")
    probes = env.probe_all()
    for probe in probes:
        typer.echo(_probe_line(probe))
        typer.echo(f"     {probe.detail}")
    failed = any(not p.ok for p in probes)
    raise typer.Exit(EXIT_ENVIRONMENT if failed else EXIT_CLEAN)


def _probe_line(probe: Probe) -> str:
    mark = "ok  " if probe.ok else "FAIL"
    return f"{mark} {probe.tool:8} {(probe.version or '-'):10} {probe.location or '-'}"


@app.command()
def check(
    json_output: bool = typer.Option(False, "--json", help="Structured findings on stdout."),
    skip_docs: bool = typer.Option(False, "--no-docs", help="Skip the DOC-* checks."),
) -> None:
    """Validate model sources against all rules. Use --json. IDs: OWN-*, REG-*, DOC-*, ENV-*."""
    ctx = _context()
    report, delegated_ok = runner.check(ctx, include_docs=not skip_docs)
    typer.echo(report.as_json_verbose() if json_output else report.as_text())
    failed = report.errors > 0 or not delegated_ok
    raise typer.Exit(EXIT_FINDINGS if failed else EXIT_CLEAN)


@app.command(name="docs")
def docs_command(
    check_only: bool = typer.Option(False, "--check", help="Fail if the committed tree drifts."),
) -> None:
    """Regenerate architecture documents from model sources. --check exits non-zero if stale.

    Replaceable markers: diagram:<view>, ownership, constraints, unverified."""
    ctx = _context()
    if check_only:
        _docs_check(ctx)
    for rendered in docs.write(ctx.config, ctx.constraints, ctx.models):
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
    """Rules from constraints.yaml, every shape, class, and check ID. Use --json for detail."""
    ctx = _context()
    result = report.build(ctx.models, ctx.constraints)
    typer.echo(result.as_json() if json_output else result.as_text())
    raise typer.Exit(EXIT_FINDINGS if result.orphaned else EXIT_CLEAN)


def main() -> None:
    sys.exit(app())


__all__ = ["app", "main"]
