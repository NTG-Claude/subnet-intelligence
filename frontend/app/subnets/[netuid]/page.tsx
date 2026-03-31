import { notFound } from 'next/navigation'

import AxisBreakdown from '@/components/AxisBreakdown'
import DriverList from '@/components/DriverList'
import HistoryChart from '@/components/HistoryChart'
import ScoreGauge from '@/components/ScoreGauge'
import SignalBreakdown from '@/components/SignalBreakdown'
import ThesisPanel from '@/components/ThesisPanel'
import { fetchSubnet, PrimaryOutputs } from '@/lib/api'

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

function countSignals(outputs: PrimaryOutputs | null): number {
  if (!outputs) return 0
  return Object.values(outputs).filter((value) => Number.isFinite(value)).length
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

  const { breakdown, history, metadata, analysis, primary_outputs } = subnet
  const primary = primary_outputs ?? analysis?.primary_outputs ?? null
  const chartData = history.map((point) => ({
    date: new Date(point.computed_at).toLocaleDateString('en-US', { month: 'short', day: 'numeric' }),
    score: point.score,
  }))
  const signalCount = countSignals(primary)
  const componentScores: Record<string, number> = primary
    ? {
        fundamental_quality: primary.fundamental_quality,
        mispricing_signal: primary.mispricing_signal,
        fragility_risk: primary.fragility_risk,
        signal_confidence: primary.signal_confidence,
      }
    : {}
  const decomposition = analysis?.earned_reflexive_fragile ?? {}

  return (
    <div className="mx-auto max-w-6xl space-y-8">
      <a href="/" className="inline-flex items-center gap-1 text-sm text-stone-400 transition-colors hover:text-stone-100">
        ← All Subnets
      </a>

      <section className="rounded-[2rem] border border-white/10 bg-[radial-gradient(circle_at_top_left,_rgba(251,191,36,0.18),_transparent_28%),radial-gradient(circle_at_bottom_right,_rgba(52,211,153,0.16),_transparent_28%),linear-gradient(135deg,_rgba(28,25,23,0.96),_rgba(12,10,9,0.92))] p-8">
        <div className="grid gap-8 lg:grid-cols-[0.7fr_1.3fr]">
          <div className="flex justify-center">
            <div className="space-y-3 text-center">
              <div className="text-xs uppercase tracking-[0.24em] text-stone-500">Legacy Composite</div>
              <ScoreGauge score={subnet.score} signalsWithData={signalCount} />
              <p className="max-w-xs text-xs leading-relaxed text-stone-500">
                Kept for compatibility only. The investment thesis should be driven by the four primary outputs below.
              </p>
            </div>
          </div>

          <div className="space-y-4">
            <div className="flex flex-wrap items-start gap-3">
              <h1 className="min-w-0 flex-[1_1_20rem] break-words text-3xl font-semibold text-stone-50">{subnet.name ?? `Subnet ${netuid}`}</h1>
              <span className="rounded-full border border-white/10 bg-black/25 px-3 py-1 text-xs font-mono text-stone-300">SN{netuid}</span>
              <span className="rounded-full border border-amber-300/20 bg-amber-200/10 px-3 py-1 text-xs text-amber-100">{subnet.label ?? 'Under Review'}</span>
            </div>

            <p className="max-w-3xl text-base leading-7 text-stone-300">{subnet.thesis ?? 'No concise thesis generated yet.'}</p>

            <div className="flex flex-wrap gap-x-6 gap-y-2 text-sm text-stone-400">
              {subnet.rank && <span>Rank <strong className="text-stone-100">#{subnet.rank}</strong></span>}
              {subnet.percentile != null && <span>Percentile <strong className="text-stone-100">{subnet.percentile.toFixed(1)}</strong></span>}
              {subnet.score_delta_7d != null && (
                <span>
                  Legacy 7d{' '}
                  <strong className={subnet.score_delta_7d >= 0 ? 'text-emerald-300' : 'text-rose-300'}>
                    {subnet.score_delta_7d >= 0 ? '+' : ''}
                    {subnet.score_delta_7d.toFixed(1)}
                  </strong>
                </span>
              )}
              {subnet.computed_at && <span>Updated <strong className="text-stone-100">{formatDate(subnet.computed_at)}</strong></span>}
            </div>

            <div className="grid gap-3 sm:grid-cols-4">
              {primary ? (
                [
                  { label: 'Fundamental Quality', value: primary.fundamental_quality },
                  { label: 'Mispricing Signal', value: primary.mispricing_signal },
                  { label: 'Fragility Risk', value: primary.fragility_risk },
                  { label: 'Signal Confidence', value: primary.signal_confidence },
                ].map((item) => (
                  <div key={item.label} className="rounded-3xl border border-white/10 bg-black/20 p-4">
                    <div className="text-xs uppercase tracking-[0.24em] text-stone-500">{item.label}</div>
                    <div className="mt-2 text-2xl font-semibold text-stone-100">{item.value.toFixed(1)}</div>
                  </div>
                ))
              ) : (
                <div className="sm:col-span-4 rounded-3xl border border-amber-300/15 bg-amber-300/5 p-4 text-sm text-amber-100">
                  This live row has not been rescored into the new investment framework yet. A fresh production score run will populate the four primary outputs.
                </div>
              )}
            </div>

            <div className="grid gap-3 sm:grid-cols-3">
              {[
                { label: 'Earned Strength', value: decomposition.earned_strength, note: 'Quality-led base strength' },
                { label: 'Reflexive Strength', value: decomposition.reflexive_strength, note: 'Momentum and crowding sensitivity' },
                { label: 'Fragile Strength', value: decomposition.fragile_strength, note: 'Stress-exposed upside' },
              ].map((item) => (
                <div key={item.label} className="rounded-3xl border border-white/10 bg-black/20 p-4">
                  <div className="text-xs uppercase tracking-[0.24em] text-stone-500">{item.label}</div>
                  <div className="mt-2 text-2xl font-semibold text-stone-100">{item.value?.toFixed(1) ?? '—'}</div>
                  <div className="mt-2 text-xs text-stone-500">{item.note}</div>
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
        <h2 className="mb-4 text-sm font-semibold uppercase tracking-[0.24em] text-stone-400">Primary Outputs</h2>
        <AxisBreakdown componentScores={componentScores} />
      </section>

      <section className="grid gap-6 xl:grid-cols-[1.1fr_0.9fr]">
        <div className="rounded-[2rem] border border-white/10 bg-white/5 p-6">
          <h2 className="mb-5 text-sm font-semibold uppercase tracking-[0.24em] text-stone-400">Legacy Compatibility Mapping</h2>
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

      <section className="grid gap-6 xl:grid-cols-2">
        <ThesisPanel
          title="Why The Market May Be Missing It"
          subtitle="Signals that point to structural improvement ahead of price recognition."
          supports={analysis?.why_mispriced?.supports}
          headwinds={analysis?.why_mispriced?.headwinds}
        />
        <ThesisPanel
          title="What Makes The Setup Fragile"
          subtitle="The main drivers that can break the thesis under pressure."
          supports={analysis?.risk_drivers?.offsets}
          headwinds={analysis?.risk_drivers?.fragility}
          bullets={analysis?.thesis_breakers}
        />
      </section>

      <section className="grid gap-6 xl:grid-cols-2">
        <ThesisPanel
          title="Why Confidence Is High Or Low"
          subtitle="Freshness, coverage, and proxy reliance behind the current trust level."
          supports={analysis?.confidence_rationale?.supports}
          headwinds={analysis?.confidence_rationale?.headwinds}
        />
        <ThesisPanel
          title="Quality Evidence"
          subtitle="The metrics most responsible for the structural-quality view."
          supports={analysis?.quality_rationale?.supports}
          headwinds={analysis?.quality_rationale?.headwinds}
        />
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
          <h2 className="mb-5 text-sm font-semibold uppercase tracking-[0.24em] text-stone-400">Legacy Score History</h2>
          <HistoryChart data={chartData} />
        </section>
      )}
    </div>
  )
}
