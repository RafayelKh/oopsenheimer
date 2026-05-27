"use client";

import { useEffect, useState } from "react";
import { ArtifactList } from "@/components/ArtifactList";
import { DoseVolumeViewer } from "@/components/DoseVolumeViewer";
import { JobStatusBadge } from "@/components/JobStatusBadge";
import { SimulationProgressBar } from "@/components/SimulationProgressBar";
import { getSimulation, getSimulationArtifacts } from "@/lib/api";
import type { ArtifactSummary, JobStatus } from "@/types/oopsenheimer";
import type { SimulationRecord } from "@/lib/api";

type SimulationStatusViewProps = {
  simulationId: string;
};

const terminalStatuses: JobStatus[] = ["completed", "failed"];

export function SimulationStatusView({ simulationId }: SimulationStatusViewProps) {
  const [simulation, setSimulation] = useState<SimulationRecord | null>(null);
  const [artifacts, setArtifacts] = useState<ArtifactSummary | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    let timer: ReturnType<typeof setInterval> | null = null;

    async function poll() {
      try {
        const next = await getSimulation(simulationId);
        if (!active) {
          return;
        }
        setSimulation(next);

        if (next.status === "completed") {
          const nextArtifacts = await getSimulationArtifacts(simulationId);
          if (active) {
            setArtifacts(nextArtifacts);
          }
        }

        if (terminalStatuses.includes(next.status) && timer) {
          clearInterval(timer);
          timer = null;
        }
      } catch (caught) {
        if (active) {
          setError(caught instanceof Error ? caught.message : "Failed to poll simulation.");
        }
        if (timer) {
          clearInterval(timer);
          timer = null;
        }
      }
    }

    poll();
    timer = setInterval(poll, 2000);

    return () => {
      active = false;
      if (timer) {
        clearInterval(timer);
      }
    };
  }, [simulationId]);

  const status = simulation?.status ?? "queued";
  const parsed = artifacts?.parsedResult;
  const showProgress = !terminalStatuses.includes(status);

  return (
    <>
      <section className="panel">
        <div className="panel-header">
          <div>
            <strong>Simulation {simulationId}</strong>
            <div className="muted">Polling every 2 seconds</div>
          </div>
          <JobStatusBadge status={status} />
        </div>
        {simulation?.errorMessage || error ? (
          <div className="panel-body error-text">{simulation?.errorMessage ?? error}</div>
        ) : null}
      </section>
      <DoseVolumeViewer parsedResult={parsed} simulationId={simulationId} />
      <section className="grid">
        <ArtifactList simulationId={simulationId} artifacts={artifacts?.artifacts} />
      </section>
      {showProgress ? (
        <SimulationProgressBar
          progressPercent={simulation?.progressPercent}
          label={simulation?.progressMessage}
          status={status}
        />
      ) : null}
    </>
  );
}
