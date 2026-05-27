"use client";

import { Canvas, type ThreeEvent } from "@react-three/fiber";
import { GizmoHelper, GizmoViewport, Grid, OrbitControls } from "@react-three/drei";
import { useEffect, useLayoutEffect, useMemo, useRef, useState } from "react";
import * as THREE from "three";
import { artifactDownloadUrl } from "@/lib/api";
import { doseUnit, formatDoseWithUnit, normalizedDose, parseNpyFloat32 } from "@/lib/npy";
import type { ArtifactSummary } from "@/types/radcraft";

type ParsedResult = NonNullable<ArtifactSummary["parsedResult"]>;

type DoseVolumeViewerProps = {
  parsedResult?: ParsedResult | null;
  simulationId: string;
};

type DoseVoxel = {
  centerCm: [number, number, number];
  color: string;
  coordinate: [number, number, number];
  norm: number;
  position: [number, number, number];
  value: number;
};
type Vector3Tuple = [number, number, number];
type HoveredDoseVoxel = {
  placement: "above" | "below";
  voxel: DoseVoxel;
  x: number;
  y: number;
};

export function DoseVolumeViewer({ parsedResult, simulationId }: DoseVolumeViewerProps) {
  const [doseValues, setDoseValues] = useState<Float32Array | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [hoveredDose, setHoveredDose] = useState<HoveredDoseVoxel | null>(null);
  const [threshold, setThreshold] = useState(0.08);
  const stageRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    let active = true;
    setDoseValues(null);
    setLoadError(null);

    async function loadDoseValues() {
      if (!parsedResult?.valuesFile) {
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
          setLoadError(caught instanceof Error ? caught.message : "Failed to load dose volume.");
        }
      }
    }

    loadDoseValues();
    return () => {
      active = false;
    };
  }, [parsedResult, simulationId]);

  const volume = useMemo(
    () => buildDoseVoxels(parsedResult, doseValues, threshold),
    [doseValues, parsedResult, threshold],
  );
  const dims = parsedResult?.dims ?? [48, 24, 24];
  const unit = doseUnit(parsedResult?.quantity, parsedResult?.unit);
  const maxLabel = parsedResult ? formatDoseWithUnit(parsedResult.max, unit) : "pending";

  useEffect(() => {
    setHoveredDose(null);
  }, [volume]);

  function handleVoxelHover(voxel: DoseVoxel, event: ThreeEvent<PointerEvent>) {
    const bounds = stageRef.current?.getBoundingClientRect();
    if (!bounds) {
      return;
    }
    const pointerX = event.clientX - bounds.left;
    const pointerY = event.clientY - bounds.top;
    setHoveredDose({
      placement: pointerY < 118 ? "below" : "above",
      voxel,
      x: Math.min(Math.max(pointerX, 12), Math.max(12, bounds.width - 232)),
      y: Math.min(Math.max(pointerY, 12), Math.max(12, bounds.height - 12)),
    });
  }

  return (
    <section className="panel dose-volume-viewer">
      <div className="panel-header">
        <div>
          <strong>3D dose volume</strong>
          <div className="muted">translucent full-volume scoring with beam path</div>
        </div>
        <span className="muted">{volume.length} voxels</span>
      </div>
      <div className="panel-body dose-volume-body">
        <div className="volume-toolbar">
          <label className="slice-control volume-threshold">
            <span>Cutoff {(threshold * 100).toFixed(0)}%</span>
            <input
              max={0.9}
              min={0}
              onChange={(event) => setThreshold(Number(event.target.value))}
              step={0.01}
              type="range"
              value={threshold}
            />
          </label>
          <span className="muted">max {maxLabel}</span>
        </div>
        {loadError ? <div className="error-text">{loadError}</div> : null}
        <div
          className={`volume-stage ${hoveredDose ? "is-hovering" : ""}`}
          aria-label="3D dose volume"
          onPointerLeave={() => setHoveredDose(null)}
          ref={stageRef}
        >
          <Canvas camera={{ position: [34, 24, 34], fov: 42 }}>
            <color attach="background" args={["#0b0d0a"]} />
            <ambientLight intensity={0.72} />
            <directionalLight position={[12, 18, 14]} intensity={1.25} />
            <BeamPath dims={dims} parsedResult={parsedResult} />
            <DoseCloud
              onVoxelHover={handleVoxelHover}
              onVoxelLeave={() => setHoveredDose(null)}
              voxels={volume}
            />
            <HoveredDoseMarker voxel={hoveredDose?.voxel ?? null} />
            <Grid
              args={[40, 20]}
              cellColor="#384035"
              sectionColor="#d7ff61"
              sectionSize={8}
              position={[0, -dims[1] / 2 - 0.15, 0]}
            />
            <OrbitControls makeDefault enableDamping dampingFactor={0.08} />
            <GizmoHelper alignment="bottom-right" margin={[64, 64]}>
              <GizmoViewport axisColors={["#ff6b6b", "#64d78b", "#38bdf8"]} labelColor="#f0f3e8" />
            </GizmoHelper>
          </Canvas>
          <DoseHoverTooltip hover={hoveredDose} unit={unit} />
        </div>
      </div>
    </section>
  );
}

