'use client'

import { useEffect, useMemo, useState } from 'react'
import { usePathname, useRouter, useSearchParams } from 'next/navigation'

import MetricCard from '@/components/ui/MetricCard'
import { MarketOverviewData, SubnetSummary } from '@/lib/api'
import { UniverseRowViewModel, UniverseSortId, sortUniverseRows, toUniverseRow } from '@/lib/view-models/research'

import CompareDock from './CompareDock'
import DiscoverMarketHero from './DiscoverMarketHero'
import DecisionRow, { MobileDecisionCard } from './DecisionRow'
import SidePreviewPanel from './SidePreviewPanel'

type SortDirection = 'asc' | 'desc'

function queryMatches(subnet: SubnetSummary, query: string): boolean {
  const q = query.toLowerCase()
  return (subnet.name ?? '').toLowerCase().includes(q) || String(subnet.netuid).includes(q)
}

function parseIds(value: string | null): number[] {
  return (value ?? '')
    .split(',')
    .map((part) => Number.parseInt(part, 10))
    .filter((item, index, all) => Number.isFinite(item) && all.indexOf(item) === index)
    .slice(0, 4)
}

function reverseRows(rows: UniverseRowViewModel[]): UniverseRowViewModel[] {
  return [...rows].reverse()
}

function rankMap(rows: UniverseRowViewModel[], key: 'quality' | 'mispricing' | 'confidence' | 'fragility') {
  const ordered = [...rows].sort((a, b) => {
    if (key === 'fragility') {
      const aValue = a.signals.find((item) => item.key === 'fragility_risk')?.value ?? Number.POSITIVE_INFINITY
      const bValue = b.signals.find((item) => item.key === 'fragility_risk')?.value ?? Number.POSITIVE_INFINITY
      return aValue - bValue || a.id - b.id
    }

    const signalKey =
      key === 'quality'
        ? 'fundamental_quality'
        : key === 'mispricing'
          ? 'mispricing_signal'
          : 'signal_confidence'
    const aValue = a.signals.find((item) => item.key === signalKey)?.value ?? Number.NEGATIVE_INFINITY
    const bValue = b.signals.find((item) => item.key === signalKey)?.value ?? Number.NEGATIVE_INFINITY
    return bValue - aValue || a.id - b.id
  })

  return new Map(ordered.map((row, index) => [row.id, index + 1]))
}

function SortHeader({
  label,
  active,
  direction,
  align = 'left',
  onClick,
}: {
  label: string
  active: boolean
  direction: SortDirection
  align?: 'left' | 'right'
  onClick: () => void
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={[
        'flex min-w-0 items-center gap-1 whitespace-nowrap transition-colors hover:text-[color:var(--text-primary)]',
        align === 'right' ? 'justify-end text-right' : 'text-left',
      ].join(' ')}
    >
      <span>{label}</span>
      <span
        className={[
          'inline-flex w-3 justify-center text-[9px] leading-none',
          active ? 'text-[color:var(--text-primary)]' : 'text-transparent',
        ].join(' ')}
        aria-hidden="true"
      >
        {active ? (direction === 'asc' ? '^' : 'v') : '^'}
      </span>
    </button>
  )
}

