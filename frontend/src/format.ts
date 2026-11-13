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

export const CATEGORY_COLORS: Record<string, string> = {
  food_dining: "#f97316", groceries: "#84cc16", transport: "#0ea5e9", shopping: "#a855f7", bills: "#eab308",
  rent: "#64748b", entertainment: "#ec4899", health: "#ef4444", personal: "#14b8a6", education: "#6366f1",
  travel: "#06b6d4", investments: "#10b37c", transfers: "#8b5cf6", cash: "#78716c", fees: "#dc2626", other: "#94a3b8",
  salary: "#10b37c", refund: "#22c55e", interest: "#059669", transfer_in: "#34d39a", other_income: "#6ee7b7",
};
export const colorFor = (c: string) => CATEGORY_COLORS[c] ?? "#94a3b8";