function DoseCloud({
  onVoxelHover,
  onVoxelLeave,
  voxels,
}: {
  onVoxelHover: (voxel: DoseVoxel, event: ThreeEvent<PointerEvent>) => void;
  onVoxelLeave: () => void;
  voxels: DoseVoxel[];
}) {
  const groups = useMemo(() => {
    const next = new Map<string, DoseVoxel[]>();
    for (const voxel of voxels) {
      const group = next.get(voxel.color) ?? [];
      group.push(voxel);
      next.set(voxel.color, group);
    }
    return Array.from(next.entries());
  }, [voxels]);

  return (
    <>
      {groups.map(([color, group]) => (
        <DoseCloudGroup
          color={color}
          key={color}
          onVoxelHover={onVoxelHover}
          onVoxelLeave={onVoxelLeave}
          voxels={group}
        />
      ))}
    </>
  );
}

function DoseCloudGroup({
  color,
  onVoxelHover,
  onVoxelLeave,
  voxels,
}: {
  color: string;
  onVoxelHover: (voxel: DoseVoxel, event: ThreeEvent<PointerEvent>) => void;
  onVoxelLeave: () => void;
  voxels: DoseVoxel[];
}) {
  const meshRef = useRef<THREE.InstancedMesh>(null);

  useLayoutEffect(() => {
    if (!meshRef.current) {
      return;
    }
    const matrixObject = new THREE.Object3D();
    voxels.forEach((voxel, index) => {
      const size = 0.28 + voxel.norm * 0.68;
      matrixObject.position.set(...voxel.position);
      matrixObject.scale.set(size, size, size);
      matrixObject.updateMatrix();
      meshRef.current?.setMatrixAt(index, matrixObject.matrix);
    });
    meshRef.current.instanceMatrix.needsUpdate = true;
  }, [voxels]);

  if (voxels.length === 0) {
    return null;
  }

  function handlePointer(event: ThreeEvent<PointerEvent>) {
    event.stopPropagation();
    if (typeof event.instanceId !== "number") {
      return;
    }
    const voxel = voxels[event.instanceId];
    if (voxel) {
      onVoxelHover(voxel, event);
    }
  }

  return (
    <instancedMesh
      ref={meshRef}
      args={[undefined, undefined, voxels.length]}
      onPointerMove={handlePointer}
      onPointerOut={(event) => {
        event.stopPropagation();
        onVoxelLeave();
      }}
      onPointerOver={handlePointer}
      renderOrder={15}
    >
      <boxGeometry args={[0.92, 0.92, 0.92]} />
      <meshBasicMaterial
        blending={THREE.NormalBlending}
        color={color}
        depthWrite={false}
        opacity={0.58}
        toneMapped={false}
        transparent
      />
    </instancedMesh>
  );
}

