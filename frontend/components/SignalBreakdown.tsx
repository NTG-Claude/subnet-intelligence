'use client'

import { ScoreBreakdown } from '@/lib/api'

interface Props {
  breakdown: ScoreBreakdown
}

const SIGNALS = [
  { key: 'capital_score', label: 'Intrinsic Quality', maxWeight: 30, description: 'Earned quality from participation, breadth, informativeness, freshness, and structural distribution.' },
  { key: 'activity_score', label: 'Economic Sustainability', maxWeight: 25, description: 'Reserve depth, slippage resilience, emission efficiency, persistence, and liquidity structure.' },
  { key: 'efficiency_score', label: 'Anti-Reflexivity', maxWeight: 20, description: 'How much of today’s strength survives after removing crowding, flow elasticity, and distortion proxies.' },
  { key: 'health_score', label: 'Stress Robustness', maxWeight: 15, description: 'Scenario resilience under outflows, liquidity shock, validator removal, and concentration stress.' },
  { key: 'dev_score', label: 'Opportunity Gap', maxWeight: 10, description: 'Where internal quality and robustness exceed current market recognition.' },
]

function barColor(pct: number): string {
  if (pct >= 70) return 'bg-emerald-400'
  if (pct >= 40) return 'bg-amber-300'
  return 'bg-rose-400'
}

export default function SignalBreakdown({ breakdown }: Props) {
  return (
    <div className="space-y-4">
      {SIGNALS.map(({ key, label, maxWeight, description }) => {
        const value = breakdown[key as keyof ScoreBreakdown]
        const pct = (value / maxWeight) * 100
        return (
          <div key={key} className="rounded-3xl border border-white/10 bg-black/20 p-4">
            <div className="mb-1 flex items-center justify-between">
              <span className="text-sm font-medium text-stone-100">{label}</span>
              <span className="text-xs font-mono text-stone-400">{value.toFixed(1)} / {maxWeight}</span>
            </div>
            <div className="h-2 overflow-hidden rounded-full bg-stone-900">
              <div className={`h-full rounded-full ${barColor(pct)}`} style={{ width: `${Math.min(100, pct)}%` }} />
            </div>
            <p className="mt-2 text-xs leading-relaxed text-stone-500">{description}</p>
          </div>
        )
      })}
    </div>
  )
}
