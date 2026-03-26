'use client'

import { ScoreBreakdown } from '@/lib/api'

interface Signal {
  key: keyof ScoreBreakdown
  label: string
  maxWeight: number
  description: string
}

const SIGNALS: Signal[] = [
  {
    key: 'capital_score',
    label: 'Capital Conviction',
    maxWeight: 25,
    description: 'Net capital flow (30d), unique stakers, and liquidity pool depth. High score = money is actively moving in.',
  },
  {
    key: 'activity_score',
    label: 'Network Activity',
    maxWeight: 25,
    description: 'Miner growth rate, new registrations (7d), and validator weight commits. Measures real participant engagement.',
  },
  {
    key: 'efficiency_score',
    label: 'Emission Efficiency',
    maxWeight: 20,
    description: 'Market cap generated per unit of TAO emission. >1.0 = subnet produces more value than it costs.',
  },
  {
    key: 'health_score',
    label: 'Distribution Health',
    maxWeight: 15,
    description: 'Gini coefficient of miner incentives + top-3 stake concentration. Low concentration = healthier subnet.',
  },
  {
    key: 'dev_score',
    label: 'Dev Activity',
    maxWeight: 15,
    description: 'GitHub commits (30d) and unique contributors. Measures open-source development momentum.',
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
  return (
    <div className="space-y-4">
      {SIGNALS.map(({ key, label, maxWeight, description }) => {
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
