import type { JobStatus } from "@/types/oopsenheimer";
import { jobStatusLabels, localizeProgressLabel } from "@/lib/armenian";

const statusProgress: Record<JobStatus, number> = {
  queued: 0,
  compiling: 12,
  compiled: 28,
  running: 35,
  parsing: 88,
  completed: 100,
  failed: 0,
};

type SimulationProgressBarProps = {
  label?: string | null;
  progressPercent?: number | null;
  status?: JobStatus;
};

export function SimulationProgressBar({
  label,
  progressPercent,
  status = "queued",
}: SimulationProgressBarProps) {
  const percent = clampPercent(progressPercent ?? statusProgress[status]);
  const showEdge = percent > 0 && percent < 100 && status !== "failed";
  const resolvedLabel = localizeProgressLabel(label, status) || jobStatusLabels[status];

  return (
    <div
      aria-label={resolvedLabel}
      aria-valuemax={100}
      aria-valuemin={0}
      aria-valuenow={percent}
      className={`simulation-progress-bar status-${status}`}
      role="progressbar"
    >
      <div className="simulation-progress-meta">
        <span>{resolvedLabel}</span>
        <strong>{percent}%</strong>
      </div>
      <div className="simulation-progress-track">
        <div className="simulation-progress-fill" style={{ width: `${percent}%` }}>
          {showEdge ? <span className="simulation-progress-edge" /> : null}
        </div>
      </div>
    </div>
  );
}

function clampPercent(value: number): number {
  if (!Number.isFinite(value)) {
    return 0;
  }
  return Math.min(100, Math.max(0, Math.round(value)));
}
