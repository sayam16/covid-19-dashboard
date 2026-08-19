export function formatNumber(value: number, compact = true) {
  return new Intl.NumberFormat("en-IN", {
    notation: compact ? "compact" : "standard",
    maximumFractionDigits: compact ? 1 : 0
  }).format(value ?? 0);
}

export function formatPercent(value: number) {
  return `${(value * 100).toFixed(1)}%`;
}

export function titleCase(value: string) {
  return value.replace(/_/g, " ").replace(/\b\w/g, (char) => char.toUpperCase());
}
