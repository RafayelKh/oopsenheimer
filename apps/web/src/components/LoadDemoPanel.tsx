"use client";

import { useRouter } from "next/navigation";
import { useEffect, useMemo, useState } from "react";
import { createScene, getExampleScene, getExamples } from "@/lib/api";
import type { ExampleSummary } from "@/lib/api";

const hiddenExampleIds = new Set(["air_baseline"]);

export function LoadDemoPanel() {
  const router = useRouter();
  const [examples, setExamples] = useState<ExampleSummary[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loadingExampleId, setLoadingExampleId] = useState<string | null>(null);
  const [loadedSceneName, setLoadedSceneName] = useState<string | null>(null);
  const [isOpen, setIsOpen] = useState(true);

  const visibleExamples = useMemo(() => examples.filter((example) => !hiddenExampleIds.has(example.id)), [examples]);

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

  useEffect(() => {
    function closeOnEscape(event: KeyboardEvent) {
      if (event.key === "Escape") {
        setIsOpen(false);
      }
    }

    if (!isOpen) {
      return;
    }

    window.addEventListener("keydown", closeOnEscape);
    return () => window.removeEventListener("keydown", closeOnEscape);
  }, [isOpen]);

  function openBlankScene() {
    setLoadedSceneName("Blank scene");
    setError(null);
    setIsOpen(false);
  }

  async function loadDemo(exampleId: string) {
    const selectedExample = examples.find((example) => example.id === exampleId);
    setLoadingExampleId(exampleId);
    setError(null);

    try {
      const example = await getExampleScene(exampleId);
      setLoadedSceneName(selectedExample?.name ?? exampleId);
      const scene = await createScene(example);
      router.push(`/scenes/${scene.id}`);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Failed to load demo scene.");
    } finally {
      setLoadingExampleId(null);
    }
  }

  return (
    <>
      <button className="examples-modal-launch" onClick={() => setIsOpen(true)} type="button">
        Examples
      </button>
      {isOpen ? (
        <div className="examples-modal-backdrop" onMouseDown={() => setIsOpen(false)}>
          <section
            aria-labelledby="examples-modal-title"
            aria-modal="true"
            className="examples-modal"
            onMouseDown={(event) => event.stopPropagation()}
            role="dialog"
          >
            <div className="examples-modal-header">
              <div>
                <strong id="examples-modal-title">Start a scene</strong>
                <div className="muted">Choose a blank workspace or load a prepared setup.</div>
              </div>
              <button className="drawer-close-button" onClick={() => setIsOpen(false)} type="button">
                Close
              </button>
            </div>
            <div className="example-choice-grid">
              <button
                className="example-choice"
                disabled={loadingExampleId !== null}
                onClick={openBlankScene}
                type="button"
              >
                <span className="example-icon-box">
                  <ExampleIcon name="blank" />
                </span>
                <strong>Blank</strong>
                <span>Start with empty air and build your own shield.</span>
              </button>
              {visibleExamples.map((example) => (
                <button
                  className="example-choice"
                  disabled={loadingExampleId !== null}
                  key={example.id}
                  onClick={() => loadDemo(example.id)}
                  type="button"
                >
                  <span className="example-icon-box">
                    <ExampleIcon name={iconForExample(example.id)} />
                  </span>
                  <strong>{example.name}</strong>
                  <span>{loadingExampleId === example.id ? "Loading..." : example.description ?? example.filename}</span>
                </button>
              ))}
            </div>
            {error ? <div className="error-text examples-modal-error">{error}</div> : null}
            {loadedSceneName ? <div className="muted scene-id">Selected {loadedSceneName}</div> : null}
          </section>
        </div>
      ) : null}
    </>
  );
}

type ExampleIconName = "blank" | "bus" | "car" | "house" | "shield" | "aperture" | "water" | "legacy";

function iconForExample(exampleId: string): ExampleIconName {
  if (exampleId.includes("bus")) {
    return "bus";
  }
  if (exampleId.includes("car")) {
    return "car";
  }
  if (exampleId.includes("house")) {
    return "house";
  }
  if (exampleId.includes("aperture")) {
    return "aperture";
  }
  if (exampleId.includes("water")) {
    return "water";
  }
  if (exampleId.includes("slab")) {
    return "shield";
  }
  return "legacy";
}

