'use client'

import { useMemo, useState } from 'react'
import Link from 'next/link'
import { SubnetSummary } from '@/lib/api'

type SortKey =
  | 'rank'
  | 'score'
  | 'name'
  | 'netuid'
  | 'label'
  | 'fundamental_quality'
  | 'mispricing_signal'
  | 'fragility_risk'
  | 'signal_confidence'

type ViewMode = 'mispricing' | 'quality' | 'resilience' | 'confidence' | 'legacy'

interface Props {
  subnets: SubnetSummary[]
  pageSize?: number
}

function scoreBarColor(score: number): string {
  if (score >= 70) return 'bg-emerald-400'
  if (score >= 40) return 'bg-amber-300'
  return 'bg-rose-400'
}

function signalBarColor(value: number, tone: 'quality' | 'mispricing' | 'fragility' | 'confidence'): string {
  if (tone === 'quality') return value >= 65 ? 'bg-emerald-400' : value >= 40 ? 'bg-lime-300' : 'bg-stone-600'
  if (tone === 'mispricing') return value >= 65 ? 'bg-sky-400' : value >= 40 ? 'bg-cyan-300' : 'bg-stone-600'
  if (tone === 'fragility') return value <= 25 ? 'bg-emerald-400' : value <= 50 ? 'bg-amber-300' : 'bg-rose-400'
  return value >= 65 ? 'bg-fuchsia-400' : value >= 40 ? 'bg-rose-300' : 'bg-stone-600'
}

function signalValue(subnet: SubnetSummary, key: 'fundamental_quality' | 'mispricing_signal' | 'fragility_risk' | 'signal_confidence'): number | null {
  return subnet.primary_outputs?.[key] ?? null
}

