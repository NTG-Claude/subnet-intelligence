'use client'

import { BacktestLabelSummary } from '@/lib/api'

interface Props {
  labels: BacktestLabelSummary[]
}

function fmt(value: number | null, pct = false): string {
  if (value == null) return '—'
  if (pct) return `${(value * 100).toFixed(1)}%`
  return value.toFixed(3)
}

export default function BacktestTable({ labels }: Props) {
  return (
    <div className="overflow-x-auto rounded-3xl border border-white/10 bg-black/20">
      <table className="w-full text-sm">
        <thead className="bg-white/5 text-xs uppercase tracking-[0.24em] text-stone-400">
          <tr>
            <th className="px-4 py-3 text-left">Label</th>
            <th className="px-4 py-3 text-right">Obs</th>
            <th className="px-4 py-3 text-right">Future Score</th>
            <th className="px-4 py-3 text-right">Return Proxy</th>
            <th className="px-4 py-3 text-right">Slippage Drift</th>
            <th className="px-4 py-3 text-right">Concentration Drift</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-white/10">
          {labels.map((row) => (
            <tr key={row.label} className="text-stone-200">
              <td className="px-4 py-3">{row.label}</td>
              <td className="px-4 py-3 text-right font-mono">{row.observations}</td>
              <td className="px-4 py-3 text-right font-mono">{fmt(row.avg_future_score_change)}</td>
              <td className="px-4 py-3 text-right font-mono">{fmt(row.avg_future_return_proxy, true)}</td>
              <td className="px-4 py-3 text-right font-mono">{fmt(row.avg_future_slippage_deterioration)}</td>
              <td className="px-4 py-3 text-right font-mono">{fmt(row.avg_future_concentration_increase)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
