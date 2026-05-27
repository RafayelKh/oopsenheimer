import type { JobStatus } from "@/types/radcraft";

type JobStatusBadgeProps = {
  status: JobStatus;
};

export function JobStatusBadge({ status }: JobStatusBadgeProps) {
  return <span className={`status-badge status-${status}`}>{status}</span>;
}
