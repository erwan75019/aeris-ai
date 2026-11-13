import Link from "next/link";

interface AppRailProps {
  active: "radar" | "twin" | "analytics";
}

const links = [
  { key: "radar", href: "/", glyph: "⌁", label: "Radar" },
  { key: "twin", href: "/twin", glyph: "◇", label: "Twin" },
  { key: "analytics", href: "/analytics", glyph: "▥", label: "Analytics" },
] as const;

export function AppRail({ active }: AppRailProps) {
  return (
    <nav className="rail" aria-label="Primary navigation">
      <Link className="brand-mark" href="/" aria-label="AERIS AI home">A</Link>
      <div className="rail-links">
        {links.map((link) => (
          <Link
            key={link.key}
            className={`rail-button${active === link.key ? " active" : ""}`}
            href={link.href}
            aria-label={link.label === "Twin" ? "Digital twin" : link.label}
          >
            <span>{link.glyph}</span><small>{link.label}</small>
          </Link>
        ))}
      </div>
      <div className="rail-version">v0.1</div>
    </nav>
  );
}
