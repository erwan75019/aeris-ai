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

export interface PredictionPoint {
  horizon_minutes: number;
  latitude: number;
  longitude: number;
  altitude_ft: number | null;
  timestamp: string;
  uncertainty_km: number | null;
}

export interface PredictionResponse {
  icao24: string;
  generated_from: string;
  model: { name: string; version: string; trained: boolean };
  points: PredictionPoint[];
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

export type SimulationAnomaly = "altitude_spike" | "heading_deviation" | "speed_drop";

export interface SimulationResponse {
  scenario_id: string;
  classification: "synthetic_simulation";
  anomaly_type: SimulationAnomaly;
  weather: {
    wind_speed_kt: number;
    wind_direction_deg: number;
    source: "user_defined_synthetic";
  };
  baseline: FlightState[];
  simulated: FlightState[];
  model_reaction: {
    baseline_anomaly_score: number;
    simulated_anomaly_score: number;
    baseline_label: "nominal" | "unusual";
    simulated_label: "nominal" | "unusual";
    anomaly_model: { name: string; version: string; trained: boolean };
    trajectory_model: { name: string; version: string; trained: boolean };
    baseline_prediction: PredictionPoint[];
    simulated_prediction: PredictionPoint[];
  };
  disclaimer: string;
}

export interface AnalyticsSummary {
  aircraft_count: number;
  mean_altitude_ft: number | null;
  unusual_count: number;
  classification: DataClassification;
}

export interface DensityForecastResponse {
  generated_at: string;
  current_aircraft: number;
  points: Array<{
    horizon_minutes: number;
    timestamp: string;
    predicted_aircraft: number;
    persistence_baseline_aircraft: number;
    test_mae_aircraft: number | null;
  }>;
  model: {
    name: string;
    version: string;
    trained: boolean;
    metrics: Record<string, number> | null;
  };
  classification: DataClassification;
  disclaimer: string;
}
