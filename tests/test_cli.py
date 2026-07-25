from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from slarti import runner
from slarti.checks import delegated
from slarti.cli import app
from slarti.findings import Finding, Report
from slarti.proc import Result
from tests.conftest import make_models

RUNNER = CliRunner()


def test_init_scaffolds_and_reports(tmp_path: Path) -> None:
    result = RUNNER.invoke(app, ["init", str(tmp_path)])
    assert result.exit_code == 0
    assert "created slarti.toml" in result.stdout


def test_explain_describes_a_check() -> None:
    result = RUNNER.invoke(app, ["explain", "OWN-3"])
    assert result.exit_code == 0
    assert "does not claim it back" in result.stdout


def test_check_without_a_project_is_an_environment_error(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    result = RUNNER.invoke(app, ["check"])
    assert result.exit_code == 2
    assert "slarti init" in result.stdout + str(result.stderr)


def stub_context(tmp_path: Path, constraints=()) -> runner.Context:
    models = make_models(tmp_path)
    models.config.path("constraints").write_text("constraints: []\n", encoding="utf-8")
    return runner.Context(config=models.config, models=models, constraints=list(constraints))


def test_check_reports_findings_and_exits_one(tmp_path: Path, monkeypatch) -> None:
    ctx = stub_context(tmp_path)
    monkeypatch.setattr("slarti.cli._context", lambda: ctx)
    finding = Finding("OWN-1", "error", "f", "Task", "class 'Task' has no owner.", "Add an owner.")
    monkeypatch.setattr(runner, "check", lambda ctx, include_docs=True: (_report(finding), True))
    result = RUNNER.invoke(app, ["check"])
    assert result.exit_code == 1
    assert "OWN-1" in result.stdout


def _report(finding: Finding) -> Report:
    return Report([finding], checked=1)


def test_delegated_failures_fail_the_run(tmp_path: Path, monkeypatch) -> None:
    ctx = stub_context(tmp_path)
    monkeypatch.setattr("slarti.cli._context", lambda: ctx)
    monkeypatch.setattr(runner, "check", lambda ctx, include_docs=True: (Report(), False))
    assert RUNNER.invoke(app, ["check"]).exit_code == 1


def test_delegated_diagnostics_pass_through(capsys) -> None:
    failure = delegated.Delegation("likec4", ["likec4"], Result(1, "out\n", "err\n"))
    assert not delegated.report([failure])
    captured = capsys.readouterr()
    assert captured.out == "out\n"
    assert captured.err == "err\n"


def test_passing_delegations_say_nothing(capsys) -> None:
    ok = delegated.Delegation("likec4", ["likec4"], Result(0, "quiet\n", ""))
    assert delegated.report([ok])
    assert capsys.readouterr().out == ""