function ExampleIcon({ name }: { name: ExampleIconName }) {
  if (name === "blank") {
    return (
      <svg aria-hidden="true" viewBox="0 0 64 64">
        <path d="M16 16h32v32H16z" fill="none" stroke="currentColor" strokeWidth="4" />
        <path d="M32 21v22M21 32h22" fill="none" stroke="currentColor" strokeLinecap="round" strokeWidth="4" />
      </svg>
    );
  }

  if (name === "car") {
    return (
      <svg aria-hidden="true" viewBox="0 0 64 64">
        <path d="M12 36h40l-4-12H23L16 36z" fill="none" stroke="currentColor" strokeLinejoin="round" strokeWidth="4" />
        <path d="M16 36h36v10H12v-6a4 4 0 0 1 4-4z" fill="none" stroke="currentColor" strokeLinejoin="round" strokeWidth="4" />
        <path d="M24 46a5 5 0 1 1-10 0M50 46a5 5 0 1 1-10 0" fill="none" stroke="currentColor" strokeLinecap="round" strokeWidth="4" />
        <path d="M28 24v12" fill="none" stroke="currentColor" strokeWidth="4" />
      </svg>
    );
  }

  if (name === "bus") {
    return (
      <svg aria-hidden="true" viewBox="0 0 64 64">
        <path d="M12 18h40a4 4 0 0 1 4 4v22H8V22a4 4 0 0 1 4-4z" fill="none" stroke="currentColor" strokeLinejoin="round" strokeWidth="4" />
        <path d="M16 26h10M31 26h10M46 26h6M16 34h10M31 34h10M46 34h6" fill="none" stroke="currentColor" strokeLinecap="round" strokeWidth="4" />
        <path d="M20 48a4 4 0 1 1-8 0M52 48a4 4 0 1 1-8 0" fill="none" stroke="currentColor" strokeLinecap="round" strokeWidth="4" />
      </svg>
    );
  }

  if (name === "house") {
    return (
      <svg aria-hidden="true" viewBox="0 0 64 64">
        <path d="M10 31 32 13l22 18" fill="none" stroke="currentColor" strokeLinecap="round" strokeLinejoin="round" strokeWidth="4" />
        <path d="M17 29v23h30V29" fill="none" stroke="currentColor" strokeLinejoin="round" strokeWidth="4" />
        <path d="M27 52V38h10v14M23 33h8M38 33h5" fill="none" stroke="currentColor" strokeLinecap="round" strokeWidth="4" />
      </svg>
    );
  }

  if (name === "aperture") {
    return (
      <svg aria-hidden="true" viewBox="0 0 64 64">
        <path d="M14 14h36v36H14z" fill="none" stroke="currentColor" strokeLinejoin="round" strokeWidth="4" />
        <circle cx="32" cy="32" fill="none" r="10" stroke="currentColor" strokeWidth="4" />
        <path d="M6 32h14M44 32h14" fill="none" stroke="currentColor" strokeLinecap="round" strokeWidth="4" />
      </svg>
    );
  }

  if (name === "water") {
    return (
      <svg aria-hidden="true" viewBox="0 0 64 64">
        <path d="M32 10s16 18 16 31a16 16 0 0 1-32 0c0-13 16-31 16-31z" fill="none" stroke="currentColor" strokeLinejoin="round" strokeWidth="4" />
        <path d="M24 42a8 8 0 0 0 8 8" fill="none" stroke="currentColor" strokeLinecap="round" strokeWidth="4" />
      </svg>
    );
  }

  if (name === "shield") {
    return (
      <svg aria-hidden="true" viewBox="0 0 64 64">
        <path d="M32 8 50 16v14c0 13-8 22-18 27-10-5-18-14-18-27V16l18-8z" fill="none" stroke="currentColor" strokeLinejoin="round" strokeWidth="4" />
        <path d="M32 14v35M18 29h28" fill="none" stroke="currentColor" strokeLinecap="round" strokeWidth="4" />
      </svg>
    );
  }

  return (
    <svg aria-hidden="true" viewBox="0 0 64 64">
      <path d="M16 16h32v32H16z" fill="none" stroke="currentColor" strokeWidth="4" />
      <path d="M24 24h16v16H24z" fill="none" stroke="currentColor" strokeWidth="4" />
      <path d="M10 32h12M42 32h12" fill="none" stroke="currentColor" strokeLinecap="round" strokeWidth="4" />
    </svg>
  );
}
