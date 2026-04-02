'use client'

import Link from 'next/link'
import { useState } from 'react'

import { UniverseRowViewModel } from '@/lib/view-models/research'
import {
  ChevronIcon,
  HintBadge,
  SignalProfileSVG,
  SparkSignalBar,
  StatusBadge,
  cn,
} from '@/components/shared/research-ui'

interface Props {
  rows: UniverseRowViewModel[]
  currentLensTitle: string
  emptyMessage: string
  compareIds: number[]
  onToggleCompare: (netuid: number) => void
}

function ResearchLine({
  title,
  body,
  items,
}: {
  title: string
  body: string
  items: { label: string; tone: 'quality' | 'mispricing' | 'fragility' | 'confidence' | 'warning' | 'neutral' }[]
}) {
  return (
    <div className="rounded-2xl border border-white/10 bg-stone-950 p-3">
      <div className="text-[11px] uppercase tracking-[0.24em] text-stone-500">{title}</div>
      <p className="mt-2 text-sm leading-6 text-stone-300">{body}</p>
      <div className="mt-3 flex flex-wrap gap-2">
        {items.length ? items.map((item) => <HintBadge key={item.label} label={item.label} tone={item.tone} />) : <span className="text-xs text-stone-500">No surfaced detail.</span>}
      </div>
    </div>
  )
}

