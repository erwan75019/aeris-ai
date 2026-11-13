import type {
  AnomalyResponse,
  FlightListResponse,
  FlightTrackResponse,
  PredictionResponse,
  SimulationAnomaly,
  SimulationResponse,
  AnalyticsSummary,
  DensityForecastResponse,
} from "./types";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "";

export interface IntelligenceReport {
  icao24: string;
  mode: "deterministic_fallback" | "llm_orchestrated";
  llm_configured: boolean;
  facts: string[];
  predictions: string[];
  hypotheses: string[];
  limitations: string[];
  tool_log: Array<{ tool: string; status: string; detail: string }>;
  agent_findings: Array<{
    agent: string;
    status: "complete" | "limited" | "failed";
    facts: string[];
    predictions: string[];
    hypotheses: string[];
    limitations: string[];
  }>;
  narrative: string | null;
  generated_at: string;
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_URL}${path}`, {
    ...init,
    headers: { "Content-Type": "application/json", ...init?.headers },
    signal: AbortSignal.timeout(8000),
  });
  if (!response.ok) {
    const body = (await response.json().catch(() => null)) as { detail?: string } | null;
    throw new Error(body?.detail ?? `AERIS API returned ${response.status}`);
  }
  return (await response.json()) as T;
}

export function getFlights(replayAt?: string): Promise<FlightListResponse> {
  const suffix = replayAt ? `/api/v1/replay/snapshot?at=${encodeURIComponent(replayAt)}` : "/api/v1/flights";
  return request<FlightListResponse>(suffix);
}

function replayQuery(replayAt?: string): string {
  return replayAt ? `?at=${encodeURIComponent(replayAt)}` : "";
}

export function getTrack(icao24: string, replayAt?: string): Promise<FlightTrackResponse> {
  return request<FlightTrackResponse>(`/api/v1/flights/${encodeURIComponent(icao24)}/track${replayQuery(replayAt)}`);
}

export function getPrediction(icao24: string, replayAt?: string): Promise<PredictionResponse> {
  return request<PredictionResponse>(`/api/v1/flights/${encodeURIComponent(icao24)}/prediction${replayQuery(replayAt)}`);
}

export function getAnomaly(icao24: string, replayAt?: string): Promise<AnomalyResponse> {
  return request<AnomalyResponse>(`/api/v1/flights/${encodeURIComponent(icao24)}/anomaly${replayQuery(replayAt)}`);
}

export function createReport(icao24: string, replayAt?: string): Promise<IntelligenceReport> {
  return request<IntelligenceReport>("/api/v1/intelligence/reports", {
    method: "POST",
    body: JSON.stringify({ icao24, include_weather: true, at: replayAt }),
  });
}

export function createSimulation(
  icao24: string,
  anomalyType: SimulationAnomaly,
  severity: number,
  windSpeedKt = 0,
  windDirectionDeg = 0,
): Promise<SimulationResponse> {
  return request<SimulationResponse>("/api/v1/simulations", {
    method: "POST",
    body: JSON.stringify({
      icao24,
      anomaly_type: anomalyType,
      severity,
      wind_speed_kt: windSpeedKt,
      wind_direction_deg: windDirectionDeg,
    }),
  });
}

export function getAnalyticsSummary(): Promise<AnalyticsSummary> {
  return request<AnalyticsSummary>("/api/v1/analytics/summary");
}

export function getDensityForecast(): Promise<DensityForecastResponse> {
  return request<DensityForecastResponse>("/api/v1/analytics/density-forecast");
}
