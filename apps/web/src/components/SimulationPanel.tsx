"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import { createSimulation } from "@/lib/api";
import { SimulationProgressBar } from "@/components/SimulationProgressBar";

type SimulationPanelProps = {
  sceneId?: string;
};

export function SimulationPanel({ sceneId }: SimulationPanelProps) {
  const router = useRouter();
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [progress, setProgress] = useState(0);
  const [progressLabel, setProgressLabel] = useState("Submitting job");
  const [error, setError] = useState<string | null>(null);

  async function runSimulation() {
    if (!sceneId) {
      return;
    }

    setIsSubmitting(true);
    setProgress(10);
    setProgressLabel("Submitting job");
    setError(null);

    try {
      const simulation = await createSimulation(sceneId);
      setProgress(simulation.progressPercent ?? 0);
      setProgressLabel(simulation.progressMessage ?? "Queued");
      router.push(`/simulations/${simulation.id}`);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Failed to create simulation.");
      setIsSubmitting(false);
      setProgress(0);
    }
  }

  return (
    <section className="panel">
      <div className="panel-header">
        <strong>Simulation</strong>
      </div>
      <div className="panel-body simulation-panel">
        <div>
          <span className="muted">Scene</span>
          <strong>{sceneId ?? "No scene loaded"}</strong>
        </div>
        <button
          className="primary-button"
          type="button"
          onClick={runSimulation}
          disabled={!sceneId || isSubmitting}
        >
          {isSubmitting ? "Submitting..." : "Run Simulation"}
        </button>
        {error ? <div className="error-text">{error}</div> : null}
      </div>
      {isSubmitting ? (
        <SimulationProgressBar progressPercent={progress} label={progressLabel} status="queued" />
      ) : null}
    </section>
  );
}
