import json
from pathlib import Path
from types import SimpleNamespace

import numpy as np

from parser import parse_usrbin_outputs


def manifest() -> dict:
    return {
        "coordinateTransform": {
            "voxelIndexToCm": {
                "originCm": [0, 0, 0],
                "voxelSizeCm": [5, 5, 5],
            }
        },
        "scoring": [
            {
                "quantity": "DOSE",
                "dims": [4, 2, 1],
                "minCm": [0, 0, 0],
                "maxCm": [20, 10, 5],
            }
        ],
    }


def test_mock_parser_produces_dose_map_json_and_npy(tmp_path: Path) -> None:
    result = parse_usrbin_outputs(tmp_path, manifest(), sim_mode="mock")

    assert result.metadata_path.exists()
    assert result.values_path.exists()
    metadata = json.loads(result.metadata_path.read_text())
    values = np.load(result.values_path)

    assert metadata["quantity"] == "DOSE"
    assert metadata["unit"] == "GeV/g"
    assert metadata["dims"] == [4, 2, 1]
    assert metadata["valuesEncoding"] == "npy"
    assert values.shape == (1, 2, 4)


def test_real_parser_converts_usbrea_text_to_dose_map(tmp_path: Path, monkeypatch) -> None:
    (tmp_path / "scene001_fort.21").write_text("binary usrbin placeholder")
    fluka_bin = tmp_path / "fluka-bin"
    fluka_bin.mkdir()
    monkeypatch.setenv("FLUKA_BIN", str(fluka_bin))
    calls: list[str] = []

    def fake_run(command, cwd, input, text, capture_output, check):
        calls.append(Path(command[0]).name)
        assert cwd == tmp_path
        assert text is True
        assert capture_output is True
        assert check is False
        if Path(command[0]).name == "usbrea":
            (tmp_path / "radcraft_usrbin_readout.txt").write_text(
                """
 Cartesian binning n. 1 "dose_map", generalized particle n. 228
 X coordinate: from 0.0000E+00 to 2.0000E+01 cm, 4 bins
 Y coordinate: from 0.0000E+00 to 1.0000E+01 cm, 2 bins
 Z coordinate: from 0.0000E+00 to 5.0000E+00 cm, 1 bins
 Data follow in a matrix A(ix,iy,iz)
 this is a track-length binning
 1.0000E+00 2.0000E+00 3.0000E+00 4.0000E+00
 5.0000E+00 6.0000E+00 7.0000E+00 8.0000E+00
"""
            )
        return SimpleNamespace(returncode=0, stderr="", stdout="")

    monkeypatch.setattr("parser.subprocess.run", fake_run)

    result = parse_usrbin_outputs(tmp_path, manifest(), sim_mode="fluka")

    assert calls == ["usbsuw", "usbrea"]
    metadata = json.loads(result.metadata_path.read_text())
    values = np.load(result.values_path)
    assert metadata["source"] == "radcraft_usrbin_readout.txt"
    assert metadata["unit"] == "GeV/g"
    assert metadata["dims"] == [4, 2, 1]
    assert metadata["min"] == 1.0
    assert metadata["max"] == 8.0
    assert values.shape == (1, 2, 4)
    assert values.tolist() == [[[1.0, 2.0, 3.0, 4.0], [5.0, 6.0, 7.0, 8.0]]]
