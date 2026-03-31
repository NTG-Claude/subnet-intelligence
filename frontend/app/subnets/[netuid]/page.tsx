import { notFound } from 'next/navigation'

import AxisBreakdown from '@/components/AxisBreakdown'
import DriverList from '@/components/DriverList'
import HistoryChart from '@/components/HistoryChart'
import ScoreGauge from '@/components/ScoreGauge'
import SignalBreakdown from '@/components/SignalBreakdown'
import { fetchSubnet } from '@/lib/api'

export const dynamic = 'force-dynamic'

interface Props {
  params: Promise<{ netuid: string }>
}

function formatDate(iso: string | null): string {
  if (!iso) return '—'
  return new Date(iso).toLocaleDateString('en-US', {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
    timeZone: 'UTC',
  })
}

function countSignals(breakdown: Record<string, number>): number {
  return Object.values(breakdown).filter((value) => value > 0).length
}

export default async function SubnetPage({ params }: Props) {
  const { netuid: netuidStr } = await params
  const netuid = parseInt(netuidStr, 10)
  if (isNaN(netuid)) notFound()

  let subnet
  try {
    subnet = await fetchSubnet(netuid)
  } catch {
    notFound()
  }

  const { breakdown, history, metadata, analysis } = subnet
  const chartData = history.map((point) => ({
    date: new Date(point.computed_at).toLocaleDateString('en-US', { month: 'short', day: 'numeric' }),
    score: point.score,
  }))
  const signalCount = countSignals(breakdown as unknown as Record<string, number>)
  const componentScores = analysis?.component_scores ?? {}
  const decomposition = analysis?.earned_reflexive_fragile ?? {}

  return (
    <div className="mx-auto max-w-6xl space-y-8">
      <a href="/" className="inline-flex items-center gap-1 text-sm text-stone-400 transition-colors hover:text-stone-100">
        ← All Subnets
      </a>

      <section className="rounded-[2rem] border border-white/10 bg-[radial-gradient(circle_at_top_left,_rgba(251,191,36,0.18),_transparent_28%),radial-gradient(circle_at_bottom_right,_rgba(52,211,153,0.16),_transparent_28%),linear-gradient(135deg,_rgba(28,25,23,0.96),_rgba(12,10,9,0.92))] p-8">
        <div className="grid gap-8 lg:grid-cols-[0.7fr_1.3fr]">
          <div className="flex justify-center">
            <ScoreGauge score={subnet.score} signalsWithData={signalCount} />
          </div>
          <div className="space-y-4">
            <div className="flex flex-wrap items-center gap-3">
              <h1 className="text-3xl font-semibold text-stone-50">{subnet.name ?? `Subnet ${netuid}`}</h1>
              <span className="rounded-full border border-white/10 bg-black/25 px-3 py-1 text-xs font-mono text-stone-300">SN{netuid}</span>
              <span className="rounded-full border border-amber-300/20 bg-amber-200/10 px-3 py-1 text-xs text-amber-100">{subnet.label ?? 'Under Review'}</span>
            </div>

            <p className="max-w-3xl text-base leading-7 text-stone-300">{subnet.thesis ?? 'No concise thesis generated yet.'}</p>

            <div className="flex flex-wrap gap-x-6 gap-y-2 text-sm text-stone-400">
              {subnet.rank && <span>Rank <strong className="text-stone-100">#{subnet.rank}</strong></span>}
              {subnet.percentile != null && <span>Percentile <strong className="text-stone-100">{subnet.percentile.toFixed(1)}</strong></span>}
              {subnet.score_delta_7d != null && <span>7d <strong className={subnet.score_delta_7d >= 0 ? 'text-emerald-300' : 'text-rose-300'}>{subnet.score_delta_7d >= 0 ? '+' : ''}{subnet.score_delta_7d.toFixed(1)}</strong></span>}
              {subnet.computed_at && <span>Updated <strong className="text-stone-100">{formatDate(subnet.computed_at)}</strong></span>}
            </div>

            <div className="grid gap-3 sm:grid-cols-3">
              {[
                { label: 'Earned Strength', value: decomposition.earned_strength },
                { label: 'Reflexive Strength', value: decomposition.reflexive_strength },
                { label: 'Fragile Strength', value: decomposition.fragile_strength },
              ].map((item) => (
                <div key={item.label} className="rounded-3xl border border-white/10 bg-black/20 p-4">
                  <div className="text-xs uppercase tracking-[0.24em] text-stone-500">{item.label}</div>
                  <div className="mt-2 text-2xl font-semibold text-stone-100">{item.value?.toFixed(1) ?? '—'}</div>
                </div>
              ))}
            </div>

            <div className="flex flex-wrap gap-3 pt-1">
              <a href={`https://taostats.io/subnet/${netuid}`} target="_blank" rel="noopener noreferrer" className="rounded-2xl bg-white/5 px-3 py-1.5 text-xs text-stone-300 transition-colors hover:bg-white/10">
                Taostats ↗
              </a>
              {metadata?.github_url && <a href={metadata.github_url} target="_blank" rel="noopener noreferrer" className="rounded-2xl bg-white/5 px-3 py-1.5 text-xs text-stone-300 transition-colors hover:bg-white/10">GitHub ↗</a>}
              {metadata?.website && <a href={metadata.website} target="_blank" rel="noopener noreferrer" className="rounded-2xl bg-white/5 px-3 py-1.5 text-xs text-stone-300 transition-colors hover:bg-white/10">Website ↗</a>}
            </div>
          </div>
        </div>
      </section>

      <section className="rounded-[2rem] border border-white/10 bg-white/5 p-6">
        <h2 className="mb-4 text-sm font-semibold uppercase tracking-[0.24em] text-stone-400">Axis Breakdown</h2>
        <AxisBreakdown componentScores={componentScores} />
      </section>

      <section className="grid gap-6 xl:grid-cols-[1.1fr_0.9fr]">
        <div className="rounded-[2rem] border border-white/10 bg-white/5 p-6">
          <h2 className="mb-5 text-sm font-semibold uppercase tracking-[0.24em] text-stone-400">Composite Mapping</h2>
          <SignalBreakdown breakdown={breakdown} />
        </div>
        <div className="rounded-[2rem] border border-white/10 bg-white/5 p-6">
          <h2 className="mb-5 text-sm font-semibold uppercase tracking-[0.24em] text-stone-400">Stress Readout</h2>
          <div className="grid gap-3 sm:grid-cols-2">
            <div className="rounded-3xl border border-white/10 bg-black/20 p-4">
              <div className="text-xs uppercase tracking-[0.24em] text-stone-500">Fragility Class</div>
              <div className="mt-2 text-xl font-semibold capitalize text-stone-100">{analysis?.fragility_class ?? 'unknown'}</div>
            </div>
            <div className="rounded-3xl border border-white/10 bg-black/20 p-4">
              <div className="text-xs uppercase tracking-[0.24em] text-stone-500">Stress Drawdown</div>
              <div className="mt-2 text-xl font-semibold text-stone-100">{analysis?.stress_drawdown?.toFixed(1) ?? '—'}</div>
            </div>
          </div>
          <div className="mt-4 space-y-3">
            {(analysis?.stress_scenarios ?? []).map((scenario) => (
              <div key={scenario.name} className="rounded-2xl border border-white/10 bg-black/20 p-4">
                <div className="flex items-center justify-between gap-3">
                  <span className="text-sm text-stone-200">{scenario.name}</span>
                  <span className="text-xs font-mono text-stone-400">drawdown {scenario.drawdown.toFixed(1)}</span>
                </div>
                <div className="mt-2 h-2 rounded-full bg-stone-900">
                  <div className="h-2 rounded-full bg-gradient-to-r from-fuchsia-400 to-rose-300" style={{ width: `${Math.min(100, scenario.drawdown)}%` }} />
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      <section className="grid gap-6 xl:grid-cols-2">
        <DriverList title="Top Positive Drivers" tone="positive" items={analysis?.top_positive_drivers ?? []} />
        <DriverList title="Top Negative Drivers" tone="negative" items={analysis?.top_negative_drivers ?? []} />
      </section>

      {(analysis?.activated_hard_rules ?? []).length > 0 && (
        <section className="rounded-[2rem] border border-rose-300/15 bg-rose-300/5 p-6">
          <h2 className="mb-4 text-sm font-semibold uppercase tracking-[0.24em] text-rose-200">Activated Hard Rules</h2>
          <div className="flex flex-wrap gap-2">
            {analysis?.activated_hard_rules?.map((rule) => (
              <span key={rule} className="rounded-full border border-rose-300/20 bg-black/20 px-3 py-1 text-xs text-rose-100">
                {rule}
              </span>
            ))}
          </div>
        </section>
      )}

      {chartData.length > 1 && (
        <section className="rounded-[2rem] border border-white/10 bg-white/5 p-6">
          <h2 className="mb-5 text-sm font-semibold uppercase tracking-[0.24em] text-stone-400">Score History</h2>
          <HistoryChart data={chartData} />
        </section>
      )}
    </div>
  )
}
