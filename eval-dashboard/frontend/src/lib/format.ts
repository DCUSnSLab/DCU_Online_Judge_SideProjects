export function fmtPct(n: number | null | undefined, total: number | null | undefined): string {
  if (n == null || total == null || total <= 0) return "-";
  return `${n}/${total}`;
}

export function clamp01(n: number): number {
  return Math.max(0, Math.min(1, n));
}

export function colorForScore(score: number | null, total: number): string {
  if (score == null) return "bg-slate-100 text-slate-400";
  const ratio = total > 0 ? score / total : 0;
  if (ratio >= 1) return "bg-emerald-100 text-emerald-900";
  if (ratio >= 0.7) return "bg-lime-100 text-lime-900";
  if (ratio >= 0.4) return "bg-amber-100 text-amber-900";
  if (ratio > 0) return "bg-orange-100 text-orange-900";
  return "bg-rose-100 text-rose-900";
}

export function colorForResult(label: string | null | undefined): string {
  switch (label) {
    case "AC":
      return "bg-emerald-500 text-white";
    case "PA":
      return "bg-amber-400 text-white";
    case "WA":
      return "bg-rose-400 text-white";
    case "CE":
      return "bg-purple-400 text-white";
    case "TLE":
    case "RTLE":
    case "MLE":
    case "RE":
    case "SE":
      return "bg-orange-400 text-white";
    case "PENDING":
    case "JUDGING":
      return "bg-slate-400 text-white";
    default:
      return "bg-slate-200 text-slate-500";
  }
}
