'use client'

import Link from 'next/link'

import StatusChip from '@/components/ui/StatusChip'
import TrustBadge from '@/components/ui/TrustBadge'
import { cn } from '@/lib/formatting'
import { SignalTone, UniverseRowViewModel } from '@/lib/view-models/research'

function signalValue(row: UniverseRowViewModel, key: UniverseRowViewModel['signals'][number]['key']): string {
  const signal = row.signals.find((item) => item.key === key)
  return signal?.value == null ? 'n/a' : signal.value.toFixed(1)
}

function toneClass(tone: SignalTone): string {
  switch (tone) {
    case 'quality':
      return 'text-[color:var(--quality-strong)]'
    case 'mispricing':
      return 'text-[color:var(--mispricing-strong)]'
    case 'fragility':
      return 'text-[color:var(--danger-strong)]'
    case 'confidence':
      return 'text-[color:var(--confidence-strong)]'
    case 'warning':
      return 'text-[color:var(--warning-strong)]'
    default:
      return 'text-[color:var(--text-primary)]'
  }
}

export default function DecisionRow({
  row,
  selected,
  focused,
  pinned,
  onFocus,
  onSelect,
}: {
  row: UniverseRowViewModel
  selected: boolean
  focused: boolean
  pinned: boolean
  onFocus: () => void
  onSelect: () => void
}) {
  return (
    <article
      className={cn(
        'grid cursor-default grid-cols-[64px_minmax(0,1.3fr)_84px_78px_92px_72px_92px_116px_minmax(0,0.9fr)] items-center gap-4 border-t border-[color:var(--border-subtle)] px-4 py-2.5 transition-colors sm:px-5',
        focused && 'bg-[color:rgba(19,32,44,0.42)]',
        selected && 'border-l-2 border-l-[color:var(--mispricing-strong)] pl-[14px] sm:pl-[18px]',
        pinned && 'bg-[color:rgba(19,32,44,0.56)]',
      )}
      tabIndex={0}
      onMouseEnter={onFocus}
      onFocus={onFocus}
      onClick={onSelect}
    >
      <div className="min-w-0 font-mono">
        <div className="text-base font-semibold tracking-tight text-[color:var(--text-primary)]">{row.rankLabel}</div>
      </div>

      <div className="min-w-0">
        <div className="flex min-w-0 items-baseline gap-3">
          <div className="truncate text-[15px] font-medium text-[color:var(--text-primary)]">{row.name}</div>
          <div className="shrink-0 font-mono text-[11px] uppercase tracking-[0.16em] text-[color:var(--text-tertiary)]">{row.netuidLabel}</div>
        </div>
      </div>

      <div className="text-right font-mono text-[13px] font-semibold text-[color:var(--text-primary)]">{row.scoreLabel}</div>
      <div className="text-right font-mono text-[13px] font-medium text-[color:var(--text-primary)]">{signalValue(row, 'fundamental_quality')}</div>
      <div className="text-right font-mono text-[13px] font-medium text-[color:var(--text-primary)]">{signalValue(row, 'mispricing_signal')}</div>
      <div className="text-right font-mono text-[13px] font-medium text-[color:var(--text-primary)]">{signalValue(row, 'fragility_risk')}</div>
      <div className="text-right font-mono text-[13px] font-medium text-[color:var(--text-primary)]">{signalValue(row, 'signal_confidence')}</div>
      <div className={cn('min-w-0 truncate text-[12px] font-semibold', toneClass(row.investability.tone))}>{row.investability.label}</div>
      <div className="flex min-w-0 flex-wrap gap-1">
        {row.warningFlags.length ? (
          row.warningFlags.slice(0, 2).map((flag) => (
            <StatusChip key={flag.label} tone={flag.tone}>
              {flag.label}
            </StatusChip>
          ))
        ) : (
          <span className="text-[11px] text-[color:var(--text-tertiary)]">Clear</span>
        )}
      </div>
    </article>
  )
}

export function MobileDecisionCard({
  row,
  selected,
  focused,
  onFocus,
  onToggleCompare,
}: {
  row: UniverseRowViewModel
  selected: boolean
  focused: boolean
  onFocus: () => void
  onToggleCompare: (id: number) => void
}) {
  return (
    <article
      className={cn('surface-panel space-y-4 p-4', focused && 'ring-1 ring-[color:var(--mispricing-border)]')}
      tabIndex={0}
      onFocus={onFocus}
    >
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <div className="flex flex-wrap items-center gap-2">
            <StatusChip tone="neutral">{row.rankLabel}</StatusChip>
            <StatusChip tone="neutral">{row.netuidLabel}</StatusChip>
          </div>
          <div className="mt-3 text-xl font-semibold tracking-tight text-[color:var(--text-primary)]">{row.name}</div>
          <p className="mt-3 text-sm leading-6 text-[color:var(--text-secondary)]">{row.thesisLine}</p>
          <p className="mt-2 text-sm leading-6 text-[color:var(--text-secondary)]">{row.decisionLine}</p>
        </div>
      </div>

      <div className="grid grid-cols-2 gap-3 text-sm">
        <div className="surface-subtle p-3">
          <div className="eyebrow">Score</div>
          <div className="mt-2 font-semibold text-[color:var(--text-primary)]">{row.scoreLabel}</div>
        </div>
        <div className="surface-subtle p-3">
          <div className="eyebrow">Quality</div>
          <div className="mt-2 font-semibold text-[color:var(--text-primary)]">{signalValue(row, 'fundamental_quality')}</div>
        </div>
        <div className="surface-subtle p-3">
          <div className="eyebrow">Opportunity</div>
          <div className="mt-2 font-semibold text-[color:var(--text-primary)]">{signalValue(row, 'mispricing_signal')}</div>
        </div>
        <div className="surface-subtle p-3">
          <div className="eyebrow">Risk</div>
          <div className="mt-2 font-semibold text-[color:var(--text-primary)]">{signalValue(row, 'fragility_risk')}</div>
        </div>
        <div className="surface-subtle p-3">
          <div className="eyebrow">Confidence</div>
          <div className="mt-2 font-semibold text-[color:var(--text-primary)]">{signalValue(row, 'signal_confidence')}</div>
        </div>
      </div>

      <div className="flex flex-wrap gap-2">
        <StatusChip tone={row.investability.tone}>{row.investability.label}</StatusChip>
        {row.warningFlags.slice(0, 3).map((flag) => (
          <StatusChip key={flag.label} tone={flag.tone}>
            {flag.label}
          </StatusChip>
        ))}
      </div>

      <TrustBadge flags={row.statusFlags} awaitingRun={row.awaitingRun} />

      <div className="flex flex-wrap gap-2">
        <button
          type="button"
          onClick={() => onToggleCompare(row.id)}
          className={cn(
            'button-secondary',
            selected && 'border-[color:var(--mispricing-border)] bg-[color:var(--mispricing-surface)] text-[color:var(--mispricing-strong)]',
          )}
        >
          {selected ? 'Remove from compare' : 'Add to compare'}
        </button>
        <Link href={row.href} className="button-primary">
          Open research
        </Link>
      </div>
    </article>
  )
}
