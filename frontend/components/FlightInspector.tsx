"use client";

import type { IntelligenceReport } from "@/lib/api";
import { formatAltitude, formatHeading, formatRate, formatSpeed, formatUtc } from "@/lib/format";
import type { AnomalyResponse, FlightState, PredictionResponse } from "@/lib/types";

interface FlightInspectorProps {
  flight: FlightState | null;
  anomaly: AnomalyResponse | null;
  prediction: PredictionResponse | null;
  report: IntelligenceReport | null;
  reportBusy: boolean;
  error: string | null;
  onCreateReport: () => void;
}

function DataPoint({ label, value }: { label: string; value: string }) {
  return (
    <div className="data-point">
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}

export function FlightInspector({
  flight,
  anomaly,
  prediction,
  report,
  reportBusy,
  error,
  onCreateReport,
}: FlightInspectorProps) {
  if (!flight) {
    return (
      <aside className="inspector empty-inspector">
        <span className="eyebrow">Flight inspector</span>
        <div className="empty-radar-icon" aria-hidden="true" />
        <h2>Select an aircraft</h2>
        <p>Choose a radar target to inspect its observed track, baseline projection and anomaly factors.</p>
      </aside>
    );
  }

  return (
    <aside className="inspector">
      <div className="inspector-heading">
        <div>
          <span className="eyebrow">Tracked aircraft</span>
          <h2>{flight.callsign ?? "Unknown callsign"}</h2>
          <code>{flight.icao24.toUpperCase()}</code>
        </div>
        <span className="source-pill">DEMO</span>
      </div>

      <div className="data-grid">
        <DataPoint label="Altitude" value={formatAltitude(flight.altitude_ft)} />
        <DataPoint label="Ground speed" value={formatSpeed(flight.ground_speed_kt)} />
        <DataPoint label="Track" value={formatHeading(flight.heading_deg)} />
        <DataPoint label="Vertical rate" value={formatRate(flight.vertical_rate_fpm)} />
      </div>

      <section className="inspector-section">
        <div className="section-title">
          <span>Statistical anomaly</span>
          <strong className={anomaly?.label === "unusual" ? "status-unusual" : "status-nominal"}>
            {anomaly ? `${Math.round(anomaly.score * 100)}%` : "…"}
          </strong>
        </div>
        <div className="score-track"><i style={{ width: `${(anomaly?.score ?? 0) * 100}%` }} /></div>
        <p className="muted-copy">A score indicates unusual geometry only; it is not evidence of an incident.</p>
      </section>

      <section className="inspector-section">
        <div className="section-title">
          <span>Trajectory projection</span>
          <strong>+15 min</strong>
        </div>
        {prediction ? (
          <>
            <div className="prediction-coordinate">
              {prediction.points.at(-1)?.latitude.toFixed(3)}° / {prediction.points.at(-1)?.longitude.toFixed(3)}°
            </div>
            <p className="muted-copy">
              {prediction.model.name.replaceAll("_", " ")} · uncertainty {prediction.points.at(-1)?.uncertainty_km} km
            </p>
          </>
        ) : <p className="muted-copy">Calculating baseline…</p>}
      </section>

      <section className="inspector-section intelligence-summary">
        <div className="section-title"><span>AERIS Intelligence</span><em>Offline-ready</em></div>
        {report ? (
          <ul>{report.facts.slice(0, 3).map((fact) => <li key={fact}>{fact}</li>)}</ul>
        ) : (
          <p className="muted-copy">Run the tool-based analyst. No LLM is required and every call is logged.</p>
        )}
        <button className="primary-action" type="button" onClick={onCreateReport} disabled={reportBusy}>
          {reportBusy ? "Running tools…" : report ? "Refresh analysis" : "Analyze flight"}
        </button>
        {error && <p className="analysis-error" role="alert">{error}</p>}
      </section>

      <footer className="inspector-footer">Last state · {formatUtc(flight.timestamp)}</footer>
    </aside>
  );
}
