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
  const [progressLabel, setProgressLabel] = useState("Առաջադրանքն ուղարկվում է");
  const [error, setError] = useState<string | null>(null);

  async function runSimulation() {
    if (!sceneId) {
      return;
    }

    setIsSubmitting(true);
    setProgress(10);
    setProgressLabel("Առաջադրանքն ուղարկվում է");
    setError(null);

    try {
      const simulation = await createSimulation(sceneId);
      setProgress(simulation.progressPercent ?? 0);
      setProgressLabel(simulation.progressMessage ?? "Հերթում է");
      router.push(`/simulations/${simulation.id}`);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Չհաջողվեց ստեղծել սիմուլյացիան։");
      setIsSubmitting(false);
      setProgress(0);
    }
  }

  return (
    <section className="panel">
      <div className="panel-header">
        <strong>Սիմուլյացիա</strong>
      </div>
      <div className="panel-body simulation-panel">
        <div>
          <span className="muted">Տեսարան</span>
          <strong>{sceneId ?? "Տեսարան բեռնված չէ"}</strong>
        </div>
        <button
          className="primary-button"
          type="button"
          onClick={runSimulation}
          disabled={!sceneId || isSubmitting}
        >
          {isSubmitting ? "Ուղարկվում է..." : "Գործարկել սիմուլյացիան"}
        </button>
        {error ? <div className="error-text">{error}</div> : null}
      </div>
      {isSubmitting ? (
        <SimulationProgressBar progressPercent={progress} label={progressLabel} status="queued" />
      ) : null}
    </section>
  );
}
