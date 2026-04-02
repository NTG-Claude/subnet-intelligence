export function cn(...classes: Array<string | false | null | undefined>): string {
  return classes.filter(Boolean).join(' ')
}

export function formatDateTime(iso: string | null | undefined): string {
  if (!iso) return 'No completed run'
  return new Date(iso).toLocaleString('en-US', {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
    timeZone: 'UTC',
    timeZoneName: 'short',
  })
}

export function formatCompactNumber(value: number | null | undefined, digits = 0): string {
  if (value == null) return 'n/a'
  return value.toLocaleString('en-US', {
    maximumFractionDigits: digits,
    minimumFractionDigits: digits,
  })
}

export function formatPercent(value: number | null | undefined): string {
  if (value == null) return 'n/a'
  return `${value.toFixed(1)}%`
}

export function formatPrice(value: number | null | undefined): string {
  if (value == null) return 'n/a'
  return value < 0.001 ? `t${value.toExponential(2)}` : `t${value.toFixed(4)}`
}

export function parseTimestamp(iso: string | null | undefined): number {
  const parsed = iso ? Date.parse(iso) : Number.NaN
  return Number.isFinite(parsed) ? parsed : 0
}

export function isStale(iso: string | null | undefined, staleHours = 36): boolean {
  const timestamp = parseTimestamp(iso)
  if (!timestamp) return false
  return Date.now() - timestamp > staleHours * 60 * 60 * 1000
}
