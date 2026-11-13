const inrFmt = new Intl.NumberFormat("en-IN", { maximumFractionDigits: 0 });
const inrFmt2 = new Intl.NumberFormat("en-IN", { minimumFractionDigits: 2, maximumFractionDigits: 2 });

export function inr(value: number | null | undefined, decimals = false): string {
  if (value === null || value === undefined || Number.isNaN(value)) return "—";
  const sign = value < 0 ? "-" : "";
  return `${sign}₹${(decimals ? inrFmt2 : inrFmt).format(Math.abs(value))}`;
}

export function compactInr(value: number): string {
  const abs = Math.abs(value);
  if (abs >= 1e7) return `₹${(value / 1e7).toFixed(1)}Cr`;
  if (abs >= 1e5) return `₹${(value / 1e5).toFixed(1)}L`;
  if (abs >= 1e3) return `₹${(value / 1e3).toFixed(abs >= 1e4 ? 0 : 1)}k`;
  return `₹${Math.round(value)}`;
}

export function monthLabel(key: string, short = false): string {
  const [y, m] = key.split("-").map(Number);
  return new Date(y, m - 1, 1).toLocaleDateString("en-IN", { month: short ? "short" : "long", year: "numeric" });
}

export function dateLabel(iso: string, withTime = false): string {
  const d = new Date(iso);
  const date = d.toLocaleDateString("en-IN", { day: "numeric", month: "short" });
  if (!withTime) return date;
  return `${date}, ${d.toLocaleTimeString("en-IN", { hour: "numeric", minute: "2-digit" })}`;
}

export function pct(value: number | null | undefined, signed = false): string {
  if (value === null || value === undefined) return "—";
  const s = signed && value > 0 ? "+" : "";
  return `${s}${value.toFixed(Math.abs(value) < 10 ? 1 : 0)}%`;
}

export function titleCase(s: string): string {
  if (/[a-z]/.test(s) || s.includes("@")) return s;
  return s.toLowerCase().replace(/\b([a-z])/g, (c) => c.toUpperCase());
}

// Printed-ledger palette: muted inks rather than app-store brights.
export const CATEGORY_COLORS: Record<string, string> = {
  food_dining: "#c8642a", groceries: "#7c8f3a", transport: "#2f5f9e", shopping: "#7a4a8c", bills: "#bd8c22",
  rent: "#4a4337", entertainment: "#b04a6a", health: "#bd331c", personal: "#2f8078", education: "#3f4f9a",
  travel: "#2a7f96", investments: "#1e6943", transfers: "#6a5aa0", cash: "#877d69", fees: "#9d2916", other: "#ada28a",
  salary: "#1e6943", refund: "#4c9766", interest: "#165538", transfer_in: "#2e7a4b", other_income: "#a8cbae",
};
export const colorFor = (c: string) => CATEGORY_COLORS[c] ?? "#ada28a";
