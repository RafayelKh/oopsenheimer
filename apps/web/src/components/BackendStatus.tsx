"use client";

import { useEffect, useState } from "react";
import { getHealth } from "@/lib/api";
import type { HealthResponse } from "@/lib/api";

type HealthState = "checking" | "ok" | "offline";

export function BackendStatus() {
  const [state, setState] = useState<HealthState>("checking");
  const [health, setHealth] = useState<HealthResponse | null>(null);

  useEffect(() => {
    let active = true;

    getHealth()
      .then((nextHealth) => {
        if (active) {
          setHealth(nextHealth);
          setState("ok");
        }
      })
      .catch(() => {
        if (active) {
          setState("offline");
        }
      });

    return () => {
      active = false;
    };
  }, []);

  const mode = health?.simMode;
  const modeClass = mode === "fluka" ? "backend-fluka" : mode === "mock" ? "backend-mock" : "";
  const modeLabel = mode === "fluka" ? "FLUKA" : mode === "mock" ? "փորձնական" : mode;
  const stateLabel =
    state === "checking" ? "ստուգվում է" : state === "offline" ? "անջատված է" : "աշխատում է";
  const label = state === "ok" && modeLabel ? `API ${modeLabel}` : `API ${stateLabel}`;

  return <span className={`backend-status backend-${state} ${modeClass}`}>{label}</span>;
}
