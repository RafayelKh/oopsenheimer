"use client";

import { Canvas } from "@react-three/fiber";
import { GizmoHelper, GizmoViewport, Grid, OrbitControls } from "@react-three/drei";

type SceneViewerProps = {
  title?: string;
};

export function SceneViewer({ title = "Scene viewer" }: SceneViewerProps) {
  return (
    <section className="panel scene-viewer">
      <div className="panel-header">
        <strong>{title}</strong>
        <span className="muted">air hidden</span>
      </div>
      <div className="voxel-stage" aria-label="Voxel scene">
        <Canvas camera={{ position: [26, 20, 24], fov: 42 }} shadows>
          <color attach="background" args={["#0b0d0a"]} />
          <ambientLight intensity={0.65} />
          <directionalLight position={[10, 16, 12]} intensity={1.4} castShadow />
          <LeadWall />
          <SourceMarker />
          <DetectorPlane />
          <BeamPath />
          <Grid
            args={[36, 20]}
            cellColor="#384035"
            sectionColor="#d7ff61"
            sectionSize={8}
            position={[0, -8.1, 0]}
          />
          <axesHelper args={[12]} />
          <OrbitControls makeDefault enableDamping dampingFactor={0.08} />
          <GizmoHelper alignment="bottom-right" margin={[64, 64]}>
            <GizmoViewport axisColors={["#ff6b6b", "#64d78b", "#38bdf8"]} labelColor="#f0f3e8" />
          </GizmoHelper>
        </Canvas>
      </div>
    </section>
  );
}

function LeadWall() {
  return (
    <mesh position={[0, 0, 0]} castShadow receiveShadow>
      <boxGeometry args={[32, 16, 0.8]} />
      <meshStandardMaterial color="#4b5563" roughness={0.72} metalness={0.18} />
    </mesh>
  );
}

function SourceMarker() {
  return (
    <mesh position={[0, 0, -11]} castShadow>
      <sphereGeometry args={[1.2, 24, 24]} />
      <meshStandardMaterial color="#ffb84d" emissive="#8a4a00" emissiveIntensity={0.45} />
    </mesh>
  );
}

function DetectorPlane() {
  return (
    <mesh position={[0, 0, 11]} receiveShadow>
      <boxGeometry args={[32, 16, 0.25]} />
      <meshStandardMaterial color="#f59e0b" transparent opacity={0.38} />
    </mesh>
  );
}

function BeamPath() {
  return (
    <mesh position={[0, 0, 0]} rotation={[Math.PI / 2, 0, 0]}>
      <cylinderGeometry args={[0.07, 0.07, 22, 16]} />
      <meshStandardMaterial color="#d7ff61" emissive="#d7ff61" emissiveIntensity={0.7} />
    </mesh>
  );
}
