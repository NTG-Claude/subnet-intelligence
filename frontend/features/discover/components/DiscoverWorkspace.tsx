'use client'

import { useEffect, useMemo, useState } from 'react'
import { usePathname, useRouter, useSearchParams } from 'next/navigation'

import PageHeader from '@/components/ui/PageHeader'
import { SubnetSummary } from '@/lib/api'
import { cn } from '@/lib/formatting'
import { toUniverseRow } from '@/lib/view-models/research'

import CompareDock from './CompareDock'
import DecisionRow, { MobileDecisionCard } from './DecisionRow'
import SidePreviewPanel from './SidePreviewPanel'

type DiscoverFilterId = 'top-ranks' | 'undervalued' | 'overvalued'

const FILTER_OPTIONS: { id: DiscoverFilterId; label: string }[] = [
  { id: 'top-ranks', label: 'Top ranks' },
  { id: 'undervalued', label: 'Undervalued' },
  { id: 'overvalued', label: 'Overvalued' },
]

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

function sortSubnets(subnets: SubnetSummary[], filter: DiscoverFilterId): SubnetSummary[] {
  const next = [...subnets]

  switch (filter) {
    case 'undervalued':
      return next.sort((left, right) => {
        const a = left.primary_outputs?.mispricing_signal ?? -1
        const b = right.primary_outputs?.mispricing_signal ?? -1
        const aq = left.primary_outputs?.fundamental_quality ?? -1
        const bq = right.primary_outputs?.fundamental_quality ?? -1
        return b - a || bq - aq || (left.rank ?? 9999) - (right.rank ?? 9999)
      })
    case 'overvalued':
      return next.sort((left, right) => {
        const a = left.primary_outputs?.mispricing_signal ?? 101
        const b = right.primary_outputs?.mispricing_signal ?? 101
        const af = left.primary_outputs?.fragility_risk ?? -1
        const bf = right.primary_outputs?.fragility_risk ?? -1
        return a - b || bf - af || (left.rank ?? 9999) - (right.rank ?? 9999)
      })
    default:
      return next.sort((left, right) => (left.rank ?? 9999) - (right.rank ?? 9999))
  }
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
  const [filter, setFilter] = useState<DiscoverFilterId>((searchParams.get('filter') as DiscoverFilterId) ?? 'top-ranks')
  const [compareIds, setCompareIds] = useState<number[]>(parseIds(searchParams.get('ids')))
  const [focusedId, setFocusedId] = useState<number | null>(null)

  useEffect(() => {
    const params = new URLSearchParams()
    if (search.trim()) params.set('q', search.trim())
    if (filter !== 'top-ranks') params.set('filter', filter)
    if (compareIds.length) params.set('ids', compareIds.join(','))
    const next = params.toString()
    router.replace(next ? `${pathname}?${next}` : pathname, { scroll: false })
  }, [compareIds, filter, pathname, router, search])

  const rows = useMemo(() => {
    const searched = search.trim() ? subnets.filter((subnet) => queryMatches(subnet, search)) : subnets
    return sortSubnets(searched, filter).map(toUniverseRow)
  }, [filter, search, subnets])

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
        <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
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

          <div className="flex flex-wrap gap-2">
            {FILTER_OPTIONS.map((option) => (
              <button
                key={option.id}
                type="button"
                onClick={() => setFilter(option.id)}
                className={cn(
                  'button-secondary',
                  filter === option.id && 'border-[color:var(--mispricing-border)] bg-[color:var(--mispricing-surface)] text-[color:var(--mispricing-strong)]',
                )}
              >
                {option.label}
              </button>
            ))}
          </div>
        </div>
      </section>

      <section className="grid gap-6 xl:grid-cols-[minmax(0,1fr)_360px]">
        <section className="surface-panel overflow-hidden p-0">
          <div className="flex items-center justify-between gap-4 border-b border-[color:var(--border-subtle)] px-4 py-4 sm:px-5">
            <div>
              <div className="section-title">Ranked subnets</div>
              <p className="mt-1 text-sm text-[color:var(--text-secondary)]">
                Hover a row to inspect why it ranks there and what the trust caveats are.
              </p>
            </div>
            <div className="text-sm text-[color:var(--text-secondary)]">{rows.length} results</div>
          </div>

          {rows.length ? (
            <>
              <div className="hidden md:block">
                <div className="grid grid-cols-[74px_minmax(0,1.5fr)_88px_88px_88px_88px] gap-3 border-b border-[color:var(--border-subtle)] px-4 py-3 text-[11px] font-medium uppercase tracking-[0.22em] text-[color:var(--text-tertiary)] sm:px-5">
                  <div>Rank</div>
                  <div>Subnet</div>
                  <div>Quality</div>
                  <div>Mispricing</div>
                  <div>Fragility</div>
                  <div>Confidence</div>
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
