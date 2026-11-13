"use client";

import { useEffect, useState } from "react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import { AppRail } from "@/components/AppRail";
import { getAnalyticsSummary, getDensityForecast, getFlights } from "@/lib/api";
import type { AnalyticsSummary, DensityForecastResponse, FlightState } from "@/lib/types";

export default function AnalyticsPage() {
  const [summary, setSummary] = useState<AnalyticsSummary | null>(null);
  const [density, setDensity] = useState<DensityForecastResponse | null>(null);
  const [flights, setFlights] = useState<FlightState[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    Promise.all([getAnalyticsSummary(), getDensityForecast(), getFlights()])
      .then(([nextSummary, nextDensity, response]) => {
        setSummary(nextSummary);
        setDensity(nextDensity);
        setFlights(response.data);
      })
      .catch((reason: unknown) => setError(reason instanceof Error ? reason.message : "Analytics unavailable"));
  }, []);

  const chart = flights.map((flight) => ({
    callsign: flight.callsign ?? flight.icao24,
    altitude: Math.round((flight.altitude_ft ?? 0) / 100) / 10,
    speed: flight.ground_speed_kt ?? 0,
  }));
  const densityChart = density ? [
    {
      horizon: "Now",
      forecast: density.current_aircraft,
      persistence: density.current_aircraft,
    },
    ...density.points.map((point) => ({
      horizon: `+${point.horizon_minutes}m`,
      forecast: point.predicted_aircraft,
      persistence: point.persistence_baseline_aircraft,
    })),
  ] : [];

  return (
    <main className="app-shell">
      <AppRail active="analytics" />
      <section className="module-workspace">
        <header className="topbar"><div className="title-lockup"><span className="eyebrow">Measured demo telemetry</span><h1>Airspace Analytics</h1></div><div className="topbar-status"><span className="demo-badge">{summary?.classification ?? "loading"}</span></div></header>
        {error && <div className="error-banner" role="alert">{error}</div>}
        <div className="analytics-page">
          <section className="metric-row">
            <article><span>Aircraft</span><strong>{summary?.aircraft_count ?? "—"}</strong></article>
            <article><span>Mean altitude</span><strong>{summary?.mean_altitude_ft ? `${Math.round(summary.mean_altitude_ft).toLocaleString()} ft` : "—"}</strong></article>
            <article><span>Unusual tracks</span><strong>{summary?.unusual_count ?? "—"}</strong></article>
            <article><span>Data class</span><strong>{summary?.classification.replaceAll("_", " ") ?? "—"}</strong></article>
          </section>
          <section className="chart-card">
            <div><span className="eyebrow">Current snapshot</span><h2>Altitude by aircraft</h2><p>Thousands of feet · synthetic demo</p></div>
            <div className="chart-frame" aria-label="Aircraft altitude bar chart" role="img">
              <ResponsiveContainer
                width="100%"
                height="100%"
                initialDimension={{ width: 720, height: 270 }}
              >
                <BarChart data={chart}><CartesianGrid stroke="rgba(135,181,199,.12)" vertical={false} /><XAxis dataKey="callsign" stroke="#78909c" fontSize={10} /><YAxis stroke="#78909c" fontSize={10} unit="k" /><Tooltip contentStyle={{ background: "#09121a", border: "1px solid rgba(135,181,199,.27)" }} /><Bar dataKey="altitude" fill="#57e1ff" radius={[3, 3, 0, 0]} isAnimationActive={false} /></BarChart>
              </ResponsiveContainer>
            </div>
          </section>
          <section className="chart-card density-card">
            <div>
              <span className="eyebrow">Experimental forecast</span>
              <h2>Regional traffic density</h2>
              <p>{density?.model.name.replaceAll("_", " ") ?? "Loading model"}</p>
              {density && <div className="density-summary"><strong>{density.current_aircraft}</strong><span>now</span><i>→</i><strong>{density.points.at(-1)?.predicted_aircraft.toFixed(1)}</strong><span>in 60 min</span></div>}
              {density && <p className="forecast-limit">Held-out synthetic MAE ±{density.points.at(-1)?.test_mae_aircraft?.toFixed(2)} aircraft. Not a capacity prediction.</p>}
            </div>
            <div className="chart-frame" aria-label="Regional traffic density forecast chart" role="img">
              <ResponsiveContainer
                width="100%"
                height="100%"
                initialDimension={{ width: 720, height: 270 }}
              >
                <LineChart data={densityChart}>
                  <CartesianGrid stroke="rgba(135,181,199,.12)" vertical={false} />
                  <XAxis dataKey="horizon" stroke="#78909c" fontSize={10} />
                  <YAxis stroke="#78909c" fontSize={10} allowDecimals={false} />
                  <Tooltip contentStyle={{ background: "#09121a", border: "1px solid rgba(135,181,199,.27)" }} />
                  <Legend wrapperStyle={{ fontSize: 9, textTransform: "uppercase" }} />
                  <Line name="Random Forest" type="monotone" dataKey="forecast" stroke="#57e1ff" strokeWidth={2.5} dot={{ r: 3 }} isAnimationActive={false} />
                  <Line name="Persistence" type="monotone" dataKey="persistence" stroke="#f3b663" strokeDasharray="4 4" dot={false} isAnimationActive={false} />
                </LineChart>
              </ResponsiveContainer>
            </div>
          </section>
          <section className="analytics-table"><div className="analytics-row heading"><span>Callsign</span><span>Altitude</span><span>Speed</span><span>Vertical rate</span></div>{flights.map((flight) => <div className="analytics-row" key={flight.icao24}><strong>{flight.callsign}</strong><span>{flight.altitude_ft?.toLocaleString()} ft</span><span>{flight.ground_speed_kt} kt</span><span>{flight.vertical_rate_fpm} fpm</span></div>)}</section>
        </div>
      </section>
    </main>
  );
}
