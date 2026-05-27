"use client";

import { useEffect, useState } from "react";
import { VoxelEditor } from "@/components/VoxelEditor";
import { getScene } from "@/lib/api";
import type { SceneRecord } from "@/lib/api";

type SceneWorkspaceProps = {
  sceneId: string;
};

export function SceneWorkspace({ sceneId }: SceneWorkspaceProps) {
  const [scene, setScene] = useState<SceneRecord | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    setScene(null);
    setError(null);

    getScene(sceneId)
      .then((nextScene) => {
        if (active) {
          setScene(nextScene);
        }
      })
      .catch((caught) => {
        if (active) {
          setError(caught instanceof Error ? caught.message : "Չհաջողվեց բեռնել տեսարանը։");
        }
      });

    return () => {
      active = false;
    };
  }, [sceneId]);

  if (error) {
    return <section className="panel panel-body error-text">{error}</section>;
  }

  if (!scene) {
    return (
      <section className="panel">
        <div className="panel-header">
          <strong>Տեսարանը բեռնվում է</strong>
          <span className="muted">{sceneId}</span>
        </div>
      </section>
    );
  }

  return <VoxelEditor initialSceneId={scene.id} initialSceneJson={scene.sceneJson} />;
}
