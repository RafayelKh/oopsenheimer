from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.models import Base, JobStatus, Scene, SimulationJob


def test_tables_can_be_created() -> None:
    engine = create_engine("sqlite:///:memory:")

    Base.metadata.create_all(engine)

    assert "scenes" in Base.metadata.tables
    assert "simulation_jobs" in Base.metadata.tables


def test_scene_can_be_inserted() -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)

    with Session(engine) as session:
        scene = Scene(name="lead_wall_demo", scene_json={"schema": "oopsenheimer.scene.v1"})
        session.add(scene)
        session.commit()

        inserted = session.scalar(select(Scene).where(Scene.name == "lead_wall_demo"))

    assert inserted is not None
    assert inserted.scene_json["schema"] == "oopsenheimer.scene.v1"


def test_simulation_job_can_be_inserted_and_status_updated() -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)

    with Session(engine) as session:
        scene = Scene(name="lead_wall_demo", scene_json={"schema": "oopsenheimer.scene.v1"})
        session.add(scene)
        session.flush()

        job = SimulationJob(
            scene_id=scene.id,
            status=JobStatus.QUEUED.value,
            storage_path="storage/jobs/job_001",
            histories=100000,
            cycles=1,
        )
        session.add(job)
        session.commit()

        job.status = JobStatus.COMPLETED.value
        session.commit()

        inserted = session.scalar(select(SimulationJob).where(SimulationJob.id == job.id))

    assert inserted is not None
    assert inserted.status == "completed"
