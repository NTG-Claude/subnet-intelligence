import { SignalStat } from '@/lib/view-models/research'
import { cn } from '@/lib/formatting'

const BAR_TONES: Record<string, string> = {
  quality: 'bg-[color:var(--quality-strong)]',
  mispricing: 'bg-[color:var(--mispricing-strong)]',
  fragility: 'bg-[color:var(--fragility-strong)]',
  confidence: 'bg-[color:var(--confidence-strong)]',
  warning: 'bg-[color:var(--warning-strong)]',
  neutral: 'bg-[color:var(--text-tertiary)]',
}

export default function SignalBar({
  signal,
  compact = false,
}: {
  signal: SignalStat
  compact?: boolean
}) {
  const rawValue = signal.value
  const visibleValue = rawValue == null ? 0 : Math.max(4, Math.min(100, rawValue))
  const label = rawValue == null ? 'n/a' : rawValue.toFixed(1)

  return (
    <div className={cn('rounded-[var(--radius-md)] border border-[color:var(--border-subtle)] bg-[color:var(--surface-2)]', compact ? 'p-3' : 'p-4')}>
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <div className={cn('text-[11px] font-medium uppercase text-[color:var(--text-tertiary)]', compact ? 'tracking-[0.22em]' : 'tracking-[0.28em]')}>
            {signal.label}
          </div>
        </div>
        <div className="shrink-0 text-right text-base font-semibold text-[color:var(--text-primary)]">{label}</div>
      </div>
      <div className="mt-3 h-2 rounded-full bg-[color:var(--surface-1)]">
        <div
          className={cn('h-2 rounded-full transition-[width] duration-200', BAR_TONES[signal.tone] ?? BAR_TONES.neutral)}
          style={{ width: `${visibleValue}%` }}
          aria-hidden="true"
        />
      </div>
    </div>
  )
}
