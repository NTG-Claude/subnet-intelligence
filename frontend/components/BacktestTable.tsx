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
            <th className="px-4 py-3 text-right">Rel 30d</th>
            <th className="px-4 py-3 text-right">Rel 90d</th>
            <th className="px-4 py-3 text-right">Drawdown</th>
            <th className="px-4 py-3 text-right">Liq Risk</th>
            <th className="px-4 py-3 text-right">Conc Risk</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-white/10">
          {labels.map((row) => (
            <tr key={row.label} className="text-stone-200">
              <td className="px-4 py-3">{row.label}</td>
              <td className="px-4 py-3 text-right font-mono">{row.observations}</td>
              <td className="px-4 py-3 text-right font-mono">{fmt(row.avg_relative_forward_return_vs_tao_30d, true)}</td>
              <td className="px-4 py-3 text-right font-mono">{fmt(row.avg_relative_forward_return_vs_tao_90d, true)}</td>
              <td className="px-4 py-3 text-right font-mono">{fmt(row.avg_drawdown_risk)}</td>
              <td className="px-4 py-3 text-right font-mono">{fmt(row.avg_liquidity_deterioration_risk)}</td>
              <td className="px-4 py-3 text-right font-mono">{fmt(row.avg_concentration_deterioration_risk)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
