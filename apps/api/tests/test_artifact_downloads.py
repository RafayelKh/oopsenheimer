import json
from pathlib import Path

from fastapi.testclient import TestClient

import app.main as main
from app.services.store import InMemoryStore


def create_completed_simulation(tmp_path: Path) -> tuple[TestClient, str]:
    main.store = InMemoryStore(tmp_path)
    client = TestClient(main.app)
    scene_path = Path(__file__).resolve().parents[3] / "packages" / "examples" / "lead_wall.scene.json"
    scene = json.loads(scene_path.read_text())
    scene_response = client.post("/scenes", json=scene)
    simulation_response = client.post(
        "/simulations",
        json={"sceneId": scene_response.json()["id"]},
    )
    return client, simulation_response.json()["id"]


def test_can_download_scene_inp_and_manifest(tmp_path: Path) -> None:
    client, simulation_id = create_completed_simulation(tmp_path)

    inp_response = client.get(f"/simulations/{simulation_id}/artifacts/scene.inp")
    manifest_response = client.get(f"/simulations/{simulation_id}/artifacts/scene.map.json")

    assert inp_response.status_code == 200
    assert "START" in inp_response.text
    assert manifest_response.status_code == 200
    assert manifest_response.json()["schema"] == "oopsenheimer.manifest.v1"


def test_artifact_download_rejects_path_traversal(tmp_path: Path) -> None:
    client, simulation_id = create_completed_simulation(tmp_path)

    response = client.get(f"/simulations/{simulation_id}/artifacts/%2E%2E/scene.json")

    assert response.status_code == 400
