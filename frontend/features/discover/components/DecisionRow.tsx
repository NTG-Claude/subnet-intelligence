'use client'

import Link from 'next/link'

import SignalBar from '@/components/ui/SignalBar'
import StatusChip from '@/components/ui/StatusChip'
import TrustBadge from '@/components/ui/TrustBadge'
import { cn } from '@/lib/formatting'
import { UniverseRowViewModel } from '@/lib/view-models/research'

export default function DecisionRow({
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
    <tr
      className={cn(
        'border-t border-[color:var(--border-subtle)] align-top',
        focused && 'bg-[color:rgba(19,32,44,0.52)]',
      )}
      tabIndex={0}
      onMouseEnter={onFocus}
      onFocus={onFocus}
    >
      <td className="px-3 py-4">
        <button
          type="button"
          aria-pressed={selected}
          onClick={() => onToggleCompare(row.id)}
          className={cn(
            'flex min-h-11 min-w-11 items-center justify-center rounded-[var(--radius-md)] border text-sm',
            selected
              ? 'border-[color:var(--mispricing-border)] bg-[color:var(--mispricing-surface)] text-[color:var(--mispricing-strong)]'
              : 'border-[color:var(--border-subtle)] bg-[color:var(--surface-2)] text-[color:var(--text-secondary)]',
          )}
        >
          {selected ? 'x' : '+'}
        </button>
      </td>
      <td className="px-3 py-4">
        <div className="text-lg font-semibold text-[color:var(--text-primary)]">{row.rankLabel}</div>
        <div className="text-xs text-[color:var(--text-tertiary)]">{row.percentileLabel}</div>
      </td>
      <td className="px-3 py-4">
        <div className="flex flex-wrap items-center gap-2">
          <StatusChip tone="neutral">{row.netuidLabel}</StatusChip>
          <StatusChip tone={row.modelLabelTone}>{row.modelLabel}</StatusChip>
        </div>
        <Link href={row.href} className="mt-3 block text-lg font-semibold tracking-tight text-[color:var(--text-primary)] hover:text-[color:var(--mispricing-strong)]">
          {row.name}
        </Link>
        <p className="mt-2 max-w-md text-sm leading-6 text-[color:var(--text-secondary)]">{row.thesisLine}</p>
      </td>
      <td className="px-3 py-4">
        <p className="text-sm leading-6 text-[color:var(--text-secondary)]">{row.decisionLine}</p>
      </td>
      {row.signals.map((signal) => (
        <td key={signal.key} className="min-w-[140px] px-3 py-4">
          <SignalBar signal={signal} compact />
        </td>
      ))}
      <td className="px-3 py-4">
        <TrustBadge flags={row.statusFlags} awaitingRun={row.awaitingRun} />
      </td>
      <td className="px-3 py-4">
        <div className="text-sm text-[color:var(--text-secondary)]">{row.updatedLabel}</div>
      </td>
      <td className="px-3 py-4">
        <div className="flex flex-col gap-2">
          <Link href={row.href} className="button-secondary">
            Research
          </Link>
          <button type="button" onClick={() => onToggleCompare(row.id)} className="button-secondary">
            {selected ? 'Remove' : 'Compare'}
          </button>
        </div>
      </td>
    </tr>
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
      className={cn(
        'surface-panel space-y-4 p-4',
        focused && 'ring-1 ring-[color:var(--mispricing-border)]',
      )}
      tabIndex={0}
      onFocus={onFocus}
    >
      <div className="flex items-start justify-between gap-3">
        <div>
          <div className="flex flex-wrap items-center gap-2">
            <StatusChip tone="neutral">{row.rankLabel}</StatusChip>
            <StatusChip tone="neutral">{row.netuidLabel}</StatusChip>
          </div>
          <Link href={row.href} className="mt-3 block text-xl font-semibold tracking-tight text-[color:var(--text-primary)]">
            {row.name}
          </Link>
          <p className="mt-2 text-sm leading-6 text-[color:var(--text-secondary)]">{row.thesisLine}</p>
        </div>
        <button
          type="button"
          onClick={() => onToggleCompare(row.id)}
          className={cn(
            'min-h-11 rounded-[var(--radius-md)] border px-4 text-sm',
            selected
              ? 'border-[color:var(--mispricing-border)] bg-[color:var(--mispricing-surface)] text-[color:var(--mispricing-strong)]'
              : 'border-[color:var(--border-subtle)] bg-[color:var(--surface-2)] text-[color:var(--text-secondary)]',
          )}
        >
          {selected ? 'Selected' : 'Compare'}
        </button>
      </div>

      <div className="grid gap-3 sm:grid-cols-2">
        {row.signals.map((signal) => (
          <SignalBar key={signal.key} signal={signal} compact />
        ))}
      </div>

      <TrustBadge flags={row.statusFlags} awaitingRun={row.awaitingRun} />

      <div className="flex items-center justify-between gap-3 text-sm text-[color:var(--text-secondary)]">
        <span>{row.updatedLabel}</span>
        <Link href={row.href} className="button-secondary">
          Open research
        </Link>
      </div>
    </article>
  )
}
