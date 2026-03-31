import { notFound } from 'next/navigation'

import AxisBreakdown from '@/components/AxisBreakdown'
import ThesisPanel from '@/components/ThesisPanel'
import { fetchSubnet, PrimaryOutputs } from '@/lib/api'

export const dynamic = 'force-dynamic'

interface Props {
  params: Promise<{ netuid: string }>
}

function formatDate(iso: string | null): string {
  if (!iso) return '-'
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

function formatNumber(value: number | null, digits = 0): string {
  if (value == null) return '-'
  return value.toLocaleString('en-US', { maximumFractionDigits: digits, minimumFractionDigits: digits })
}

function formatPrice(value: number | null): string {
  if (value == null) return '-'
  return `t${value.toFixed(4)}`
}

function formatPercent(value: number | null): string {
  if (value == null) return '-'
  return `${value.toFixed(1)}%`
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

  const { metadata, analysis, primary_outputs } = subnet
  const primary = primary_outputs ?? analysis?.primary_outputs ?? null
  const signalCount = countSignals(primary)
  const componentScores: Record<string, number> = primary
    ? {
        fundamental_quality: primary.fundamental_quality,
        mispricing_signal: primary.mispricing_signal,
        fragility_risk: primary.fragility_risk,
        signal_confidence: primary.signal_confidence,
      }
    : {}

  return (
    <div className="mx-auto max-w-6xl space-y-8">
      <a href="/" className="inline-flex items-center gap-1 text-sm text-stone-400 transition-colors hover:text-stone-100">
        Back to research universe
      </a>

      <section className="rounded-[2rem] border border-white/10 bg-[radial-gradient(circle_at_top_left,_rgba(251,191,36,0.18),_transparent_28%),radial-gradient(circle_at_bottom_right,_rgba(52,211,153,0.16),_transparent_28%),linear-gradient(135deg,_rgba(28,25,23,0.96),_rgba(12,10,9,0.92))] p-8">
        <div className="space-y-6">
          <div className="space-y-5">
            <div className="flex flex-wrap items-start gap-3">
              <h1 className="min-w-0 flex-[1_1_20rem] break-words text-3xl font-semibold text-stone-50">
                {subnet.name ?? `Subnet ${netuid}`}
              </h1>
              <span className="rounded-full border border-white/10 bg-black/25 px-3 py-1 text-xs font-mono text-stone-300">SN{netuid}</span>
              <span className="rounded-full border border-amber-300/20 bg-amber-200/10 px-3 py-1 text-xs text-amber-100">
                {subnet.label ?? 'Under Review'}
              </span>
            </div>

            <p className="max-w-3xl text-base leading-7 text-stone-300">
              {subnet.thesis ?? 'No concise thesis generated yet.'}
            </p>

            <div className="flex flex-wrap gap-x-6 gap-y-2 text-sm text-stone-400">
              {subnet.rank && (
                <span>
                  Rank <strong className="text-stone-100">#{subnet.rank}</strong>
                </span>
              )}
              {subnet.percentile != null && (
                <span>
                  Percentile <strong className="text-stone-100">{subnet.percentile.toFixed(1)}</strong>
                </span>
              )}
              {subnet.computed_at && (
                <span>
                  Updated <strong className="text-stone-100">{formatDate(subnet.computed_at)}</strong>
                </span>
              )}
              <span>
                Signals with data <strong className="text-stone-100">{signalCount}/4</strong>
              </span>
            </div>

            <div className="grid gap-4 lg:grid-cols-[1.15fr_0.85fr]">
              <div className="rounded-[1.75rem] border border-white/10 bg-black/20 p-5">
                <div className="text-xs uppercase tracking-[0.24em] text-stone-500">Investment Read</div>
                <div className="mt-3 grid gap-3 sm:grid-cols-2">
                  <div className="rounded-2xl border border-white/10 bg-white/5 p-4">
                    <div className="text-xs uppercase tracking-[0.24em] text-stone-500">Market Structure</div>
                    <div className="mt-2 text-lg font-semibold text-stone-100">{formatNumber(subnet.tao_in_pool)} pool</div>
                    <div className="mt-1 text-sm text-stone-500">{formatPercent(subnet.staking_apy)} staking APY</div>
                  </div>
                  <div className="rounded-2xl border border-white/10 bg-white/5 p-4">
                    <div className="text-xs uppercase tracking-[0.24em] text-stone-500">Stress Profile</div>
                    <div className="mt-2 text-lg font-semibold text-stone-100">{analysis?.fragility_class ?? 'unknown'}</div>
                    <div className="mt-1 text-sm text-stone-500">Drawdown {analysis?.stress_drawdown?.toFixed(1) ?? '-'}</div>
                  </div>
                </div>
              </div>

              <div className="rounded-[1.75rem] border border-white/10 bg-black/20 p-5">
                <div className="text-xs uppercase tracking-[0.24em] text-stone-500">Primary Outputs</div>
                {primary ? (
                  <div className="mt-3 grid gap-3 sm:grid-cols-2">
                    {[
                      { label: 'Fundamental Quality', value: primary.fundamental_quality },
                      { label: 'Mispricing Signal', value: primary.mispricing_signal },
                      { label: 'Fragility Risk', value: primary.fragility_risk },
                      { label: 'Signal Confidence', value: primary.signal_confidence },
                    ].map((item) => (
                      <div key={item.label} className="rounded-2xl border border-white/10 bg-white/5 p-4">
                        <div className="text-xs uppercase tracking-[0.24em] text-stone-500">{item.label}</div>
                        <div className="mt-2 text-2xl font-semibold text-stone-100">{item.value.toFixed(1)}</div>
                      </div>
                    ))}
                  </div>
                ) : (
                  <div className="mt-3 rounded-3xl border border-amber-300/15 bg-amber-300/5 p-4 text-sm text-amber-100">
                    This live row has not been rescored into the new investment framework yet. A fresh production score run will populate the four primary outputs.
                  </div>
                )}
              </div>
            </div>

            <div className="grid gap-3 sm:grid-cols-4">
              <div className="rounded-3xl border border-white/10 bg-black/20 p-4">
                <div className="text-xs uppercase tracking-[0.24em] text-stone-500">Alpha Price</div>
                <div className="mt-2 text-2xl font-semibold text-stone-100">{formatPrice(subnet.alpha_price_tao)}</div>
              </div>
              <div className="rounded-3xl border border-white/10 bg-black/20 p-4">
                <div className="text-xs uppercase tracking-[0.24em] text-stone-500">Market Cap</div>
                <div className="mt-2 text-2xl font-semibold text-stone-100">{formatNumber(subnet.market_cap_tao)}</div>
              </div>
              <div className="rounded-3xl border border-white/10 bg-black/20 p-4">
                <div className="text-xs uppercase tracking-[0.24em] text-stone-500">Pool Depth</div>
                <div className="mt-2 text-2xl font-semibold text-stone-100">{formatNumber(subnet.tao_in_pool)}</div>
              </div>
              <div className="rounded-3xl border border-white/10 bg-black/20 p-4">
                <div className="text-xs uppercase tracking-[0.24em] text-stone-500">Staking APY</div>
                <div className="mt-2 text-2xl font-semibold text-stone-100">{formatPercent(subnet.staking_apy)}</div>
              </div>
            </div>

            <div className="flex flex-wrap gap-3 pt-1">
              <a
                href={`https://taostats.io/subnet/${netuid}`}
                target="_blank"
                rel="noopener noreferrer"
                className="rounded-2xl bg-white/5 px-3 py-1.5 text-xs text-stone-300 transition-colors hover:bg-white/10"
              >
                Taostats
              </a>
              {metadata?.github_url && (
                <a
                  href={metadata.github_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="rounded-2xl bg-white/5 px-3 py-1.5 text-xs text-stone-300 transition-colors hover:bg-white/10"
                >
                  GitHub
                </a>
              )}
              {metadata?.website && (
                <a
                  href={metadata.website}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="rounded-2xl bg-white/5 px-3 py-1.5 text-xs text-stone-300 transition-colors hover:bg-white/10"
                >
                  Website
                </a>
              )}
            </div>
          </div>
        </div>
      </section>

      <section className="grid gap-6 xl:grid-cols-[1.1fr_0.9fr]">
        <div className="rounded-[2rem] border border-white/10 bg-white/5 p-6">
          <div className="mb-4">
            <h2 className="text-sm font-semibold uppercase tracking-[0.24em] text-stone-400">Signal Profile</h2>
            <p className="mt-2 max-w-2xl text-sm text-stone-500">
              This is the core investment view. Quality and mispricing matter only if fragility and confidence do not break the thesis.
            </p>
          </div>
          <AxisBreakdown componentScores={componentScores} />
        </div>

        <div className="rounded-[2rem] border border-white/10 bg-white/5 p-6">
          <h2 className="mb-5 text-sm font-semibold uppercase tracking-[0.24em] text-stone-400">Research Context</h2>
          <div className="space-y-3">
            <div className="rounded-2xl border border-white/10 bg-black/20 p-4">
              <div className="text-xs uppercase tracking-[0.24em] text-stone-500">Thesis Breakers</div>
              <div className="mt-3 space-y-2">
                {(analysis?.thesis_breakers ?? []).length === 0 && (
                  <div className="text-sm text-stone-500">No explicit thesis breakers recorded.</div>
                )}
                {(analysis?.thesis_breakers ?? []).map((breaker) => (
                  <div key={breaker} className="rounded-2xl border border-amber-300/15 bg-amber-300/5 p-3 text-sm text-stone-300">
                    {breaker}
                  </div>
                ))}
              </div>
            </div>
            {(analysis?.activated_hard_rules ?? []).length > 0 && (
              <div className="rounded-2xl border border-white/10 bg-black/20 p-4">
                <div className="text-xs uppercase tracking-[0.24em] text-stone-500">Activated Hard Rules</div>
                <div className="mt-3 flex flex-wrap gap-2">
                  {analysis?.activated_hard_rules?.map((rule) => (
                    <span key={rule} className="rounded-full border border-rose-300/20 bg-rose-300/10 px-3 py-1 text-xs text-rose-100">
                      {rule}
                    </span>
                  ))}
                </div>
              </div>
            )}
          </div>
        </div>
      </section>

      <section className="grid gap-6 xl:grid-cols-[1.1fr_0.9fr]">
        <div className="rounded-[2rem] border border-white/10 bg-white/5 p-6">
          <h2 className="mb-5 text-sm font-semibold uppercase tracking-[0.24em] text-stone-400">Stress Readout</h2>
          <div className="grid gap-3 sm:grid-cols-2">
            <div className="rounded-3xl border border-white/10 bg-black/20 p-4">
              <div className="text-xs uppercase tracking-[0.24em] text-stone-500">Fragility Class</div>
              <div className="mt-2 text-xl font-semibold capitalize text-stone-100">{analysis?.fragility_class ?? 'unknown'}</div>
            </div>
            <div className="rounded-3xl border border-white/10 bg-black/20 p-4">
              <div className="text-xs uppercase tracking-[0.24em] text-stone-500">Stress Drawdown</div>
              <div className="mt-2 text-xl font-semibold text-stone-100">{analysis?.stress_drawdown?.toFixed(1) ?? '-'}</div>
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
                  <div
                    className="h-2 rounded-full bg-gradient-to-r from-fuchsia-400 to-rose-300"
                    style={{ width: `${Math.min(100, scenario.drawdown)}%` }}
                  />
                </div>
              </div>
            ))}
          </div>
        </div>

        <div className="rounded-[2rem] border border-white/10 bg-white/5 p-6">
          <div className="mb-4">
            <h2 className="text-sm font-semibold uppercase tracking-[0.24em] text-stone-400">Quick Context</h2>
            <p className="mt-2 text-sm text-stone-500">
              These fields stay visible because they often decide whether an otherwise interesting thesis is actually investable.
            </p>
          </div>
          <div className="grid gap-3 sm:grid-cols-2">
            <div className="rounded-2xl border border-white/10 bg-black/20 p-4">
              <div className="text-xs uppercase tracking-[0.24em] text-stone-500">Pool Depth</div>
              <div className="mt-2 text-xl font-semibold text-stone-100">{formatNumber(subnet.tao_in_pool)}</div>
            </div>
            <div className="rounded-2xl border border-white/10 bg-black/20 p-4">
              <div className="text-xs uppercase tracking-[0.24em] text-stone-500">Alpha Price</div>
              <div className="mt-2 text-xl font-semibold text-stone-100">{formatPrice(subnet.alpha_price_tao)}</div>
            </div>
            <div className="rounded-2xl border border-white/10 bg-black/20 p-4">
              <div className="text-xs uppercase tracking-[0.24em] text-stone-500">Market Cap</div>
              <div className="mt-2 text-xl font-semibold text-stone-100">{formatNumber(subnet.market_cap_tao)}</div>
            </div>
            <div className="rounded-2xl border border-white/10 bg-black/20 p-4">
              <div className="text-xs uppercase tracking-[0.24em] text-stone-500">Staking APY</div>
              <div className="mt-2 text-xl font-semibold text-stone-100">{formatPercent(subnet.staking_apy)}</div>
            </div>
          </div>
        </div>
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
    </div>
  )
}
