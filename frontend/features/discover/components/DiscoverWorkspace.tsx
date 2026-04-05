'use client'

import { useEffect, useMemo, useState } from 'react'
import { usePathname, useRouter } from 'next/navigation'

import MetricCard from '@/components/ui/MetricCard'
import SegmentedControl from '@/components/ui/SegmentedControl'
import {
  fetchSubnetSignalHistory,
  MarketOverviewData,
  PreviewMetricDeltas as ApiPreviewMetricDeltas,
  SubnetSignalHistoryPoint,
  SubnetSummary,
} from '@/lib/api'
import { UniverseRowViewModel, UniverseSortId, sortUniverseRows, toUniverseRow } from '@/lib/view-models/research'

import CompareDock from './CompareDock'
import DecisionRow, { DISCOVER_TABLE_GRID } from './DecisionRow'
import DiscoverMarketHero from './DiscoverMarketHero'
import SidePreviewPanel from './SidePreviewPanel'

type SortDirection = 'asc' | 'desc'
type MarketTimeframeId = '7d' | '30d' | '90d' | '180d' | 'max'
type MetricDeltaWindow = '1d' | '7d' | '30d'
type MetricDelta = { value: number | null; hasHistory: boolean }
type PreviewMetricDeltas = {
  strength: Record<MetricDeltaWindow, MetricDelta>
  upside: Record<MetricDeltaWindow, MetricDelta>
  risk: Record<MetricDeltaWindow, MetricDelta>
  evidence: Record<MetricDeltaWindow, MetricDelta>
}
type RankDelta = { change: number; previousRank: number } | null

const TIMESERIES_CACHE_TTL_MS = 5 * 60 * 1000
const PREVIEW_HISTORY_CACHE_PREFIX = 'discover-preview-history-v1'
const DETAIL_WARMUP_LIMIT = 3

const cachedPreviewHistory = new Map<number, { fetchedAt: number; points: SubnetSignalHistoryPoint[] }>()
const cachedPreviewHistoryPromises = new Map<number, Promise<SubnetSignalHistoryPoint[]>>()
const warmedDetailPayloads = new Set<number>()
const detailWarmupPromises = new Map<number, Promise<void>>()

const MARKET_TIMEFRAME_ITEMS = [
  { id: '7d', label: '7D' },
  { id: '30d', label: '30D' },
  { id: '90d', label: '90D' },
  { id: '180d', label: '180D' },
  { id: 'max', label: 'MAX' },
] as const

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

function parseSort(value: string | null): UniverseSortId {
  switch (value) {
    case 'score':
    case 'quality':
    case 'mispricing':
    case 'fragility':
    case 'confidence':
    case 'rank':
      return value
    default:
      return 'rank'
  }
}

function parseDirection(value: string | null): SortDirection {
  return value === 'desc' ? 'desc' : 'asc'
}

function parseMarketTimeframe(value: string | null): MarketTimeframeId {
  switch (value) {
    case '7d':
    case '30d':
    case '90d':
    case '180d':
    case 'max':
      return value
    default:
      return 'max'
  }
}

function emptyDelta(): MetricDelta {
  return { value: null, hasHistory: false }
}

function nearestPointAtOrBefore(points: SubnetSignalHistoryPoint[], targetTime: number) {
  let match: SubnetSignalHistoryPoint | null = null
  for (const point of points) {
    const pointTime = Date.parse(point.computed_at)
    if (!Number.isFinite(pointTime) || pointTime > targetTime) continue
    match = point
  }
  return match
}

function signalDelta(
  points: SubnetSignalHistoryPoint[],
  metric: 'quality' | 'opportunity' | 'risk' | 'confidence',
  days: number,
): MetricDelta {
  const latestPoint = points[points.length - 1]
  if (!latestPoint) return emptyDelta()

  const latestValue = latestPoint[metric]
  if (latestValue == null) return emptyDelta()

  const referencePoint = nearestPointAtOrBefore(points, Date.parse(latestPoint.computed_at) - days * 24 * 60 * 60 * 1000)
  if (!referencePoint) return emptyDelta()

  const referenceValue = referencePoint[metric]
  if (referenceValue == null) return emptyDelta()

  return {
    value: Number((latestValue - referenceValue).toFixed(1)),
    hasHistory: true,
  }
}

