import type { ArtifactSummary, JobStatus, MaterialSummary } from "@/types/radcraft";

export const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://127.0.0.1:8000";

export type HealthResponse = {
  status: "ok";
  simMode: string;
  flukaConfigured: boolean;
};

export type ExampleSummary = {
  id: string;
  name: string;
  filename: string;
  description?: string;
};

export type SceneRecord = {
  id: string;
  name: string;
  sceneJson: Record<string, unknown>;
  createdAt: string;
};

export type SimulationRecord = {
  id: string;
  sceneId: string;
  status: JobStatus;
  progressPercent?: number;
  progressMessage?: string | null;
  createdAt: string;
  storagePath?: string | null;
  errorMessage?: string | null;
};

class ApiError extends Error {
  constructor(
    message: string,
    readonly status: number,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...init?.headers,
    },
  });

  if (!response.ok) {
    let message = `API request failed with status ${response.status}`;
    try {
      const body = await response.json();
      message = typeof body.detail === "string" ? body.detail : message;
    } catch {
      // Keep the status-based message when the response is not JSON.
    }
    throw new ApiError(message, response.status);
  }

  return response.json() as Promise<T>;
}

export function getHealth(): Promise<HealthResponse> {
  return request<HealthResponse>("/health");
}

export function getExamples(): Promise<ExampleSummary[]> {
  return request<ExampleSummary[]>("/examples");
}

export function getExampleScene(exampleId: string): Promise<Record<string, unknown>> {
  return request<Record<string, unknown>>(`/examples/${exampleId}`);
}

export function getMaterials(): Promise<MaterialSummary[]> {
  return request<MaterialSummary[]>("/materials");
}

export function createScene(sceneJson: Record<string, unknown>): Promise<SceneRecord> {
  return request<SceneRecord>("/scenes", {
    method: "POST",
    body: JSON.stringify(sceneJson),
  });
}

export function getScene(sceneId: string): Promise<SceneRecord> {
  return request<SceneRecord>(`/scenes/${sceneId}`);
}

export function createSimulation(sceneId: string): Promise<SimulationRecord> {
  return request<SimulationRecord>("/simulations", {
    method: "POST",
    body: JSON.stringify({ sceneId }),
  });
}

export function getSimulation(simulationId: string): Promise<SimulationRecord> {
  return request<SimulationRecord>(`/simulations/${simulationId}`);
}

export function getSimulationArtifacts(simulationId: string): Promise<ArtifactSummary> {
  return request<ArtifactSummary>(`/simulations/${simulationId}/artifacts`);
}

export function artifactDownloadUrl(simulationId: string, artifactPath: string): string {
  return `${API_BASE_URL}/simulations/${simulationId}/artifacts/${artifactPath
    .split("/")
    .map(encodeURIComponent)
    .join("/")}`;
}
