import json
from pathlib import Path
from types import SimpleNamespace

from celery._state import _set_task_join_will_block
from tasks import (
    _read_fluka_progress_file,
    _update_fluka_progress_from_output,
    compile_scene_task,
    enqueue_mock_pipeline,
    parse_results_task,
    run_fluka_task,
    status_path,
)
from worker import celery_app


def test_mock_tasks_update_status_and_create_placeholder_files(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr("tasks.settings.storage_root", tmp_path)
    celery_app.conf.task_always_eager = True
    simulation_id = "sim_001"
    scene_id = "scene_001"
    example_scene = Path(__file__).resolve().parents[3] / "packages" / "examples" / "lead_wall.scene.json"
    scene_dir = tmp_path / "scenes" / scene_id
    scene_dir.mkdir(parents=True)
    (scene_dir / "scene.json").write_text(example_scene.read_text())
    (tmp_path / "jobs" / simulation_id).mkdir(parents=True)
    status_path(simulation_id).write_text(
        json.dumps(
            {
                "simulationId": simulation_id,
                "sceneId": scene_id,
                "status": "queued",
                "storagePath": str(tmp_path / "jobs" / simulation_id),
            },
            indent=2,
        )
        + "\n"
    )

    compile_scene_task.delay(simulation_id)
    run_fluka_task.delay(simulation_id)
    parse_results_task.delay(simulation_id)

    status = json.loads(status_path(simulation_id).read_text())
    assert status["status"] == "completed"
    assert (tmp_path / "jobs" / simulation_id / "scene.inp").exists()
    assert (tmp_path / "jobs" / simulation_id / "scene.vxl").exists()
    assert (tmp_path / "jobs" / simulation_id / "scene.map.json").exists()
    assert (tmp_path / "jobs" / simulation_id / "scene.meta.json").exists()
    assert (tmp_path / "jobs" / simulation_id / "parsed" / "dose_map.json").exists()


def test_local_pipeline_does_not_join_celery_results(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr("tasks.settings.storage_root", tmp_path)
    monkeypatch.setattr("tasks.settings.sim_mode", "mock")
    simulation_id = "sim_pipeline"
    scene_id = "scene_pipeline"
    example_scene = Path(__file__).resolve().parents[3] / "packages" / "examples" / "lead_wall.scene.json"
    scene_dir = tmp_path / "scenes" / scene_id
    scene_dir.mkdir(parents=True)
    (scene_dir / "scene.json").write_text(example_scene.read_text())
    (tmp_path / "jobs" / simulation_id).mkdir(parents=True)
    status_path(simulation_id).write_text(
        json.dumps(
            {
                "simulationId": simulation_id,
                "sceneId": scene_id,
                "status": "queued",
                "storagePath": str(tmp_path / "jobs" / simulation_id),
            },
            indent=2,
        )
        + "\n"
    )

    _set_task_join_will_block(True)
    try:
        enqueue_mock_pipeline(simulation_id)
    finally:
        _set_task_join_will_block(False)

    status = json.loads(status_path(simulation_id).read_text())
    assert status["status"] == "completed"
    assert status["progressPercent"] == 100


def test_running_status_can_track_fluka_particle_progress(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr("tasks.settings.storage_root", tmp_path)
    simulation_id = "sim_fluka_progress"
    job_dir = tmp_path / "jobs" / simulation_id
    fluka_dir = job_dir / "fluka_123"
    fluka_dir.mkdir(parents=True)
    (fluka_dir / "scene001.out").write_text(
        " NEXT SEEDS:       0       0       0\n"
        "      54000                 46000                 46000             8.9045632E-04\n"
    )
    status_path(simulation_id).write_text(
        json.dumps(
            {
                "simulationId": simulation_id,
                "sceneId": "scene_001",
                "status": "running",
                "progressPercent": 35,
                "progressMessage": "Running FLUKA",
                "storagePath": str(job_dir),
            },
            indent=2,
        )
        + "\n"
    )

    _update_fluka_progress_from_output(simulation_id)

    status = json.loads(status_path(simulation_id).read_text())
    assert status["status"] == "running"
    assert status["progressPercent"] == 63
    assert status["progressMessage"] == "Running FLUKA (54% particles)"


def test_fluka_progress_parser_uses_latest_particle_line(tmp_path) -> None:
    output = tmp_path / "scene001.out"
    output.write_text(
        "      52000                 48000                 48000             1.0E-03\n"
        " NEXT SEEDS: 260A985C       0       0       0\n"
        "      54000                 46000                 46000             1.0E-03\n"
    )

    assert _read_fluka_progress_file(output) == (54000, 100000)


def test_compile_scene_task_captures_errors(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr("tasks.settings.storage_root", tmp_path)
    simulation_id = "sim_bad"
    (tmp_path / "jobs" / simulation_id).mkdir(parents=True)
    status_path(simulation_id).write_text(
        json.dumps(
            {
                "simulationId": simulation_id,
                "sceneId": "missing_scene",
                "status": "queued",
                "storagePath": str(tmp_path / "jobs" / simulation_id),
            },
            indent=2,
        )
        + "\n"
    )

    compile_scene_task(simulation_id)

    status = json.loads(status_path(simulation_id).read_text())
    assert status["status"] == "failed"
    assert "scene JSON not found" in status["errorMessage"]


def test_run_fluka_task_real_mode_fails_clearly_without_fluka_bin(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr("tasks.settings.storage_root", tmp_path)
    monkeypatch.setattr("tasks.settings.sim_mode", "fluka")
    monkeypatch.delenv("FLUKA_BIN", raising=False)
    simulation_id = "sim_no_fluka"
    (tmp_path / "jobs" / simulation_id).mkdir(parents=True)
    status_path(simulation_id).write_text(
        json.dumps(
            {
                "simulationId": simulation_id,
                "sceneId": "scene_001",
                "status": "compiled",
                "storagePath": str(tmp_path / "jobs" / simulation_id),
            },
            indent=2,
        )
        + "\n"
    )

    run_fluka_task(simulation_id)

    status = json.loads(status_path(simulation_id).read_text())
    assert status["status"] == "failed"
    assert "FLUKA_BIN is not set" in status["errorMessage"]
    monkeypatch.setattr("tasks.settings.sim_mode", "mock")


def test_mocked_rfluka_success_reaches_parsing(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr("tasks.settings.storage_root", tmp_path)
    monkeypatch.setattr("tasks.settings.sim_mode", "fluka")
    monkeypatch.setenv("FLUKA_BIN", "/opt/fluka/bin")
    simulation_id = "sim_fluka_success"
    job_dir = tmp_path / "jobs" / simulation_id
    job_dir.mkdir(parents=True)
    status_path(simulation_id).write_text(
        json.dumps(
            {
                "simulationId": simulation_id,
                "sceneId": "scene_001",
                "status": "compiled",
                "storagePath": str(job_dir),
            },
            indent=2,
        )
        + "\n"
    )

    import runner

    def fake_run_rfluka(job_dir, input_file, cycles, timeout_seconds):
        return SimpleNamespace(exit_code=0)

    monkeypatch.setattr(runner, "run_rfluka", fake_run_rfluka)

    run_fluka_task(simulation_id)

    status = json.loads(status_path(simulation_id).read_text())
    assert status["status"] == "parsing"
    monkeypatch.setattr("tasks.settings.sim_mode", "mock")


def test_rfluka_nonzero_with_usrbin_output_reaches_parsing(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr("tasks.settings.storage_root", tmp_path)
    monkeypatch.setattr("tasks.settings.sim_mode", "fluka")
    monkeypatch.setenv("FLUKA_BIN", "/opt/fluka/bin")
    simulation_id = "sim_fluka_nonzero_with_output"
    job_dir = tmp_path / "jobs" / simulation_id
    job_dir.mkdir(parents=True)
    usrbin = job_dir / "scene001_fort.21"
    usrbin.write_text("output")
    status_path(simulation_id).write_text(
        json.dumps(
            {
                "simulationId": simulation_id,
                "sceneId": "scene_001",
                "status": "compiled",
                "storagePath": str(job_dir),
            },
            indent=2,
        )
        + "\n"
    )

    import runner

    def fake_run_rfluka(job_dir, input_file, cycles, timeout_seconds):
        return SimpleNamespace(exit_code=12, output_files=[usrbin])

    monkeypatch.setattr(runner, "run_rfluka", fake_run_rfluka)

    run_fluka_task(simulation_id)

    status = json.loads(status_path(simulation_id).read_text())
    assert status["status"] == "parsing"
    monkeypatch.setattr("tasks.settings.sim_mode", "mock")


def test_rfluka_nonzero_reports_scene_error_log(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr("tasks.settings.storage_root", tmp_path)
    monkeypatch.setattr("tasks.settings.sim_mode", "fluka")
    monkeypatch.setenv("FLUKA_BIN", "/opt/fluka/bin")
    simulation_id = "sim_fluka_error_log"
    job_dir = tmp_path / "jobs" / simulation_id
    logs_dir = job_dir / "logs"
    logs_dir.mkdir(parents=True)
    stderr_log = logs_dir / "rfluka.stderr.log"
    stdout_log = logs_dir / "rfluka.stdout.log"
    stderr_log.write_text("")
    stdout_log.write_text("Error: No ranscene002 generated!\n")
    (job_dir / "scene001.err").write_text(
        "\n *** Unable to resolve name element CONCRETE in card ***\n"
        " ASSIGNMA    CONCRETE   R000008\n"
        " *** run stopped ***\n"
    )
    status_path(simulation_id).write_text(
        json.dumps(
            {
                "simulationId": simulation_id,
                "sceneId": "scene_001",
                "status": "compiled",
                "storagePath": str(job_dir),
            },
            indent=2,
        )
        + "\n"
    )

    import runner

    def fake_run_rfluka(job_dir, input_file, cycles, timeout_seconds):
        return SimpleNamespace(
            exit_code=12,
            output_files=[],
            stderr_log=stderr_log,
            stdout_log=stdout_log,
        )

    monkeypatch.setattr(runner, "run_rfluka", fake_run_rfluka)

    run_fluka_task(simulation_id)

    status = json.loads(status_path(simulation_id).read_text())
    assert status["status"] == "failed"
    assert "scene001.err" in status["errorMessage"]
    assert "Unable to resolve name element CONCRETE" in status["errorMessage"]
    monkeypatch.setattr("tasks.settings.sim_mode", "mock")
