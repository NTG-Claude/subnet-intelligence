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
    <div
      className={cn(
        'rounded-[var(--radius-lg)] border border-[color:rgba(148,163,184,0.12)] bg-[linear-gradient(180deg,rgba(20,31,43,0.92),rgba(16,27,39,0.96))]',
        compact ? 'px-4 py-3.5' : 'p-4',
      )}
    >
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <div
            className={cn(
              'text-[11px] font-medium uppercase text-[color:var(--text-tertiary)]',
              compact ? 'tracking-[0.24em]' : 'tracking-[0.28em]',
            )}
          >
            {signal.label}
          </div>
        </div>
        <div className={cn('shrink-0 text-right font-semibold text-[color:var(--text-primary)]', compact ? 'text-[1.05rem]' : 'text-base')}>{label}</div>
      </div>
      <div className={cn('rounded-full bg-[color:rgba(8,15,24,0.7)]', compact ? 'mt-5 h-2.5' : 'mt-3 h-2')}>
        <div
          className={cn(compact ? 'h-2.5' : 'h-2', 'rounded-full transition-[width] duration-200', BAR_TONES[signal.tone] ?? BAR_TONES.neutral)}
          style={{ width: `${visibleValue}%` }}
          aria-hidden="true"
        />
      </div>
    </div>
  )
}
