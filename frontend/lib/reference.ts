export interface AirportReference {
  icao: string;
  name: string;
  latitude: number;
  longitude: number;
  source: "static_reference";
}

export const AIRPORTS: AirportReference[] = [
  { icao: "LFPG", name: "Paris Charles de Gaulle", latitude: 49.0097, longitude: 2.5479, source: "static_reference" },
  { icao: "LFPO", name: "Paris Orly", latitude: 48.7262, longitude: 2.3652, source: "static_reference" },
  { icao: "LFBO", name: "Toulouse-Blagnac", latitude: 43.6293, longitude: 1.3638, source: "static_reference" },
];

export const AIRSPACE_ZONES = {
  all: { label: "All demo airspace", bounds: null },
  west: { label: "Western sector", bounds: [-6, 44, 2, 52] },
  central: { label: "Central sector", bounds: [2, 45, 9, 53] },
  east: { label: "Eastern sector", bounds: [9, 45, 12, 50] },
} as const;

export type AirspaceZone = keyof typeof AIRSPACE_ZONES;