export default function SubnetTable({ subnets, pageSize = 20 }: Props) {
  const [search, setSearch] = useState('')
  const [viewMode, setViewMode] = useState<ViewMode>('mispricing')
  const [sortKey, setSortKey] = useState<SortKey>('mispricing_signal')
  const [sortAsc, setSortAsc] = useState(false)
  const [page, setPage] = useState(0)

  const filtered = useMemo(() => {
    const q = search.toLowerCase()
    return subnets.filter((s) => (s.name ?? '').toLowerCase().includes(q) || String(s.netuid).includes(q) || (s.label ?? '').toLowerCase().includes(q))
  }, [subnets, search])

  const sorted = useMemo(() => {
    return [...filtered].sort((a, b) => {
      let va: number | string = 0
      let vb: number | string = 0

      if (sortKey === 'name') {
        va = a.name ?? ''
        vb = b.name ?? ''
      } else if (sortKey === 'label') {
        va = a.label ?? ''
        vb = b.label ?? ''
      } else if (sortKey === 'fundamental_quality' || sortKey === 'mispricing_signal' || sortKey === 'fragility_risk' || sortKey === 'signal_confidence') {
        va = signalValue(a, sortKey) ?? (sortKey === 'fragility_risk' ? 999 : -1)
        vb = signalValue(b, sortKey) ?? (sortKey === 'fragility_risk' ? 999 : -1)
      } else if (sortKey === 'rank') {
        va = a.rank ?? 9999
        vb = b.rank ?? 9999
      } else {
        va = ((a as unknown as Record<string, unknown>)[sortKey] as number) ?? 0
        vb = ((b as unknown as Record<string, unknown>)[sortKey] as number) ?? 0
      }

      if (va < vb) return sortAsc ? -1 : 1
      if (va > vb) return sortAsc ? 1 : -1
      return 0
    })
  }, [filtered, sortKey, sortAsc])

  const totalPages = Math.ceil(sorted.length / pageSize)
  const pageData = sorted.slice(page * pageSize, (page + 1) * pageSize)

  const viewButtons: { mode: ViewMode; label: string; key: SortKey; asc: boolean; description: string }[] = [
    { mode: 'mispricing', label: 'Mispricing First', key: 'mispricing_signal', asc: false, description: 'Expectation gaps and delayed price recognition first.' },
    { mode: 'quality', label: 'Quality First', key: 'fundamental_quality', asc: false, description: 'Structural quality first, independent of the legacy score.' },
    { mode: 'resilience', label: 'Lowest Fragility', key: 'fragility_risk', asc: true, description: 'Stress resilience first, with lower fragility ranked higher.' },
    { mode: 'confidence', label: 'Highest Confidence', key: 'signal_confidence', asc: false, description: 'Evidence quality and signal trustworthiness first.' },
    { mode: 'legacy', label: 'Legacy Composite', key: 'score', asc: false, description: 'Compatibility mode using the old composite score.' },
  ]

  const setView = (mode: ViewMode) => {
    const next = viewButtons.find((button) => button.mode === mode)
    if (!next) return
    setViewMode(mode)
    setSortKey(next.key)
    setSortAsc(next.asc)
    setPage(0)
  }

  const toggleSort = (key: SortKey) => {
    if (sortKey === key) {
      setSortAsc((prev) => !prev)
    } else {
      setSortKey(key)
      setSortAsc(key === 'fragility_risk')
      setPage(0)
    }
  }

  const SortBtn = ({ k, label }: { k: SortKey; label: string }) => (
    <button onClick={() => toggleSort(k)} className="flex items-center gap-1 transition-colors hover:text-lime-300">
      {label}
      <span className="text-stone-600">{sortKey === k ? (sortAsc ? '↑' : '↓') : '↕'}</span>
    </button>
  )

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap gap-2">
        {viewButtons.map((button) => (
          <button
            key={button.mode}
            onClick={() => setView(button.mode)}
            className={`rounded-full border px-3 py-1.5 text-xs transition-colors ${
              viewMode === button.mode
                ? 'border-lime-300/30 bg-lime-200/10 text-lime-100'
                : 'border-white/10 bg-white/5 text-stone-400 hover:bg-white/10 hover:text-stone-200'
            }`}
          >
            {button.label}
          </button>
        ))}
      </div>

      <p className="max-w-3xl text-sm text-stone-500">
        {viewButtons.find((button) => button.mode === viewMode)?.description}
      </p>

      <input
        type="search"
        placeholder="Search by name, label, or netuid..."
        value={search}
        onChange={(e) => {
          setSearch(e.target.value)
          setPage(0)
        }}
        className="w-full rounded-2xl border border-white/10 bg-white/5 px-4 py-3 text-sm text-stone-100 placeholder:text-stone-500 focus:outline-none focus:ring-2 focus:ring-lime-300/40 sm:w-96"
      />

      <div className="overflow-x-auto rounded-3xl border border-white/10 bg-black/20 shadow-[0_20px_80px_rgba(0,0,0,0.35)]">
        <table className="w-full text-sm">
          <thead className="bg-white/5 text-xs uppercase tracking-[0.24em] text-stone-400">
            <tr>
              <th className="px-4 py-3 text-left"><SortBtn k="netuid" label="SN" /></th>
              <th className="px-4 py-3 text-left"><SortBtn k="name" label="Name" /></th>
              <th className="hidden px-4 py-3 text-left xl:table-cell"><SortBtn k="label" label="Label" /></th>
              <th className="hidden px-4 py-3 text-right lg:table-cell"><SortBtn k="fundamental_quality" label="FQ" /></th>
              <th className="px-4 py-3 text-right"><SortBtn k="mispricing_signal" label="MP" /></th>
              <th className="hidden px-4 py-3 text-right md:table-cell"><SortBtn k="fragility_risk" label="FR" /></th>
              <th className="hidden px-4 py-3 text-right xl:table-cell"><SortBtn k="signal_confidence" label="CF" /></th>
              <th className="px-4 py-3 text-right"><SortBtn k="score" label="Legacy" /></th>
            </tr>
          </thead>
          <tbody className="divide-y divide-white/10">
            {pageData.map((s) => (
              <tr key={s.netuid} className="transition-colors hover:bg-white/5">
                <td className="px-4 py-3 font-mono text-xs text-stone-400">{s.netuid}</td>
                <td className="px-4 py-3">
                  <Link href={`/subnets/${s.netuid}`} className="font-medium text-stone-100 transition-colors hover:text-lime-300">
                    {s.name ?? `Subnet ${s.netuid}`}
                  </Link>
                  {s.thesis && <div className="mt-1 max-w-md text-xs text-stone-500">{s.thesis}</div>}
                  <div className="mt-2 flex flex-wrap gap-x-4 gap-y-1 text-[11px] text-stone-400">
                    <span>Rank #{s.rank ?? '—'}</span>
                    <span>{s.percentile != null ? `${s.percentile.toFixed(1)} pct` : 'No percentile'}</span>
                    <span>{s.alpha_price_tao != null && s.alpha_price_tao > 0 ? `Price τ${s.alpha_price_tao < 0.001 ? s.alpha_price_tao.toExponential(2) : s.alpha_price_tao.toFixed(4)}` : 'No price'}</span>
                    <span>{s.staking_apy != null && s.staking_apy > 0 ? `APY ${s.staking_apy.toFixed(1)}%` : 'No APY'}</span>
                  </div>
                </td>
                <td className="hidden px-4 py-3 xl:table-cell">
                  <span className="rounded-full border border-amber-300/20 bg-amber-200/10 px-2.5 py-1 text-xs text-amber-100">
                    {s.label ?? 'Under Review'}
                  </span>
                </td>
                <td className="hidden px-4 py-3 text-right lg:table-cell">
                  {s.primary_outputs ? (
                    <div className="space-y-1">
                      <div className="font-semibold tabular-nums text-stone-100">{s.primary_outputs.fundamental_quality.toFixed(1)}</div>
                      <div className="ml-auto h-1.5 w-20 overflow-hidden rounded-full bg-stone-900">
                        <div className={`h-full rounded-full ${signalBarColor(s.primary_outputs.fundamental_quality, 'quality')}`} style={{ width: `${s.primary_outputs.fundamental_quality}%` }} />
                      </div>
                    </div>
                  ) : (
                    <span className="text-stone-600">Awaiting run</span>
                  )}
                </td>
                <td className="px-4 py-3 text-right">
                  {s.primary_outputs ? (
                    <div className="space-y-1">
                      <div className="font-semibold tabular-nums text-stone-100">{s.primary_outputs.mispricing_signal.toFixed(1)}</div>
                      <div className="ml-auto h-1.5 w-20 overflow-hidden rounded-full bg-stone-900">
                        <div className={`h-full rounded-full ${signalBarColor(s.primary_outputs.mispricing_signal, 'mispricing')}`} style={{ width: `${s.primary_outputs.mispricing_signal}%` }} />
                      </div>
                    </div>
                  ) : (
                    <span className="text-stone-600">Awaiting run</span>
                  )}
                </td>
                <td className="hidden px-4 py-3 text-right md:table-cell">
                  {s.primary_outputs ? (
                    <div className="space-y-1">
                      <div className="font-semibold tabular-nums text-stone-100">{s.primary_outputs.fragility_risk.toFixed(1)}</div>
                      <div className="ml-auto h-1.5 w-20 overflow-hidden rounded-full bg-stone-900">
                        <div className={`h-full rounded-full ${signalBarColor(s.primary_outputs.fragility_risk, 'fragility')}`} style={{ width: `${s.primary_outputs.fragility_risk}%` }} />
                      </div>
                    </div>
                  ) : (
                    <span className="text-stone-600">Awaiting run</span>
                  )}
                </td>
                <td className="hidden px-4 py-3 text-right xl:table-cell">
                  {s.primary_outputs ? (
                    <div className="space-y-1">
                      <div className="font-semibold tabular-nums text-stone-100">{s.primary_outputs.signal_confidence.toFixed(1)}</div>
                      <div className="ml-auto h-1.5 w-20 overflow-hidden rounded-full bg-stone-900">
                        <div className={`h-full rounded-full ${signalBarColor(s.primary_outputs.signal_confidence, 'confidence')}`} style={{ width: `${s.primary_outputs.signal_confidence}%` }} />
                      </div>
                    </div>
                  ) : (
                    <span className="text-stone-600">Awaiting run</span>
                  )}
                </td>
                <td className="px-4 py-3">
                  <div className="flex items-center justify-end gap-2">
                    <div className="h-1.5 w-20 overflow-hidden rounded-full bg-stone-900">
                      <div className={`h-full rounded-full ${scoreBarColor(s.score)}`} style={{ width: `${s.score}%` }} />
                    </div>
                    <span className="font-semibold tabular-nums text-stone-100">{s.score.toFixed(1)}</span>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {totalPages > 1 && (
        <div className="flex items-center justify-between text-sm text-stone-400">
          <span>{sorted.length} subnets</span>
          <div className="flex gap-2">
            <button
              onClick={() => setPage((p) => Math.max(0, p - 1))}
              disabled={page === 0}
              className="rounded-2xl bg-white/5 px-3 py-1.5 transition-colors hover:bg-white/10 disabled:cursor-not-allowed disabled:opacity-40"
            >
              ← Prev
            </button>
            <span className="px-3 py-1.5">{page + 1} / {totalPages}</span>
            <button
              onClick={() => setPage((p) => Math.min(totalPages - 1, p + 1))}
              disabled={page === totalPages - 1}
              className="rounded-2xl bg-white/5 px-3 py-1.5 transition-colors hover:bg-white/10 disabled:cursor-not-allowed disabled:opacity-40"
            >
              Next →
            </button>
          </div>
        </div>
      )}
    </div>
  )
}
