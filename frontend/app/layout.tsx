import type { Metadata } from "next";

import "./globals.css";

export const metadata: Metadata = {
  title: "AERIS AI — Airspace Intelligence",
  description: "Experimental airspace analytics, replay and trajectory forecasting.",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
