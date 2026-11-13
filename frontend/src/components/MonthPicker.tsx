import { ChevronLeft, ChevronRight } from "lucide-react";
import { monthLabel } from "../format";

export function MonthPicker({ months, value, onChange }: { months: string[]; value: string; onChange: (m: string) => void }) {
  const sorted = [...months].sort();
  const i = sorted.indexOf(value);
  return (
    <div className="flex items-center gap-1 border border-ink-900 bg-white p-1">
      <button className="rounded-lg p-1.5 text-ink-600 hover:bg-ink-50 disabled:opacity-30" disabled={i <= 0}
        onClick={() => onChange(sorted[i - 1])} aria-label="Previous month"><ChevronLeft className="h-4 w-4" /></button>
      <select className="bg-transparent px-1 font-mono text-xs font-semibold uppercase tracking-wider focus:outline-none" value={value}
        onChange={(e) => onChange(e.target.value)} aria-label="Month">
        {[...sorted].reverse().map((m) => <option key={m} value={m}>{monthLabel(m)}</option>)}
      </select>
      <button className="rounded-lg p-1.5 text-ink-600 hover:bg-ink-50 disabled:opacity-30" disabled={i < 0 || i >= sorted.length - 1}
        onClick={() => onChange(sorted[i + 1])} aria-label="Next month"><ChevronRight className="h-4 w-4" /></button>
    </div>
  );
}
