'use client'

import { useState, useMemo } from 'react'
import Link from 'next/link'
import { SubnetSummary } from '@/lib/api'

type SortKey = 'rank' | 'score' | 'name' | 'netuid'

interface Props {
  subnets: SubnetSummary[]
  pageSize?: number
}

function scoreBarColor(score: number): string {
  if (score >= 70) return 'bg-green-500'
  if (score >= 40) return 'bg-yellow-500'
  return 'bg-red-500'
}

export default function SubnetTable({ subnets, pageSize = 20 }: Props) {
  const [search, setSearch] = useState('')
  const [sortKey, setSortKey] = useState<SortKey>('rank')
  const [sortAsc, setSortAsc] = useState(true)
  const [page, setPage] = useState(0)

  const filtered = useMemo(() => {
    const q = search.toLowerCase()
    return subnets.filter(
      (s) =>
        (s.name ?? '').toLowerCase().includes(q) ||
        String(s.netuid).includes(q)
    )
  }, [subnets, search])

  const sorted = useMemo(() => {
    return [...filtered].sort((a, b) => {
      let va: number | string = 0
      let vb: number | string = 0
      if (sortKey === 'name') {
        va = a.name ?? ''
        vb = b.name ?? ''
      } else if (sortKey === 'rank') {
        va = a.rank ?? 9999
        vb = b.rank ?? 9999
      } else {
        va = (a as Record<string, unknown>)[sortKey] as number
        vb = (b as Record<string, unknown>)[sortKey] as number
      }
      if (va < vb) return sortAsc ? -1 : 1
      if (va > vb) return sortAsc ? 1 : -1
      return 0
    })
  }, [filtered, sortKey, sortAsc])

  const totalPages = Math.ceil(sorted.length / pageSize)
  const pageData = sorted.slice(page * pageSize, (page + 1) * pageSize)

  const toggleSort = (key: SortKey) => {
    if (sortKey === key) setSort(key, !sortAsc)
    else setSort(key, true)
  }

  function setSort(key: SortKey, asc: boolean) {
    setSortKey(key)
    setSortAsc(asc)
    setPage(0)
  }

  const SortBtn = ({ k, label }: { k: SortKey; label: string }) => (
    <button
      onClick={() => toggleSort(k)}
      className="flex items-center gap-1 hover:text-green-400 transition-colors"
    >
      {label}
      <span className="text-slate-600">
        {sortKey === k ? (sortAsc ? '↑' : '↓') : '↕'}
      </span>
    </button>
  )

  return (
    <div className="space-y-4">
      <input
        type="search"
        placeholder="Search by name or netuid…"
        value={search}
        onChange={(e) => { setSearch(e.target.value); setPage(0) }}
        className="w-full sm:w-72 px-3 py-2 text-sm bg-slate-800 border border-slate-700 rounded-lg text-slate-200 placeholder-slate-500 focus:outline-none focus:ring-1 focus:ring-green-500"
      />

      <div className="overflow-x-auto rounded-xl border border-slate-800">
        <table className="w-full text-sm">
          <thead className="text-xs text-slate-400 uppercase tracking-wider bg-slate-900">
            <tr>
              <th className="px-4 py-3 text-left"><SortBtn k="rank" label="Rank" /></th>
              <th className="px-4 py-3 text-left"><SortBtn k="netuid" label="SN" /></th>
              <th className="px-4 py-3 text-left"><SortBtn k="name" label="Name" /></th>
              <th className="px-4 py-3 text-left"><SortBtn k="score" label="Score" /></th>
              <th className="px-4 py-3 text-left hidden sm:table-cell">Percentile</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-800/50">
            {pageData.map((s) => (
              <tr
                key={s.netuid}
                className="hover:bg-slate-800/40 transition-colors"
              >
                <td className="px-4 py-3 text-slate-400 tabular-nums">
                  #{s.rank ?? '—'}
                </td>
                <td className="px-4 py-3 font-mono text-slate-400 text-xs">
                  {s.netuid}
                </td>
                <td className="px-4 py-3">
                  <Link
                    href={`/subnets/${s.netuid}`}
                    className="font-medium text-slate-200 hover:text-green-400 transition-colors"
                  >
                    {s.name ?? `Subnet ${s.netuid}`}
                  </Link>
                </td>
                <td className="px-4 py-3">
                  <div className="flex items-center gap-2">
                    <div className="w-24 h-1.5 bg-slate-800 rounded-full overflow-hidden">
                      <div
                        className={`h-full rounded-full ${scoreBarColor(s.score)}`}
                        style={{ width: `${s.score}%` }}
                      />
                    </div>
                    <span className="tabular-nums font-semibold text-slate-200">
                      {s.score.toFixed(1)}
                    </span>
                  </div>
                </td>
                <td className="px-4 py-3 text-slate-400 tabular-nums hidden sm:table-cell">
                  {s.percentile != null ? `${s.percentile}%` : '—'}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {totalPages > 1 && (
        <div className="flex items-center justify-between text-sm text-slate-400">
          <span>{sorted.length} subnets</span>
          <div className="flex gap-2">
            <button
              onClick={() => setPage((p) => Math.max(0, p - 1))}
              disabled={page === 0}
              className="px-3 py-1.5 rounded bg-slate-800 hover:bg-slate-700 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
            >
              ← Prev
            </button>
            <span className="px-3 py-1.5">
              {page + 1} / {totalPages}
            </span>
            <button
              onClick={() => setPage((p) => Math.min(totalPages - 1, p + 1))}
              disabled={page === totalPages - 1}
              className="px-3 py-1.5 rounded bg-slate-800 hover:bg-slate-700 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
            >
              Next →
            </button>
          </div>
        </div>
      )}
    </div>
  )
}
