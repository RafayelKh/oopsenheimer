"use client";

import { create } from "zustand";
import type { JobStatus } from "@/types/radcraft";

type OopsEnheimerState = {
  activeSceneId: string | null;
  activeSimulationId: string | null;
  latestStatus: JobStatus | null;
  setActiveSceneId: (sceneId: string | null) => void;
  setActiveSimulationId: (simulationId: string | null) => void;
  setLatestStatus: (status: JobStatus | null) => void;
};

export const useOopsEnheimerStore = create<OopsEnheimerState>((set) => ({
  activeSceneId: null,
  activeSimulationId: null,
  latestStatus: null,
  setActiveSceneId: (activeSceneId) => set({ activeSceneId }),
  setActiveSimulationId: (activeSimulationId) => set({ activeSimulationId }),
  setLatestStatus: (latestStatus) => set({ latestStatus }),
}));
