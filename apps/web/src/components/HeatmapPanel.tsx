"use client";

import { useEffect, useMemo, useState } from "react";
import { artifactDownloadUrl } from "@/lib/api";
import { doseColor, doseUnit, formatDoseWithUnit, parseNpyFloat32 } from "@/lib/npy";
import type { ArtifactSummary } from "@/types/oopsenheimer";

type ParsedResult = NonNullable<ArtifactSummary["parsedResult"]>;
type Axis = "x" | "y" | "z";

type HeatmapPanelProps = {
  parsedResult?: ParsedResult | null;
  simulationId?: string;
};

const defaultResult: ParsedResult = {
  quantity: "DOSE",
  unit: "GeV/g",
  dims: [8, 8, 1],
  min: 0,
  max: 1,
};

export function HeatmapPanel({ parsedResult, simulationId }: HeatmapPanelProps) {
  const result = parsedResult ?? defaultResult;
  const [doseValues, setDoseValues] = useState<Float32Array | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [axis, setAxis] = useState<Axis>("z");
  const maxSlice = Math.max(0, axisLimit(result.dims, axis) - 1);
  const [sliceIndex, setSliceIndex] = useState(0);
  const clampedSlice = Math.min(sliceIndex, maxSlice);

  useEffect(() => {
    let active = true;
    setDoseValues(null);
    setLoadError(null);

    async function loadDoseValues() {
      if (!simulationId || !parsedResult?.valuesFile) {
        return;
      }

      try {
        const response = await fetch(
          artifactDownloadUrl(simulationId, `parsed/${parsedResult.valuesFile}`),
        );
        if (!response.ok) {
          throw new Error(`Dose artifact request failed with ${response.status}`);
        }
        const parsed = parseNpyFloat32(await response.arrayBuffer());
        const expectedCount = parsedResult.dims[0] * parsedResult.dims[1] * parsedResult.dims[2];
        if (parsed.values.length !== expectedCount) {
          throw new Error(`Dose array has ${parsed.values.length} values, expected ${expectedCount}`);
        }
        if (active) {
          setDoseValues(parsed.values);
        }
      } catch (caught) {
        if (active) {
          setLoadError(caught instanceof Error ? caught.message : "Failed to load dose array.");
        }
      }
    }

    loadDoseValues();
    return () => {
      active = false;
    };
  }, [parsedResult, simulationId]);

  const cells = useMemo(
    () => buildSliceCells(result, doseValues, axis, clampedSlice),
    [axis, clampedSlice, doseValues, result],
  );
  const isRealDose = Boolean(doseValues);
  const simMode = parsedResult?.simMode ?? parsedResult?.source;
  const unit = doseUnit(result.quantity, result.unit);

  return (
    <section className="panel">
      <div className="panel-header">
        <strong>Dose slice</strong>
        <span className="muted">
          {result.quantity} {formatDoseWithUnit(result.min, unit)}-{formatDoseWithUnit(result.max, unit)}
        </span>
      </div>
      <div className="panel-body heatmap-panel">
        <div className="heatmap-controls">
          <div className="segmented-control" aria-label="Slice axis">
            {(["x", "y", "z"] as Axis[]).map((nextAxis) => (
              <button
                key={nextAxis}
                type="button"
                className={axis === nextAxis ? "selected" : ""}
                onClick={() => {
                  setAxis(nextAxis);
                  setSliceIndex(0);
                }}
              >
                {nextAxis.toUpperCase()}
              </button>
            ))}
          </div>
          <label className="slice-control">
            <span>Slice {clampedSlice}</span>
            <input
              type="range"
              min={0}
              max={maxSlice}
              value={clampedSlice}
              onChange={(event) => setSliceIndex(Number(event.target.value))}
            />
          </label>
        </div>
        {loadError ? <div className="error-text">{loadError}</div> : null}
        {simMode === "mock" ? (
          <div className="error-text">
            Mock mode result: this is synthetic and will not respond to geometry changes.
          </div>
        ) : null}
        <div className="muted heatmap-source">
          {isRealDose ? `rendering ${parsedResult?.source ?? "dose_map.npy"}` : "preview values"}
        </div>
        <div
          className="heatmap-grid"
          style={{ gridTemplateColumns: `repeat(${cells.columns}, minmax(8px, 1fr))` }}
          aria-label="Dose heatmap slice"
        >
          {cells.values.map((value, index) => (
            <span
              key={index}
              title={formatDoseWithUnit(value, unit)}
              style={{ backgroundColor: doseColor(value, result.min, result.max) }}
            />
          ))}
        </div>
      </div>
    </section>
  );
}

function axisLimit(dims: [number, number, number], axis: Axis): number {
  const [nx, ny, nz] = dims;
  if (axis === "x") {
    return nx;
  }
  if (axis === "y") {
    return ny;
  }
  return nz;
}

function buildSliceCells(
  result: ParsedResult,
  doseValues: Float32Array | null,
  axis: Axis,
  slice: number,
): { columns: number; values: number[] } {
  const [nx, ny, nz] = result.dims;
  const values: number[] = [];

  if (axis === "z") {
    for (let y = 0; y < ny; y += 1) {
      for (let x = 0; x < nx; x += 1) {
        values.push(valueAt(doseValues, x, y, slice, result.dims));
      }
    }
    return { columns: nx, values };
  }

  if (axis === "y") {
    for (let z = 0; z < nz; z += 1) {
      for (let x = 0; x < nx; x += 1) {
        values.push(valueAt(doseValues, x, slice, z, result.dims));
      }
    }
    return { columns: nx, values };
  }

  for (let z = 0; z < nz; z += 1) {
    for (let y = 0; y < ny; y += 1) {
      values.push(valueAt(doseValues, slice, y, z, result.dims));
    }
  }
  return { columns: ny, values };
}

function valueAt(
  doseValues: Float32Array | null,
  x: number,
  y: number,
  z: number,
  dims: [number, number, number],
): number {
  const [nx, ny, nz] = dims;
  const index = z * nx * ny + y * nx + x;
  if (doseValues) {
    return doseValues[index] ?? 0;
  }
  const total = Math.max(1, nx * ny * nz - 1);
  return index / total;
}
