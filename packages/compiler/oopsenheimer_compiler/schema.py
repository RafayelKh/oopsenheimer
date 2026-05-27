"""Pydantic models for Oops-enheimer scene JSON."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    NonNegativeInt,
    PositiveFloat,
    PositiveInt,
    field_validator,
    model_validator,
)


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)


class Units(StrictModel):
    length: Literal["cm"]
    energy: Literal["GeV"]
    density: Literal["g/cm3"] = "g/cm3"


class Grid(StrictModel):
    dims: tuple[PositiveInt, PositiveInt, PositiveInt]
    voxel_size_cm: tuple[PositiveFloat, PositiveFloat, PositiveFloat] = Field(alias="voxelSizeCm")
    origin_cm: tuple[float, float, float] = Field(alias="originCm")
    axis_order: Literal["x-fastest"] = Field(alias="axisOrder")


class Boundary(StrictModel):
    outside_material_id: str = Field(alias="outsideMaterialId")
    blackhole_margin_cm: NonNegativeInt = Field(alias="blackholeMarginCm")
    world_air_margin_cm: NonNegativeInt = Field(alias="worldAirMarginCm")


class BlockDefinition(StrictModel):
    material_id: str = Field(alias="materialId")
    label: str | None = None
    tags: list[str] = Field(default_factory=list)
    color: str | None = None


class RleRun(StrictModel):
    block_id: str = Field(alias="blockId")
    count: PositiveInt


class ChunkPayload(StrictModel):
    id: str | None = None
    origin: tuple[NonNegativeInt, NonNegativeInt, NonNegativeInt]
    size: tuple[PositiveInt, PositiveInt, PositiveInt]
    encoding: Literal["rle"]
    runs: list[RleRun]

    @property
    def voxel_count(self) -> int:
        sx, sy, sz = self.size
        return sx * sy * sz

    @model_validator(mode="after")
    def validate_rle_count(self) -> "ChunkPayload":
        run_count = sum(run.count for run in self.runs)
        if run_count != self.voxel_count:
            raise ValueError(
                f"chunk RLE count {run_count} does not match chunk size voxel count {self.voxel_count}"
            )
        return self


class OrganFallback(StrictModel):
    on_too_many_organs: Literal["reject_scene"] = Field(alias="onTooManyOrgans")


class OrganPolicy(StrictModel):
    mode: Literal["merge_by_material_and_tag"]
    max_organs: PositiveInt = Field(alias="maxOrgans", le=32767)
    reserve_organ_zero_for_outside: bool = Field(alias="reserveOrganZeroForOutside")
    split_rules: list[dict[str, Any]] = Field(default_factory=list, alias="splitRules")
    fallback: OrganFallback


class World(StrictModel):
    id: str
    grid: Grid
    boundary: Boundary
    palette: dict[str, BlockDefinition]
    chunks: list[ChunkPayload] = Field(default_factory=list)
    organ_policy: OrganPolicy = Field(alias="organPolicy")

    @model_validator(mode="after")
    def validate_chunks_fit_world(self) -> "World":
        nx, ny, nz = self.grid.dims
        for chunk in self.chunks:
            ox, oy, oz = chunk.origin
            sx, sy, sz = chunk.size
            if ox + sx > nx or oy + sy > ny or oz + sz > nz:
                chunk_id = f" '{chunk.id}'" if chunk.id else ""
                raise ValueError(
                    f"chunk{chunk_id} exceeds world dims: origin={chunk.origin}, "
                    f"size={chunk.size}, world_dims={self.grid.dims}"
                )
        return self


class MaterialDefinition(StrictModel):
    fluka_name: str | None = Field(default=None, alias="flukaName")
    density: float | None = None
    density_g_cm3: float | None = Field(default=None, alias="densityGcm3")
    label: str | None = None
    color: str | None = None


ALLOWED_FLUKA_PARTICLES = {
    "PHOTON",
    "NEUTRON",
    "PROTON",
    "ELECTRON",
    "POSITRON",
    "MUON+",
    "MUON-",
    "PION+",
    "PION-",
}


class SourceDefinition(StrictModel):
    id: str
    type: Literal["photon_beam", "particle_beam"]
    particle: str = "PHOTON"
    energy_gev: PositiveFloat = Field(alias="energyGeV")
    position_cm: tuple[float, float, float] = Field(alias="positionCm")
    direction: tuple[float, float, float]

    @field_validator("particle")
    @classmethod
    def normalize_particle(cls, value: str) -> str:
        particle = value.upper()
        if particle not in ALLOWED_FLUKA_PARTICLES:
            allowed = ", ".join(sorted(ALLOWED_FLUKA_PARTICLES))
            raise ValueError(f"unsupported FLUKA particle '{value}'. Expected one of: {allowed}")
        return particle


class ScoringDefinition(StrictModel):
    id: str
    type: Literal["usrbin_cartesian"]
    quantity: str
    dims: tuple[PositiveInt, PositiveInt, PositiveInt]
    min_cm: tuple[float, float, float] = Field(alias="minCm")
    max_cm: tuple[float, float, float] = Field(alias="maxCm")


class RunValidation(StrictModel):
    geometry_debug: bool = Field(default=True, alias="geometryDebug")


class RunSettings(StrictModel):
    defaults: str = "PRECISIO"
    histories: PositiveInt
    random_seed: int = Field(alias="randomSeed")
    cycles: PositiveInt
    validation: RunValidation = Field(default_factory=RunValidation)


class FlukaInputSettings(StrictModel):
    filename: str
    title: str
    include_comments: bool = Field(default=True, alias="includeComments")


class VoxelFileSettings(StrictModel):
    filename: str
    format: Literal["fluka_unformatted_vxl"]
    compact_organ_ids: bool = Field(default=True, alias="compactOrganIds")


class ManifestSettings(StrictModel):
    filename: str
    include_voxel_to_organ_map: bool = Field(default=False, alias="includeVoxelToOrganMap")
    include_organ_to_region_map: bool = Field(default=True, alias="includeOrganToRegionMap")
    include_material_map: bool = Field(default=True, alias="includeMaterialMap")


class EmitSettings(StrictModel):
    backend: Literal["fluka_voxel"]
    fluka_input: FlukaInputSettings = Field(alias="flukaInput")
    voxel_file: VoxelFileSettings = Field(alias="voxelFile")
    manifest: ManifestSettings


class SceneDefinition(StrictModel):
    schema_: Literal["oopsenheimer.scene.v1"] = Field(alias="schema")
    units: Units
    world: World
    materials: dict[str, MaterialDefinition]
    sources: list[SourceDefinition] = Field(default_factory=list)
    scoring: list[ScoringDefinition] = Field(default_factory=list)
    run: RunSettings
    emit: EmitSettings
