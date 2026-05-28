"""FastAPI application for Oopsenheimer."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from fastapi import BackgroundTasks, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

from app.config import settings
from app.schemas import ArtifactList, HealthResponse, SceneRecord, SimulationCreate, SimulationRecord
from app.services.queue import enqueue_simulation
from app.services.store import InMemoryStore

app = FastAPI(title="Oosenhaimer API", version="0.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://127.0.0.1:3000", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
store = InMemoryStore(settings.storage_root)


def repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


EXAMPLE_SCENES = {
    "lead_wall": {
        "name": "Հին կապարե պատ",
        "filename": "lead_wall.scene.json",
        "description": "Սկզբնական փոքր 32 x 16 x 16 կապարե պատի կոմպիլյատորի օրինակ։",
    },
    "air_baseline": {
        "name": "Օդային ելակետ",
        "filename": "air_baseline.scene.json",
        "description": "Դատարկ 48 x 24 x 24 աշխարհ՝ անպաշտպան ճառագայթը ստուգելու համար։",
    },
    "lead_slab": {
        "name": "Կապարե սալային պաշտպանիչ",
        "filename": "lead_slab.scene.json",
        "description": "Խիտ ամբողջական կապարե սալ՝ ճառագայթի ճանապարհին։",
    },
    "lead_aperture": {
        "name": "Բացվածքով կապարե սալ",
        "filename": "lead_aperture.scene.json",
        "description": "Կապարե սալ՝ ճառագայթի շուրջ կենտրոնական բացվածքով։",
    },
    "water_phantom": {
        "name": "Ջրային ֆանտոմ",
        "filename": "water_phantom.scene.json",
        "description": "Կապարե կոլիմատոր և հետո ջրային թիրախ։",
    },
    "house_occupant": {
        "name": "Տուն բնակչով",
        "filename": "house_occupant.scene.json",
        "description": "Վոքսելային տուն՝ դռնով, ապակե պատուհաններով, տանիքով և ներսում հյուսվածքանման մարդու պատկերով։",
    },
    "car": {
        "name": "Ավտոմեքենա",
        "filename": "car.scene.json",
        "description": "Փոքր մեքենա՝ պողպատե թափքով, ապակե սրահով, ռետինե անիվներով և վարորդով։",
    },
    "bus": {
        "name": "Ավտոբուս",
        "filename": "bus.scene.json",
        "description": "Մեծ ուղևորային ավտոբուս՝ պատուհաններով, դռներով, անիվներով, նստատեղերով, վարորդով և ուղևորներով։",
    },
}

MATERIAL_LABELS_HY = {
    "air": "Օդ",
    "lead": "Կապար",
    "water": "Ջուր",
    "concrete": "Բետոն",
    "silicon": "Սիլիցիում",
    "wood": "Փայտ",
    "glass": "Ապակի",
    "tissue": "Հյուսվածք",
    "steel": "Պողպատ",
    "rubber": "Ռետին",
    "plastic": "Պլաստիկ",
}


def example_scene_path(example_id: str = "lead_wall") -> Path:
    example = EXAMPLE_SCENES.get(example_id)
    if example is None:
        raise KeyError(example_id)
    return repo_root() / "packages" / "examples" / example["filename"]


def load_example_scene(example_id: str = "lead_wall") -> dict[str, Any]:
    scene = json.loads(example_scene_path(example_id).read_text())
    for material_id, label in MATERIAL_LABELS_HY.items():
        if material_id in scene.get("materials", {}):
            scene["materials"][material_id]["label"] = label
        palette = scene.get("world", {}).get("palette", {})
        if material_id in palette:
            palette[material_id]["label"] = label
    return scene


@app.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(
        status="ok",
        simMode=settings.sim_mode,
        flukaConfigured=bool(settings.fluka_bin),
    )


@app.get("/materials")
def materials() -> list[dict[str, Any]]:
    material_map: dict[str, dict[str, Any]] = {}
    for example_id in EXAMPLE_SCENES:
        scene = load_example_scene(example_id)
        for material_id, definition in scene.get("materials", {}).items():
            material_map.setdefault(material_id, definition)
    return [
        {"id": material_id, **definition}
        for material_id, definition in sorted(material_map.items())
    ]


@app.get("/examples")
def examples() -> list[dict[str, str]]:
    return [
        {
            "id": example_id,
            **example,
        }
        for example_id, example in EXAMPLE_SCENES.items()
        if example_id != "lead_wall"
    ]


@app.get("/examples/{example_id}")
def get_example(example_id: str) -> dict[str, Any]:
    if example_id not in EXAMPLE_SCENES:
        raise HTTPException(status_code=404, detail="Օրինակը չի գտնվել։")
    return load_example_scene(example_id)


@app.post("/scenes", response_model=SceneRecord)
def create_scene(payload: dict[str, Any]) -> SceneRecord:
    scene_json = payload.get("sceneJson") or payload

    if not isinstance(scene_json, dict) or scene_json.get("schema") != "oopsenheimer.scene.v1":
        raise HTTPException(status_code=422, detail="Սպասվում է Oosenhaimer-ի տեսարանի JSON։")

    return store.create_scene(scene_json)


@app.get("/scenes/{scene_id}", response_model=SceneRecord)
def get_scene(scene_id: str) -> SceneRecord:
    scene = store.get_scene(scene_id)
    if scene is None:
        raise HTTPException(status_code=404, detail="Տեսարանը չի գտնվել։")
    return scene


@app.post("/simulations", response_model=SimulationRecord)
def create_simulation(payload: SimulationCreate, background_tasks: BackgroundTasks) -> SimulationRecord:
    if store.get_scene(payload.scene_id) is None:
        raise HTTPException(status_code=404, detail="Տեսարանը չի գտնվել։")
    simulation = store.create_simulation(payload.scene_id)
    background_tasks.add_task(enqueue_simulation, simulation.id, store.storage_root)
    return simulation


@app.get("/simulations/{simulation_id}", response_model=SimulationRecord)
def get_simulation(simulation_id: str) -> SimulationRecord:
    simulation = store.get_simulation(simulation_id)
    if simulation is None:
        raise HTTPException(status_code=404, detail="Սիմուլյացիան չի գտնվել։")
    return simulation


@app.get("/simulations/{simulation_id}/artifacts", response_model=ArtifactList)
def simulation_artifacts(simulation_id: str) -> ArtifactList:
    simulation = store.get_simulation(simulation_id)
    if simulation is None:
        raise HTTPException(status_code=404, detail="Սիմուլյացիան չի գտնվել։")

    parsed_result = None
    if simulation.storage_path is not None:
        parsed_path = Path(simulation.storage_path) / "parsed" / "dose_map.json"
        if parsed_path.exists():
            parsed_result = json.loads(parsed_path.read_text())

    return ArtifactList(
        simulationId=simulation_id,
        artifacts=store.list_artifacts(simulation_id),
        parsedResult=parsed_result,
    )


@app.get("/simulations/{simulation_id}/artifacts/{artifact_path:path}")
def download_artifact(simulation_id: str, artifact_path: str) -> FileResponse:
    simulation = store.get_simulation(simulation_id)
    if simulation is None or simulation.storage_path is None:
        raise HTTPException(status_code=404, detail="Սիմուլյացիան չի գտնվել։")

    root = Path(simulation.storage_path).resolve()
    requested = (root / artifact_path).resolve()
    if requested == root or root not in requested.parents:
        raise HTTPException(status_code=400, detail="Արտեֆակտի ուղին անվավեր է։")
    if not requested.exists() or not requested.is_file():
        raise HTTPException(status_code=404, detail="Արտեֆակտը չի գտնվել։")

    return FileResponse(requested, filename=requested.name)
