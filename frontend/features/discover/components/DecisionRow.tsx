'use client'

import Link from 'next/link'

import StatusChip from '@/components/ui/StatusChip'
import TrustBadge from '@/components/ui/TrustBadge'
import { cn } from '@/lib/formatting'
import { UniverseRowViewModel } from '@/lib/view-models/research'

function signalValue(row: UniverseRowViewModel, key: UniverseRowViewModel['signals'][number]['key']): string {
  const signal = row.signals.find((item) => item.key === key)
  return signal?.value == null ? 'n/a' : signal.value.toFixed(1)
}

export default function DecisionRow({
  row,
  selected,
  focused,
  onFocus,
}: {
  row: UniverseRowViewModel
  selected: boolean
  focused: boolean
  onFocus: () => void
}) {
  return (
    <article
      className={cn(
        'grid cursor-default grid-cols-[74px_minmax(0,1.5fr)_88px_88px_88px_88px] items-center gap-3 border-t border-[color:var(--border-subtle)] px-4 py-3 transition-colors sm:px-5',
        focused && 'bg-[color:rgba(19,32,44,0.6)]',
        selected && 'ring-1 ring-inset ring-[color:var(--mispricing-border)]',
      )}
      tabIndex={0}
      onMouseEnter={onFocus}
      onFocus={onFocus}
    >
      <div className="min-w-0">
        <div className="text-lg font-semibold tracking-tight text-[color:var(--text-primary)]">{row.rankLabel}</div>
        <div className="mt-1 text-xs text-[color:var(--text-tertiary)]">{row.percentileLabel}</div>
      </div>

      <div className="min-w-0">
        <div className="flex min-w-0 items-center gap-3">
          <div className="min-w-0">
            <div className="truncate text-base font-medium text-[color:var(--text-primary)]">{row.name}</div>
            <div className="mt-1 text-xs uppercase tracking-[0.18em] text-[color:var(--text-tertiary)]">{row.netuidLabel}</div>
          </div>
          <StatusChip tone={row.modelLabelTone} className="shrink-0">
            {row.modelLabel}
          </StatusChip>
        </div>
      </div>

      <div className="text-sm font-medium text-[color:var(--text-primary)]">{signalValue(row, 'fundamental_quality')}</div>
      <div className="text-sm font-medium text-[color:var(--text-primary)]">{signalValue(row, 'mispricing_signal')}</div>
      <div className="text-sm font-medium text-[color:var(--text-primary)]">{signalValue(row, 'fragility_risk')}</div>
      <div className="text-sm font-medium text-[color:var(--text-primary)]">{signalValue(row, 'signal_confidence')}</div>
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
            <StatusChip tone={row.modelLabelTone}>{row.modelLabel}</StatusChip>
          </div>
          <div className="mt-3 text-xl font-semibold tracking-tight text-[color:var(--text-primary)]">{row.name}</div>
          <p className="mt-3 text-sm leading-6 text-[color:var(--text-secondary)]">{row.thesisLine}</p>
          <p className="mt-2 text-sm leading-6 text-[color:var(--text-secondary)]">{row.decisionLine}</p>
        </div>
      </div>

      <div className="grid grid-cols-2 gap-3 text-sm">
        <div className="surface-subtle p-3">
          <div className="eyebrow">Quality</div>
          <div className="mt-2 font-semibold text-[color:var(--text-primary)]">{signalValue(row, 'fundamental_quality')}</div>
        </div>
        <div className="surface-subtle p-3">
          <div className="eyebrow">Mispricing</div>
          <div className="mt-2 font-semibold text-[color:var(--text-primary)]">{signalValue(row, 'mispricing_signal')}</div>
        </div>
        <div className="surface-subtle p-3">
          <div className="eyebrow">Fragility</div>
          <div className="mt-2 font-semibold text-[color:var(--text-primary)]">{signalValue(row, 'fragility_risk')}</div>
        </div>
        <div className="surface-subtle p-3">
          <div className="eyebrow">Confidence</div>
          <div className="mt-2 font-semibold text-[color:var(--text-primary)]">{signalValue(row, 'signal_confidence')}</div>
        </div>
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
