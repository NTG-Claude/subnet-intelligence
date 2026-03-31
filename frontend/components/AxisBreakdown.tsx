'use client'

interface Props {
  componentScores: Record<string, number>
}

const AXES = [
  { key: 'intrinsic_quality', label: 'Intrinsic Quality', tint: 'from-emerald-400 to-lime-300' },
  { key: 'economic_sustainability', label: 'Economic Sustainability', tint: 'from-sky-400 to-cyan-300' },
  { key: 'reflexivity', label: 'Reflexivity / Distortion', tint: 'from-amber-300 to-orange-400' },
  { key: 'stress_robustness', label: 'Stress Robustness', tint: 'from-fuchsia-400 to-rose-300' },
  { key: 'opportunity_gap', label: 'Opportunity Gap', tint: 'from-violet-400 to-indigo-300' },
]

export default function AxisBreakdown({ componentScores }: Props) {
  return (
    <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-5">
      {AXES.map((axis) => {
        const value = componentScores[axis.key] ?? 0
        const width = Math.max(0, Math.min(100, value))
        return (
          <div key={axis.key} className="rounded-3xl border border-white/10 bg-white/5 p-4">
            <div className="mb-2 text-xs uppercase tracking-[0.24em] text-stone-400">{axis.label}</div>
            <div className="mb-3 text-2xl font-semibold text-stone-100">{value.toFixed(1)}</div>
            <div className="h-2 rounded-full bg-stone-900">
              <div className={`h-2 rounded-full bg-gradient-to-r ${axis.tint}`} style={{ width: `${width}%` }} />
            </div>
          </div>
        )
      })}
    </div>
  )
}
