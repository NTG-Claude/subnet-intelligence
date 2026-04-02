'use client'

import { useEffect, useMemo, useState } from 'react'
import { usePathname, useRouter, useSearchParams } from 'next/navigation'

import FilterDrawer from '@/components/ui/FilterDrawer'
import PageHeader from '@/components/ui/PageHeader'
import SegmentedControl from '@/components/ui/SegmentedControl'
import MetricCard from '@/components/ui/MetricCard'
import { SubnetSummary } from '@/lib/api'
import { cn, isStale } from '@/lib/formatting'
import {
  UNIVERSE_SORTS,
  UniverseSortId,
  applyUniverseLens,
  sortUniverseRows,
  toUniverseRow,
} from '@/lib/view-models/research'

import CompareDock from './CompareDock'
import DecisionRow, { MobileDecisionCard } from './DecisionRow'
import SidePreviewPanel from './SidePreviewPanel'

const VIEW_OPTIONS = [
  { id: 'all', label: 'Best Ideas' },
  { id: 'high-mispricing-confidence', label: 'Mispriced' },
  { id: 'strong-quality', label: 'Quality' },
  { id: 'under-review', label: 'Under Review' },
  { id: 'custom', label: 'Custom' },
]

function queryMatches(subnet: SubnetSummary, query: string): boolean {
  const q = query.toLowerCase()
  return (
    (subnet.name ?? '').toLowerCase().includes(q) ||
    String(subnet.netuid).includes(q) ||
    (subnet.thesis ?? '').toLowerCase().includes(q)
  )
}

function parseIds(value: string | null): number[] {
  return (value ?? '')
    .split(',')
    .map((part) => Number.parseInt(part, 10))
    .filter((item, index, all) => Number.isFinite(item) && all.indexOf(item) === index)
    .slice(0, 4)
}

