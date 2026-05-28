import os
from pathlib import Path

import pytest

from runner import FlukaRunnerError, run_rfluka


def test_run_rfluka_fails_clearly_without_fluka_bin(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.delenv("FLUKA_BIN", raising=False)

    with pytest.raises(FlukaRunnerError, match="FLUKA_BIN is not set"):
        run_rfluka(tmp_path, "scene.inp", cycles=1, timeout_seconds=1)


def test_run_rfluka_captures_success_logs_and_outputs(tmp_path: Path, monkeypatch) -> None:
    fluka_bin = make_fluka_bin(tmp_path, "echo ok\ntouch fort.21\n")
    monkeypatch.setenv("FLUKA_BIN", str(fluka_bin))

    result = run_rfluka(tmp_path, "scene.inp", cycles=5, timeout_seconds=10)

    assert result.command == [str(fluka_bin / "rfluka"), "-M", "5", "scene.inp"]
    assert result.exit_code == 0
    assert result.stdout_log.read_text() == "ok\n"
    assert tmp_path / "fort.21" in result.output_files


def test_run_rfluka_captures_nonzero_exit(tmp_path: Path, monkeypatch) -> None:
    fluka_bin = make_fluka_bin(tmp_path, "echo 'bad input' >&2\nexit 42\n")
    monkeypatch.setenv("FLUKA_BIN", str(fluka_bin))

    result = run_rfluka(tmp_path, "scene.inp", cycles=1, timeout_seconds=10)

    assert result.exit_code == 42
    assert result.stderr_log.read_text() == "bad input\n"


def test_run_rfluka_times_out_and_records_failure(tmp_path: Path, monkeypatch) -> None:
    fluka_bin = make_fluka_bin(tmp_path, "sleep 10\n")
    monkeypatch.setenv("FLUKA_BIN", str(fluka_bin))

    result = run_rfluka(tmp_path, "scene.inp", cycles=1, timeout_seconds=1)

    assert result.exit_code == -1
    assert "timed out after 1s" in result.stderr_log.read_text()


def test_run_rfluka_kills_stalled_run_without_particle_progress(tmp_path: Path, monkeypatch) -> None:
    fluka_bin = make_fluka_bin(tmp_path, "sleep 10\n")
    monkeypatch.setenv("FLUKA_BIN", str(fluka_bin))

    result = run_rfluka(tmp_path, "scene.inp", cycles=1, timeout_seconds=10, stall_timeout_seconds=1)

    assert result.exit_code == -2
    assert "stalled after 1s without particle progress" in result.stderr_log.read_text()


def make_fluka_bin(tmp_path: Path, body: str) -> Path:
    fluka_bin = tmp_path / "fluka-bin"
    fluka_bin.mkdir()
    rfluka = fluka_bin / "rfluka"
    rfluka.write_text(f"#!/bin/sh\n{body}")
    os.chmod(rfluka, 0o755)
    return fluka_bin
