"use client";

import * as maplibregl from "maplibre-gl";
import type { GeoJSONSource, Map as MapLibreMap, StyleSpecification } from "maplibre-gl";
import "maplibre-gl/dist/maplibre-gl.css";
import { useEffect, useRef, useState } from "react";

import type { FlightState, FlightTrackResponse, PredictionPoint, PredictionResponse } from "@/lib/types";

const CENTER: [number, number] = [2.35, 48.86];

const localRadarStyle: StyleSpecification = {
  version: 8,
  name: "AERIS local radar",
  sources: {},
  layers: [
    { id: "background", type: "background", paint: { "background-color": "#071019" } },
  ],
};

function circle(center: [number, number], radiusDegrees: number): [number, number][] {
  return Array.from({ length: 97 }, (_, index) => {
    const angle = (index / 96) * Math.PI * 2;
    const longitude = center[0] + (radiusDegrees * Math.cos(angle)) / Math.cos((center[1] * Math.PI) / 180);
    const latitude = center[1] + radiusDegrees * Math.sin(angle);
    return [longitude, latitude] as [number, number];
  });
}

const referenceLines: GeoJSON.FeatureCollection = {
  type: "FeatureCollection",
  features: [0.75, 1.5, 2.25, 3].map((radius) => ({
    type: "Feature",
    properties: { radius },
    geometry: { type: "LineString", coordinates: circle(CENTER, radius) },
  })),
};

function lineFeature(points: Array<{ longitude: number; latitude: number }>): GeoJSON.Feature {
  return {
    type: "Feature",
    properties: {},
    geometry: {
      type: "LineString",
      coordinates: points.map((point) => [point.longitude, point.latitude]),
    },
  };
}

interface RadarMapProps {
  flights: FlightState[];
  selectedIcao24: string | null;
  track: FlightTrackResponse | null;
  prediction: PredictionResponse | null;
  scenario?: FlightState[] | null;
  scenarioPrediction?: PredictionPoint[] | null;
  onSelect: (icao24: string) => void;
}