function CompactRow({
  row,
  expanded,
  selected,
  onToggleExpand,
  onToggleCompare,
}: {
  row: UniverseRowViewModel
  expanded: boolean
  selected: boolean
  onToggleExpand: () => void
  onToggleCompare: () => void
}) {
  return (
    <article
      className={cn(
        'rounded-2xl border bg-[#11161c] transition-colors',
        expanded ? 'border-white/15' : 'border-white/10 hover:border-white/[0.14]',
      )}
    >
      {/* Compact summary row */}
      <div
        className="flex items-center gap-3 px-4 py-3 cursor-pointer sm:gap-4"
        onClick={onToggleExpand}
      >
        {/* Left: identity */}
        <div className="flex items-center gap-3 min-w-0 flex-1">
          <span className="shrink-0 rounded-lg bg-white/[0.06] px-2 py-0.5 text-[11px] font-medium text-stone-400">
            {row.netuidLabel}
          </span>

          <SignalProfileSVG signals={row.signals} />

          <div className="min-w-0 flex-1">
            <div className="flex items-center gap-2">
              <Link
                href={row.href}
                onClick={(e) => e.stopPropagation()}
                className="truncate text-sm font-semibold text-stone-100 transition-colors hover:text-sky-200"
              >
                {row.name}
              </Link>
              {row.statusFlags.slice(0, 1).map((flag) => (
                <span
                  key={flag.label}
                  className={cn(
                    'hidden shrink-0 rounded-full border px-2 py-0.5 text-[10px] font-medium uppercase tracking-[0.14em] sm:inline-flex',
                    flag.tone === 'warning'
                      ? 'border-amber-500/20 bg-amber-500/10 text-amber-300'
                      : flag.tone === 'confidence'
                        ? 'border-violet-500/20 bg-violet-500/10 text-violet-300'
                        : 'border-white/10 bg-white/[0.03] text-stone-400',
                  )}
                >
                  {flag.label}
                </span>
              ))}
            </div>
            <p className="mt-0.5 truncate text-xs text-stone-500 hidden sm:block">{row.thesisLine}</p>
          </div>
        </div>

        {/* Center: signal bars (desktop) */}
        <div className="hidden lg:flex items-center gap-3">
          {row.signals.map((signal) => (
            <SparkSignalBar key={signal.key} signal={signal} />
          ))}
        </div>

        {/* Right: rank + actions */}
        <div className="flex items-center gap-2 shrink-0">
          <span className="hidden sm:block text-xs font-medium text-stone-400 w-10 text-right tabular-nums">
            {row.rankLabel}
          </span>

          <button
            onClick={(e) => {
              e.stopPropagation()
              onToggleCompare()
            }}
            className={cn(
              'focus-ring shrink-0 flex h-7 w-7 items-center justify-center rounded-lg border transition-colors',
              selected
                ? 'border-sky-500/30 bg-sky-500/15 text-sky-300'
                : 'border-white/10 bg-transparent text-stone-500 hover:text-stone-300 hover:border-white/20',
            )}
            title={selected ? 'Remove from compare' : 'Add to compare'}
          >
            <svg width="14" height="14" viewBox="0 0 14 14" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round">
              {selected ? (
                <>
                  <path d="M3.5 7L6 9.5L10.5 4.5" />
                </>
              ) : (
                <>
                  <path d="M7 3.5V10.5" />
                  <path d="M3.5 7H10.5" />
                </>
              )}
            </svg>
          </button>

          <ChevronIcon expanded={expanded} className="text-stone-500 shrink-0" />
        </div>
      </div>

      {/* Mobile signal bars (below summary, always visible) */}
      <div className="flex items-center gap-3 px-4 pb-2 lg:hidden flex-wrap">
        {row.signals.map((signal) => (
          <SparkSignalBar key={signal.key} signal={signal} />
        ))}
      </div>

      {/* Expandable detail section */}
      <div className="expandable-grid" data-expanded={expanded}>
        <div>
          <div className="border-t border-white/[0.06] px-4 py-4 space-y-3">
            {/* Decision line */}
            <p className="text-sm leading-6 text-stone-400">{row.decisionLine}</p>

            {/* Analysis cards */}
            <div className="grid gap-3 md:grid-cols-2">
              <ResearchLine title="Opportunity" body={row.opportunityRead} items={row.opportunityNotes} />
              <ResearchLine title="Quality" body={row.qualityRead} items={[]} />
              <ResearchLine title="Fragility" body={row.fragilityRead} items={row.riskNotes} />
              <ResearchLine title="Confidence" body={row.confidenceRead} items={row.uncertaintyNotes} />
            </div>

            {/* Footer: metadata + actions */}
            <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between pt-1">
              <div className="flex flex-wrap items-center gap-3 text-xs text-stone-500">
                <span>Rank {row.rankLabel}</span>
                <span className="text-stone-700">·</span>
                <span>{row.percentileLabel} percentile</span>
                <span className="text-stone-700">·</span>
                <span>Trust: {row.trustLabel}</span>
                <span className="text-stone-700">·</span>
                <span>{row.updatedLabel}</span>
              </div>
              <Link
                href={row.href}
                className="focus-ring inline-flex items-center justify-center rounded-xl border border-white/10 bg-white/[0.04] px-4 py-2 text-sm text-stone-200 transition-colors hover:bg-white/[0.08]"
              >
                Open memo
              </Link>
            </div>
          </div>
        </div>
      </div>
    </article>
  )
}

export default function ResearchList({ rows, currentLensTitle, emptyMessage, compareIds, onToggleCompare }: Props) {
  const [expandedIds, setExpandedIds] = useState<Set<number>>(new Set())

  const toggleExpand = (id: number) => {
    setExpandedIds((prev) => {
      const next = new Set(prev)
      if (next.has(id)) next.delete(id)
      else next.add(id)
      return next
    })
  }

  return (
    <div className="space-y-2">
      {rows.length === 0 ? (
        <div className="rounded-2xl border border-dashed border-white/10 bg-stone-950 p-10 text-center">
          <div className="text-[11px] uppercase tracking-[0.24em] text-stone-500">{currentLensTitle}</div>
          <p className="mt-3 text-sm leading-6 text-stone-400">{emptyMessage}</p>
        </div>
      ) : null}

      {rows.map((row, index) => (
        <div key={row.id} className="row-enter" style={{ animationDelay: `${index * 25}ms` }}>
          <CompactRow
            row={row}
            expanded={expandedIds.has(row.id)}
            selected={compareIds.includes(row.id)}
            onToggleExpand={() => toggleExpand(row.id)}
            onToggleCompare={() => onToggleCompare(row.id)}
          />
        </div>
      ))}
    </div>
  )
}
