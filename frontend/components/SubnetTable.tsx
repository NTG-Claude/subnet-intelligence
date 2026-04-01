'use client'

import Link from 'next/link'
import { useMemo, useState } from 'react'

import { SubnetSummary } from '@/lib/api'
import { UNIVERSE_LENSES, applyUniverseLens, toUniverseRow } from '@/lib/view-models/research'
import { HintBadge, SignalPill, StatusBadge, cn } from '@/components/shared/research-ui'

interface Props {
  subnets: SubnetSummary[]
  pageSize?: number
}

function queryMatches(subnet: SubnetSummary, query: string): boolean {
  const q = query.toLowerCase()
  return (
    (subnet.name ?? '').toLowerCase().includes(q) ||
    String(subnet.netuid).includes(q) ||
    (subnet.label ?? '').toLowerCase().includes(q) ||
    (subnet.thesis ?? '').toLowerCase().includes(q)
  )
}

export default function SubnetTable({ subnets, pageSize = 24 }: Props) {
  const [search, setSearch] = useState('')
  const [view, setView] = useState('high-mispricing-confidence')
  const [hideLowConfidence, setHideLowConfidence] = useState(false)
  const [showTelemetryRepairOnly, setShowTelemetryRepairOnly] = useState(false)
  const [excludeFragile, setExcludeFragile] = useState(false)
  const [compareIds, setCompareIds] = useState<number[]>([])
  const [page, setPage] = useState(0)

  const filtered = useMemo(() => {
    let next = applyUniverseLens(subnets, view)

    if (search.trim()) {
      next = next.filter((subnet) => queryMatches(subnet, search))
    }
    if (hideLowConfidence) {
      next = next.filter((subnet) => (subnet.primary_outputs?.signal_confidence ?? 0) >= 50)
    }
    if (showTelemetryRepairOnly) {
      next = next.filter((subnet) => {
        const conditioning = subnet.analysis_preview?.conditioning
        return Boolean((conditioning?.visibility?.reconstructed?.length ?? 0) || (conditioning?.visibility?.discarded?.length ?? 0))
      })
    }
    if (excludeFragile) {
      next = next.filter((subnet) => (subnet.primary_outputs?.fragility_risk ?? 0) <= 55)
    }

    return next
  }, [excludeFragile, hideLowConfidence, search, showTelemetryRepairOnly, subnets, view])

  const rows = useMemo(() => filtered.map(toUniverseRow), [filtered])
  const totalPages = Math.max(1, Math.ceil(rows.length / pageSize))
  const pageRows = rows.slice(page * pageSize, (page + 1) * pageSize)
  const currentLens = UNIVERSE_LENSES.find((lens) => lens.id === view) ?? UNIVERSE_LENSES[0]

  const toggleCompare = (netuid: number) => {
    setCompareIds((current) => {
      if (current.includes(netuid)) {
        return current.filter((id) => id !== netuid)
      }
      if (current.length >= 4) {
        return [...current.slice(1), netuid]
      }
      return [...current, netuid]
    })
  }

  return (
    <div className="space-y-5">
      <div className="grid gap-4 lg:grid-cols-[1.35fr_0.65fr]">
        <div className="rounded-3xl border border-white/10 bg-black/20 p-4">
          <div className="flex flex-wrap gap-2">
            {UNIVERSE_LENSES.map((lens) => (
              <button
                key={lens.id}
                onClick={() => {
                  setView(lens.id)
                  setPage(0)
                }}
                className={cn(
                  'rounded-full border px-3 py-2 text-xs font-medium transition-colors',
                  view === lens.id
                    ? 'border-white/20 bg-white/10 text-stone-100'
                    : 'border-white/10 bg-white/[0.03] text-stone-400 hover:border-white/20 hover:text-stone-200',
                )}
              >
                {lens.title}
              </button>
            ))}
          </div>
          <p className="mt-3 max-w-3xl text-sm leading-6 text-stone-400">{currentLens.description}</p>
        </div>

        <div className="rounded-3xl border border-white/10 bg-black/20 p-4">
          <div className="text-[11px] uppercase tracking-[0.24em] text-stone-500">Filter Chips</div>
          <div className="mt-3 flex flex-wrap gap-2">
            <button
              onClick={() => {
                setHideLowConfidence((value) => !value)
                setPage(0)
              }}
              className={cn(
                'rounded-full border px-3 py-1.5 text-xs transition-colors',
                hideLowConfidence ? 'border-violet-500/30 bg-violet-500/10 text-violet-200' : 'border-white/10 bg-white/[0.03] text-stone-400',
              )}
            >
              Hide low confidence
            </button>
            <button
              onClick={() => {
                setShowTelemetryRepairOnly((value) => !value)
                setPage(0)
              }}
              className={cn(
                'rounded-full border px-3 py-1.5 text-xs transition-colors',
                showTelemetryRepairOnly ? 'border-amber-500/30 bg-amber-500/10 text-amber-200' : 'border-white/10 bg-white/[0.03] text-stone-400',
              )}
            >
              Telemetry repair cases
            </button>
            <button
              onClick={() => {
                setExcludeFragile((value) => !value)
                setPage(0)
              }}
              className={cn(
                'rounded-full border px-3 py-1.5 text-xs transition-colors',
                excludeFragile ? 'border-rose-500/30 bg-rose-500/10 text-rose-200' : 'border-white/10 bg-white/[0.03] text-stone-400',
              )}
            >
              Exclude fragile setups
            </button>
          </div>
        </div>
      </div>

      <div className="flex flex-col gap-3 rounded-3xl border border-white/10 bg-black/20 p-4 lg:flex-row lg:items-center lg:justify-between">
        <div className="space-y-1">
          <div className="text-[11px] uppercase tracking-[0.24em] text-stone-500">Search</div>
          <p className="text-sm text-stone-400">Filter by subnet name, thesis wording, label, or netuid.</p>
        </div>
        <input
          type="search"
          placeholder="Search subnet, thesis, label, netuid..."
          value={search}
          onChange={(event) => {
            setSearch(event.target.value)
            setPage(0)
          }}
          className="w-full rounded-2xl border border-white/10 bg-white/[0.03] px-4 py-3 text-sm text-stone-100 outline-none ring-0 placeholder:text-stone-500 focus:border-white/20 lg:max-w-md"
        />
      </div>

      <div className="space-y-4">
        {pageRows.length === 0 ? (
          <div className="rounded-3xl border border-dashed border-white/10 bg-black/20 p-10 text-center text-sm text-stone-500">
            {currentLens.emptyMessage}
          </div>
        ) : (
          pageRows.map((row) => {
            const selected = compareIds.includes(row.id)
            return (
              <article key={row.id} className="rounded-[1.75rem] border border-white/10 bg-white/[0.035] p-4 sm:p-5">
                <div className="flex flex-col gap-4 xl:flex-row xl:items-start xl:justify-between">
                  <div className="min-w-0 flex-1 space-y-4">
                    <div className="flex flex-wrap items-center gap-2">
                      <StatusBadge tone="neutral">{row.netuidLabel}</StatusBadge>
                      <StatusBadge tone={row.awaitingRun ? 'warning' : 'neutral'}>{row.label}</StatusBadge>
                      <StatusBadge tone={row.awaitingRun ? 'warning' : row.trustLabel.includes('Clean') ? 'confidence' : 'warning'}>
                        {row.trustLabel}
                      </StatusBadge>
                    </div>

                    <div className="space-y-2">
                      <div className="flex flex-wrap items-end gap-3">
                        <Link href={row.href} className="text-2xl font-semibold tracking-tight text-stone-50 transition-colors hover:text-sky-200">
                          {row.name}
                        </Link>
                        <div className="text-sm text-stone-500">{row.decisionLine}</div>
                      </div>
                      <p className="max-w-4xl text-sm leading-6 text-stone-300">{row.thesisLine}</p>
                    </div>

                    <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
                      {row.signals.map((signal) => (
                        <SignalPill key={signal.key} signal={signal} />
                      ))}
                    </div>

                    <div className="grid gap-3 lg:grid-cols-3">
                      <div className="rounded-2xl border border-white/10 bg-black/20 p-4">
                        <div className="text-[11px] uppercase tracking-[0.24em] text-stone-500">Why it is interesting</div>
                        <div className="mt-3 flex flex-wrap gap-2">
                          {row.positives.length ? row.positives.map((item) => <HintBadge key={item.label} label={item.label} tone={item.tone} />) : <span className="text-sm text-stone-500">No explicit positive drivers surfaced in the summary feed.</span>}
                        </div>
                      </div>
                      <div className="rounded-2xl border border-white/10 bg-black/20 p-4">
                        <div className="text-[11px] uppercase tracking-[0.24em] text-stone-500">What can break it</div>
                        <div className="mt-3 flex flex-wrap gap-2">
                          {row.negatives.length ? row.negatives.map((item) => <HintBadge key={item.label} label={item.label} tone={item.tone} />) : <span className="text-sm text-stone-500">Open the memo for full failure conditions.</span>}
                        </div>
                      </div>
                      <div className="rounded-2xl border border-white/10 bg-black/20 p-4">
                        <div className="text-[11px] uppercase tracking-[0.24em] text-stone-500">Confidence and data trust</div>
                        <div className="mt-3 flex flex-wrap gap-2">
                          {row.warnings.length ? row.warnings.map((item) => <HintBadge key={item.label} label={item.label} tone={item.tone} />) : <span className="text-sm text-stone-500">No large trust warning surfaced in the summary view.</span>}
                        </div>
                      </div>
                    </div>
                  </div>

                  <div className="w-full xl:max-w-[220px]">
                    <div className="rounded-2xl border border-white/10 bg-black/20 p-4">
                      <div className="space-y-3">
                        {row.metrics.map((metric) => (
                          <div key={metric.label} className="flex items-center justify-between gap-3 text-sm">
                            <span className="text-stone-500">{metric.label}</span>
                            <span className="font-medium text-stone-100">{metric.value}</span>
                          </div>
                        ))}
                      </div>
                      <div className="mt-4 flex flex-col gap-2">
                        <Link href={row.href} className="rounded-2xl border border-white/10 bg-white/[0.05] px-3 py-2 text-center text-sm text-stone-100 transition-colors hover:bg-white/[0.09]">
                          Open memo
                        </Link>
                        <button
                          onClick={() => toggleCompare(row.id)}
                          className={cn(
                            'rounded-2xl border px-3 py-2 text-sm transition-colors',
                            selected
                              ? 'border-sky-500/30 bg-sky-500/10 text-sky-200'
                              : 'border-white/10 bg-white/[0.03] text-stone-300 hover:bg-white/[0.08]',
                          )}
                        >
                          {selected ? 'Selected for compare' : row.compareLabel}
                        </button>
                      </div>
                    </div>
                  </div>
                </div>
              </article>
            )
          })
        )}
      </div>

      <div className="flex flex-col gap-3 rounded-3xl border border-white/10 bg-black/20 p-4 sm:flex-row sm:items-center sm:justify-between">
        <div className="text-sm text-stone-400">
          {rows.length} result{rows.length === 1 ? '' : 's'}
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={() => setPage((current) => Math.max(0, current - 1))}
            disabled={page === 0}
            className="rounded-2xl border border-white/10 bg-white/[0.03] px-3 py-2 text-sm text-stone-300 transition-colors hover:bg-white/[0.08] disabled:cursor-not-allowed disabled:opacity-40"
          >
            Prev
          </button>
          <div className="px-3 py-2 text-sm text-stone-400">
            {Math.min(page + 1, totalPages)} / {totalPages}
          </div>
          <button
            onClick={() => setPage((current) => Math.min(totalPages - 1, current + 1))}
            disabled={page >= totalPages - 1}
            className="rounded-2xl border border-white/10 bg-white/[0.03] px-3 py-2 text-sm text-stone-300 transition-colors hover:bg-white/[0.08] disabled:cursor-not-allowed disabled:opacity-40"
          >
            Next
          </button>
        </div>
      </div>

      {compareIds.length > 0 ? (
        <div className="sticky bottom-4 z-30 rounded-3xl border border-sky-500/20 bg-stone-950/95 p-4 shadow-[0_20px_80px_rgba(0,0,0,0.45)] backdrop-blur">
          <div className="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
            <div>
              <div className="text-[11px] uppercase tracking-[0.24em] text-sky-300">Compare Tray</div>
              <div className="mt-1 text-sm text-stone-300">
                {compareIds.length} subnet{compareIds.length === 1 ? '' : 's'} selected. Compare up to four across signals, drivers, confidence, and stress.
              </div>
            </div>
            <div className="flex flex-wrap gap-2">
              {compareIds.map((id) => (
                <StatusBadge key={id} tone="mispricing">
                  SN{id}
                </StatusBadge>
              ))}
              <Link href={`/compare?ids=${compareIds.join(',')}`} className="rounded-2xl border border-sky-500/20 bg-sky-500/10 px-4 py-2 text-sm text-sky-200 transition-colors hover:bg-sky-500/20">
                Open compare
              </Link>
            </div>
          </div>
        </div>
      ) : null}
    </div>
  )
}