export function RadarMap({ flights, selectedIcao24, track, prediction, scenario, scenarioPrediction, onSelect }: RadarMapProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const mapRef = useRef<MapLibreMap | null>(null);
  const markersRef = useRef<maplibregl.Marker[]>([]);
  const [mapError, setMapError] = useState(false);
  const [styleReady, setStyleReady] = useState(false);

  useEffect(() => {
    if (!containerRef.current || mapRef.current) return;
    try {
      maplibregl.setWorkerUrl(
        new URL("maplibre-gl/dist/maplibre-gl-worker.mjs", import.meta.url).toString(),
      );
      const externalStyle = process.env.NEXT_PUBLIC_MAP_STYLE_URL;
      const map = new maplibregl.Map({
        container: containerRef.current,
        style: externalStyle || localRadarStyle,
        center: CENTER,
        zoom: 5.4,
        minZoom: 3,
        maxZoom: 12,
        attributionControl: externalStyle ? { compact: true } : false,
      });
      map.addControl(new maplibregl.NavigationControl({ showCompass: true }), "bottom-left");
      map.on("load", () => {
        map.addSource("range-rings", { type: "geojson", data: referenceLines });
        map.addLayer({
          id: "range-rings",
          type: "line",
          source: "range-rings",
          paint: { "line-color": "#164b5c", "line-width": 1, "line-opacity": 0.52 },
        });
        map.addSource("scenario-prediction", {
          type: "geojson",
          data: { type: "FeatureCollection", features: [] },
        });
        map.addLayer({
          id: "scenario-prediction",
          type: "line",
          source: "scenario-prediction",
          paint: {
            "line-color": "#c58cff",
            "line-width": 2,
            "line-dasharray": [1, 2.5],
            "line-opacity": 0.95,
          },
        });
        map.addSource("scenario-track", {
          type: "geojson",
          data: { type: "FeatureCollection", features: [] },
        });
        map.addLayer({
          id: "scenario-track",
          type: "line",
          source: "scenario-track",
          paint: {
            "line-color": "#ff776f",
            "line-width": 2.5,
            "line-dasharray": [1, 1.5],
            "line-opacity": 0.95,
          },
        });
        map.addSource("observed-track", {
          type: "geojson",
          data: { type: "FeatureCollection", features: [] },
        });
        map.addLayer({
          id: "observed-track",
          type: "line",
          source: "observed-track",
          paint: { "line-color": "#56e1ff", "line-width": 2.5, "line-opacity": 0.95 },
        });
        map.addSource("predicted-track", {
          type: "geojson",
          data: { type: "FeatureCollection", features: [] },
        });
        map.addLayer({
          id: "predicted-track",
          type: "line",
          source: "predicted-track",
          paint: {
            "line-color": "#f3b663",
            "line-width": 2,
            "line-dasharray": [2, 2],
            "line-opacity": 0.95,
          },
        });
        setStyleReady(true);
      });
      map.on("error", (event) => {
        if (event.error.message.includes("Worker failed")) setMapError(true);
      });
      mapRef.current = map;
    } catch {
      window.setTimeout(() => setMapError(true), 0);
    }
    return () => {
      mapRef.current?.remove();
      mapRef.current = null;
    };
  }, []);

  useEffect(() => {
    const map = mapRef.current;
    if (!map) return;
    markersRef.current.forEach((marker) => marker.remove());
    markersRef.current = flights.map((flight) => {
      const element = document.createElement("button");
      element.type = "button";
      element.className = `aircraft-marker${flight.icao24 === selectedIcao24 ? " selected" : ""}`;
      element.setAttribute("aria-label", `Select ${flight.callsign ?? flight.icao24}`);
      const glyph = document.createElement("span");
      glyph.textContent = "✈";
      glyph.style.transform = `rotate(${flight.heading_deg ?? 0}deg)`;
      element.append(glyph);
      element.addEventListener("click", () => onSelect(flight.icao24));
      return new maplibregl.Marker({ element, anchor: "center" })
        .setLngLat([flight.longitude, flight.latitude])
        .addTo(map);
    });
    if (flights.length > 1) {
      const bounds = flights.reduce(
        (current, flight) => current.extend([flight.longitude, flight.latitude]),
        new maplibregl.LngLatBounds(
          [flights[0].longitude, flights[0].latitude],
          [flights[0].longitude, flights[0].latitude],
        ),
      );
      map.fitBounds(bounds, { padding: 72, maxZoom: 6.2, duration: 0 });
    }
  }, [flights, onSelect, selectedIcao24]);

  useEffect(() => {
    const map = mapRef.current;
    if (!map || !styleReady) return;
    const trackSource = map.getSource("observed-track") as GeoJSONSource | undefined;
    const predictionSource = map.getSource("predicted-track") as GeoJSONSource | undefined;
    const scenarioSource = map.getSource("scenario-track") as GeoJSONSource | undefined;
    const scenarioPredictionSource = map.getSource("scenario-prediction") as GeoJSONSource | undefined;
    trackSource?.setData({
      type: "FeatureCollection",
      features: track?.points.length ? [lineFeature(track.points)] : [],
    });
    const latest = track?.points.at(-1);
    const projection = latest && prediction ? [latest, ...prediction.points] : [];
    predictionSource?.setData({
      type: "FeatureCollection",
      features: projection.length ? [lineFeature(projection)] : [],
    });
    scenarioSource?.setData({
      type: "FeatureCollection",
      features: scenario?.length ? [lineFeature(scenario)] : [],
    });
    const scenarioLatest = scenario?.at(-1);
    const scenarioProjection = scenarioLatest && scenarioPrediction
      ? [scenarioLatest, ...scenarioPrediction]
      : [];
    scenarioPredictionSource?.setData({
      type: "FeatureCollection",
      features: scenarioProjection.length ? [lineFeature(scenarioProjection)] : [],
    });
  }, [track, prediction, scenario, scenarioPrediction, styleReady]);

  if (mapError) {
    return (
      <div className="map-fallback" role="status">
        <strong>3D graphics are unavailable.</strong>
        <span>The flight list and analysis tools remain usable.</span>
      </div>
    );
  }

  return <div ref={containerRef} className="radar-map" aria-label="Interactive demonstration airspace map" />;
}
