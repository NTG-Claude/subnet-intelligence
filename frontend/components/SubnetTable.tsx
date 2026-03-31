'use client'

import { useMemo, useState } from 'react'
import Link from 'next/link'
import { SubnetSummary } from '@/lib/api'

type SortKey = 'rank' | 'score' | 'name' | 'netuid' | 'alpha_price_tao' | 'market_cap_tao' | 'staking_apy' | 'label'

interface Props {
  subnets: SubnetSummary[]
  pageSize?: number
}

function scoreBarColor(score: number): string {
  if (score >= 70) return 'bg-emerald-400'
  if (score >= 40) return 'bg-amber-300'
  return 'bg-rose-400'
}

export default function SubnetTable({ subnets, pageSize = 20 }: Props) {
  const [search, setSearch] = useState('')
  const [sortKey, setSortKey] = useState<SortKey>('rank')
  const [sortAsc, setSortAsc] = useState(true)
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

  const toggleSort = (key: SortKey) => {
    if (sortKey === key) {
      setSortAsc((prev) => !prev)
    } else {
      setSortKey(key)
      setSortAsc(true)
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
              <th className="px-4 py-3 text-left"><SortBtn k="rank" label="Rank" /></th>
              <th className="px-4 py-3 text-left"><SortBtn k="netuid" label="SN" /></th>
              <th className="px-4 py-3 text-left"><SortBtn k="name" label="Name" /></th>
              <th className="hidden px-4 py-3 text-left xl:table-cell"><SortBtn k="label" label="Label" /></th>
              <th className="px-4 py-3 text-left"><SortBtn k="score" label="Score" /></th>
              <th className="hidden px-4 py-3 text-right lg:table-cell"><SortBtn k="alpha_price_tao" label="Alpha Price" /></th>
              <th className="hidden px-4 py-3 text-right lg:table-cell"><SortBtn k="market_cap_tao" label="Pool Proxy" /></th>
              <th className="hidden px-4 py-3 text-right md:table-cell"><SortBtn k="staking_apy" label="APY" /></th>
            </tr>
          </thead>
          <tbody className="divide-y divide-white/10">
            {pageData.map((s) => (
              <tr key={s.netuid} className="transition-colors hover:bg-white/5">
                <td className="px-4 py-3 tabular-nums text-stone-400">#{s.rank ?? '—'}</td>
                <td className="px-4 py-3 font-mono text-xs text-stone-400">{s.netuid}</td>
                <td className="px-4 py-3">
                  <Link href={`/subnets/${s.netuid}`} className="font-medium text-stone-100 transition-colors hover:text-lime-300">
                    {s.name ?? `Subnet ${s.netuid}`}
                  </Link>
                  {s.thesis && <div className="mt-1 max-w-md text-xs text-stone-500">{s.thesis}</div>}
                  {s.primary_outputs && (
                    <div className="mt-2 flex flex-wrap gap-2 text-[11px] text-stone-400">
                      <span>FQ {s.primary_outputs.fundamental_quality.toFixed(0)}</span>
                      <span>MP {s.primary_outputs.mispricing_signal.toFixed(0)}</span>
                      <span>FR {s.primary_outputs.fragility_risk.toFixed(0)}</span>
                      <span>CF {s.primary_outputs.signal_confidence.toFixed(0)}</span>
                    </div>
                  )}
                </td>
                <td className="hidden px-4 py-3 xl:table-cell">
                  <span className="rounded-full border border-amber-300/20 bg-amber-200/10 px-2.5 py-1 text-xs text-amber-100">
                    {s.label ?? 'Under Review'}
                  </span>
                </td>
                <td className="px-4 py-3">
                  <div className="flex items-center gap-2">
                    <div className="h-1.5 w-24 overflow-hidden rounded-full bg-stone-900">
                      <div className={`h-full rounded-full ${scoreBarColor(s.score)}`} style={{ width: `${s.score}%` }} />
                    </div>
                    <span className="font-semibold tabular-nums text-stone-100">{s.score.toFixed(1)}</span>
                  </div>
                </td>
                <td className="hidden px-4 py-3 text-right tabular-nums text-stone-300 lg:table-cell">
                  {s.alpha_price_tao != null && s.alpha_price_tao > 0 ? `τ${s.alpha_price_tao < 0.001 ? s.alpha_price_tao.toExponential(2) : s.alpha_price_tao.toFixed(4)}` : '—'}
                </td>
                <td className="hidden px-4 py-3 text-right tabular-nums text-stone-300 lg:table-cell">
                  {s.market_cap_tao != null && s.market_cap_tao > 0 ? `τ${s.market_cap_tao >= 1000 ? `${(s.market_cap_tao / 1000).toFixed(1)}k` : s.market_cap_tao.toFixed(0)}` : '—'}
                </td>
                <td className="hidden px-4 py-3 text-right tabular-nums md:table-cell">
                  {s.staking_apy != null && s.staking_apy > 0 ? <span className="font-medium text-emerald-300">{s.staking_apy.toFixed(1)}%</span> : <span className="text-stone-600">—</span>}
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
