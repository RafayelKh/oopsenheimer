import type { JobStatus } from "@/types/oopsenheimer";

export const jobStatusLabels: Record<JobStatus, string> = {
  queued: "Հերթում է",
  compiling: "Տեսարանը կոմպիլացվում է",
  compiled: "Տեսարանը կոմպիլացվել է",
  running: "FLUKA-ն աշխատում է",
  parsing: "Դոզան մշակվում է",
  completed: "Ավարտված է",
  failed: "Ձախողվել է",
};

const progressLabelTranslations: Record<string, string> = {
  Queued: jobStatusLabels.queued,
  "Compiling scene": jobStatusLabels.compiling,
  "Scene compiled": jobStatusLabels.compiled,
  "Running FLUKA": jobStatusLabels.running,
  "Parsing dose": jobStatusLabels.parsing,
  Completed: jobStatusLabels.completed,
  Failed: jobStatusLabels.failed,
  "Preparing simulation": "Սիմուլյացիան պատրաստվում է",
  "Saving scene": "Տեսարանը պահվում է",
  "Submitting job": "Առաջադրանքն ուղարկվում է",
};

export function localizeProgressLabel(label: string | null | undefined, status: JobStatus): string {
  if (!label) {
    return jobStatusLabels[status];
  }

  const flukaMatch = /^Running FLUKA \((\d+)% particles\)$/.exec(label);
  if (flukaMatch) {
    return `FLUKA-ն աշխատում է (${flukaMatch[1]}% մասնիկներ)`;
  }

  return progressLabelTranslations[label] ?? label;
}