function buildPreviewMetricDeltasFromHistory(points: SubnetSignalHistoryPoint[] | null): PreviewMetricDeltas | null {
  if (!points?.length) return null

  return {
    strength: {
      '1d': signalDelta(points, 'quality', 1),
      '7d': signalDelta(points, 'quality', 7),
      '30d': signalDelta(points, 'quality', 30),
    },
    upside: {
      '1d': signalDelta(points, 'opportunity', 1),
      '7d': signalDelta(points, 'opportunity', 7),
      '30d': signalDelta(points, 'opportunity', 30),
    },
    risk: {
      '1d': signalDelta(points, 'risk', 1),
      '7d': signalDelta(points, 'risk', 7),
      '30d': signalDelta(points, 'risk', 30),
    },
    evidence: {
      '1d': signalDelta(points, 'confidence', 1),
      '7d': signalDelta(points, 'confidence', 7),
      '30d': signalDelta(points, 'confidence', 30),
    },
  }
}

function hasFreshPreviewHistory(netuid: number, now = Date.now()): boolean {
  const cached = cachedPreviewHistory.get(netuid)
  return Boolean(cached && now - cached.fetchedAt < TIMESERIES_CACHE_TTL_MS)
}

function rememberPreviewHistory(netuid: number, points: SubnetSignalHistoryPoint[], now = Date.now()) {
  cachedPreviewHistory.set(netuid, { fetchedAt: now, points })

  if (typeof window !== 'undefined') {
    window.sessionStorage.setItem(
      `${PREVIEW_HISTORY_CACHE_PREFIX}:${netuid}`,
      JSON.stringify({
        fetchedAt: now,
        points,
      }),
    )
  }
}

function getCachedPreviewHistory(netuid: number): SubnetSignalHistoryPoint[] | null {
  if (hasFreshPreviewHistory(netuid)) {
    return cachedPreviewHistory.get(netuid)?.points ?? null
  }

  if (typeof window === 'undefined') return null

  const raw = window.sessionStorage.getItem(`${PREVIEW_HISTORY_CACHE_PREFIX}:${netuid}`)
  if (!raw) return null

  try {
    const parsed = JSON.parse(raw) as { fetchedAt?: number; points?: SubnetSignalHistoryPoint[] }
    if (!parsed.fetchedAt || !parsed.points) return null
    if (Date.now() - parsed.fetchedAt >= TIMESERIES_CACHE_TTL_MS) return null

    cachedPreviewHistory.set(netuid, { fetchedAt: parsed.fetchedAt, points: parsed.points })
    return parsed.points
  } catch {
    return null
  }
}

async function loadPreviewHistory(netuid: number): Promise<SubnetSignalHistoryPoint[]> {
  const existing = getCachedPreviewHistory(netuid)
  if (existing) return existing

  const inFlight = cachedPreviewHistoryPromises.get(netuid)
  if (inFlight) return inFlight

  const request = fetchSubnetSignalHistory(netuid, 120)
    .then((points) => {
      rememberPreviewHistory(netuid, points)
      return points
    })
    .finally(() => {
      cachedPreviewHistoryPromises.delete(netuid)
    })

  cachedPreviewHistoryPromises.set(netuid, request)
  return request
}

async function warmDetailPayload(netuid: number): Promise<void> {
  if (warmedDetailPayloads.has(netuid)) return

  const existing = detailWarmupPromises.get(netuid)
  if (existing) return existing

  const request = fetch(`/api/v1/subnets/${netuid}?view=page`, {
    method: 'GET',
  })
    .then(() => {
      warmedDetailPayloads.add(netuid)
    })
    .catch(() => {
      // Ignore warmup failures; the real navigation still handles errors normally.
    })
    .finally(() => {
      detailWarmupPromises.delete(netuid)
    })

  detailWarmupPromises.set(netuid, request)
  return request
}

