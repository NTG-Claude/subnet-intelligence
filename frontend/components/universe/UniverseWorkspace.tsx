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
import { DropdownPill, MetricGrid, ResearchPanel, StatusBadge, cn } from '@/components/shared/research-ui'
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

function PageNumbers({
  currentPage,
  totalPages,
  onPageChange,
}: {
  currentPage: number
  totalPages: number
  onPageChange: (page: number) => void
}) {
  const pages: (number | 'ellipsis')[] = []

  if (totalPages <= 7) {
    for (let i = 0; i < totalPages; i++) pages.push(i)
  } else {
    pages.push(0)
    if (currentPage > 2) pages.push('ellipsis')
    for (let i = Math.max(1, currentPage - 1); i <= Math.min(totalPages - 2, currentPage + 1); i++) {
      pages.push(i)
    }
    if (currentPage < totalPages - 3) pages.push('ellipsis')
    pages.push(totalPages - 1)
  }

  return (
    <div className="flex items-center gap-1">
      {pages.map((p, idx) =>
        p === 'ellipsis' ? (
          <span key={`e${idx}`} className="px-1.5 text-xs text-stone-600">
            ...
          </span>
        ) : (
          <button
            key={p}
            onClick={() => onPageChange(p)}
            className={cn(
              'focus-ring h-8 min-w-[2rem] rounded-lg px-2 text-xs font-medium transition-colors',
              p === currentPage
                ? 'bg-white/[0.08] text-stone-100'
                : 'text-stone-500 hover:bg-white/[0.04] hover:text-stone-300',
            )}
          >
            {p + 1}
          </button>
        ),
      )}
    </div>
  )
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
  const [showMobileFilters, setShowMobileFilters] = useState(false)
  const pageSize = 12

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

  const hasActiveFilters = telemetryOnly || excludeFragile || selectedOnly || search.trim() || lensId !== 'high-mispricing-confidence' || sortId !== 'rank'

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

  const removeCompare = (netuid: number) => {
    setCompareIds((current) => current.filter((id) => id !== netuid))
  }

  const compareNames = useMemo(
    () =>
      compareIds.map((id) => {
        const subnet = subnets.find((item) => item.netuid === id)
        return { id, name: subnet?.name?.trim() || `SN${id}` }
      }),
    [compareIds, subnets],
  )

  const lensOptions = UNIVERSE_LENSES.map((l) => ({ id: l.id, title: l.title, description: l.description }))
  const sortOptions = UNIVERSE_SORTS.map((s) => ({ id: s.id, title: s.label }))

  return (
    <div className="space-y-4 page-enter">
      {/* Header section */}
      <section className="rounded-[1.6rem] border border-white/10 bg-[#10151b] p-4 sm:p-5">
        <div className="flex flex-col gap-4 xl:flex-row xl:items-end xl:justify-between">
          <div className="space-y-2">
            <div className="flex flex-wrap items-center gap-2">
              <StatusBadge tone="neutral">Universe workspace</StatusBadge>
              <StatusBadge tone={lastRun ? (isStale(lastRun) ? 'warning' : 'confidence') : 'warning'}>
                {lastRun ? (isStale(lastRun) ? 'Stale run' : 'Run live') : 'Awaiting run'}
              </StatusBadge>
            </div>
            <h1 className="text-2xl font-semibold tracking-tight text-stone-50 sm:text-3xl">Subnet research</h1>
            <p className="max-w-3xl text-sm leading-6 text-stone-500">
              Screen, compare, and build conviction. Expand any row for the full analysis read.
            </p>
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

      {/* Consolidated filter toolbar */}
      <div className="rounded-2xl border border-white/10 bg-stone-950/80 backdrop-blur-sm px-3 py-2.5 sm:px-4 sm:py-3">
        <div className="flex flex-wrap items-center gap-2">
          {/* Search */}
          <input
            type="search"
            value={search}
            onChange={(event) => {
              setSearch(event.target.value)
              setPage(0)
            }}
            placeholder="Search..."
            className="focus-ring w-full rounded-xl border border-white/10 bg-white/[0.03] px-3 py-2 text-sm text-stone-100 outline-none placeholder:text-stone-600 sm:w-52"
          />

          {/* Mobile filter toggle */}
          <button
            onClick={() => setShowMobileFilters((v) => !v)}
            className="flex items-center gap-1 rounded-full border border-white/10 px-3 py-1.5 text-xs text-stone-400 sm:hidden"
          >
            Filters
            <svg width="10" height="10" viewBox="0 0 10 10" className={cn('transition-transform', showMobileFilters && 'rotate-180')}>
              <path d="M2 3.5L5 6.5L8 3.5" stroke="currentColor" strokeWidth="1.3" fill="none" strokeLinecap="round" strokeLinejoin="round" />
            </svg>
          </button>

          {/* Desktop filters (always visible) + Mobile filters (toggle) */}
          <div className={cn('flex flex-wrap items-center gap-2', showMobileFilters ? 'flex' : 'hidden sm:flex')}>
            <DropdownPill label="Lens" value={lensId} options={lensOptions} onChange={(id) => { setLensId(id); setPage(0) }} />
            <DropdownPill label="Sort" value={sortId} options={sortOptions} onChange={(id) => setSortId(id as UniverseSortId)} />

            <div className="h-4 w-px bg-white/10 hidden sm:block" />

            {/* Workflow chips */}
            <button
              onClick={() => { setTelemetryOnly((value) => !value); setPage(0) }}
              className={cn(
                'rounded-full border px-2.5 py-1 text-[11px] font-medium transition-colors',
                telemetryOnly ? 'border-amber-500/30 bg-amber-500/10 text-amber-200' : 'border-white/10 text-stone-500 hover:text-stone-300',
              )}
            >
              Telemetry repairs
            </button>
            <button
              onClick={() => { setExcludeFragile((value) => !value); setPage(0) }}
              className={cn(
                'rounded-full border px-2.5 py-1 text-[11px] font-medium transition-colors',
                excludeFragile ? 'border-rose-500/30 bg-rose-500/10 text-rose-200' : 'border-white/10 text-stone-500 hover:text-stone-300',
              )}
            >
              Exclude fragile
            </button>
            <button
              onClick={() => { setSelectedOnly((value) => !value); setPage(0) }}
              className={cn(
                'rounded-full border px-2.5 py-1 text-[11px] font-medium transition-colors',
                selectedOnly ? 'border-sky-500/30 bg-sky-500/10 text-sky-200' : 'border-white/10 text-stone-500 hover:text-stone-300',
              )}
            >
              Compare only
            </button>

            {hasActiveFilters && (
              <button
                onClick={resetAll}
                className="rounded-full px-2.5 py-1 text-[11px] text-stone-500 transition-colors hover:text-stone-300"
              >
                Clear all
              </button>
            )}
          </div>
        </div>
      </div>

      {/* Main result list */}
      <div>
        <ResearchList
          rows={pageRows}
          currentLensTitle={currentLens.title}
          emptyMessage={currentLens.emptyMessage}
          compareIds={compareIds}
          onToggleCompare={toggleCompare}
        />

        {/* Pagination */}
        <div className="mt-3 flex flex-col gap-2 rounded-2xl border border-white/10 bg-stone-950/60 px-4 py-3 sm:flex-row sm:items-center sm:justify-between">
          <div className="text-xs text-stone-500">
            {rows.length > 0
              ? `Showing ${currentPage * pageSize + 1}–${Math.min((currentPage + 1) * pageSize, rows.length)} of ${rows.length}`
              : `${rows.length} results`}
          </div>
          {totalPages > 1 && (
            <PageNumbers currentPage={currentPage} totalPages={totalPages} onPageChange={setPage} />
          )}
        </div>
      </div>

      {/* Secondary insight area */}
      <ResearchPanel
        title="Secondary Insight Area"
        subtitle="Quick lens boards for idea discovery — always feed findings back into the memo and compare workflow."
        className="bg-[#10151b]"
      >
        <PrimarySignalBoard subnets={filteredSubnets.filter((subnet) => subnet.primary_outputs)} />
      </ResearchPanel>

      {/* Compare tray */}
      {compareIds.length > 0 ? (
        <div className="slide-up sticky bottom-4 z-30 rounded-2xl border border-sky-500/20 bg-stone-950/95 px-4 py-3 shadow-[0_16px_48px_rgba(0,0,0,0.5)] backdrop-blur">
          <div className="flex flex-col gap-2 lg:flex-row lg:items-center lg:justify-between">
            <div className="flex items-center gap-3">
              <span className="text-[11px] uppercase tracking-[0.18em] text-sky-300">Compare</span>
              <div className="flex flex-wrap items-center gap-1.5">
                {compareNames.map(({ id, name }) => (
                  <span
                    key={id}
                    className="inline-flex items-center gap-1 rounded-lg border border-sky-500/20 bg-sky-500/10 px-2 py-0.5 text-xs text-sky-200"
                  >
                    {name}
                    <button
                      onClick={() => removeCompare(id)}
                      className="ml-0.5 rounded text-sky-400 transition-colors hover:text-sky-100"
                      aria-label={`Remove ${name}`}
                    >
                      <svg width="10" height="10" viewBox="0 0 10 10" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round">
                        <path d="M3 3L7 7M7 3L3 7" />
                      </svg>
                    </button>
                  </span>
                ))}
              </div>
            </div>
            <Link
              href={`/compare?ids=${compareIds.join(',')}`}
              className="focus-ring rounded-xl border border-sky-500/20 bg-sky-500/10 px-4 py-2 text-center text-sm font-medium text-sky-200 transition-colors hover:bg-sky-500/20"
            >
              Open compare
            </Link>
          </div>
        </div>
      ) : null}
    </div>
  )
}
