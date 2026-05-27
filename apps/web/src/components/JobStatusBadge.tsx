import type { JobStatus } from "@/types/oopsenheimer";
import { jobStatusLabels } from "@/lib/armenian";

type JobStatusBadgeProps = {
  status: JobStatus;
};

export function JobStatusBadge({ status }: JobStatusBadgeProps) {
  return <span className={`status-badge status-${status}`}>{jobStatusLabels[status]}</span>;
}
