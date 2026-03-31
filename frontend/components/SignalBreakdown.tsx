'use client'

import { ScoreBreakdown } from '@/lib/api'

interface Props {
  breakdown: ScoreBreakdown
}

const SIGNALS = [
  { key: 'capital_score', label: 'Legacy Quality Sleeve', maxWeight: 30, description: 'Compatibility sleeve derived from the new fundamental-quality output.' },
  { key: 'activity_score', label: 'Legacy Mispricing Sleeve', maxWeight: 25, description: 'Compatibility sleeve derived from the new mispricing output instead of the old opportunity algebra.' },
  { key: 'efficiency_score', label: 'Legacy Durability Sleeve', maxWeight: 20, description: 'Compatibility sleeve that rewards lower fragility rather than the former anti-reflexivity shortcut.' },
  { key: 'health_score', label: 'Legacy Confidence Sleeve', maxWeight: 15, description: 'Compatibility sleeve derived from evidence quality, freshness, and lower proxy reliance.' },
  { key: 'dev_score', label: 'Legacy Upside Balance', maxWeight: 10, description: 'Compatibility sleeve blending upside with fragility discipline for older consumers.' },
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
