export type JobStatus =
  | "queued"
  | "compiling"
  | "compiled"
  | "running"
  | "parsing"
  | "completed"
  | "failed";

export type MaterialSummary = {
  id: string;
  label?: string;
  color?: string;
  flukaName?: string;
  density?: number;
};

export type ArtifactSummary = {
  simulationId: string;
  artifacts: string[];
    parsedResult?: {
    quantity: string;
    unit?: string;
    dims: [number, number, number];
    originCm?: [number, number, number];
    voxelSizeCm?: [number, number, number];
    min: number;
    max: number;
    valuesEncoding?: string;
    valuesFile?: string;
    source?: string;
    simMode?: string;
    sources?: Array<{
      id: string;
      type: string;
      particle: string;
      energyGeV: number;
      positionCm: [number, number, number];
      direction: [number, number, number];
    }>;
  } | null;
};