export default function DiscoverWorkspace({
  subnets,
  lastRun,
  market,
}: {
  subnets: SubnetSummary[]
  lastRun: string | null
  market: MarketOverviewData
  trackedUniverse: number
  awaitingRunCount: number
  lowConfidenceCount: number
}) {
  const router = useRouter()
  const pathname = usePathname()
  const searchParams = useSearchParams()

  const [search, setSearch] = useState(searchParams.get('q') ?? '')
  const [sort, setSort] = useState<UniverseSortId>((searchParams.get('sort') as UniverseSortId) ?? 'rank')
  const [direction, setDirection] = useState<SortDirection>((searchParams.get('dir') as SortDirection) ?? 'asc')
  const [compareIds, setCompareIds] = useState<number[]>(parseIds(searchParams.get('ids')))
  const [focusedId, setFocusedId] = useState<number | null>(null)
  const [pinnedId, setPinnedId] = useState<number | null>(null)

  useEffect(() => {
    const params = new URLSearchParams()
    if (search.trim()) params.set('q', search.trim())
    if (sort !== 'rank') params.set('sort', sort)
    if (direction !== 'asc') params.set('dir', direction)
    if (compareIds.length) params.set('ids', compareIds.join(','))
    const next = params.toString()
    router.replace(next ? `${pathname}?${next}` : pathname, { scroll: false })
  }, [compareIds, direction, pathname, router, search, sort])

  const rows = useMemo(() => {
    const searched = search.trim() ? subnets.filter((subnet) => queryMatches(subnet, search)) : subnets
    const sorted = sortUniverseRows(searched.map(toUniverseRow), sort)
    return direction === 'asc' ? sorted : reverseRows(sorted)
  }, [direction, search, sort, subnets])

  useEffect(() => {
    if (!rows.length) {
      setFocusedId(null)
      setPinnedId(null)
      return
    }
    if (!focusedId || !rows.some((row) => row.id === focusedId)) {
      setFocusedId(rows[0].id)
    }
    if (pinnedId && !rows.some((row) => row.id === pinnedId)) {
      setPinnedId(null)
    }
  }, [focusedId, pinnedId, rows])

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
      if (event.key === 'Enter' && focusedId) {
        event.preventDefault()
        const row = rows.find((item) => item.id === focusedId)
        if (row) router.push(row.href)
      }
    }

    window.addEventListener('keydown', onKeyDown)
    return () => window.removeEventListener('keydown', onKeyDown)
  }, [focusedId, router, rows])

  function toggleCompare(netuid: number) {
    setCompareIds((current) => {
      if (current.includes(netuid)) return current.filter((id) => id !== netuid)
      if (current.length >= 4) return [...current.slice(1), netuid]
      return [...current, netuid]
    })
  }

  function toggleSort(nextSort: UniverseSortId) {
    if (sort === nextSort) {
      setDirection((current) => (current === 'asc' ? 'desc' : 'asc'))
      return
    }
    setSort(nextSort)
    setDirection('asc')
  }

  function handlePreviewFocus(id: number) {
    setFocusedId(id)
  }

  function handlePinToggle(id: number) {
    setPinnedId((current) => (current === id ? null : id))
    setFocusedId(id)
  }

  const previewId = pinnedId ?? focusedId
  const previewRow = rows.find((row) => row.id === previewId) ?? null
  const metricRanks = useMemo(() => {
    if (!previewRow) return null
    const strengthRanks = rankMap(rows, 'quality')
    const upsideRanks = rankMap(rows, 'mispricing')
    const riskRanks = rankMap(rows, 'fragility')
    const evidenceRanks = rankMap(rows, 'confidence')
    return {
      strength: strengthRanks.get(previewRow.id) ?? rows.length,
      upside: upsideRanks.get(previewRow.id) ?? rows.length,
      risk: riskRanks.get(previewRow.id) ?? rows.length,
      evidence: evidenceRanks.get(previewRow.id) ?? rows.length,
      total: rows.length,
    }
  }, [previewRow, rows])
  const compareItems = compareIds
    .map((id) => subnets.find((subnet) => subnet.netuid === id))
    .filter((item): item is SubnetSummary => Boolean(item))
    .map((subnet) => ({
      id: subnet.netuid,
      name: subnet.name?.trim() || `SN${subnet.netuid}`,
    }))

  return (
    <div className="space-y-6 pb-28">
      <DiscoverMarketHero market={market} lastRun={lastRun} />

      <section className="surface-panel p-4 sm:p-5">
        <div className="space-y-5">
          <div className="w-full max-w-xl">
            <label htmlFor="discover-search" className="eyebrow">
              Search
            </label>
            <input
              id="discover-search"
              type="search"
              value={search}
              onChange={(event) => setSearch(event.target.value)}
              placeholder="Search subnet or netuid"
              className="mt-2 min-h-11 w-full rounded-[var(--radius-md)] border border-[color:var(--border-subtle)] bg-[color:var(--surface-2)] px-4 text-sm text-[color:var(--text-primary)] outline-none placeholder:text-[color:var(--text-tertiary)]"
            />
          </div>

          <div>
            <div className="eyebrow">How To Read The Table</div>
            <div className="mt-3 grid gap-3 md:grid-cols-2 xl:grid-cols-4">
              <MetricCard
                label="Quality"
                value="How strong is the subnet?"
                meta="Higher means participation, liquidity, and structure look healthier and more durable."
                accent="quality"
              />
              <MetricCard
                label="Opportunity"
                value="How much upside is left?"
                meta="Higher means the model still sees a cleaner, less-crowded gap between current pricing and fairer value."
                accent="mispricing"
              />
              <MetricCard
                label="Risk"
                value="How easily can the thesis break?"
                meta="Lower is better. A lower score means less fragility under stress, crowding, or thin liquidity."
                accent="fragility"
              />
              <MetricCard
                label="Confidence"
                value="How much should I trust the read?"
                meta="Higher means the evidence base is cleaner, more complete, and easier to underwrite."
                accent="confidence"
              />
            </div>
          </div>
        </div>
      </section>

      <section className="grid gap-6 xl:grid-cols-[minmax(0,1fr)_360px]">
        <section className="surface-panel overflow-hidden p-0">
          <div className="flex items-center justify-between gap-4 border-b border-[color:var(--border-subtle)] px-4 py-3 sm:px-5">
            <div>
              <div className="section-title">Ranked subnets</div>
              <p className="mt-1 text-sm text-[color:var(--text-secondary)]">
                Score stays central, while quality, opportunity, risk, confidence, and investability make weak structures easier to spot fast.
              </p>
            </div>
            <div className="text-sm text-[color:var(--text-secondary)]">{rows.length} results</div>
          </div>

          {rows.length ? (
            <>
              <div className="hidden md:block">
                <div className="grid grid-cols-[64px_minmax(0,1.4fr)_84px_78px_92px_72px_92px_116px] gap-4 border-b border-[color:var(--border-subtle)] bg-[color:rgba(8,16,23,0.48)] px-4 py-2.5 text-[10px] font-medium uppercase tracking-[0.24em] text-[color:var(--text-tertiary)] sm:px-5">
                  <SortHeader label="Rank" active={sort === 'rank'} direction={direction} onClick={() => toggleSort('rank')} />
                  <div>Subnet</div>
                  <SortHeader label="Score" active={sort === 'score'} direction={direction} align="right" onClick={() => toggleSort('score')} />
                  <SortHeader label="Quality" active={sort === 'quality'} direction={direction} align="right" onClick={() => toggleSort('quality')} />
                  <SortHeader label="Opportunity" active={sort === 'mispricing'} direction={direction} align="right" onClick={() => toggleSort('mispricing')} />
                  <SortHeader label="Risk" active={sort === 'fragility'} direction={direction} align="right" onClick={() => toggleSort('fragility')} />
                  <SortHeader label="Confidence" active={sort === 'confidence'} direction={direction} align="right" onClick={() => toggleSort('confidence')} />
                  <div>Status</div>
                </div>

                <div>
                  {rows.map((row) => (
                    <DecisionRow
                      key={row.id}
                      row={row}
                      selected={compareIds.includes(row.id)}
                      focused={previewId === row.id}
                      pinned={pinnedId === row.id}
                      onFocus={() => handlePreviewFocus(row.id)}
                      onSelect={() => handlePinToggle(row.id)}
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
              No subnets match the current search.
            </div>
          )}
        </section>

        <SidePreviewPanel
          row={previewRow}
          metricRanks={metricRanks}
          selected={previewRow ? compareIds.includes(previewRow.id) : false}
          onToggleCompare={toggleCompare}
        />
      </section>

      <CompareDock items={compareItems} onRemove={(id) => setCompareIds((current) => current.filter((item) => item !== id))} />
    </div>
  )
}
