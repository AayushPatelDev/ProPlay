export const BASE_FEATURES = ["goals", "assists", "minutes", "age", "position"];
export const POSITIONS = ["Goalkeeper", "Defender", "Midfielder", "Attacker"];
export const POSITION_SHORT = { Goalkeeper: "GK", Defender: "DEF", Midfielder: "MID", Attacker: "FWD" };

export function formatEUR(value) {
  if (value == null || Number.isNaN(value)) return "—";
  const abs = Math.abs(value);
  if (abs >= 1e9) return `€${(value / 1e9).toFixed(2)}B`;
  if (abs >= 1e6) return `€${(value / 1e6).toFixed(abs >= 1e8 ? 0 : 1)}M`;
  if (abs >= 1e3) return `€${Math.round(value / 1e3)}K`;
  return `€${Math.round(value)}`;
}

export const formatNumber = (value) => (value == null ? "—" : new Intl.NumberFormat("en-GB").format(value));

export const formatPct = (value, digits = 0) =>
  value == null || !Number.isFinite(value) ? "—" : `${value > 0 ? "+" : ""}${value.toFixed(digits)}%`;

export const formatSeason = (season) => `${season}/${String(season + 1).slice(-2)}`;

export const initials = (name = "") =>
  name
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((part) => part[0])
    .join("")
    .toUpperCase();
