"use client";

import { useEffect, useState } from "react";
import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

import { AppRail } from "@/components/AppRail";
import { getAnalyticsSummary, getFlights } from "@/lib/api";
import type { AnalyticsSummary, FlightState } from "@/lib/types";

export default function AnalyticsPage() {
  const [summary, setSummary] = useState<AnalyticsSummary | null>(null);
  const [flights, setFlights] = useState<FlightState[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    Promise.all([getAnalyticsSummary(), getFlights()])
      .then(([nextSummary, response]) => { setSummary(nextSummary); setFlights(response.data); })
      .catch((reason: unknown) => setError(reason instanceof Error ? reason.message : "Analytics unavailable"));
  }, []);

  const chart = flights.map((flight) => ({
    callsign: flight.callsign ?? flight.icao24,
    altitude: Math.round((flight.altitude_ft ?? 0) / 100) / 10,
    speed: flight.ground_speed_kt ?? 0,
  }));

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
                <BarChart data={chart}><CartesianGrid stroke="rgba(135,181,199,.12)" vertical={false} /><XAxis dataKey="callsign" stroke="#78909c" fontSize={10} /><YAxis stroke="#78909c" fontSize={10} unit="k" /><Tooltip contentStyle={{ background: "#09121a", border: "1px solid rgba(135,181,199,.27)" }} /><Bar dataKey="altitude" fill="#57e1ff" radius={[3, 3, 0, 0]} /></BarChart>
              </ResponsiveContainer>
            </div>
          </section>
          <section className="analytics-table"><div className="analytics-row heading"><span>Callsign</span><span>Altitude</span><span>Speed</span><span>Vertical rate</span></div>{flights.map((flight) => <div className="analytics-row" key={flight.icao24}><strong>{flight.callsign}</strong><span>{flight.altitude_ft?.toLocaleString()} ft</span><span>{flight.ground_speed_kt} kt</span><span>{flight.vertical_rate_fpm} fpm</span></div>)}</section>
        </div>
      </section>
    </main>
  );
}