function normalizePreviewMetricDeltas(deltas: ApiPreviewMetricDeltas | null | undefined): PreviewMetricDeltas | null {
  if (!deltas) return null

  return {
    strength: {
      '1d': { value: deltas.strength['1d']?.value ?? null, hasHistory: deltas.strength['1d']?.has_history ?? false },
      '7d': { value: deltas.strength['7d']?.value ?? null, hasHistory: deltas.strength['7d']?.has_history ?? false },
      '30d': { value: deltas.strength['30d']?.value ?? null, hasHistory: deltas.strength['30d']?.has_history ?? false },
    },
    upside: {
      '1d': { value: deltas.upside['1d']?.value ?? null, hasHistory: deltas.upside['1d']?.has_history ?? false },
      '7d': { value: deltas.upside['7d']?.value ?? null, hasHistory: deltas.upside['7d']?.has_history ?? false },
      '30d': { value: deltas.upside['30d']?.value ?? null, hasHistory: deltas.upside['30d']?.has_history ?? false },
    },
    risk: {
      '1d': { value: deltas.risk['1d']?.value ?? null, hasHistory: deltas.risk['1d']?.has_history ?? false },
      '7d': { value: deltas.risk['7d']?.value ?? null, hasHistory: deltas.risk['7d']?.has_history ?? false },
      '30d': { value: deltas.risk['30d']?.value ?? null, hasHistory: deltas.risk['30d']?.has_history ?? false },
    },
    evidence: {
      '1d': { value: deltas.evidence['1d']?.value ?? null, hasHistory: deltas.evidence['1d']?.has_history ?? false },
      '7d': { value: deltas.evidence['7d']?.value ?? null, hasHistory: deltas.evidence['7d']?.has_history ?? false },
      '30d': { value: deltas.evidence['30d']?.value ?? null, hasHistory: deltas.evidence['30d']?.has_history ?? false },
    },
  }
}

function filterMarketPoints(points: MarketOverviewData['points'], timeframe: MarketTimeframeId) {
  if (timeframe === 'max' || points.length <= 1) return points

  const latestPoint = points[points.length - 1]
  const latestTime = Date.parse(latestPoint.computed_at)
  if (!Number.isFinite(latestTime)) return points

  const days = timeframe === '7d' ? 7 : timeframe === '30d' ? 30 : timeframe === '90d' ? 90 : 180
  const cutoff = latestTime - days * 24 * 60 * 60 * 1000
  const filtered = points.filter((point) => {
    const pointTime = Date.parse(point.computed_at)
    return Number.isFinite(pointTime) && pointTime >= cutoff
  })
  return filtered.length ? filtered : points
}

function applyMarketTimeframe(market: MarketOverviewData, timeframe: MarketTimeframeId): MarketOverviewData {
  return {
    ...market,
    points: filterMarketPoints(market.points, timeframe),
  }
}

function buildRankDeltaMap(subnets: SubnetSummary[]): Map<number, RankDelta> {
  const previousRanks = new Map<number, number>()

  subnets.forEach((subnet) => {
    if (subnet.previous_rank != null) {
      previousRanks.set(subnet.netuid, subnet.previous_rank)
    }
  })

  if (!previousRanks.size) return new Map()

  return new Map(
    subnets.map((subnet) => {
      const currentRank = subnet.rank
      const previousRank = previousRanks.get(subnet.netuid)
      if (!previousRank || currentRank == null) return [subnet.netuid, null]
      return [
        subnet.netuid,
        {
          change: previousRank - currentRank,
          previousRank,
        },
      ]
    }),
  )
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
        'flex min-w-0 items-center gap-1.5 whitespace-nowrap font-medium transition-colors hover:text-[color:var(--text-primary)]',
        align === 'right' ? 'justify-end text-right' : 'text-left',
      ].join(' ')}
    >
      <span>{label}</span>
      <span
        className={[
          'inline-flex w-3 justify-center text-[10px] leading-none',
          active ? 'text-[color:var(--text-primary)]' : 'text-transparent',
        ].join(' ')}
        aria-hidden="true"
      >
        {active ? (direction === 'asc' ? '↑' : '↓') : '↑'}
      </span>
    </button>
  )
}

