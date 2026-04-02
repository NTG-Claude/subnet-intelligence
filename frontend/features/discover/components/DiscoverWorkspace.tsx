'use client'

import { useEffect, useMemo, useState } from 'react'
import { usePathname, useRouter, useSearchParams } from 'next/navigation'

import PageHeader from '@/components/ui/PageHeader'
import { SubnetSummary } from '@/lib/api'
import { UniverseRowViewModel, UniverseSortId, sortUniverseRows, toUniverseRow } from '@/lib/view-models/research'

import CompareDock from './CompareDock'
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
  const [sort, setSort] = useState<UniverseSortId>((searchParams.get('sort') as UniverseSortId) ?? 'rank')
  const [direction, setDirection] = useState<SortDirection>((searchParams.get('dir') as SortDirection) ?? 'asc')
  const [compareIds, setCompareIds] = useState<number[]>(parseIds(searchParams.get('ids')))
  const [focusedId, setFocusedId] = useState<number | null>(null)

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

  const previewRow = rows.find((row) => row.id === focusedId) ?? null
  const compareItems = compareIds
    .map((id) => subnets.find((subnet) => subnet.netuid === id))
    .filter((item): item is SubnetSummary => Boolean(item))
    .map((subnet) => ({
      id: subnet.netuid,
      name: subnet.name?.trim() || `SN${subnet.netuid}`,
    }))

  return (
    <div className="space-y-6 pb-28">
      <PageHeader
        title="Discover subnets"
        subtitle="A ranked screening list with minimal noise. Hover a row to inspect the investment read and trust notes on the right."
        variant="compact"
        stats={lastRun ? [{ label: 'Last run', value: lastRun.slice(0, 16).replace('T', ' ') }] : undefined}
      />

      <section className="surface-panel p-4 sm:p-5">
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
      </section>

      <section className="grid gap-6 xl:grid-cols-[minmax(0,1fr)_360px]">
        <section className="surface-panel overflow-hidden p-0">
          <div className="flex items-center justify-between gap-4 border-b border-[color:var(--border-subtle)] px-4 py-3 sm:px-5">
            <div>
              <div className="section-title">Ranked subnets</div>
              <p className="mt-1 text-sm text-[color:var(--text-secondary)]">
                Click any column to sort. Hover a row to inspect why it ranks there and what the trust caveats are.
              </p>
            </div>
            <div className="text-sm text-[color:var(--text-secondary)]">{rows.length} results</div>
          </div>

          {rows.length ? (
            <>
              <div className="hidden md:block">
                <div className="grid grid-cols-[64px_minmax(0,1.35fr)_92px_110px_72px_126px] gap-4 border-b border-[color:var(--border-subtle)] bg-[color:rgba(8,16,23,0.48)] px-4 py-2.5 text-[10px] font-medium uppercase tracking-[0.24em] text-[color:var(--text-tertiary)] sm:px-5">
                  <SortHeader label="Rank" active={sort === 'rank'} direction={direction} onClick={() => toggleSort('rank')} />
                  <div>Subnet</div>
                  <SortHeader label="Strength" active={sort === 'quality'} direction={direction} align="right" onClick={() => toggleSort('quality')} />
                  <SortHeader label="Upside Gap" active={sort === 'mispricing'} direction={direction} align="right" onClick={() => toggleSort('mispricing')} />
                  <SortHeader label="Risk" active={sort === 'fragility'} direction={direction} align="right" onClick={() => toggleSort('fragility')} />
                  <SortHeader label="Evidence Quality" active={sort === 'confidence'} direction={direction} align="right" onClick={() => toggleSort('confidence')} />
                </div>

                <div>
                  {rows.map((row) => (
                    <DecisionRow
                      key={row.id}
                      row={row}
                      selected={compareIds.includes(row.id)}
                      focused={focusedId === row.id}
                      onFocus={() => setFocusedId(row.id)}
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

        <SidePreviewPanel row={previewRow} selected={previewRow ? compareIds.includes(previewRow.id) : false} onToggleCompare={toggleCompare} />
      </section>

      <CompareDock items={compareItems} onRemove={(id) => setCompareIds((current) => current.filter((item) => item !== id))} />
    </div>
  )
}
