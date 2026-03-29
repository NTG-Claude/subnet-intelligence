'use client'

import { ScoreBreakdown } from '@/lib/api'

interface Signal {
  key: keyof ScoreBreakdown
  label: string
  maxWeight: number
  description: string
}

// Score v3 — Investment Intelligence Model
const SIGNALS: Signal[] = [
  {
    key: 'capital_score',
    label: 'Undervalue',
    maxWeight: 30,
    description: 'Quality-per-TAO ratio: how much network quality do you get per unit of market cap? High = fundamentally strong but under-priced. The P/E ratio for subnets.',
  },
  {
    key: 'activity_score',
    label: 'Yield Quality',
    maxWeight: 25,
    description: 'Risk-adjusted yield: capped APY (≤500%) weighted by pool depth and emission efficiency. Shallow pools are penalised — deep pools produce stable, reliable yield.',
  },
  {
    key: 'efficiency_score',
    label: 'Network Health',
    maxWeight: 25,
    description: 'Active neurons (7d weight commits), validator count, Gini coefficient of incentives, and top-3 stake concentration. Measures real, decentralised activity.',
  },
  {
    key: 'dev_score',
    label: 'Dev Activity',
    maxWeight: 20,
    description: 'GitHub commits and unique contributors (30d). Open-source development velocity — the long-term sustainability signal.',
  },
]

function barColor(pct: number): string {
  if (pct >= 70) return 'bg-green-500'
  if (pct >= 40) return 'bg-yellow-500'
  return 'bg-red-500'
}

interface Props {
  breakdown: ScoreBreakdown
}

export default function SignalBreakdown({ breakdown }: Props) {
  // v3 uses 4 active signals; health_score is 0 and hidden
  const active = SIGNALS.filter(({ key }) => {
    if (key === 'health_score') return false
    return breakdown[key] > 0 || key === 'dev_score'
  })

  return (
    <div className="space-y-4">
      {active.map(({ key, label, maxWeight, description }) => {
        const value = breakdown[key]
        const pct = (value / maxWeight) * 100

        return (
          <div key={key} className="group">
            <div className="flex items-center justify-between mb-1">
              <div className="flex items-center gap-2">
                <span className="text-sm font-medium text-slate-200">{label}</span>
                <span className="hidden group-hover:block text-xs text-slate-400 bg-slate-800 border border-slate-700 rounded px-2 py-1 max-w-xs z-10 absolute mt-6 shadow-xl">
                  {description}
                </span>
              </div>
              <div className="flex items-center gap-2 text-xs text-slate-400">
                <span className="tabular-nums font-mono">{value.toFixed(1)}</span>
                <span>/ {maxWeight}</span>
              </div>
            </div>

            <div className="h-2 bg-slate-800 rounded-full overflow-hidden">
              <div
                className={`h-full rounded-full transition-all duration-500 ${barColor(pct)}`}
                style={{ width: `${Math.min(100, pct)}%` }}
              />
            </div>

            <p className="mt-1 text-xs text-slate-500 leading-relaxed">{description}</p>
          </div>
        )
      })}
    </div>
  )
}