function HoveredDoseMarker({ voxel }: { voxel: DoseVoxel | null }) {
  if (!voxel) {
    return null;
  }

  const sideLength = (0.28 + voxel.norm * 0.68) * 0.92 + 0.1;
  return (
    <mesh position={voxel.position} renderOrder={40}>
      <boxGeometry args={[sideLength, sideLength, sideLength]} />
      <meshBasicMaterial
        color="#fff3b0"
        depthWrite={false}
        opacity={0.95}
        toneMapped={false}
        transparent
        wireframe
      />
    </mesh>
  );
}

function DoseHoverTooltip({ hover, unit }: { hover: HoveredDoseVoxel | null; unit: string }) {
  if (!hover) {
    return null;
  }

  const [gridX, gridY, gridZ] = hover.voxel.coordinate;
  const [cmX, cmY, cmZ] = hover.voxel.centerCm;
  return (
    <div
      className={`dose-hover-tooltip ${hover.placement}`}
      style={{ left: hover.x, top: hover.y }}
    >
      <div className="tooltip-label">Voxel dose</div>
      <strong>{formatDoseWithUnit(hover.voxel.value, unit)}</strong>
      <dl>
        <div>
          <dt>relative</dt>
          <dd>{(hover.voxel.norm * 100).toFixed(1)}%</dd>
        </div>
        <div>
          <dt>grid</dt>
          <dd>
            {gridX}, {gridY}, {gridZ}
          </dd>
        </div>
        <div>
          <dt>center</dt>
          <dd>
            {cmX.toFixed(1)}, {cmY.toFixed(1)}, {cmZ.toFixed(1)} cm
          </dd>
        </div>
      </dl>
    </div>
  );
}

function BeamPath({
  dims,
  parsedResult,
}: {
  dims: [number, number, number];
  parsedResult?: ParsedResult | null;
}) {
  const source = parsedSourcePosition(dims, parsedResult);
  const direction = parsedSourceDirection(parsedResult);
  const path = buildBeamPathGeometry(source, direction, [dims[0] / 2, dims[1] / 2, dims[2] / 2]);

  return (
    <group>
      <mesh position={path.center} quaternion={path.quaternion}>
        <cylinderGeometry args={[0.1, 0.1, path.length, 20]} />
        <meshStandardMaterial color="#d7ff61" emissive="#d7ff61" emissiveIntensity={0.72} />
      </mesh>
      <mesh position={source} castShadow>
        <sphereGeometry args={[0.65, 24, 24]} />
        <meshStandardMaterial color="#ffb84d" emissive="#8a4a00" emissiveIntensity={0.5} />
      </mesh>
    </group>
  );
}

function parsedSourcePosition(
  dims: [number, number, number],
  parsedResult?: ParsedResult | null,
): Vector3Tuple {
  const sourcePosition = parsedResult?.sources?.[0]?.positionCm;
  const voxelSize = parsedResult?.voxelSizeCm;
  const origin = parsedResult?.originCm ?? [0, 0, 0];
  if (!sourcePosition || !voxelSize) {
    return [0.5, 0.5, -dims[2] / 2 - 3];
  }

  return [
    (sourcePosition[0] - origin[0]) / voxelSize[0] - dims[0] / 2,
    (sourcePosition[1] - origin[1]) / voxelSize[1] - dims[1] / 2,
    (sourcePosition[2] - origin[2]) / voxelSize[2] - dims[2] / 2,
  ];
}

function parsedSourceDirection(parsedResult?: ParsedResult | null): Vector3Tuple {
  const sourceDirection = parsedResult?.sources?.[0]?.direction;
  const voxelSize = parsedResult?.voxelSizeCm ?? [1, 1, 1];
  if (!sourceDirection) {
    return [0, 0, 1];
  }

  return normalizeDirection([
    sourceDirection[0] / voxelSize[0],
    sourceDirection[1] / voxelSize[1],
    sourceDirection[2] / voxelSize[2],
  ]);
}