export default function DiscoverWorkspace({
  subnets,
  lastRun,
  trackedUniverse,
  awaitingRunCount,
  lowConfidenceCount,
}: {
  subnets: SubnetSummary[]
  lastRun: string | null
  trackedUniverse: number
  awaitingRunCount: number
  lowConfidenceCount: number
}) {
  const router = useRouter()
  const pathname = usePathname()
  const searchParams = useSearchParams()

  const [search, setSearch] = useState(searchParams.get('q') ?? '')
  const [view, setView] = useState(searchParams.get('view') ?? 'all')
  const [sort, setSort] = useState<UniverseSortId>((searchParams.get('sort') as UniverseSortId) ?? 'rank')
  const [telemetryOnly, setTelemetryOnly] = useState(searchParams.get('trust') === 'repaired')
  const [excludeFragile, setExcludeFragile] = useState(searchParams.get('fragility') === 'exclude')
  const [selectedOnly, setSelectedOnly] = useState(searchParams.get('selectedOnly') === '1')
  const [compareIds, setCompareIds] = useState<number[]>(parseIds(searchParams.get('ids')))
  const [filtersOpen, setFiltersOpen] = useState(view === 'custom')
  const [focusedId, setFocusedId] = useState<number | null>(null)

  useEffect(() => {
    const params = new URLSearchParams()
    if (search.trim()) params.set('q', search.trim())
    if (view !== 'all') params.set('view', view)
    if (sort !== 'rank') params.set('sort', sort)
    if (telemetryOnly) params.set('trust', 'repaired')
    if (excludeFragile) params.set('fragility', 'exclude')
    if (selectedOnly) params.set('selectedOnly', '1')
    if (compareIds.length) params.set('ids', compareIds.join(','))
    const next = params.toString()
    router.replace(next ? `${pathname}?${next}` : pathname, { scroll: false })
  }, [compareIds, excludeFragile, pathname, router, search, selectedOnly, sort, telemetryOnly, view])

  const filteredSubnets = useMemo(() => {
    let next = applyUniverseLens(subnets, view === 'custom' ? 'all' : view)

    if (search.trim()) next = next.filter((subnet) => queryMatches(subnet, search))
    if (telemetryOnly) {
      next = next.filter((subnet) => {
        const visibility = subnet.analysis_preview?.conditioning?.visibility
        return Boolean((visibility?.reconstructed?.length ?? 0) || (visibility?.discarded?.length ?? 0))
      })
    }
    if (excludeFragile) next = next.filter((subnet) => (subnet.primary_outputs?.fragility_risk ?? 0) <= 60)
    if (selectedOnly) next = next.filter((subnet) => compareIds.includes(subnet.netuid))

    return next
  }, [compareIds, excludeFragile, search, selectedOnly, subnets, telemetryOnly, view])

  const rows = useMemo(() => sortUniverseRows(filteredSubnets.map(toUniverseRow), sort), [filteredSubnets, sort])

  useEffect(() => {
    if (!rows.length) {
      setFocusedId(null)
      return
    }
    if (!focusedId || !rows.some((row) => row.id === focusedId)) {
      setFocusedId(rows[0].id)
    }
  }, [focusedId, rows])

  useEffect(() => {
    function onKeyDown(event: KeyboardEvent) {
      if (event.target instanceof HTMLInputElement || event.target instanceof HTMLTextAreaElement) return
      if (event.key === '/') {
        event.preventDefault()
        document.getElementById('discover-search')?.focus()
      }
      if (!rows.length) return
      const currentIndex = rows.findIndex((row) => row.id === focusedId)
      if (event.key === 'j') {
        event.preventDefault()
        const next = rows[Math.min(rows.length - 1, Math.max(0, currentIndex + 1))]
        setFocusedId(next.id)
      }
      if (event.key === 'k') {
        event.preventDefault()
        const next = rows[Math.max(0, currentIndex - 1)]
        setFocusedId(next.id)
      }
      if (event.key === 'c' && focusedId) {
        event.preventDefault()
        toggleCompare(focusedId)
      }
      if (event.key === 'Enter' && focusedId) {
        event.preventDefault()
        const row = rows.find((item) => item.id === focusedId)
        if (row) router.push(row.href)
      }
      if (event.key === 'Escape') {
        setFiltersOpen(false)
      }
    }

    window.addEventListener('keydown', onKeyDown)
    return () => window.removeEventListener('keydown', onKeyDown)
  }, [focusedId, router, rows])

  function setPrimaryView(next: string) {
    setView(next)
    if (next === 'custom') {
      setFiltersOpen(true)
      return
    }
    setTelemetryOnly(false)
    setExcludeFragile(false)
    setSelectedOnly(false)
    setFiltersOpen(false)
  }

  function toggleCompare(netuid: number) {
    setCompareIds((current) => {
      if (current.includes(netuid)) return current.filter((id) => id !== netuid)
      if (current.length >= 4) return [...current.slice(1), netuid]
      return [...current, netuid]
    })
  }

  const previewRow = rows.find((row) => row.id === focusedId) ?? null
  const compareItems = compareIds
    .map((id) => subnets.find((subnet) => subnet.netuid === id))
    .filter((item): item is SubnetSummary => Boolean(item))
    .map((subnet) => ({
      id: subnet.netuid,
      name: subnet.name?.trim() || `SN${subnet.netuid}`,
    }))

  const trustIssueCount = awaitingRunCount + lowConfidenceCount

  return (
    <div className="space-y-6 pb-28">
      <PageHeader
        title="Discover subnets"
        subtitle="Screen by idea quality, mispricing, fragility, and trust. Use the compact list to build a shortlist, then step into compare or deep research."
        variant="compact"
        stats={[
          { label: 'Last run', value: lastRun ? (isStale(lastRun) ? 'Stale run' : 'Live run') : 'Awaiting run', tone: lastRun ? (isStale(lastRun) ? 'warning' : 'success') : 'warning' },
          { label: 'Tracked subnets', value: String(trackedUniverse) },
          { label: 'Trust issues', value: String(trustIssueCount), tone: trustIssueCount ? 'warning' : 'success' },
        ]}
      />

      <section className="grid gap-6 2xl:grid-cols-[minmax(0,1fr)_320px]">
        <div className="space-y-6">
          <div className="surface-panel p-4 sm:p-5">
            <div className="flex flex-col gap-4">
              <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
                <div className="flex-1">
                  <label htmlFor="discover-search" className="eyebrow">
                    Search
                  </label>
                  <input
                    id="discover-search"
                    type="search"
                    value={search}
                    onChange={(event) => setSearch(event.target.value)}
                    placeholder="Search subnet, thesis, or netuid"
                    className="mt-2 min-h-12 w-full rounded-[var(--radius-md)] border border-[color:var(--border-subtle)] bg-[color:var(--surface-2)] px-4 text-sm text-[color:var(--text-primary)] outline-none placeholder:text-[color:var(--text-tertiary)]"
                  />
                </div>
                <SegmentedControl items={VIEW_OPTIONS} value={view} onChange={setPrimaryView} />
              </div>

              <div className="grid gap-3 md:grid-cols-3">
                <MetricCard label="Screening workflow" value="Scan first" meta="Rows stay compact. Preview and research carry depth." />
                <MetricCard label="Selection cap" value="4 names" meta="Compare stays decision-focused instead of turning into a wall." />
                <MetricCard label="Keyboard" value="/ j k c" meta="Search, navigate rows, and toggle compare without leaving the list." />
              </div>
            </div>
          </div>

          <FilterDrawer
            title="Advanced filters"
            subtitle="Keep these collapsed by default. Open them when you need to refine the current view rather than replace it."
            open={filtersOpen}
            onToggle={() => setFiltersOpen((current) => !current)}
          >
            <div className="grid gap-4 pt-2 lg:grid-cols-2">
              <div className="grid gap-3 sm:grid-cols-2">
                <button type="button" onClick={() => setTelemetryOnly((current) => !current)} className={cn('button-secondary justify-start', telemetryOnly && 'border-[color:var(--warning-border)] bg-[color:var(--warning-surface)] text-[color:var(--warning-strong)]')}>
                  Telemetry repairs only
                </button>
                <button type="button" onClick={() => setExcludeFragile((current) => !current)} className={cn('button-secondary justify-start', excludeFragile && 'border-[color:var(--fragility-border)] bg-[color:var(--fragility-surface)] text-[color:var(--fragility-strong)]')}>
                  Exclude fragile
                </button>
                <button type="button" onClick={() => setSelectedOnly((current) => !current)} className={cn('button-secondary justify-start', selectedOnly && 'border-[color:var(--mispricing-border)] bg-[color:var(--mispricing-surface)] text-[color:var(--mispricing-strong)]')}>
                  Compare tray only
                </button>
                <button
                  type="button"
                  onClick={() => {
                    setSearch('')
                    setSort('rank')
                    setTelemetryOnly(false)
                    setExcludeFragile(false)
                    setSelectedOnly(false)
                    setView('all')
                  }}
                  className="button-secondary justify-start"
                >
                  Reset filters
                </button>
              </div>

              <div>
                <div className="eyebrow">Sort</div>
                <div className="mt-2 flex flex-wrap gap-2">
                  {UNIVERSE_SORTS.map((item) => (
                    <button
                      key={item.id}
                      type="button"
                      onClick={() => setSort(item.id)}
                      className={cn('button-secondary', sort === item.id && 'border-[color:var(--confidence-border)] bg-[color:var(--confidence-surface)] text-[color:var(--confidence-strong)]')}
                    >
                      {item.label}
                    </button>
                  ))}
                </div>
              </div>
            </div>
          </FilterDrawer>

          <section className="surface-panel overflow-hidden p-0">
            <div className="flex items-center justify-between gap-4 border-b border-[color:var(--border-subtle)] px-4 py-4 sm:px-5">
              <div>
                <div className="section-title">Results</div>
                <p className="mt-1 text-sm text-[color:var(--text-secondary)]">
                  Each row shows only the information needed for first-pass screening. Trust state stays visible in every result.
                </p>
              </div>
              <div className="text-sm text-[color:var(--text-secondary)]">{rows.length} results</div>
            </div>

            {rows.length ? (
              <>
                <div className="hidden md:block">
                  <div className="grid grid-cols-[minmax(0,1.25fr)_minmax(360px,0.95fr)] gap-5 border-b border-[color:var(--border-subtle)] px-5 py-3">
                    <div className="grid gap-3 xl:grid-cols-[minmax(0,1.05fr)_minmax(0,0.95fr)]">
                      <div className="eyebrow">Subnet and thesis</div>
                      <div className="eyebrow">Trust and action</div>
                    </div>
                    <div className="grid gap-3 sm:grid-cols-2">
                      {['Quality', 'Mispricing', 'Fragility', 'Confidence'].map((label) => (
                        <div key={label} className="eyebrow">
                          {label}
                        </div>
                      ))}
                    </div>
                  </div>

                  <div>
                    {rows.map((row) => (
                      <DecisionRow
                        key={row.id}
                        row={row}
                        selected={compareIds.includes(row.id)}
                        focused={focusedId === row.id}
                        onFocus={() => setFocusedId(row.id)}
                        onToggleCompare={toggleCompare}
                      />
                    ))}
                  </div>
                </div>

                <div className="space-y-4 p-4 md:hidden">
                  {rows.map((row) => (
                    <MobileDecisionCard
                      key={row.id}
                      row={row}
                      selected={compareIds.includes(row.id)}
                      focused={focusedId === row.id}
                      onFocus={() => setFocusedId(row.id)}
                      onToggleCompare={toggleCompare}
                    />
                  ))}
                </div>
              </>
            ) : (
              <div className="p-8 text-center text-sm text-[color:var(--text-secondary)]">
                No subnets match the current screening stack. Clear filters or switch the primary view.
              </div>
            )}
          </section>
        </div>

        <SidePreviewPanel
          row={previewRow}
          selected={previewRow ? compareIds.includes(previewRow.id) : false}
          onToggleCompare={toggleCompare}
        />
      </section>

      <CompareDock items={compareItems} onRemove={(id) => setCompareIds((current) => current.filter((item) => item !== id))} />
    </div>
  )
}
