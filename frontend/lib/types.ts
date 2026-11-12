export type DataClassification =
  | "synthetic_demo"
  | "historical"
  | "live"
  | "synthetic_simulation";

export interface FlightState {
  icao24: string;
  callsign: string | null;
  latitude: number;
  longitude: number;
  altitude_ft: number | null;
  ground_speed_kt: number | null;
  heading_deg: number | null;
  vertical_rate_fpm: number | null;
  timestamp: string;
  source: string;
  on_ground: boolean;
}

export interface FlightListResponse {
  data: FlightState[];
  meta: {
    mode: "demo" | "historical" | "live";
    data_classification: DataClassification;
    source: string;
    count: number;
    generated_at: string;
    replay_at: string | null;
  };
}

export interface FlightTrackResponse {
  icao24: string;
  callsign: string | null;
  points: FlightState[];
  source: string;
  data_classification: DataClassification;
}

export interface PredictionResponse {
  icao24: string;
  generated_from: string;
  model: { name: string; version: string; trained: boolean };
  points: Array<{
    horizon_minutes: number;
    latitude: number;
    longitude: number;
    altitude_ft: number | null;
    timestamp: string;
    uncertainty_km: number | null;
  }>;
  disclaimer: string;
}

export interface AnomalyResponse {
  icao24: string;
  score: number;
  label: "nominal" | "unusual";
  classification: DataClassification;
  factors: Record<string, number>;
  model: { name: string; version: string; trained: boolean };
  disclaimer: string;
}
