"use client";

import { useEffect, useMemo, useState } from "react";

import { AppRail } from "@/components/AppRail";
import { FlightInspector } from "@/components/FlightInspector";
import { RadarMap } from "@/components/RadarMap";
import {
  createReport,
  getAnomaly,
  getFlights,
  getPrediction,
  getTrack,
  type IntelligenceReport,
} from "@/lib/api";
import { formatUtc } from "@/lib/format";
import type {
  AnomalyResponse,
  FlightListResponse,
  FlightState,
  FlightTrackResponse,
  PredictionResponse,
} from "@/lib/types";

const REPLAY_START = Date.parse("2025-01-15T12:00:00Z");

interface AnalysisState {
  key: string;
  track: FlightTrackResponse;
  prediction: PredictionResponse;
  anomaly: AnomalyResponse;
}

export default function RadarPage() {
  const [responseState, setResponseState] = useState<{ key: string; data: FlightListResponse } | null>(null);
  const [selectedIcao24, setSelectedIcao24] = useState<string | null>(null);
  const [analysisState, setAnalysisState] = useState<AnalysisState | null>(null);
  const [reportState, setReportState] = useState<{ key: string; data: IntelligenceReport } | null>(null);
  const [reportBusyKey, setReportBusyKey] = useState<string | null>(null);
  const [search, setSearch] = useState("");
  const [minute, setMinute] = useState(60);
  const [playing, setPlaying] = useState(false);
  const [speed, setSpeed] = useState(1);
  const [error, setError] = useState<string | null>(null);
  const [analysisError, setAnalysisError] = useState<string | null>(null);
  const [retrySequence, setRetrySequence] = useState(0);

  const replayAt = useMemo(() => new Date(REPLAY_START + minute * 60_000).toISOString(), [minute]);
  const response = responseState?.key === replayAt ? responseState.data : null;
  const loading = response === null;
  const analysisKey = selectedIcao24 ? `${selectedIcao24}:${replayAt}` : null;
  const analysis = analysisState?.key === analysisKey ? analysisState : null;
  const report = reportState?.key === analysisKey ? reportState.data : null;
  const reportBusy = reportBusyKey === analysisKey;

  useEffect(() => {
    let active = true;
    getFlights(replayAt)
      .then((nextResponse) => {
        if (!active) return;
        setResponseState({ key: replayAt, data: nextResponse });
        setError(null);
      })
      .catch((reason: unknown) => {
        if (active) setError(reason instanceof Error ? reason.message : "Unable to reach the AERIS API");
      })
    return () => { active = false; };
  }, [replayAt, retrySequence]);

  useEffect(() => {
    if (!playing) return;
    const timer = window.setInterval(() => {
      setMinute((current) => {
        if (current >= 60) {
          setPlaying(false);
          return 60;
        }
        return Math.min(60, current + speed);
      });
    }, 1000);
    return () => window.clearInterval(timer);
  }, [playing, speed]);

  useEffect(() => {
    if (!selectedIcao24) return;
    let active = true;
    const key = `${selectedIcao24}:${replayAt}`;
    Promise.all([
      getTrack(selectedIcao24, replayAt),
      getPrediction(selectedIcao24, replayAt),
      getAnomaly(selectedIcao24, replayAt),
    ]).then(([nextTrack, nextPrediction, nextAnomaly]) => {
      if (!active) return;
      setAnalysisState({ key, track: nextTrack, prediction: nextPrediction, anomaly: nextAnomaly });
      setAnalysisError(null);
    }).catch((reason: unknown) => {
      if (active) setAnalysisError(reason instanceof Error ? reason.message : "Flight analysis failed");
    });
    return () => { active = false; };
  }, [replayAt, selectedIcao24]);

  const flights = useMemo(() => {
    const query = search.trim().toLowerCase();
    if (!query) return response?.data ?? [];
    return (response?.data ?? []).filter((flight) =>
      flight.icao24.includes(query) || flight.callsign?.toLowerCase().includes(query)
    );
  }, [response, search]);

  const selectedFlight: FlightState | null =
    response?.data.find((flight) => flight.icao24 === selectedIcao24) ?? null;

  const handleReport = async () => {
    if (!selectedIcao24 || !analysisKey) return;
    const requestedKey = analysisKey;
    setReportBusyKey(requestedKey);
    try {
      const nextReport = await createReport(selectedIcao24, replayAt);
      setReportState({ key: requestedKey, data: nextReport });
      setAnalysisError(null);
    } catch (reason) {
      setAnalysisError(reason instanceof Error ? reason.message : "Intelligence tools failed");
    } finally {
      setReportBusyKey((current) => current === requestedKey ? null : current);
    }
  };

  return (
    <main className="app-shell">
      <AppRail active="radar" />

      <section className="workspace">
        <header className="topbar">
          <div className="title-lockup">
            <span className="eyebrow">Airspace intelligence / Paris sector</span>
            <h1>Live Airspace</h1>
          </div>
          <div className="topbar-status">
            <span className="demo-badge">Synthetic demo</span>
            <span className={`connection-status ${error ? "offline" : ""}`}><i />{error ? "API issue" : "API connected"}</span>
            <time>{formatUtc(replayAt)}</time>
          </div>
        </header>

        {error && (
          <div className="error-banner" role="alert">
            <span>{error}</span><button type="button" onClick={() => setRetrySequence((value) => value + 1)}>Retry</button>
          </div>
        )}

        <div className="main-grid">
          <section className="radar-panel">
            <div className="map-toolbar">
              <label className="search-box">
                <span aria-hidden="true">⌕</span>
                <input
                  value={search}
                  onChange={(event) => setSearch(event.target.value)}
                  placeholder="Search callsign or ICAO24"
                  aria-label="Search callsign or ICAO24"
                />
                {search && <button type="button" onClick={() => setSearch("")} aria-label="Clear search">×</button>}
              </label>
              <div className="traffic-metric"><strong>{flights.length}</strong><span>aircraft in view</span></div>
              <div className="traffic-metric"><strong>{response?.meta.source ?? "—"}</strong><span>active source</span></div>
            </div>

            <div className="map-stage">
              <RadarMap
                flights={flights}
                selectedIcao24={selectedIcao24}
                track={analysis?.track ?? null}
                prediction={analysis?.prediction ?? null}
                onSelect={setSelectedIcao24}
              />
              {loading && <div className="loading-state" role="status"><i />Updating positions…</div>}
              {!loading && !error && flights.length === 0 && (
                <div className="empty-state" role="status"><strong>No aircraft in this view</strong><button type="button" onClick={() => setSearch("")}>Clear search</button></div>
              )}
              <div className="map-legend">
                <span><i className="observed-line" />Observed</span>
                <span><i className="predicted-line" />Model projection</span>
              </div>
              <div className="non-operational">Research display · not for operational use</div>
            </div>

            <div className="timeline-panel">
              <button className="play-button" type="button" onClick={() => setPlaying((value) => !value)} aria-label={playing ? "Pause replay" : "Play replay"}>
                {playing ? "Ⅱ" : "▶"}
              </button>
              <button className="reset-button" type="button" onClick={() => { setMinute(0); setPlaying(false); }}>↺</button>
              <div className="timeline-track">
                <div className="timeline-labels"><span>12:00</span><strong>{formatUtc(replayAt)}</strong><span>13:00</span></div>
                <input type="range" min="0" max="60" value={minute} onChange={(event) => setMinute(Number(event.target.value))} aria-label="Replay minute" />
              </div>
              <div className="speed-control" aria-label="Replay speed">
                {[1, 2, 4].map((value) => <button key={value} className={speed === value ? "active" : ""} type="button" onClick={() => setSpeed(value)}>×{value}</button>)}
              </div>
            </div>
          </section>

          <FlightInspector
            flight={selectedFlight}
            anomaly={analysis?.anomaly ?? null}
            prediction={analysis?.prediction ?? null}
            report={report}
            reportBusy={reportBusy}
            error={analysisError}
            onCreateReport={() => void handleReport()}
          />
        </div>
      </section>
    </main>
  );
}
