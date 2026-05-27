import json
from pathlib import Path

from fastapi.testclient import TestClient

import app.main as main
from app.services.store import InMemoryStore


def test_post_simulations_completes_mock_job(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("STORAGE_ROOT", str(tmp_path))
    main.store = InMemoryStore(tmp_path)
    client = TestClient(main.app)
    scene_path = Path(__file__).resolve().parents[3] / "packages" / "examples" / "lead_wall.scene.json"
    scene = json.loads(scene_path.read_text())

    scene_response = client.post("/scenes", json=scene)
    assert scene_response.status_code == 200

    simulation_response = client.post(
        "/simulations",
        json={"sceneId": scene_response.json()["id"]},
    )
    assert simulation_response.status_code == 200
    simulation = simulation_response.json()
    assert simulation["status"] == "queued"
    assert simulation["progressPercent"] == 0

    refreshed_response = client.get(f"/simulations/{simulation['id']}")
    assert refreshed_response.status_code == 200
    refreshed = refreshed_response.json()
    assert refreshed["status"] == "completed"
    assert refreshed["progressPercent"] == 100

    artifacts_response = client.get(f"/simulations/{simulation['id']}/artifacts")
    assert artifacts_response.status_code == 200
    artifacts = artifacts_response.json()
    assert "parsed/dose_map.json" in artifacts["artifacts"]
    assert artifacts["parsedResult"]["quantity"] == "DOSE"
