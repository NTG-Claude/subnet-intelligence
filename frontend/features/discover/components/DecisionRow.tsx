'use client'

import Link from 'next/link'

import StatusChip from '@/components/ui/StatusChip'
import TrustBadge from '@/components/ui/TrustBadge'
import { cn } from '@/lib/formatting'
import { SignalTone, UniverseRowViewModel } from '@/lib/view-models/research'

export const DISCOVER_TABLE_GRID = 'grid-cols-[88px_minmax(180px,1.15fr)_92px_92px_108px_92px_88px_108px]'

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
      return 'text-[color:var(--fragility-strong)]'
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
  rankDelta,
  selected,
  focused,
  pinned,
  onFocus,
  onSelect,
}: {
  row: UniverseRowViewModel
  rankDelta: { change: number; previousRank: number } | null
  selected: boolean
  focused: boolean
  pinned: boolean
  onFocus: () => void
  onSelect: () => void
}) {
  return (
    <article
      className={cn(
        'grid cursor-default items-center gap-x-5 border-t border-[color:var(--border-subtle)] px-5 py-4 transition-colors',
        DISCOVER_TABLE_GRID,
        focused && 'bg-[color:rgba(19,32,44,0.42)]',
        selected && 'border-l-2 border-l-[color:var(--mispricing-strong)] pl-4',
        pinned && 'bg-[color:rgba(19,32,44,0.56)]',
      )}
      tabIndex={0}
      onMouseEnter={onFocus}
      onFocus={onFocus}
      onClick={onSelect}
    >
      <div className="min-w-0 font-mono">
        <div className="flex items-center gap-2">
          <div className="text-[15px] font-semibold tracking-tight text-[color:var(--text-primary)]">{row.rankLabel}</div>
          <RankDeltaBadge rankDelta={rankDelta} />
        </div>
      </div>

      <div className="min-w-0">
        <div className="flex min-w-0 items-baseline gap-3">
          <div className="truncate text-[15px] font-semibold text-[color:var(--text-primary)]">{row.name}</div>
          <div className="shrink-0 font-mono text-[11px] tracking-[0.08em] text-[color:var(--text-tertiary)]">{row.netuidLabel}</div>
        </div>
      </div>

      <div className="text-right font-mono text-[13px] font-semibold tabular-nums text-[color:var(--text-primary)]">{row.scoreLabel}</div>
      <div className="text-right font-mono text-[13px] font-medium tabular-nums text-[color:var(--text-primary)]">{signalValue(row, 'fundamental_quality')}</div>
      <div className="text-right font-mono text-[13px] font-medium tabular-nums text-[color:var(--text-primary)]">{signalValue(row, 'mispricing_signal')}</div>
      <div className="text-right font-mono text-[13px] font-medium tabular-nums text-[color:var(--text-primary)]">{signalValue(row, 'fragility_risk')}</div>
      <div className="text-right font-mono text-[13px] font-medium tabular-nums text-[color:var(--text-primary)]">{signalValue(row, 'signal_confidence')}</div>
      <div className={cn('min-w-0 truncate pl-4 text-left text-[13px] font-medium', toneClass(row.investability.tone))}>{row.investability.label}</div>
    </article>
  )
}

function RankDeltaBadge({ rankDelta }: { rankDelta: { change: number; previousRank: number } | null }) {
  if (!rankDelta || rankDelta.change === 0) return null

  const improved = rankDelta.change > 0
  const arrow = improved ? '↑' : '↓'
  const magnitude = Math.abs(rankDelta.change)

  return (
    <div
      className={cn(
        'inline-flex min-w-[42px] items-center justify-center gap-1 rounded-full px-2 py-1 text-[11px] font-semibold',
        improved
          ? 'bg-[color:var(--quality-surface)] text-[color:var(--quality-strong)]'
          : 'bg-[color:var(--fragility-surface)] text-[color:var(--fragility-strong)]',
      )}
      title={`Previous rank #${rankDelta.previousRank}`}
    >
      <span aria-hidden="true">{arrow}</span>
      <span>{magnitude}</span>
    </div>
  )
}

export function MobileDecisionCard({
  row,
  rankDelta,
  focused,
  onFocus,
}: {
  row: UniverseRowViewModel
  rankDelta: { change: number; previousRank: number } | null
  focused: boolean
  onFocus: () => void
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
            <StatusChip tone={row.investability.tone}>{row.investability.label}</StatusChip>
            {rankDelta ? <RankDeltaBadge rankDelta={rankDelta} /> : null}
          </div>
          <div className="mt-3 text-xl font-semibold tracking-tight text-[color:var(--text-primary)]">{row.name}</div>
        </div>
        <div className="surface-subtle min-w-[96px] p-3 text-right">
          <div className="eyebrow">Score</div>
          <div className="mt-2 font-mono text-lg font-semibold text-[color:var(--text-primary)]">{row.scoreLabel}</div>
        </div>
      </div>

      <div className="grid grid-cols-2 gap-3 text-sm sm:grid-cols-4">
        <div className="surface-subtle p-3">
          <div className="eyebrow">Quality</div>
          <div className="mt-2 font-mono font-semibold text-[color:var(--text-primary)]">{signalValue(row, 'fundamental_quality')}</div>
        </div>
        <div className="surface-subtle p-3">
          <div className="eyebrow">Opportunity</div>
          <div className="mt-2 font-mono font-semibold text-[color:var(--text-primary)]">{signalValue(row, 'mispricing_signal')}</div>
        </div>
        <div className="surface-subtle p-3">
          <div className="eyebrow">Risk</div>
          <div className="mt-2 font-mono font-semibold text-[color:var(--text-primary)]">{signalValue(row, 'fragility_risk')}</div>
        </div>
        <div className="surface-subtle p-3">
          <div className="eyebrow">Confidence</div>
          <div className="mt-2 font-mono font-semibold text-[color:var(--text-primary)]">{signalValue(row, 'signal_confidence')}</div>
        </div>
      </div>

      <p className="text-sm leading-6 text-[color:var(--text-secondary)]">{row.thesisLine}</p>
      <p className="text-sm leading-6 text-[color:var(--text-secondary)]">{row.decisionLine}</p>

      <TrustBadge flags={row.statusFlags} awaitingRun={row.awaitingRun} />

      {row.warningFlags.length ? (
        <div className="flex flex-wrap gap-2">
          {row.warningFlags.slice(0, 3).map((flag) => (
            <StatusChip key={flag.label} tone={flag.tone}>
              {flag.label}
            </StatusChip>
          ))}
        </div>
      ) : null}

      <div className="flex flex-wrap gap-2">
        <Link href={row.href} className="button-primary">
          Open research
        </Link>
      </div>
    </article>
  )
}
