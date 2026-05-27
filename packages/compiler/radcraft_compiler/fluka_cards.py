"""Typed FLUKA card renderers."""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Sequence


def _format_field(value: object) -> str:
    if value is None:
        return ""
    if isinstance(value, float):
        return _format_float(value)
    return str(value)


def _format_float(value: float) -> str:
    for precision in range(8, 0, -1):
        rendered = f"{value:.{precision}g}"
        if len(rendered) <= 10:
            return rendered
    for precision in range(3, 0, -1):
        rendered = f"{value:.{precision}e}"
        if len(rendered) <= 10:
            return rendered
    return f"{value:.1e}"[:10]


def render_comment(text: str) -> str:
    return f"* {text}"


@dataclass(frozen=True)
class FlukaCard:
    keyword: str
    fields: Sequence[object] = field(default_factory=tuple)
    sdum: str | None = None

    def render(self) -> str:
        if len(self.fields) > 6:
            raise ValueError("FLUKA cards support at most six WHAT fields")
        columns = [self.keyword.ljust(10)]
        columns.extend(_format_field(value).rjust(10) for value in self.fields)
        if self.sdum:
            columns.extend(" " * 10 for _ in range(6 - len(self.fields)))
            columns.append(self.sdum.ljust(10))
        return "".join(columns).rstrip()


@dataclass(frozen=True)
class DefaultsCard:
    defaults: str = "PRECISIO"

    def render(self) -> str:
        return FlukaCard("DEFAULTS", sdum=self.defaults).render()


@dataclass(frozen=True)
class BeamCard:
    particle: str
    energy_gev: float

    def render(self) -> str:
        return FlukaCard("BEAM", fields=(self.energy_gev,), sdum=self.particle.upper()).render()


@dataclass(frozen=True)
class BeamPosCard:
    position_cm: tuple[float, float, float]
    direction: tuple[float, float, float]

    def render(self) -> str:
        direction = _normalize_direction(self.direction)
        u_beam, v_beam, w_beam = direction
        u_beam, v_beam = _fit_transverse_cosines(u_beam, v_beam)
        has_non_default_direction = (
            not math.isclose(u_beam, 0.0, abs_tol=1e-12)
            or not math.isclose(v_beam, 0.0, abs_tol=1e-12)
            or w_beam < 0.0
        )
        fields: Sequence[object] = self.position_cm
        if has_non_default_direction:
            fields = (*self.position_cm, u_beam, v_beam)
        return FlukaCard(
            "BEAMPOS",
            fields=fields,
            sdum="NEGATIVE" if w_beam < 0.0 else None,
        ).render()


def _normalize_direction(direction: tuple[float, float, float]) -> tuple[float, float, float]:
    norm = math.sqrt(sum(component * component for component in direction))
    if norm <= 1e-12:
        return (0.0, 0.0, 1.0)
    return tuple(component / norm for component in direction)  # type: ignore[return-value]


def _fit_transverse_cosines(u_beam: float, v_beam: float) -> tuple[float, float]:
    transverse_norm = math.sqrt(u_beam * u_beam + v_beam * v_beam)
    max_transverse_norm = 0.99999998
    if transverse_norm < max_transverse_norm:
        return u_beam, v_beam
    scale = max_transverse_norm / transverse_norm
    return u_beam * scale, v_beam * scale


@dataclass(frozen=True)
class AssignMatCard:
    material_name: str
    region_name: str

    def render(self) -> str:
        return FlukaCard("ASSIGNMA", fields=(self.material_name, self.region_name)).render()


@dataclass(frozen=True)
class MaterialCard:
    name: str
    density_g_cm3: float
    atomic_number: float = 0.0

    def render(self) -> str:
        return FlukaCard(
            "MATERIAL",
            fields=(self.atomic_number, None, self.density_g_cm3, None, None, None),
            sdum=self.name,
        ).render()


@dataclass(frozen=True)
class CompoundCard:
    material_name: str
    components: Sequence[tuple[float, str]]

    def render(self) -> str:
        fields: list[object] = []
        for fraction, component_name in self.components:
            fields.extend((fraction, component_name))
        return FlukaCard("COMPOUND", fields=fields, sdum=self.material_name).render()


@dataclass(frozen=True)
class UsrbinCard:
    quantity: str
    name: str
    mesh_id: int
    lower_cm: tuple[float, float, float]
    upper_cm: tuple[float, float, float]
    bins: tuple[int, int, int]

    def render(self) -> str:
        header = FlukaCard(
            "USRBIN",
            fields=(10.0, self.quantity.upper(), -abs(self.mesh_id), *self.upper_cm),
            sdum=self.name,
        ).render()
        lower = FlukaCard("USRBIN", fields=(*self.lower_cm, *self.bins), sdum="&").render()
        return "\n".join([header, lower])


@dataclass(frozen=True)
class RandomizeCard:
    seed: int

    def render(self) -> str:
        return FlukaCard("RANDOMIZ", fields=(1.0, self.seed)).render()


@dataclass(frozen=True)
class StartCard:
    histories: int

    def render(self) -> str:
        return FlukaCard("START", fields=(self.histories,)).render()


@dataclass(frozen=True)
class StopCard:
    def render(self) -> str:
        return FlukaCard("STOP").render()
