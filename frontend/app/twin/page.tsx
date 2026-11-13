"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";

import { AppRail } from "@/components/AppRail";
import { RadarMap } from "@/components/RadarMap";
import { createSimulation, getFlights } from "@/lib/api";
import type {
  FlightListResponse,
  FlightTrackResponse,
  PredictionResponse,
  SimulationAnomaly,
  SimulationResponse,
} from "@/lib/types";

const labels: Record<SimulationAnomaly, string> = {
  heading_deviation: "Heading deviation",
  altitude_spike: "Altitude spike",
  speed_drop: "Speed reduction",
};

export default function DigitalTwinPage() {
  const [flights, setFlights] = useState<FlightListResponse | null>(null);
  const [selected, setSelected] = useState("ae0001");
  const [anomaly, setAnomaly] = useState<SimulationAnomaly>("heading_deviation");
  const [severity, setSeverity] = useState(0.6);
  const [windSpeed, setWindSpeed] = useState(20);
  const [windDirection, setWindDirection] = useState(270);
  const [simulation, setSimulation] = useState<SimulationResponse | null>(null);
  const [busy, setBusy] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const requestSequence = useRef(0);

  useEffect(() => {
    const sequence = ++requestSequence.current;
    Promise.all([
      getFlights(),
      createSimulation("ae0001", "heading_deviation", 0.6, 20, 270),
    ])
      .then(([response, initialSimulation]) => {
        if (sequence === requestSequence.current) {
          setFlights(response);
          setSimulation(initialSimulation);
          setBusy(false);
        }
      })
      .catch((reason: unknown) => {
        if (sequence === requestSequence.current) {
          setError(reason instanceof Error ? reason.message : "Unable to load the scenario lab");
          setBusy(false);
        }
      });
  }, []);

  const run = useCallback(async () => {
    const sequence = ++requestSequence.current;
    setBusy(true);
    try {
      const nextSimulation = await createSimulation(
        selected,
        anomaly,
        severity,
        windSpeed,
        windDirection,
      );
      if (sequence === requestSequence.current) {
        setSimulation(nextSimulation);
        setError(null);
      }
    } catch (reason) {
      if (sequence === requestSequence.current) {
        setError(reason instanceof Error ? reason.message : "Simulation failed");
      }
    } finally {
      if (sequence === requestSequence.current) {
        setBusy(false);
      }
    }
  }, [anomaly, selected, severity, windDirection, windSpeed]);

  const baselineTrack = useMemo<FlightTrackResponse | null>(() => simulation ? ({
    icao24: selected,
    callsign: flights?.data.find((flight) => flight.icao24 === selected)?.callsign ?? null,
    points: simulation.baseline,
    source: "aeris_demo",
    data_classification: "synthetic_demo",
  }) : null, [flights, selected, simulation]);

  const baselinePrediction = useMemo<PredictionResponse | null>(() => simulation ? ({
    icao24: selected,
    generated_from: simulation.baseline.at(-1)?.timestamp ?? "",
    model: simulation.model_reaction.trajectory_model,
    points: simulation.model_reaction.baseline_prediction,
    disclaimer: simulation.disclaimer,
  }) : null, [selected, simulation]);

  return (
    <main className="app-shell">
      <AppRail active="twin" />
      <section className="module-workspace">
        <header className="topbar">
          <div className="title-lockup"><span className="eyebrow">Experimental scenario lab</span><h1>Digital Twin</h1></div>
          <div className="topbar-status"><span className="demo-badge">Synthetic only</span><span>Isolated from observed data</span></div>
        </header>
        {error && <div className="error-banner" role="alert">{error}</div>}
        <div className="twin-layout">
          <section className="twin-map map-stage">
            <RadarMap
              flights={flights?.data ?? []}
              selectedIcao24={selected}
              track={baselineTrack}
              prediction={baselinePrediction}
              scenario={simulation?.simulated}
              scenarioPrediction={simulation?.model_reaction.simulated_prediction}
              onSelect={(icao24) => { setSelected(icao24); setSimulation(null); }}
            />
            <div className="map-legend twin-legend"><span><i className="observed-line" />Baseline</span><span><i className="predicted-line" />Baseline forecast</span><span><i className="scenario-line" />Simulated</span><span><i className="scenario-prediction-line" />Scenario forecast</span></div>
            <div className="non-operational">Synthetic scenario · not a certified simulator</div>
          </section>
          <aside className="module-panel">
            <span className="eyebrow">Scenario controls</span>
            <h2>Inject a bounded anomaly</h2>
            <label>Aircraft<select value={selected} onChange={(event) => { setSelected(event.target.value); setSimulation(null); }}>{flights?.data.map((flight) => <option key={flight.icao24} value={flight.icao24}>{flight.callsign}</option>)}</select></label>
            <label>Anomaly type<select value={anomaly} onChange={(event) => { setAnomaly(event.target.value as SimulationAnomaly); setSimulation(null); }}>{Object.entries(labels).map(([value, label]) => <option key={value} value={value}>{label}</option>)}</select></label>
            <label>Severity <strong>{Math.round(severity * 100)}%</strong><input aria-label="Scenario severity" type="range" min="0.1" max="1" step="0.1" value={severity} onChange={(event) => { setSeverity(Number(event.target.value)); setSimulation(null); }} /></label>
            <label>Synthetic wind <strong>{windSpeed} kt</strong><input aria-label="Synthetic wind speed" type="range" min="0" max="100" step="5" value={windSpeed} onChange={(event) => { setWindSpeed(Number(event.target.value)); setSimulation(null); }} /></label>
            <label>Wind from <strong>{windDirection}°</strong><input aria-label="Synthetic wind direction" type="range" min="0" max="355" step="5" value={windDirection} onChange={(event) => { setWindDirection(Number(event.target.value)); setSimulation(null); }} /></label>
            <button className="primary-action" type="button" onClick={() => void run()} disabled={busy}>{busy ? "Simulating…" : "Run scenario"}</button>
            {simulation && <div className="scenario-result">
              <span>Scenario ID</span><code>{simulation.scenario_id}</code><strong>{simulation.classification.replaceAll("_", " ")}</strong>
              <div className="reaction-grid">
                <article><span>ML score before</span><b>{Math.round(simulation.model_reaction.baseline_anomaly_score * 100)}%</b><small>{simulation.model_reaction.baseline_label}</small></article>
                <article><span>ML score after</span><b>{Math.round(simulation.model_reaction.simulated_anomaly_score * 100)}%</b><small>{simulation.model_reaction.simulated_label}</small></article>
              </div>
              <p>{simulation.model_reaction.anomaly_model.name.replaceAll("_", " ")} · {simulation.model_reaction.trajectory_model.name} trajectory forecast · synthetic wind {simulation.weather.wind_speed_kt} kt from {simulation.weather.wind_direction_deg}°.</p>
              <p>{simulation.disclaimer}</p>
            </div>}
          </aside>
        </div>
      </section>
    </main>
  );
}
