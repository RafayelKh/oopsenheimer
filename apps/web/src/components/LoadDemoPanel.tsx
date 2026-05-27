"use client";

import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { createScene, getExampleScene, getExamples } from "@/lib/api";
import type { ExampleSummary } from "@/lib/api";

export function LoadDemoPanel() {
  const router = useRouter();
  const [examples, setExamples] = useState<ExampleSummary[]>([]);
  const [sceneJson, setSceneJson] = useState<Record<string, unknown> | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loadingExampleId, setLoadingExampleId] = useState<string | null>(null);
  const [isOpen, setIsOpen] = useState(false);

  useEffect(() => {
    let active = true;

    getExamples()
      .then((nextExamples) => {
        if (active) {
          setExamples(nextExamples);
        }
      })
      .catch((caught) => {
        if (active) {
          setError(caught instanceof Error ? caught.message : "Failed to load examples.");
        }
      });

    return () => {
      active = false;
    };
  }, []);

  async function loadDemo(exampleId: string) {
    setLoadingExampleId(exampleId);
    setError(null);

    try {
      const example = await getExampleScene(exampleId);
      setSceneJson(example);
      const scene = await createScene(example);
      router.push(`/scenes/${scene.id}`);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Failed to load demo scene.");
    } finally {
      setLoadingExampleId(null);
    }
  }

  return (
    <section className={`examples-drawer ${isOpen ? "open" : ""}`}>
      <button
        aria-expanded={isOpen}
        className={`edge-drawer-toggle right-drawer-toggle ${isOpen ? "open" : ""}`}
        onClick={() => setIsOpen((current) => !current)}
        type="button"
      >
        {isOpen ? "Close" : "Examples"}
      </button>
      <div className="drawer-header">
        <div>
          <strong>Example scenes</strong>
          <div className="muted">Load a full voxel setup</div>
        </div>
        <button className="drawer-close-button" onClick={() => setIsOpen(false)} type="button">
          Close
        </button>
      </div>
      <div className="drawer-scroll demo-panel">
        <div className="demo-grid">
          {examples.map((example) => (
            <button
              className="demo-card"
              disabled={loadingExampleId !== null}
              key={example.id}
              onClick={() => loadDemo(example.id)}
              type="button"
            >
              <strong>{example.name}</strong>
              <span>{example.description ?? example.filename}</span>
              <small>{loadingExampleId === example.id ? "Loading..." : example.filename}</small>
            </button>
          ))}
        </div>
        {error ? <div className="error-text">{error}</div> : null}
        {sceneJson ? <div className="muted scene-id">Loaded {String(sceneJson.world && typeof sceneJson.world === "object" ? (sceneJson.world as Record<string, unknown>).id ?? "scene" : "scene")}</div> : null}
      </div>
    </section>
  );
}
