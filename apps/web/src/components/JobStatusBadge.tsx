import type { JobStatus } from "@/types/oopsenheimer";

type JobStatusBadgeProps = {
  status: JobStatus;
};

export function JobStatusBadge({ status }: JobStatusBadgeProps) {
  return <span className={`status-badge status-${status}`}>{status}</span>;
}