function DiscoverTableHeader({
  sort,
  direction,
  onToggleSort,
}: {
  sort: UniverseSortId
  direction: SortDirection
  onToggleSort: (sort: UniverseSortId) => void
}) {
  return (
    <div
      className={[
        'grid items-center gap-x-5 border-b border-[color:var(--border-subtle)] bg-[color:rgba(8,16,23,0.48)] px-5 py-3 text-[12px] text-[color:var(--text-secondary)]',
        DISCOVER_TABLE_GRID,
      ].join(' ')}
    >
      <SortHeader label="Rank" active={sort === 'rank'} direction={direction} onClick={() => onToggleSort('rank')} />
      <div className="font-medium">Subnet</div>
      <SortHeader label="Score" active={sort === 'score'} direction={direction} align="right" onClick={() => onToggleSort('score')} />
      <SortHeader label="Quality" active={sort === 'quality'} direction={direction} align="right" onClick={() => onToggleSort('quality')} />
      <SortHeader label="Opportunity" active={sort === 'mispricing'} direction={direction} align="right" onClick={() => onToggleSort('mispricing')} />
      <SortHeader label="Risk" active={sort === 'fragility'} direction={direction} align="right" onClick={() => onToggleSort('fragility')} />
      <SortHeader label="Confidence" active={sort === 'confidence'} direction={direction} align="right" onClick={() => onToggleSort('confidence')} />
      <div className="pl-4 font-medium">Status</div>
    </div>
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
}) {
  const router = useRouter()
  const pathname = usePathname()

  const [search, setSearch] = useState('')
  const [sort, setSort] = useState<UniverseSortId>('rank')
  const [direction, setDirection] = useState<SortDirection>('asc')
  const [marketTimeframe, setMarketTimeframe] = useState<MarketTimeframeId>('max')
  const [compareIds, setCompareIds] = useState<number[]>([])
  const [focusedId, setFocusedId] = useState<number | null>(null)
  const [pinnedId, setPinnedId] = useState<number | null>(null)
  const [previewHistory, setPreviewHistory] = useState<SubnetSignalHistoryPoint[] | null>(null)
  const [previewHistoryStatus, setPreviewHistoryStatus] = useState<'idle' | 'loading' | 'ready' | 'unavailable'>('idle')
  const [queryStateReady, setQueryStateReady] = useState(false)

  useEffect(() => {
    const params = new URLSearchParams(window.location.search)
    setSearch(params.get('q') ?? '')
    setSort(parseSort(params.get('sort')))
    setDirection(parseDirection(params.get('dir')))
    setMarketTimeframe(parseMarketTimeframe(params.get('tf')))
    setCompareIds(parseIds(params.get('ids')))
    setQueryStateReady(true)
  }, [])

  useEffect(() => {
    if (!queryStateReady) return

    const params = new URLSearchParams()
    if (search.trim()) params.set('q', search.trim())
    if (sort !== 'rank') params.set('sort', sort)
    if (direction !== 'asc') params.set('dir', direction)
    if (marketTimeframe !== 'max') params.set('tf', marketTimeframe)
    if (compareIds.length) params.set('ids', compareIds.join(','))
    const next = params.toString()
    router.replace(next ? `${pathname}?${next}` : pathname, { scroll: false })
  }, [compareIds, direction, marketTimeframe, pathname, queryStateReady, router, search, sort])

  useEffect(() => {
    const previewId = pinnedId ?? focusedId
    if (!previewId) return

    const row = subnets.find((item) => item.netuid === previewId)
    if (!row) return

    router.prefetch(`/subnets/${row.netuid}`)
    void warmDetailPayload(row.netuid)
  }, [focusedId, pinnedId, router, subnets])

  const rows = useMemo(() => {
    const searched = search.trim() ? subnets.filter((subnet) => queryMatches(subnet, search)) : subnets
    const sorted = sortUniverseRows(searched.map(toUniverseRow), sort)
    return direction === 'asc' ? sorted : reverseRows(sorted)
  }, [direction, search, sort, subnets])

  useEffect(() => {
    if (!rows.length) return

    let cancelled = false
    let idleId: number | null = null
    let timeoutId: ReturnType<typeof setTimeout> | null = null

    const warmRows = rows.slice(0, DETAIL_WARMUP_LIMIT)

    const runWarmup = () => {
      if (cancelled) return
      warmRows.forEach((row) => {
        router.prefetch(row.href)
        void warmDetailPayload(row.id)
      })
    }

    if (typeof window !== 'undefined' && 'requestIdleCallback' in window) {
      idleId = window.requestIdleCallback(() => {
        runWarmup()
      })
    } else {
      timeoutId = setTimeout(() => {
        runWarmup()
      }, 350)
    }

    return () => {
      cancelled = true
      if (idleId != null && typeof window !== 'undefined' && 'cancelIdleCallback' in window) {
        window.cancelIdleCallback(idleId)
      }
      if (timeoutId != null) {
        clearTimeout(timeoutId)
      }
    }
  }, [router, rows])

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

  useEffect(() => {
    const previewNetuid = pinnedId ?? focusedId
    if (!previewNetuid) {
      setPreviewHistory(null)
      setPreviewHistoryStatus('idle')
      return
    }

    const previewSubnet = subnets.find((item) => item.netuid === previewNetuid) ?? null
    if (previewSubnet?.preview_metric_deltas) {
      setPreviewHistory(null)
      setPreviewHistoryStatus('ready')
      return
    }

    const cached = getCachedPreviewHistory(previewNetuid)
    if (cached) {
      setPreviewHistory(cached)
      setPreviewHistoryStatus('ready')
      return
    }

    let cancelled = false
    let timeoutId: ReturnType<typeof setTimeout> | null = null
    setPreviewHistory(null)
    setPreviewHistoryStatus('loading')

    timeoutId = setTimeout(() => {
      void loadPreviewHistory(previewNetuid)
        .then((points) => {
          if (!cancelled) {
            setPreviewHistory(points)
            setPreviewHistoryStatus('ready')
          }
        })
        .catch(() => {
          if (!cancelled) {
            setPreviewHistory(null)
            setPreviewHistoryStatus('unavailable')
          }
        })
    }, pinnedId === previewNetuid ? 0 : 180)

    return () => {
      cancelled = true
      if (timeoutId != null) {
        clearTimeout(timeoutId)
      }
    }
  }, [focusedId, pinnedId, subnets])

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
  const previewSubnet = previewId != null ? subnets.find((subnet) => subnet.netuid === previewId) ?? null : null
  const metricDeltas = useMemo(
    () =>
      normalizePreviewMetricDeltas(previewSubnet?.preview_metric_deltas) ??
      buildPreviewMetricDeltasFromHistory(previewHistory),
    [previewHistory, previewSubnet?.preview_metric_deltas],
  )
  const metricHistoryStatus = metricDeltas
    ? 'ready'
    : previewHistoryStatus === 'loading' || previewHistoryStatus === 'idle'
      ? 'loading'
      : 'unavailable'
  const rankDeltaMap = useMemo(() => buildRankDeltaMap(subnets), [subnets])
  const compareItems = compareIds
    .map((id) => subnets.find((subnet) => subnet.netuid === id))
    .filter((item): item is SubnetSummary => Boolean(item))
    .map((subnet) => ({
      id: subnet.netuid,
      name: subnet.name?.trim() || `SN${subnet.netuid}`,
    }))
  const marketForTimeframe = useMemo(() => applyMarketTimeframe(market, marketTimeframe), [market, marketTimeframe])

  return (
    <div className="space-y-6 pb-28">
      <DiscoverMarketHero
        market={marketForTimeframe}
        lastRun={lastRun}
        timeframe={marketTimeframe}
        timeframeControl={
          <SegmentedControl
            items={[...MARKET_TIMEFRAME_ITEMS]}
            value={marketTimeframe}
            onChange={(value) => setMarketTimeframe(value as MarketTimeframeId)}
          />
        }
      />

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

      <section className="grid gap-5 xl:grid-cols-[minmax(0,1fr)_300px]">
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
              <div className="hidden overflow-x-auto md:block">
                <div className="min-w-[940px]">
                  <DiscoverTableHeader sort={sort} direction={direction} onToggleSort={toggleSort} />

                  <div>
                    {rows.map((row) => (
                      <DecisionRow
                        key={row.id}
                        row={row}
                        rankDelta={rankDeltaMap.get(row.id) ?? null}
                        selected={compareIds.includes(row.id)}
                        focused={previewId === row.id}
                        pinned={pinnedId === row.id}
                        onFocus={() => handlePreviewFocus(row.id)}
                        onSelect={() => handlePinToggle(row.id)}
                        linkName
                      />
                    ))}
                  </div>
                </div>
              </div>

              <div className="overflow-x-auto md:hidden">
                <div className="min-w-[940px]">
                  <DiscoverTableHeader sort={sort} direction={direction} onToggleSort={toggleSort} />

                  <div>
                    {rows.map((row) => (
                      <DecisionRow
                        key={row.id}
                        row={row}
                        rankDelta={rankDeltaMap.get(row.id) ?? null}
                        selected={false}
                        focused={false}
                        pinned={false}
                        onFocus={() => {}}
                        linkName
                      />
                    ))}
                  </div>
                </div>
              </div>
            </>
          ) : (
            <div className="p-8 text-center text-sm text-[color:var(--text-secondary)]">
              No subnets match the current search.
            </div>
          )}
        </section>

        <SidePreviewPanel row={previewRow} metricDeltas={metricDeltas} metricHistoryStatus={metricHistoryStatus} />
      </section>

      <CompareDock items={compareItems} onRemove={(id) => setCompareIds((current) => current.filter((item) => item !== id))} />
    </div>
  )
}
