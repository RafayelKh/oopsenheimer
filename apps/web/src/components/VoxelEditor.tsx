"use client";

import { Canvas, useFrame, useThree, type ThreeEvent } from "@react-three/fiber";
import { Environment, GizmoHelper, GizmoViewport, Grid, OrbitControls } from "@react-three/drei";
import { useCallback, useEffect, useLayoutEffect, useMemo, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import * as THREE from "three";
import { createScene, createSimulation } from "@/lib/api";
import { MaterialPalette, materials } from "@/components/MaterialPalette";
import { SimulationProgressBar } from "@/components/SimulationProgressBar";

const dims = [48, 24, 24] as const;
const voxelSizeCm = [10 / 3, 10 / 3, 10 / 3] as const;
type MaterialId = (typeof materials)[number]["id"];
type Vector3Tuple = [number, number, number];
type VoxelCoordinate = [number, number, number];
type EditorMode = "orbit" | "walk";
type VoxelEditMode = "paint" | "erase";
type VoxelHit = {
  normal: VoxelCoordinate;
  voxel: VoxelCoordinate;
};
type BeamSettings = {
  energyGeV: number;
  particle: BeamParticle;
  positionCm: Vector3Tuple;
  direction: Vector3Tuple;
};

const beamParticles = [
  { value: "PHOTON", label: "Ֆոտոններ" },
  { value: "NEUTRON", label: "Նեյտրոններ" },
  { value: "PROTON", label: "Պրոտոններ" },
  { value: "ELECTRON", label: "Էլեկտրոններ" },
  { value: "POSITRON", label: "Պոզիտրոններ" },
  { value: "MUON+", label: "Մյուոն +" },
  { value: "MUON-", label: "Մյուոն -" },
  { value: "PION+", label: "Պիոն +" },
  { value: "PION-", label: "Պիոն -" },
] as const;
type BeamParticle = (typeof beamParticles)[number]["value"];

const materialLookup = Object.fromEntries(materials.map((material) => [material.id, material]));
const defaultBeamSettings: BeamSettings = {
  energyGeV: 0.001,
  particle: "PHOTON",
  positionCm: [81.6666666667, 41.6666666667, -10],
  direction: [0, 0, 1],
};
const walkControls = {
  eyeHeight: 1.62,
  height: 1.82,
  radius: 0.32,
  walkSpeed: 5.2,
  sprintMultiplier: 1.55,
  verticalSpeed: 10.4,
  rayDistance: 10,
};

type VoxelEditorProps = {
  initialSceneId?: string | null;
  initialSceneJson?: Record<string, unknown> | null;
};

export function VoxelEditor({ initialSceneId = null, initialSceneJson = null }: VoxelEditorProps) {
  const router = useRouter();
  const [grid, setGrid] = useState<MaterialId[]>(() => gridFromSceneJson(initialSceneJson));
  const [selectedMaterial, setSelectedMaterial] = useState<MaterialId>("lead");
  const [beamSettings, setBeamSettings] = useState<BeamSettings>(() => beamFromSceneJson(initialSceneJson));
  const [sliceIndex, setSliceIndex] = useState(() => firstNonAirSlice(gridFromSceneJson(initialSceneJson)));
  const [savedSceneId, setSavedSceneId] = useState<string | null>(initialSceneId);
  const [isRunning, setIsRunning] = useState(false);
  const [runProgress, setRunProgress] = useState(0);
  const [runProgressLabel, setRunProgressLabel] = useState("Սիմուլյացիան պատրաստվում է");
  const [error, setError] = useState<string | null>(null);
  const [isEditLocked, setIsEditLocked] = useState(false);
  const [editorMode, setEditorMode] = useState<EditorMode>("orbit");
  const [isWalkPointerLocked, setIsWalkPointerLocked] = useState(false);
  const [isControlDrawerOpen, setIsControlDrawerOpen] = useState(true);
  const [closeGuardMessage, setCloseGuardMessage] = useState<string | null>(null);

  const counts = useMemo(() => countMaterials(grid), [grid]);
  const sceneJson = useMemo(() => buildSceneJson(grid, beamSettings), [beamSettings, grid]);

  const captureBeamFromCamera = useCallback((positionCm: Vector3Tuple, direction: Vector3Tuple) => {
    setBeamSettings((current) => ({ ...current, positionCm, direction }));
    setSavedSceneId(null);
  }, []);

  useEffect(() => {
    const nextGrid = gridFromSceneJson(initialSceneJson);
    setGrid(nextGrid);
    setBeamSettings(beamFromSceneJson(initialSceneJson));
    setSliceIndex(firstNonAirSlice(nextGrid));
    setSavedSceneId(initialSceneId);
  }, [initialSceneId, initialSceneJson]);

  useEffect(() => {
    function guardCloseShortcut(event: KeyboardEvent) {
      if ((event.metaKey || event.ctrlKey) && event.code === "KeyW") {
        event.preventDefault();
        event.stopImmediatePropagation();
        setCloseGuardMessage("Փակումը արգելափակվեց");
      }
    }

    function guardUnload(event: BeforeUnloadEvent) {
      event.preventDefault();
      event.returnValue = "";
    }

    window.addEventListener("keydown", guardCloseShortcut, { capture: true });
    window.addEventListener("beforeunload", guardUnload);
    return () => {
      window.removeEventListener("keydown", guardCloseShortcut, { capture: true });
      window.removeEventListener("beforeunload", guardUnload);
    };
  }, []);

  useEffect(() => {
    if (!closeGuardMessage) {
      return;
    }

    const timeoutId = window.setTimeout(() => setCloseGuardMessage(null), 1800);
    return () => window.clearTimeout(timeoutId);
  }, [closeGuardMessage]);

  useEffect(() => {
    function updateEditLock(event: KeyboardEvent) {
      setIsEditLocked(event.metaKey || event.ctrlKey);
    }

    function clearEditLock() {
      setIsEditLocked(false);
    }

    window.addEventListener("keydown", updateEditLock);
    window.addEventListener("keyup", updateEditLock);
    window.addEventListener("blur", clearEditLock);
    return () => {
      window.removeEventListener("keydown", updateEditLock);
      window.removeEventListener("keyup", updateEditLock);
      window.removeEventListener("blur", clearEditLock);
    };
  }, []);

  function applyVoxel(x: number, y: number, z: number, mode: VoxelEditMode) {
    if (x < 0 || x >= dims[0] || y < 0 || y >= dims[1] || z < 0 || z >= dims[2]) {
      return;
    }

    const index = voxelIndex(x, y, z);
    setGrid((current) => {
      const nextMaterial = mode === "erase" ? "air" : selectedMaterial;
      if (current[index] === nextMaterial) {
        return current;
      }
      const next = [...current];
      next[index] = nextMaterial;
      return next;
    });
    setSavedSceneId(null);
  }

  function editSliceVoxel(x: number, y: number, mode: "paint" | "erase") {
    applyVoxel(x, y, sliceIndex, mode);
  }

  async function runSimulation() {
    setIsRunning(true);
    setRunProgress(4);
    setRunProgressLabel("Սիմուլյացիան պատրաստվում է");
    setError(null);
    try {
      let sceneId = savedSceneId;
      if (!sceneId) {
        setRunProgress(8);
        setRunProgressLabel("Տեսարանը պահվում է");
        sceneId = (await createScene(sceneJson)).id;
      }
      setSavedSceneId(sceneId);
      setRunProgress(14);
      setRunProgressLabel("Առաջադրանքն ուղարկվում է");
      const simulation = await createSimulation(sceneId);
      setRunProgress(simulation.progressPercent ?? 0);
      setRunProgressLabel(simulation.progressMessage ?? "Հերթում է");
      router.push(`/simulations/${simulation.id}`);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Չհաջողվեց գործարկել սիմուլյացիան։");
      setIsRunning(false);
      setRunProgress(0);
    }
  }

  return (
    <section className="editor-shell">
      <button
        aria-expanded={isControlDrawerOpen}
        className={`edge-drawer-toggle left-drawer-toggle ${isControlDrawerOpen ? "open" : ""}`}
        onClick={() => setIsControlDrawerOpen((isOpen) => !isOpen)}
        type="button"
      >
        {isControlDrawerOpen ? "Փակել" : "Կառավարում"}
      </button>

      <aside className={`editor-control-drawer ${isControlDrawerOpen ? "open" : ""}`}>
        <div className="drawer-header">
          <div>
            <strong>Կառավարում</strong>
            <div className="muted">Նյութեր, ճառագայթ, տեսարան</div>
          </div>
        </div>
        <div className="drawer-scroll">
          <section className="tutorial-panel">
            <div>
              <strong>Առաջին գործարկում</strong>
              <span className="muted">Կարճ ուղեցույց սկսնակների համար</span>
            </div>
            <ol>
              <li>Ընտրեք դատարկ տեսարան կամ օրինակ, հետո նյութերով նկարեք օբյեկտը կամ պաշտպանիչ շերտը։</li>
              <li>Ճառագայթ բաժնում ընտրեք մասնիկը, էներգիան, մեկնարկային կետը և ուղղությունը։</li>
              <li>Դատարկ տարածքը թողեք որպես օդ, իսկ խիտ նյութերը տեղադրեք այնտեղ, որտեղ պետք է ստուգել պաշտպանությունը։</li>
              <li>Գործարկեք սիմուլյացիան և նայեք դոզայի տեսքին․ պաշտպանիչի հետևում փոքր արժեքները նշանակում են ավելի լավ կլանում։</li>
            </ol>
          </section>
          <MaterialPalette selectedId={selectedMaterial} onSelect={(id) => setSelectedMaterial(id as MaterialId)} />
          <BeamSettingsPanel
            beamSettings={beamSettings}
            onChange={(nextSettings) => {
              setBeamSettings(nextSettings);
              setSavedSceneId(null);
            }}
          />
          <section className="panel">
            <div className="panel-header">
              <strong>Շերտի ներկում</strong>
              <span className="muted">{materialLookup[selectedMaterial].label}</span>
            </div>
            <div className="panel-body editor-controls">
              <label className="slice-control editor-slider">
                <span>Z շերտ {sliceIndex}</span>
                <input
                  max={dims[2] - 1}
                  min={0}
                  onChange={(event) => setSliceIndex(Number(event.target.value))}
                  type="range"
                  value={sliceIndex}
                />
              </label>
              <div className="voxel-paint-grid" style={{ gridTemplateColumns: `repeat(${dims[0]}, 1fr)` }}>
                {Array.from({ length: dims[0] * dims[1] }, (_, cellIndex) => {
                  const x = cellIndex % dims[0];
                  const y = dims[1] - 1 - Math.floor(cellIndex / dims[0]);
                  const materialId = grid[voxelIndex(x, y, sliceIndex)];
                  return (
                    <button
                      aria-label={`Ներկել ${x},${y},${sliceIndex}`}
                      className="voxel-cell"
                      key={`${x}-${y}`}
                      onClick={(event) => editSliceVoxel(x, y, event.shiftKey ? "erase" : "paint")}
                      onPointerEnter={(event) => {
                        if (event.buttons === 1) {
                          editSliceVoxel(x, y, event.shiftKey ? "erase" : "paint");
                        }
                      }}
                      style={{ backgroundColor: materialLookup[materialId].color }}
                      title={`${x}, ${y}, ${sliceIndex}: ${materialLookup[materialId].label}`}
                      type="button"
                    />
                  );
                })}
              </div>
            </div>
          </section>

          <section className="panel">
            <div className="panel-header">
              <strong>Տեսարան</strong>
              <span className="muted">{savedSceneId ? "պահված" : "չպահված"}</span>
            </div>
            <div className="panel-body editor-actions">
              <div className="material-counts">
                {materials.map((material) => (
                  <span key={material.id}>
                    <span className="swatch" style={{ backgroundColor: material.color }} />
                    {counts[material.id] ?? 0}
                  </span>
                ))}
              </div>
              {savedSceneId ? <div className="muted scene-id">Տեսարան {savedSceneId}</div> : null}
            </div>
          </section>
        </div>
      </aside>

      <div className="editor-canvas-panel">
        <div className="editor-run-panel">
          <button className="primary-button run-button" disabled={isRunning} onClick={runSimulation} type="button">
            {isRunning ? "Սկսվում է..." : "Գործարկել սիմուլյացիան"}
          </button>
          {error ? <div className="error-text run-error">{error}</div> : null}
        </div>
        <div className="editor-floating-header">
          <div>
            <strong>Վոքսելային խմբագիր</strong>
            <div className="muted">48 x 24 x 24 վոքսելային տեսարան</div>
          </div>
          <div className="editor-mode-toggle" aria-label="Խմբագրի ռեժիմ" role="group">
            {(["orbit", "walk"] as const).map((mode) => (
              <button
                className={editorMode === mode ? "selected" : ""}
                key={mode}
                onClick={() => setEditorMode(mode)}
                type="button"
              >
                {mode === "orbit" ? "Պտտում" : "Թռիչք"}
              </button>
            ))}
          </div>
          <span className="muted">
            {editorMode === "walk" ? (isWalkPointerLocked ? "թռիչքի ռեժիմ" : "թռիչքը պատրաստ է") : isEditLocked ? "խմբագրումը կողպված է" : `Z ${sliceIndex}`}
          </span>
        </div>
        <div
          className={`voxel-stage ${editorMode === "walk" ? "walk-mode" : ""}`}
          aria-label="Վոքսելային խմբագրի 3D նախադիտում"
          onContextMenu={(event) => event.preventDefault()}
        >
          <Canvas camera={{ position: [34, 24, 34], fov: 70 }} shadows>
            <color attach="background" args={["#141813"]} />
            <Environment preset="warehouse" />
            <ambientLight intensity={1.05} />
            <hemisphereLight args={["#e8f5d2", "#2d3a32", 1.15]} />
            <directionalLight position={[12, 22, 14]} intensity={1.9} castShadow />
            <directionalLight position={[-18, 9, -12]} intensity={0.85} />
            <VoxelPreview
              editingEnabled={editorMode === "orbit"}
              grid={grid}
              onEdit={applyVoxel}
            />
            <EmptySliceBuildPlane
              onEdit={applyVoxel}
              paintingEnabled={editorMode === "orbit" && isEditLocked}
              sliceIndex={sliceIndex}
            />
            <SourceMarker beamSettings={beamSettings} />
            <DetectorPlane />
            <BeamPath beamSettings={beamSettings} />
            <BeamCameraCapture enabled={editorMode === "orbit"} onCapture={captureBeamFromCamera} />
            <FirstPersonVoxelControls
              enabled={editorMode === "walk"}
              grid={grid}
              onEdit={applyVoxel}
              onCapture={captureBeamFromCamera}
              onLockChange={setIsWalkPointerLocked}
            />
            <Grid
              args={[40, 20]}
              cellColor="#384035"
              sectionColor="#d7ff61"
              sectionSize={8}
              position={[0, -dims[1] / 2 - 0.15, 0]}
            />
            <OrbitControls makeDefault enableDamping dampingFactor={0.08} enabled={editorMode === "orbit" && !isEditLocked} />
            <GizmoHelper alignment="bottom-right" margin={[64, 64]}>
              <GizmoViewport axisColors={["#ff6b6b", "#64d78b", "#38bdf8"]} labelColor="#f0f3e8" />
            </GizmoHelper>
          </Canvas>
          {editorMode === "walk" ? (
            <div className="walk-hud" aria-hidden="true">
              <span className="walk-crosshair" />
            </div>
          ) : null}
        </div>
      </div>
      {closeGuardMessage ? <div className="close-guard-toast">{closeGuardMessage}</div> : null}
      {isRunning ? (
        <SimulationProgressBar progressPercent={runProgress} label={runProgressLabel} status="queued" />
      ) : null}
    </section>
  );
}

function BeamSettingsPanel({
  beamSettings,
  onChange,
}: {
  beamSettings: BeamSettings;
  onChange: (settings: BeamSettings) => void;
}) {
  const particleLabel = beamParticles.find((particle) => particle.value === beamSettings.particle)?.label ?? beamSettings.particle;

  function updateEnergy(value: number) {
    onChange({ ...beamSettings, energyGeV: Math.max(0.000001, value) });
  }

  function updateParticle(value: string) {
    onChange({ ...beamSettings, particle: toBeamParticle(value) });
  }

  function updatePosition(axis: 0 | 1 | 2, value: number) {
    const positionCm = [...beamSettings.positionCm] as [number, number, number];
    positionCm[axis] = value;
    onChange({ ...beamSettings, positionCm });
  }

  function updateDirection(axis: 0 | 1 | 2, value: number) {
    const direction = [...beamSettings.direction] as [number, number, number];
    direction[axis] = Number.isFinite(value) ? value : 0;
    onChange({ ...beamSettings, direction });
  }

  return (
    <section className="panel">
      <div className="panel-header">
        <strong>Ճառագայթ</strong>
        <span className="muted">{particleLabel} ճառագայթ</span>
      </div>
      <div className="panel-body beam-controls">
        <label className="numeric-control">
          <span>Մասնիկ</span>
          <select onChange={(event) => updateParticle(event.target.value)} value={beamSettings.particle}>
            {beamParticles.map((particle) => (
              <option key={particle.value} value={particle.value}>
                {particle.label}
              </option>
            ))}
          </select>
        </label>
        <label className="numeric-control">
          <span>Էներգիա GeV</span>
          <input
            min={0.000001}
            onChange={(event) => updateEnergy(Number(event.target.value))}
            step={0.0001}
            type="number"
            value={beamSettings.energyGeV}
          />
        </label>
        <div className="beam-position-grid">
          {(["X", "Y", "Z"] as const).map((axis, index) => {
            const axisIndex = index as 0 | 1 | 2;
            return (
              <label className="numeric-control" key={axis}>
                <span>{axis} cm</span>
                <input
                  max={axisIndex === 0 ? 160 : 80}
                  min={axisIndex === 2 ? -50 : 0}
                  onChange={(event) => updatePosition(axisIndex, Number(event.target.value))}
                  step={axisIndex === 2 ? 1 : 0.5}
                  type="number"
                  value={roundForInput(beamSettings.positionCm[axisIndex])}
                />
              </label>
            );
          })}
        </div>
        <div className="beam-position-grid beam-vector-grid">
          {(["Ուղղ. X", "Ուղղ. Y", "Ուղղ. Z"] as const).map((axis, index) => {
            const axisIndex = index as 0 | 1 | 2;
            return (
              <label className="numeric-control" key={axis}>
                <span>{axis}</span>
                <input
                  max={1}
                  min={-1}
                  onChange={(event) => updateDirection(axisIndex, Number(event.target.value))}
                  step={0.001}
                  type="number"
                  value={roundForInput(beamSettings.direction[axisIndex])}
                />
              </label>
            );
          })}
        </div>
      </div>
    </section>
  );
}

function BeamCameraCapture({
  enabled,
  onCapture,
}: {
  enabled: boolean;
  onCapture: (positionCm: Vector3Tuple, direction: Vector3Tuple) => void;
}) {
  const { camera } = useThree();

  useEffect(() => {
    if (!enabled) {
      return;
    }

    function handleKeyDown(event: KeyboardEvent) {
      if (event.code !== "Space" || event.repeat || isEditableKeyboardTarget(event.target)) {
        return;
      }
      event.preventDefault();

      const direction = new THREE.Vector3();
      camera.getWorldDirection(direction);
      onCapture(
        renderPositionToCm([camera.position.x, camera.position.y, camera.position.z]),
        renderDirectionToCm([direction.x, direction.y, direction.z]),
      );
    }

    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [camera, enabled, onCapture]);

  return null;
}

function FirstPersonVoxelControls({
  enabled,
  grid,
  onCapture,
  onEdit,
  onLockChange,
}: {
  enabled: boolean;
  grid: MaterialId[];
  onCapture: (positionCm: Vector3Tuple, direction: Vector3Tuple) => void;
  onEdit: (x: number, y: number, z: number, mode: VoxelEditMode) => void;
  onLockChange: (isLocked: boolean) => void;
}) {
  const { camera, gl } = useThree();
  const gridRef = useRef(grid);
  const onEditRef = useRef(onEdit);
  const keysRef = useRef<Record<string, boolean>>({});
  const velocityRef = useRef(new THREE.Vector3());
  const yawRef = useRef(Math.PI);
  const pitchRef = useRef(0);

  useEffect(() => {
    gridRef.current = grid;
  }, [grid]);

  useEffect(() => {
    onEditRef.current = onEdit;
  }, [onEdit]);

  useEffect(() => {
    if (!enabled) {
      keysRef.current = {};
      velocityRef.current.set(0, 0, 0);
      onLockChange(false);
      if (document.pointerLockElement === gl.domElement) {
        document.exitPointerLock();
      }
      return;
    }

    const spawn = findWalkSpawn(gridRef.current);
    camera.position.set(spawn[0], spawn[1], spawn[2]);
    yawRef.current = Math.PI;
    pitchRef.current = 0;
    applyFirstPersonRotation(camera, yawRef.current, pitchRef.current);
    velocityRef.current.set(0, 0, 0);
  }, [camera, enabled, gl.domElement, onLockChange]);

  useEffect(() => {
    if (!enabled) {
      return;
    }

    const canvas = gl.domElement;

    function requestLock() {
      canvas.requestPointerLock();
    }

    function updatePointerLock() {
      const isLocked = document.pointerLockElement === canvas;
      onLockChange(isLocked);
      if (isLocked) {
        const euler = new THREE.Euler().setFromQuaternion(camera.quaternion, "YXZ");
        yawRef.current = euler.y;
        pitchRef.current = euler.x;
      } else {
        keysRef.current = {};
        velocityRef.current.set(0, 0, 0);
      }
    }

    function handleMouseMove(event: MouseEvent) {
      if (document.pointerLockElement !== canvas) {
        return;
      }

      yawRef.current -= event.movementX * 0.0021;
      pitchRef.current = THREE.MathUtils.clamp(
        pitchRef.current - event.movementY * 0.0021,
        -Math.PI / 2 + 0.04,
        Math.PI / 2 - 0.04,
      );
      applyFirstPersonRotation(camera, yawRef.current, pitchRef.current);
    }

    function handleKeyDown(event: KeyboardEvent) {
      if (document.pointerLockElement !== canvas) {
        return;
      }
      if (isEditableKeyboardTarget(event.target)) {
        return;
      }

      if (event.code === "Enter" && !event.repeat) {
        event.preventDefault();
        const direction = new THREE.Vector3();
        camera.getWorldDirection(direction);
        onCapture(
          renderPositionToCm([camera.position.x, camera.position.y, camera.position.z]),
          renderDirectionToCm([direction.x, direction.y, direction.z]),
        );
        return;
      }

      if (isFirstPersonKey(event.code)) {
        event.preventDefault();
      }

      keysRef.current[event.code] = true;
    }

    function handleKeyUp(event: KeyboardEvent) {
      if (document.pointerLockElement !== canvas) {
        return;
      }
      keysRef.current[event.code] = false;
      if (event.code === "MetaLeft" || event.code === "MetaRight") {
        keysRef.current.MetaLeft = false;
        keysRef.current.MetaRight = false;
      }
    }

    function handleMouseDown(event: MouseEvent) {
      if (document.pointerLockElement !== canvas) {
        return;
      }
      if (event.button !== 0 && event.button !== 2) {
        return;
      }

      event.preventDefault();
      const mode: VoxelEditMode = event.shiftKey || event.button === 2 ? "erase" : "paint";
      editFromFirstPersonRay(camera, gridRef.current, onEditRef.current, mode);
    }

    function handleContextMenu(event: MouseEvent) {
      if (document.pointerLockElement === canvas || event.target === canvas) {
        event.preventDefault();
      }
    }

    function handleBlur() {
      keysRef.current = {};
      velocityRef.current.set(0, 0, 0);
    }

    canvas.addEventListener("click", requestLock);
    document.addEventListener("pointerlockchange", updatePointerLock);
    document.addEventListener("mousemove", handleMouseMove);
    document.addEventListener("mousedown", handleMouseDown);
    document.addEventListener("contextmenu", handleContextMenu);
    window.addEventListener("keydown", handleKeyDown);
    window.addEventListener("keyup", handleKeyUp);
    window.addEventListener("blur", handleBlur);

    return () => {
      canvas.removeEventListener("click", requestLock);
      document.removeEventListener("pointerlockchange", updatePointerLock);
      document.removeEventListener("mousemove", handleMouseMove);
      document.removeEventListener("mousedown", handleMouseDown);
      document.removeEventListener("contextmenu", handleContextMenu);
      window.removeEventListener("keydown", handleKeyDown);
      window.removeEventListener("keyup", handleKeyUp);
      window.removeEventListener("blur", handleBlur);
      onLockChange(false);
    };
  }, [camera, enabled, gl.domElement, onCapture, onLockChange]);

  useFrame((_, frameDelta) => {
    if (!enabled || document.pointerLockElement !== gl.domElement) {
      return;
    }

    const delta = Math.min(frameDelta, 0.045);
    const keys = keysRef.current;
    const forward = new THREE.Vector3();
    camera.getWorldDirection(forward);
    forward.y = 0;
    if (forward.lengthSq() < 1e-8) {
      forward.set(0, 0, 1);
    } else {
      forward.normalize();
    }

    const right = new THREE.Vector3(1, 0, 0).applyQuaternion(camera.quaternion);
    right.y = 0;
    if (right.lengthSq() < 1e-8) {
      right.set(1, 0, 0);
    } else {
      right.normalize();
    }
    const wishDirection = new THREE.Vector3();
    if (keys.KeyW) {
      wishDirection.add(forward);
    }
    if (keys.KeyS) {
      wishDirection.sub(forward);
    }
    if (keys.KeyD) {
      wishDirection.add(right);
    }
    if (keys.KeyA) {
      wishDirection.sub(right);
    }

    const speed = walkControls.walkSpeed * (keys.ShiftLeft || keys.ShiftRight ? walkControls.sprintMultiplier : 1);
    const verticalDirection =
      (keys.Space ? 1 : 0) -
      (keys.ControlLeft || keys.ControlRight || keys.MetaLeft || keys.MetaRight ? 1 : 0);
    const velocity = velocityRef.current;
    if (wishDirection.lengthSq() > 1e-8) {
      wishDirection.normalize().multiplyScalar(speed);
      velocity.x = wishDirection.x;
      velocity.z = wishDirection.z;
    } else {
      velocity.x = 0;
      velocity.z = 0;
    }
    velocity.y = verticalDirection * walkControls.verticalSpeed * (keys.ShiftLeft || keys.ShiftRight ? walkControls.sprintMultiplier : 1);

    const moved = movePlayer(camera.position, velocity, delta, gridRef.current);
    camera.position.copy(moved.position);
    velocityRef.current.copy(moved.velocity);
  });

  return null;
}

function EmptySliceBuildPlane({
  onEdit,
  paintingEnabled,
  sliceIndex,
}: {
  onEdit: (x: number, y: number, z: number, mode: VoxelEditMode) => void;
  paintingEnabled: boolean;
  sliceIndex: number;
}) {
  const zPosition = sliceIndex - dims[2] / 2 + 0.5;

  if (!paintingEnabled) {
    return null;
  }

  function editFromPoint(event: ThreeEvent<PointerEvent>, mode: VoxelEditMode) {
    const x = Math.min(dims[0] - 1, Math.max(0, Math.floor(event.point.x + dims[0] / 2)));
    const y = Math.min(dims[1] - 1, Math.max(0, Math.floor(event.point.y + dims[1] / 2)));
    onEdit(x, y, sliceIndex, mode);
  }

  return (
    <group position={[0, 0, zPosition]} renderOrder={20}>
      <mesh
        onPointerDown={(event) => {
          if (!paintingEnabled) {
            return;
          }
          const mode = editModeFromPointerButton(event.nativeEvent.button);
          if (!mode) {
            return;
          }
          event.stopPropagation();
          editFromPoint(event, mode);
        }}
        onPointerMove={(event) => {
          const mode = editModeFromPointerButtons(event.nativeEvent.buttons);
          if (!paintingEnabled || !mode) {
            return;
          }
          event.stopPropagation();
          editFromPoint(event, mode);
        }}
      >
        <planeGeometry args={[dims[0], dims[1], dims[0], dims[1]]} />
        <meshBasicMaterial
          depthWrite={false}
          opacity={0}
          side={THREE.DoubleSide}
          transparent
        />
      </mesh>
    </group>
  );
}

type VoxelInstance = {
  x: number;
  y: number;
  z: number;
  position: [number, number, number];
};

function VoxelPreview({
  editingEnabled,
  grid,
  onEdit,
}: {
  editingEnabled: boolean;
  grid: MaterialId[];
  onEdit: (x: number, y: number, z: number, mode: VoxelEditMode) => void;
}) {
  const groups = useMemo(() => {
    const next = new Map<MaterialId, VoxelInstance[]>();
    for (let z = 0; z < dims[2]; z += 1) {
      for (let y = 0; y < dims[1]; y += 1) {
        for (let x = 0; x < dims[0]; x += 1) {
          const materialId = grid[voxelIndex(x, y, z)];
          if (materialId === "air") {
            continue;
          }
          const positions = next.get(materialId) ?? [];
          positions.push({
            x,
            y,
            z,
            position: [x - dims[0] / 2 + 0.5, y - dims[1] / 2 + 0.5, z - dims[2] / 2 + 0.5],
          });
          next.set(materialId, positions);
        }
      }
    }
    return next;
  }, [grid]);

  return (
    <>
      {materials
        .filter((material) => material.id !== "air")
        .map((material) => (
          <VoxelInstances
            color={material.color}
            editingEnabled={editingEnabled}
            key={material.id}
            onEdit={onEdit}
            voxels={groups.get(material.id) ?? []}
          />
        ))}
    </>
  );
}

function VoxelInstances({
  color,
  editingEnabled,
  onEdit,
  voxels,
}: {
  color: string;
  editingEnabled: boolean;
  onEdit: (x: number, y: number, z: number, mode: VoxelEditMode) => void;
  voxels: VoxelInstance[];
}) {
  const meshRef = useRef<THREE.InstancedMesh>(null);

  useLayoutEffect(() => {
    if (!meshRef.current) {
      return;
    }
    const matrixObject = new THREE.Object3D();
    voxels.forEach((voxel, index) => {
      matrixObject.position.set(voxel.position[0], voxel.position[1], voxel.position[2]);
      matrixObject.updateMatrix();
      meshRef.current?.setMatrixAt(index, matrixObject.matrix);
    });
    meshRef.current.instanceMatrix.needsUpdate = true;
  }, [meshRef, voxels]);

  if (voxels.length === 0) {
    return null;
  }

  return (
    <instancedMesh
      ref={meshRef}
      args={[undefined, undefined, voxels.length]}
      castShadow
      onPointerDown={(event) => {
        const mode = editModeFromPointerButton(event.nativeEvent.button);
        if (!editingEnabled || !mode) {
          return;
        }
        event.stopPropagation();
        if (event.instanceId === undefined) {
          return;
        }
        const voxel = voxels[event.instanceId];
        editVoxelFace(voxel, event, onEdit, mode);
      }}
      onPointerEnter={(event: ThreeEvent<PointerEvent>) => {
        const mode = editModeFromPointerButtons(event.nativeEvent.buttons);
        if (!editingEnabled || !mode || event.instanceId === undefined) {
          return;
        }
        event.stopPropagation();
        const voxel = voxels[event.instanceId];
        editVoxelFace(voxel, event, onEdit, mode);
      }}
      receiveShadow
    >
      <boxGeometry args={[0.94, 0.94, 0.94]} />
      <meshStandardMaterial color={color} roughness={0.78} metalness={0.08} />
    </instancedMesh>
  );
}

function editVoxelFace(
  voxel: VoxelInstance,
  event: ThreeEvent<MouseEvent | PointerEvent>,
  onEdit: (x: number, y: number, z: number, mode: VoxelEditMode) => void,
  mode: VoxelEditMode,
) {
  if (mode === "erase") {
    onEdit(voxel.x, voxel.y, voxel.z, "erase");
    return;
  }

  const normal = event.face?.normal ?? new THREE.Vector3(0, 0, 1);
  onEdit(
    voxel.x + Math.round(normal.x),
    voxel.y + Math.round(normal.y),
    voxel.z + Math.round(normal.z),
    "paint",
  );
}

function editModeFromPointerButton(button: number): VoxelEditMode | null {
  if (button === 0) {
    return "paint";
  }
  if (button === 2) {
    return "erase";
  }
  return null;
}

function editModeFromPointerButtons(buttons: number): VoxelEditMode | null {
  if ((buttons & 2) === 2) {
    return "erase";
  }
  if ((buttons & 1) === 1) {
    return "paint";
  }
  return null;
}

function applyFirstPersonRotation(camera: THREE.Camera, yaw: number, pitch: number) {
  camera.quaternion.setFromEuler(new THREE.Euler(pitch, yaw, 0, "YXZ"));
}

function isFirstPersonKey(code: string): boolean {
  return [
    "KeyW",
    "KeyA",
    "KeyS",
    "KeyD",
    "Space",
    "ShiftLeft",
    "ShiftRight",
    "ControlLeft",
    "ControlRight",
    "MetaLeft",
    "MetaRight",
  ].includes(code);
}

function findWalkSpawn(grid: MaterialId[]): Vector3Tuple {
  const xOrder = centeredIndexOrder(dims[0]);
  const zOrder = centeredIndexOrder(dims[2]);

  for (let y = 0; y < dims[1] - 1; y += 1) {
    for (const z of zOrder) {
      for (const x of xOrder) {
        const position = new THREE.Vector3(
          x - dims[0] / 2 + 0.5,
          y - dims[1] / 2 + walkControls.eyeHeight,
          z - dims[2] / 2 + 0.5,
        );
        if (!playerCollides(position, grid)) {
          return [position.x, position.y, position.z];
        }
      }
    }
  }

  return [0, -dims[1] / 2 + walkControls.eyeHeight, -dims[2] / 2 + 2];
}

function centeredIndexOrder(size: number): number[] {
  const center = (size - 1) / 2;
  return Array.from({ length: size }, (_, index) => index).sort(
    (left, right) => Math.abs(left - center) - Math.abs(right - center),
  );
}

function editFromFirstPersonRay(
  camera: THREE.Camera,
  grid: MaterialId[],
  onEdit: (x: number, y: number, z: number, mode: VoxelEditMode) => void,
  mode: VoxelEditMode,
) {
  const origin = camera.position.clone();
  const direction = new THREE.Vector3();
  camera.getWorldDirection(direction).normalize();

  const hit = raycastVoxelGrid(origin, direction, grid, walkControls.rayDistance);
  if (mode === "erase") {
    if (hit) {
      onEdit(hit.voxel[0], hit.voxel[1], hit.voxel[2], "erase");
    }
    return;
  }

  const target = hit
    ? addVoxelCoordinates(hit.voxel, hit.normal)
    : raycastBuildFloor(origin, direction, walkControls.rayDistance);
  if (!target || !isVoxelInBounds(target[0], target[1], target[2])) {
    return;
  }
  if (grid[voxelIndex(target[0], target[1], target[2])] !== "air" || voxelIntersectsPlayer(target, origin)) {
    return;
  }

  onEdit(target[0], target[1], target[2], "paint");
}

function raycastVoxelGrid(
  origin: THREE.Vector3,
  direction: THREE.Vector3,
  grid: MaterialId[],
  maxDistance: number,
): VoxelHit | null {
  const point = new THREE.Vector3();
  let previous = renderPointToVoxel(origin);

  for (let distance = 0; distance <= maxDistance; distance += 0.04) {
    point.copy(origin).addScaledVector(direction, distance);
    const voxel = renderPointToVoxel(point);
    if (!voxel) {
      previous = null;
      continue;
    }

    if (grid[voxelIndex(voxel[0], voxel[1], voxel[2])] !== "air") {
      return {
        normal: faceNormalFromTransition(previous, voxel, direction),
        voxel,
      };
    }

    previous = voxel;
  }

  return null;
}

function raycastBuildFloor(
  origin: THREE.Vector3,
  direction: THREE.Vector3,
  maxDistance: number,
): VoxelCoordinate | null {
  const floorY = -dims[1] / 2;
  if (direction.y >= -1e-5) {
    return null;
  }

  const distance = (floorY - origin.y) / direction.y;
  if (distance < 0 || distance > maxDistance) {
    return null;
  }

  const point = origin.clone().addScaledVector(direction, distance);
  const x = Math.floor(point.x + dims[0] / 2);
  const z = Math.floor(point.z + dims[2] / 2);
  if (!isVoxelInBounds(x, 0, z)) {
    return null;
  }

  return [x, 0, z];
}

function renderPointToVoxel(point: THREE.Vector3): VoxelCoordinate | null {
  const x = Math.floor(point.x + dims[0] / 2);
  const y = Math.floor(point.y + dims[1] / 2);
  const z = Math.floor(point.z + dims[2] / 2);
  return isVoxelInBounds(x, y, z) ? [x, y, z] : null;
}

function faceNormalFromTransition(
  previous: VoxelCoordinate | null,
  current: VoxelCoordinate,
  direction: THREE.Vector3,
): VoxelCoordinate {
  if (previous) {
    const diff: VoxelCoordinate = [
      previous[0] - current[0],
      previous[1] - current[1],
      previous[2] - current[2],
    ];
    const dominant = dominantCoordinateIndex(diff);
    if (dominant !== null) {
      const normal: VoxelCoordinate = [0, 0, 0];
      normal[dominant] = Math.sign(diff[dominant]);
      return normal;
    }
  }

  const directionValues = [direction.x, direction.y, direction.z];
  const axis = dominantCoordinateIndex(directionValues) ?? 2;
  const normal: VoxelCoordinate = [0, 0, 0];
  normal[axis] = directionValues[axis] > 0 ? -1 : 1;
  return normal;
}

function dominantCoordinateIndex(values: readonly number[]): 0 | 1 | 2 | null {
  let bestIndex: 0 | 1 | 2 | null = null;
  let bestValue = 1e-8;
  for (let index = 0; index < 3; index += 1) {
    const magnitude = Math.abs(values[index]);
    if (magnitude > bestValue) {
      bestValue = magnitude;
      bestIndex = index as 0 | 1 | 2;
    }
  }
  return bestIndex;
}

function addVoxelCoordinates(left: VoxelCoordinate, right: VoxelCoordinate): VoxelCoordinate {
  return [left[0] + right[0], left[1] + right[1], left[2] + right[2]];
}

function movePlayer(
  currentPosition: THREE.Vector3,
  currentVelocity: THREE.Vector3,
  delta: number,
  grid: MaterialId[],
): { onGround: boolean; position: THREE.Vector3; velocity: THREE.Vector3 } {
  const position = currentPosition.clone();
  const velocity = currentVelocity.clone();
  const movement = velocity.clone().multiplyScalar(delta);
  let onGround = false;

  for (const axis of ["x", "z", "y"] as const) {
    const attempt = position.clone();
    attempt[axis] += movement[axis];

    if (axis === "y" && attempt.y - walkControls.eyeHeight < -dims[1] / 2) {
      position.y = -dims[1] / 2 + walkControls.eyeHeight;
      velocity.y = 0;
      onGround = true;
      continue;
    }

    if (playerCollides(attempt, grid)) {
      if (axis === "y" && movement.y < 0) {
        onGround = true;
      }
      velocity[axis] = 0;
      continue;
    }

    position[axis] = attempt[axis];
  }

  if (!onGround && velocity.y <= 0) {
    const groundProbe = position.clone();
    groundProbe.y -= 0.05;
    onGround = groundProbe.y - walkControls.eyeHeight <= -dims[1] / 2 || playerCollides(groundProbe, grid);
  }

  return { onGround, position, velocity };
}

function playerCollides(eyePosition: THREE.Vector3, grid: MaterialId[]): boolean {
  const minX = eyePosition.x - walkControls.radius;
  const maxX = eyePosition.x + walkControls.radius;
  const minY = eyePosition.y - walkControls.eyeHeight;
  const maxY = minY + walkControls.height;
  const minZ = eyePosition.z - walkControls.radius;
  const maxZ = eyePosition.z + walkControls.radius;

  if (
    minX < -dims[0] / 2 ||
    maxX > dims[0] / 2 ||
    minY < -dims[1] / 2 - 1e-5 ||
    maxY > dims[1] / 2 ||
    minZ < -dims[2] / 2 ||
    maxZ > dims[2] / 2
  ) {
    return true;
  }

  const minVoxelX = Math.max(0, Math.floor(minX + dims[0] / 2));
  const maxVoxelX = Math.min(dims[0] - 1, Math.floor(maxX + dims[0] / 2));
  const minVoxelY = Math.max(0, Math.floor(minY + dims[1] / 2 + 1e-4));
  const maxVoxelY = Math.min(dims[1] - 1, Math.floor(maxY + dims[1] / 2 - 1e-4));
  const minVoxelZ = Math.max(0, Math.floor(minZ + dims[2] / 2));
  const maxVoxelZ = Math.min(dims[2] - 1, Math.floor(maxZ + dims[2] / 2));

  for (let z = minVoxelZ; z <= maxVoxelZ; z += 1) {
    for (let y = minVoxelY; y <= maxVoxelY; y += 1) {
      for (let x = minVoxelX; x <= maxVoxelX; x += 1) {
        if (grid[voxelIndex(x, y, z)] !== "air") {
          return true;
        }
      }
    }
  }

  return false;
}

function voxelIntersectsPlayer(voxel: VoxelCoordinate, eyePosition: THREE.Vector3): boolean {
  const voxelMinX = voxel[0] - dims[0] / 2;
  const voxelMaxX = voxelMinX + 1;
  const voxelMinY = voxel[1] - dims[1] / 2;
  const voxelMaxY = voxelMinY + 1;
  const voxelMinZ = voxel[2] - dims[2] / 2;
  const voxelMaxZ = voxelMinZ + 1;

  const playerMinX = eyePosition.x - walkControls.radius;
  const playerMaxX = eyePosition.x + walkControls.radius;
  const playerMinY = eyePosition.y - walkControls.eyeHeight;
  const playerMaxY = playerMinY + walkControls.height;
  const playerMinZ = eyePosition.z - walkControls.radius;
  const playerMaxZ = eyePosition.z + walkControls.radius;

  return (
    voxelMinX < playerMaxX &&
    voxelMaxX > playerMinX &&
    voxelMinY < playerMaxY &&
    voxelMaxY > playerMinY &&
    voxelMinZ < playerMaxZ &&
    voxelMaxZ > playerMinZ
  );
}

function SourceMarker({ beamSettings }: { beamSettings: BeamSettings }) {
  const position = cmToRenderPosition(beamSettings.positionCm);
  return (
    <mesh position={position} castShadow>
      <sphereGeometry args={[1.15, 24, 24]} />
      <meshStandardMaterial color="#ffb84d" emissive="#8a4a00" emissiveIntensity={0.45} />
    </mesh>
  );
}

function DetectorPlane() {
  return (
    <mesh position={[0, 0, dims[2] / 2 - 0.5]} receiveShadow>
      <boxGeometry args={[dims[0], dims[1], 0.25]} />
      <meshStandardMaterial color="#f59e0b" transparent opacity={0.28} />
    </mesh>
  );
}

function BeamPath({ beamSettings }: { beamSettings: BeamSettings }) {
  const path = buildBeamPathGeometry(
    cmToRenderPosition(beamSettings.positionCm),
    cmDirectionToRenderDirection(beamSettings.direction),
    [dims[0] / 2, dims[1] / 2, dims[2] / 2],
  );

  return (
    <mesh position={path.center} quaternion={path.quaternion}>
      <cylinderGeometry args={[0.07, 0.07, path.length, 16]} />
      <meshStandardMaterial color="#d7ff61" emissive="#d7ff61" emissiveIntensity={0.7} />
    </mesh>
  );
}

function createEmptyGrid(): MaterialId[] {
  return Array.from({ length: dims[0] * dims[1] * dims[2] }, () => "air");
}

function gridFromSceneJson(sceneJson?: Record<string, unknown> | null): MaterialId[] {
  if (!sceneJson) {
    return createEmptyGrid();
  }

  const world = sceneJson.world as Record<string, unknown> | undefined;
  const gridDefinition = world?.grid as Record<string, unknown> | undefined;
  const sceneDims = gridDefinition?.dims;
  const chunks = world?.chunks;
  const firstChunk = Array.isArray(chunks) ? (chunks[0] as Record<string, unknown> | undefined) : undefined;
  const runs = firstChunk?.runs;

  if (!isNumberTuple(sceneDims, dims) || !Array.isArray(runs)) {
    return createEmptyGrid();
  }

  const grid: MaterialId[] = [];
  for (const run of runs) {
    if (!run || typeof run !== "object") {
      continue;
    }
    const blockId = (run as Record<string, unknown>).blockId;
    const count = (run as Record<string, unknown>).count;
    const materialId = isMaterialId(blockId) ? blockId : "air";
    if (typeof count === "number" && Number.isFinite(count) && count > 0) {
      grid.push(...Array.from({ length: count }, () => materialId));
    }
  }

  const expectedCount = dims[0] * dims[1] * dims[2];
  if (grid.length !== expectedCount) {
    return createEmptyGrid();
  }
  return grid;
}

function beamFromSceneJson(sceneJson?: Record<string, unknown> | null): BeamSettings {
  const sources = sceneJson?.sources;
  const firstSource = Array.isArray(sources) ? (sources[0] as Record<string, unknown> | undefined) : undefined;
  const energy = firstSource?.energyGeV;
  const particle = firstSource?.particle;
  const position = firstSource?.positionCm;
  const direction = firstSource?.direction;

  return {
    energyGeV: typeof energy === "number" && energy > 0 ? energy : defaultBeamSettings.energyGeV,
    particle: typeof particle === "string" ? toBeamParticle(particle) : defaultBeamSettings.particle,
    positionCm: isThreeNumberTuple(position) ? position : defaultBeamSettings.positionCm,
    direction: isThreeNumberTuple(direction) ? normalizeDirection(direction) : defaultBeamSettings.direction,
  };
}

function toBeamParticle(value: string): BeamParticle {
  const normalized = value.toUpperCase();
  return beamParticles.some((particle) => particle.value === normalized)
    ? (normalized as BeamParticle)
    : defaultBeamSettings.particle;
}

function isNumberTuple(value: unknown, expected: readonly number[]): boolean {
  return (
    Array.isArray(value) &&
    value.length === expected.length &&
    value.every((entry, index) => typeof entry === "number" && entry === expected[index])
  );
}

function isThreeNumberTuple(value: unknown): value is [number, number, number] {
  return (
    Array.isArray(value) &&
    value.length === 3 &&
    value.every((entry) => typeof entry === "number" && Number.isFinite(entry))
  );
}

function isMaterialId(value: unknown): value is MaterialId {
  return typeof value === "string" && value in materialLookup;
}

function firstNonAirSlice(grid: MaterialId[]): number {
  const sliceSize = dims[0] * dims[1];
  for (let z = 0; z < dims[2]; z += 1) {
    const start = z * sliceSize;
    const end = start + sliceSize;
    if (grid.slice(start, end).some((materialId) => materialId !== "air")) {
      return z;
    }
  }
  return 7;
}

function voxelIndex(x: number, y: number, z: number): number {
  return z * dims[0] * dims[1] + y * dims[0] + x;
}

function isVoxelInBounds(x: number, y: number, z: number): boolean {
  return x >= 0 && x < dims[0] && y >= 0 && y < dims[1] && z >= 0 && z < dims[2];
}

function countMaterials(grid: MaterialId[]): Record<string, number> {
  return grid.reduce<Record<string, number>>((counts, materialId) => {
    counts[materialId] = (counts[materialId] ?? 0) + 1;
    return counts;
  }, {});
}

function buildSceneJson(grid: MaterialId[], beamSettings: BeamSettings): Record<string, unknown> {
  const maxCm = dims.map((value, index) => value * voxelSizeCm[index]);
  return {
    schema: "oopsenheimer.scene.v1",
    units: { length: "cm", energy: "GeV", density: "g/cm3" },
    world: {
      id: "editor_scene",
      grid: {
        dims,
        voxelSizeCm,
        originCm: [0, 0, 0],
        axisOrder: "x-fastest",
      },
      boundary: {
        outsideMaterialId: "air",
        blackholeMarginCm: 100,
        worldAirMarginCm: 50,
      },
      palette: Object.fromEntries(
        materials.map((material) => [
          material.id,
          {
            materialId: material.id,
            label: material.label,
            color: material.color,
          },
        ]),
      ),
      chunks: [
        {
          id: "main",
          origin: [0, 0, 0],
          size: dims,
          encoding: "rle",
          runs: encodeRle(grid),
        },
      ],
      organPolicy: {
        mode: "merge_by_material_and_tag",
        maxOrgans: 32767,
        reserveOrganZeroForOutside: true,
        splitRules: [],
        fallback: { onTooManyOrgans: "reject_scene" },
      },
    },
    materials: Object.fromEntries(
      materials.map((material) => [
        material.id,
        {
          flukaName: material.flukaName,
          density: material.density,
          label: material.label,
          color: material.color,
        },
      ]),
    ),
    sources: [
      {
        id: "primary_beam",
        type: "particle_beam",
        particle: beamSettings.particle,
        energyGeV: beamSettings.energyGeV,
        positionCm: beamSettings.positionCm,
        direction: normalizeDirection(beamSettings.direction),
      },
    ],
    scoring: [
      {
        id: "dose_map",
        type: "usrbin_cartesian",
        quantity: "DOSE",
        dims,
        minCm: [0, 0, 0],
        maxCm,
      },
    ],
    run: {
      defaults: "PRECISIO",
      histories: 100000,
      randomSeed: 12345,
      cycles: 1,
      validation: { geometryDebug: true },
    },
    emit: {
      backend: "fluka_voxel",
      flukaInput: {
        filename: "scene.inp",
        title: "Oosenhaimer-ի խմբագրով ստեղծված տեսարան",
        includeComments: true,
      },
      voxelFile: {
        filename: "scene.vxl",
        format: "fluka_unformatted_vxl",
        compactOrganIds: true,
      },
      manifest: {
        filename: "scene.map.json",
        includeVoxelToOrganMap: false,
        includeOrganToRegionMap: true,
        includeMaterialMap: true,
      },
    },
  };
}

function cmToRenderPosition(positionCm: [number, number, number]): [number, number, number] {
  return [
    positionCm[0] / voxelSizeCm[0] - dims[0] / 2,
    positionCm[1] / voxelSizeCm[1] - dims[1] / 2,
    positionCm[2] / voxelSizeCm[2] - dims[2] / 2,
  ];
}

function renderPositionToCm(position: Vector3Tuple): Vector3Tuple {
  return [
    (position[0] + dims[0] / 2) * voxelSizeCm[0],
    (position[1] + dims[1] / 2) * voxelSizeCm[1],
    (position[2] + dims[2] / 2) * voxelSizeCm[2],
  ];
}

function renderDirectionToCm(direction: Vector3Tuple): Vector3Tuple {
  return normalizeDirection([
    direction[0] * voxelSizeCm[0],
    direction[1] * voxelSizeCm[1],
    direction[2] * voxelSizeCm[2],
  ]);
}

function cmDirectionToRenderDirection(direction: Vector3Tuple): Vector3Tuple {
  return normalizeDirection([
    direction[0] / voxelSizeCm[0],
    direction[1] / voxelSizeCm[1],
    direction[2] / voxelSizeCm[2],
  ]);
}

function normalizeDirection(direction: Vector3Tuple): Vector3Tuple {
  const vector = new THREE.Vector3(direction[0], direction[1], direction[2]);
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

function isEditableKeyboardTarget(target: EventTarget | null): boolean {
  if (!(target instanceof HTMLElement)) {
    return false;
  }
  return target.isContentEditable || ["INPUT", "TEXTAREA", "SELECT"].includes(target.tagName);
}

function roundForInput(value: number): number {
  return Number(value.toFixed(6));
}

function encodeRle(grid: MaterialId[]): { blockId: string; count: number }[] {
  const runs: { blockId: string; count: number }[] = [];
  for (const materialId of grid) {
    const previous = runs.at(-1);
    if (previous?.blockId === materialId) {
      previous.count += 1;
    } else {
      runs.push({ blockId: materialId, count: 1 });
    }
  }
  return runs;
}
