import os
import subprocess
from pathlib import Path

import pytest

from runner import FlukaRunnerError, run_rfluka


def test_run_rfluka_fails_clearly_without_fluka_bin(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.delenv("FLUKA_BIN", raising=False)

    with pytest.raises(FlukaRunnerError, match="FLUKA_BIN is not set"):
        run_rfluka(tmp_path, "scene.inp", cycles=1, timeout_seconds=1)


def test_run_rfluka_captures_success_logs_and_outputs(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("FLUKA_BIN", "/opt/fluka/bin")

    def fake_run(command, cwd, text, capture_output, timeout, check):
        Path(cwd, "fort.21").write_text("output")
        return subprocess.CompletedProcess(command, 0, stdout="ok\n", stderr="")

    monkeypatch.setattr(subprocess, "run", fake_run)

    result = run_rfluka(tmp_path, "scene.inp", cycles=5, timeout_seconds=10)

    assert result.command == ["/opt/fluka/bin/rfluka", "-M", "5", "scene.inp"]
    assert result.exit_code == 0
    assert result.stdout_log.read_text() == "ok\n"
    assert tmp_path / "fort.21" in result.output_files


def test_run_rfluka_captures_nonzero_exit(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("FLUKA_BIN", "/opt/fluka/bin")

    def fake_run(command, cwd, text, capture_output, timeout, check):
        return subprocess.CompletedProcess(command, 42, stdout="", stderr="bad input\n")

    monkeypatch.setattr(subprocess, "run", fake_run)

    result = run_rfluka(tmp_path, "scene.inp", cycles=1, timeout_seconds=10)

    assert result.exit_code == 42
    assert result.stderr_log.read_text() == "bad input\n"
