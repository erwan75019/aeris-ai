export function formatAltitude(value: number | null): string {
  return value === null ? "—" : `${Math.round(value).toLocaleString("en-US")} ft`;
}

export function formatSpeed(value: number | null): string {
  return value === null ? "—" : `${Math.round(value)} kt`;
}

export function formatHeading(value: number | null): string {
  return value === null ? "—" : `${Math.round(value).toString().padStart(3, "0")}°`;
}

export function formatRate(value: number | null): string {
  if (value === null) return "—";
  const rounded = Math.round(value);
  if (rounded < 0) return `−${Math.abs(rounded).toLocaleString("en-US")} fpm`;
  if (rounded > 0) return `+${rounded.toLocaleString("en-US")} fpm`;
  return "0 fpm";
}

export function formatUtc(value: string): string {
  return `${new Date(value).toLocaleTimeString("en-GB", {
    hour12: false,
    timeZone: "UTC",
  })} UTC`;
}
