'use client'

import Link from 'next/link'
import { useMemo, useState } from 'react'

import { SubnetSummary } from '@/lib/api'
import {
  UNIVERSE_LENSES,
  UNIVERSE_SORTS,
  UniverseSortId,
  applyUniverseLens,
  sortUniverseRows,
  toUniverseRow,
} from '@/lib/view-models/research'
import PrimarySignalBoard from '@/components/PrimarySignalBoard'
import { MetricGrid, ResearchPanel, StatusBadge, cn } from '@/components/shared/research-ui'
import ResearchList from '@/components/universe/ResearchList'

interface Props {
  subnets: SubnetSummary[]
  lastRun: string | null
  trackedUniverse: number
  focusedUniverse: number
  awaitingRunCount: number
  lowConfidenceCount: number
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

function isStale(iso: string | null): boolean {
  if (!iso) return false
  const parsed = Date.parse(iso)
  if (!Number.isFinite(parsed)) return false
  return Date.now() - parsed > 36 * 60 * 60 * 1000
}

export default function UniverseWorkspace({
  subnets,
  lastRun,
  trackedUniverse,
  focusedUniverse,
  awaitingRunCount,
  lowConfidenceCount,
}: Props) {
  const [search, setSearch] = useState('')
  const [lensId, setLensId] = useState('high-mispricing-confidence')
  const [sortId, setSortId] = useState<UniverseSortId>('rank')
  const [telemetryOnly, setTelemetryOnly] = useState(false)
  const [selectedOnly, setSelectedOnly] = useState(false)
  const [excludeFragile, setExcludeFragile] = useState(false)
  const [compareIds, setCompareIds] = useState<number[]>([])
  const [page, setPage] = useState(0)
  const pageSize = 18

  const filteredSubnets = useMemo(() => {
    let next = applyUniverseLens(subnets, lensId)

    if (search.trim()) {
      next = next.filter((subnet) => queryMatches(subnet, search))
    }

    if (telemetryOnly) {
      next = next.filter((subnet) => {
        const visibility = subnet.analysis_preview?.conditioning?.visibility
        return Boolean((visibility?.reconstructed?.length ?? 0) || (visibility?.discarded?.length ?? 0))
      })
    }

    if (excludeFragile) {
      next = next.filter((subnet) => (subnet.primary_outputs?.fragility_risk ?? 0) <= 60)
    }

    if (selectedOnly) {
      next = next.filter((subnet) => compareIds.includes(subnet.netuid))
    }

    return next
  }, [compareIds, excludeFragile, lensId, search, selectedOnly, subnets, telemetryOnly])

  const rows = useMemo(() => sortUniverseRows(filteredSubnets.map(toUniverseRow), sortId), [filteredSubnets, sortId])
  const totalPages = Math.max(1, Math.ceil(rows.length / pageSize))
  const currentPage = Math.min(page, totalPages - 1)
  const pageRows = rows.slice(currentPage * pageSize, (currentPage + 1) * pageSize)
  const currentLens = UNIVERSE_LENSES.find((lens) => lens.id === lensId) ?? UNIVERSE_LENSES[0]

  const resetAll = () => {
    setSearch('')
    setLensId('high-mispricing-confidence')
    setSortId('rank')
    setTelemetryOnly(false)
    setSelectedOnly(false)
    setExcludeFragile(false)
    setPage(0)
  }

  const toggleCompare = (netuid: number) => {
    setCompareIds((current) => {
      if (current.includes(netuid)) return current.filter((id) => id !== netuid)
      if (current.length >= 4) return [...current.slice(1), netuid]
      return [...current, netuid]
    })
  }

  const compareNames = useMemo(
    () =>
      compareIds.map((id) => {
        const subnet = subnets.find((item) => item.netuid === id)
        return subnet?.name?.trim() || `SN${id}`
      }),
    [compareIds, subnets],
  )

  return (
    <div className="space-y-6">
      <section className="rounded-[1.9rem] border border-white/10 bg-[#10151b] p-4 sm:p-5">
        <div className="flex flex-col gap-4 xl:flex-row xl:items-end xl:justify-between">
          <div className="space-y-3">
            <div className="flex flex-wrap items-center gap-2">
              <StatusBadge tone="neutral">Universe workspace</StatusBadge>
              <StatusBadge tone={lastRun ? (isStale(lastRun) ? 'warning' : 'confidence') : 'warning'}>
                {lastRun ? (isStale(lastRun) ? 'Stale run' : 'Run live') : 'Awaiting run'}
              </StatusBadge>
            </div>
            <div>
              <h1 className="text-2xl font-semibold tracking-tight text-stone-50 sm:text-3xl">V2-native research workspace</h1>
              <p className="mt-2 max-w-4xl text-sm leading-6 text-stone-400">
                Screen first, then open the memo. The universe list is the primary surface; the lens panels below are only secondary shortcuts for idea discovery.
              </p>
            </div>
          </div>

          <div className="grid gap-3 sm:grid-cols-[minmax(0,1fr)_auto] xl:min-w-[440px]">
            <input
              type="search"
              value={search}
              onChange={(event) => {
                setSearch(event.target.value)
                setPage(0)
              }}
              placeholder="Search subnet, thesis, label, netuid..."
              className="w-full rounded-2xl border border-white/10 bg-stone-950 px-4 py-3 text-sm text-stone-100 outline-none placeholder:text-stone-500 focus:border-white/20"
            />
            <button
              onClick={resetAll}
              className="rounded-2xl border border-white/10 bg-white/[0.04] px-4 py-3 text-sm text-stone-300 transition-colors hover:bg-white/[0.08]"
            >
              Clear filters
            </button>
          </div>
        </div>

        <div className="mt-4">
          <MetricGrid
            dense
            items={[
              {
                label: 'Last run',
                value: lastRun
                  ? new Date(lastRun).toLocaleString('en-US', {
                      month: 'short',
                      day: 'numeric',
                      hour: '2-digit',
                      minute: '2-digit',
                      timeZone: 'UTC',
                      timeZoneName: 'short',
                    })
                  : 'No run',
              },
              { label: 'Tracked subnets', value: String(trackedUniverse) },
              { label: 'Focused universe', value: String(focusedUniverse) },
              { label: 'Awaiting run', value: String(awaitingRunCount), tone: awaitingRunCount ? 'warning' : 'neutral' },
              { label: 'Low confidence', value: String(lowConfidenceCount), tone: lowConfidenceCount ? 'confidence' : 'neutral' },
            ]}
          />
        </div>
      </section>

      <ResearchPanel
        title="Filters / Saved Views / Quick Lenses"
        subtitle="Use the saved views to jump into a research slice, then tighten the list with workflow chips and sorting."
        className="bg-[#10151b]"
      >
        <div className="space-y-4">
          <div className="flex flex-wrap gap-2">
            {UNIVERSE_LENSES.map((lens) => (
              <button
                key={lens.id}
                onClick={() => {
                  setLensId(lens.id)
                  setPage(0)
                }}
                className={cn(
                  'rounded-full border px-3 py-2 text-xs font-medium transition-colors',
                  lensId === lens.id
                    ? 'border-white/20 bg-white/[0.08] text-stone-100'
                    : 'border-white/10 bg-stone-950 text-stone-400 hover:border-white/20 hover:text-stone-200',
                )}
              >
                {lens.title}
              </button>
            ))}
          </div>

          <div className="grid gap-4 xl:grid-cols-[minmax(0,1fr)_auto]">
            <div className="space-y-3">
              <p className="text-sm leading-6 text-stone-400">{currentLens.description}</p>
              <div className="flex flex-wrap gap-2">
                <button
                  onClick={() => {
                    setTelemetryOnly((value) => !value)
                    setPage(0)
                  }}
                  className={cn(
                    'rounded-full border px-3 py-1.5 text-xs transition-colors',
                    telemetryOnly ? 'border-amber-500/30 bg-amber-500/10 text-amber-200' : 'border-white/10 bg-stone-950 text-stone-400',
                  )}
                >
                  Telemetry repairs only
                </button>
                <button
                  onClick={() => {
                    setExcludeFragile((value) => !value)
                    setPage(0)
                  }}
                  className={cn(
                    'rounded-full border px-3 py-1.5 text-xs transition-colors',
                    excludeFragile ? 'border-rose-500/30 bg-rose-500/10 text-rose-200' : 'border-white/10 bg-stone-950 text-stone-400',
                  )}
                >
                  Exclude fragile setups
                </button>
                <button
                  onClick={() => {
                    setSelectedOnly((value) => !value)
                    setPage(0)
                  }}
                  className={cn(
                    'rounded-full border px-3 py-1.5 text-xs transition-colors',
                    selectedOnly ? 'border-sky-500/30 bg-sky-500/10 text-sky-200' : 'border-white/10 bg-stone-950 text-stone-400',
                  )}
                >
                  Compare tray only
                </button>
              </div>
            </div>

            <div className="flex flex-wrap gap-2 xl:justify-end">
              {UNIVERSE_SORTS.map((sort) => (
                <button
                  key={sort.id}
                  onClick={() => setSortId(sort.id)}
                  className={cn(
                    'rounded-full border px-3 py-1.5 text-xs transition-colors',
                    sortId === sort.id
                      ? 'border-violet-500/30 bg-violet-500/10 text-violet-200'
                      : 'border-white/10 bg-stone-950 text-stone-400 hover:border-white/20 hover:text-stone-200',
                  )}
                >
                  Sort: {sort.label}
                </button>
              ))}
            </div>
          </div>
        </div>
      </ResearchPanel>

      <ResearchPanel
        title="Main Result List"
        subtitle="Each row should answer the same workflow question: why is this interesting, what breaks it, and how much should we trust the evidence."
        className="bg-[#10151b]"
      >
        <ResearchList
          rows={pageRows}
          currentLensTitle={currentLens.title}
          emptyMessage={currentLens.emptyMessage}
          compareIds={compareIds}
          onToggleCompare={toggleCompare}
        />

        <div className="mt-4 flex flex-col gap-3 rounded-2xl border border-white/10 bg-stone-950 p-4 sm:flex-row sm:items-center sm:justify-between">
          <div className="text-sm text-stone-400">
            {rows.length} result{rows.length === 1 ? '' : 's'}
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={() => setPage((current) => Math.max(0, current - 1))}
              disabled={currentPage === 0}
              className="rounded-2xl border border-white/10 bg-white/[0.04] px-3 py-2 text-sm text-stone-300 transition-colors hover:bg-white/[0.08] disabled:cursor-not-allowed disabled:opacity-40"
            >
              Prev
            </button>
            <div className="px-3 py-2 text-sm text-stone-400">
              {currentPage + 1} / {totalPages}
            </div>
            <button
              onClick={() => setPage((current) => Math.min(totalPages - 1, current + 1))}
              disabled={currentPage >= totalPages - 1}
              className="rounded-2xl border border-white/10 bg-white/[0.04] px-3 py-2 text-sm text-stone-300 transition-colors hover:bg-white/[0.08] disabled:cursor-not-allowed disabled:opacity-40"
            >
              Next
            </button>
          </div>
        </div>
      </ResearchPanel>

      <ResearchPanel
        title="Secondary Insight Area"
        subtitle="These lens boards help you spot candidates fast, but they should always feed back into the memo and compare workflow."
        className="bg-[#10151b]"
      >
        <PrimarySignalBoard subnets={filteredSubnets.filter((subnet) => subnet.primary_outputs)} />
      </ResearchPanel>

      {compareIds.length > 0 ? (
        <div className="sticky bottom-4 z-30 rounded-3xl border border-sky-500/20 bg-stone-950/95 p-4 shadow-[0_16px_48px_rgba(0,0,0,0.45)] backdrop-blur">
          <div className="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
            <div>
              <div className="text-[11px] uppercase tracking-[0.24em] text-sky-300">Compare tray</div>
              <div className="mt-1 text-sm text-stone-300">
                {compareIds.length} subnet{compareIds.length === 1 ? '' : 's'} selected for side-by-side review across signals, explainability, trust, and stress.
              </div>
            </div>
            <div className="flex flex-wrap items-center gap-2">
              {compareNames.map((name, index) => (
                <StatusBadge key={`${name}-${index}`} tone="mispricing">
                  {name}
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
