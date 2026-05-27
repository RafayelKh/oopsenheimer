import pytest
from pydantic import ValidationError

from radcraft_compiler.schema import SceneDefinition


def valid_scene() -> dict:
    return {
        "schema": "radcraft.scene.v1",
        "units": {"length": "cm", "energy": "GeV", "density": "g/cm3"},
        "world": {
            "id": "unit_test_scene",
            "grid": {
                "dims": [2, 2, 1],
                "voxelSizeCm": [5, 5, 5],
                "originCm": [0, 0, 0],
                "axisOrder": "x-fastest",
            },
            "boundary": {
                "outsideMaterialId": "air",
                "blackholeMarginCm": 100,
                "worldAirMarginCm": 50,
            },
            "palette": {
                "air": {"materialId": "air"},
                "lead": {"materialId": "lead"},
            },
            "chunks": [
                {
                    "id": "main",
                    "origin": [0, 0, 0],
                    "size": [2, 2, 1],
                    "encoding": "rle",
                    "runs": [
                        {"blockId": "air", "count": 2},
                        {"blockId": "lead", "count": 2},
                    ],
                }
            ],
            "organPolicy": {
                "mode": "merge_by_material_and_tag",
                "maxOrgans": 32767,
                "reserveOrganZeroForOutside": True,
                "splitRules": [],
                "fallback": {"onTooManyOrgans": "reject_scene"},
            },
        },
        "materials": {
            "air": {"flukaName": "AIR", "density": 0.0012},
            "lead": {"flukaName": "LEAD", "density": 11.35},
        },
        "sources": [
            {
                "id": "source",
                "type": "photon_beam",
                "particle": "photon",
                "energyGeV": 0.001,
                "positionCm": [-10, 5, 2.5],
                "direction": [1, 0, 0],
            }
        ],
        "scoring": [
            {
                "id": "dose_map",
                "type": "usrbin_cartesian",
                "quantity": "DOSE",
                "dims": [2, 2, 1],
                "minCm": [0, 0, 0],
                "maxCm": [10, 10, 5],
            }
        ],
        "run": {
            "defaults": "PRECISIO",
            "histories": 100000,
            "randomSeed": 12345,
            "cycles": 1,
            "validation": {"geometryDebug": True},
        },
        "emit": {
            "backend": "fluka_voxel",
            "flukaInput": {
                "filename": "scene.inp",
                "title": "Oops-enheimer generated scene",
                "includeComments": True,
            },
            "voxelFile": {
                "filename": "scene.vxl",
                "format": "fluka_unformatted_vxl",
                "compactOrganIds": True,
            },
            "manifest": {
                "filename": "scene.map.json",
                "includeVoxelToOrganMap": False,
                "includeOrganToRegionMap": True,
                "includeMaterialMap": True,
            },
        },
    }


def test_valid_scene_loads() -> None:
    scene = SceneDefinition.model_validate(valid_scene())
    assert scene.schema_ == "radcraft.scene.v1"
    assert scene.world.grid.dims == (2, 2, 1)
    assert scene.sources[0].particle == "PHOTON"


def test_beam_particle_can_be_neutron() -> None:
    data = valid_scene()
    data["sources"][0]["type"] = "particle_beam"
    data["sources"][0]["particle"] = "neutron"

    scene = SceneDefinition.model_validate(data)

    assert scene.sources[0].particle == "NEUTRON"


def test_unknown_beam_particle_fails_clearly() -> None:
    data = valid_scene()
    data["sources"][0]["particle"] = "banana"

    with pytest.raises(ValidationError, match="unsupported FLUKA particle"):
        SceneDefinition.model_validate(data)


def test_invalid_dimensions_fail_with_clear_error() -> None:
    data = valid_scene()
    data["world"]["grid"]["dims"] = [2, 0, 1]

    with pytest.raises(ValidationError, match="greater than 0"):
        SceneDefinition.model_validate(data)


def test_invalid_unit_names_fail_with_clear_error() -> None:
    data = valid_scene()
    data["units"]["length"] = "mm"

    with pytest.raises(ValidationError, match="Input should be 'cm'"):
        SceneDefinition.model_validate(data)


def test_chunk_overflow_fails_with_clear_error() -> None:
    data = valid_scene()
    data["world"]["chunks"][0]["origin"] = [1, 0, 0]

    with pytest.raises(ValidationError, match="exceeds world dims"):
        SceneDefinition.model_validate(data)


def test_chunk_encoding_only_supports_rle() -> None:
    data = valid_scene()
    data["world"]["chunks"][0]["encoding"] = "raw"

    with pytest.raises(ValidationError, match="Input should be 'rle'"):
        SceneDefinition.model_validate(data)