function normalizeDirection(direction: Vector3Tuple): Vector3Tuple {
  const vector = new THREE.Vector3(...direction);
  if (vector.lengthSq() < 1e-12) {
    return [0, 0, 1];
  }
  vector.normalize();
  return [vector.x, vector.y, vector.z];
}

function buildBeamPathGeometry(origin: Vector3Tuple, direction: Vector3Tuple, halfExtents: Vector3Tuple) {
  const source = new THREE.Vector3(...origin);
  const beamDirection = new THREE.Vector3(...normalizeDirection(direction));
  const length = distanceToBoxExit(source, beamDirection, halfExtents);
  const centerVector = source.clone().addScaledVector(beamDirection, length / 2);
  const quaternion = new THREE.Quaternion().setFromUnitVectors(new THREE.Vector3(0, 1, 0), beamDirection);

  return {
    center: [centerVector.x, centerVector.y, centerVector.z] as Vector3Tuple,
    length,
    quaternion,
  };
}

function distanceToBoxExit(origin: THREE.Vector3, direction: THREE.Vector3, halfExtents: Vector3Tuple): number {
  let tMin = -Infinity;
  let tMax = Infinity;
  const originValues = [origin.x, origin.y, origin.z];
  const directionValues = [direction.x, direction.y, direction.z];

  for (let axis = 0; axis < 3; axis += 1) {
    const axisOrigin = originValues[axis];
    const axisDirection = directionValues[axis];
    const halfExtent = halfExtents[axis];

    if (Math.abs(axisDirection) < 1e-8) {
      if (axisOrigin < -halfExtent || axisOrigin > halfExtent) {
        return Math.max(...halfExtents) * 1.6;
      }
      continue;
    }

    const t1 = (-halfExtent - axisOrigin) / axisDirection;
    const t2 = (halfExtent - axisOrigin) / axisDirection;
    tMin = Math.max(tMin, Math.min(t1, t2));
    tMax = Math.min(tMax, Math.max(t1, t2));
  }

  if (tMax < Math.max(tMin, 0)) {
    return Math.max(...halfExtents) * 1.6;
  }

  return Math.max(0.1, tMax + 2);
}

function buildDoseVoxels(
  parsedResult: ParsedResult | null | undefined,
  doseValues: Float32Array | null,
  threshold: number,
): DoseVoxel[] {
  if (!parsedResult || !doseValues || parsedResult.max <= parsedResult.min) {
    return [];
  }

  const [nx, ny, nz] = parsedResult.dims;
  const origin = parsedResult.originCm ?? [0, 0, 0];
  const voxelSize = parsedResult.voxelSizeCm ?? [1, 1, 1];
  const voxels: DoseVoxel[] = [];
  for (let z = 0; z < nz; z += 1) {
    for (let y = 0; y < ny; y += 1) {
      for (let x = 0; x < nx; x += 1) {
        const index = z * nx * ny + y * nx + x;
        const value = doseValues[index] ?? 0;
        const norm = normalizedDose(value, parsedResult.min, parsedResult.max);
        if (norm < threshold) {
          continue;
        }
        voxels.push({
          centerCm: [
            origin[0] + (x + 0.5) * voxelSize[0],
            origin[1] + (y + 0.5) * voxelSize[1],
            origin[2] + (z + 0.5) * voxelSize[2],
          ],
          color: colorForNorm(norm),
          coordinate: [x, y, z],
          norm,
          position: [x - nx / 2 + 0.5, y - ny / 2 + 0.5, z - nz / 2 + 0.5],
          value,
        });
      }
    }
  }
  return voxels;
}

function colorForNorm(norm: number): string {
  const stops = [
    "#2563eb",
    "#06b6d4",
    "#22c55e",
    "#d7ff61",
    "#ffb84d",
    "#ff6b6b",
    "#fff3b0",
  ];
  const index = Math.min(stops.length - 1, Math.max(0, Math.floor(norm * stops.length)));
  return stops[index];
}
