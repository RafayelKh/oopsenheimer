from fastapi.testclient import TestClient

from app.main import app


def test_get_lead_wall_example_returns_scene_json() -> None:
    response = TestClient(app).get("/examples/lead_wall")

    assert response.status_code == 200
    assert response.json()["schema"] == "oopsenheimer.scene.v1"


def test_get_examples_lists_demo_scenes() -> None:
    response = TestClient(app).get("/examples")

    assert response.status_code == 200
    example_ids = {example["id"] for example in response.json()}
    assert {
        "air_baseline",
        "lead_slab",
        "lead_aperture",
        "water_phantom",
        "house_occupant",
        "car",
        "bus",
    }.issubset(example_ids)


def test_get_unknown_example_returns_404() -> None:
    response = TestClient(app).get("/examples/missing")

    assert response.status_code == 404


def test_get_materials_lists_visual_house_materials() -> None:
    response = TestClient(app).get("/materials")

    assert response.status_code == 200
    material_ids = {material["id"] for material in response.json()}
    assert {"wood", "glass", "tissue", "steel", "rubber", "plastic"}.issubset(material_ids)
