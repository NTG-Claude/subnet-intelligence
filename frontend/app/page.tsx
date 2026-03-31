import BacktestTable from '@/components/BacktestTable'
import DistributionChart from '@/components/DistributionChart'
import PrimarySignalBoard from '@/components/PrimarySignalBoard'
import ScoreGauge from '@/components/ScoreGauge'
import SubnetTable from '@/components/SubnetTable'
import { fetchDistribution, fetchLabelBacktests, fetchLatestRun, fetchLeaderboard, fetchSubnets } from '@/lib/api'

export const dynamic = 'force-dynamic'

function formatDate(iso: string | null): string {
  if (!iso) return 'Never'
  return new Date(iso).toLocaleString('en-US', {
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
    timeZone: 'UTC',
    timeZoneName: 'short',
  })
}

export default async function HomePage() {
  const [{ subnets: allSubnets }, leaderboard, dist, latest, backtests] = await Promise.all([
    fetchSubnets(200).catch(() => ({ subnets: [], total: 0 })),
    fetchLeaderboard().catch(() => ({ top: [], bottom: [] })),
    fetchDistribution().catch(() => ({ buckets: [], total_subnets: 0 })),
    fetchLatestRun().catch(() => ({ last_score_run: null, subnet_count: 0 })),
    fetchLabelBacktests(90).catch(() => ({ labels: [], observations: 0, examples: [], targets: [] })),
  ])
  const investableWithSignals = allSubnets.filter((subnet) => subnet.primary_outputs)

  return (
    <div className="space-y-10">
      <section className="relative overflow-hidden rounded-[2rem] border border-white/10 bg-[radial-gradient(circle_at_top_left,_rgba(196,181,253,0.24),_transparent_30%),radial-gradient(circle_at_bottom_right,_rgba(163,230,53,0.18),_transparent_35%),linear-gradient(135deg,_rgba(28,25,23,0.95),_rgba(12,10,9,0.92))] p-8 shadow-[0_30px_120px_rgba(0,0,0,0.45)]">
        <div className="grid gap-8 lg:grid-cols-[1.4fr_0.9fr]">
          <div className="space-y-5">
            <div className="inline-flex rounded-full border border-lime-200/20 bg-lime-200/10 px-3 py-1 text-xs uppercase tracking-[0.3em] text-lime-100">
              Investment Framework
            </div>
            <div>
              <h1 className="max-w-3xl text-4xl font-semibold tracking-tight text-stone-50 sm:text-5xl">
                From heuristic ranking to investment-grade subnet research.
              </h1>
              <p className="mt-4 max-w-2xl text-base leading-7 text-stone-300">
                This view now centers fundamental quality, mispricing, fragility, and confidence instead of treating one aggregate score as the whole truth.
              </p>
            </div>
            <div className="grid gap-4 sm:grid-cols-4">
              <div className="rounded-3xl border border-white/10 bg-black/20 p-4">
                <div className="text-xs uppercase tracking-[0.24em] text-stone-500">Last run</div>
                <div className="mt-2 text-lg font-semibold text-stone-100">{formatDate(latest.last_score_run)}</div>
              </div>
              <div className="rounded-3xl border border-white/10 bg-black/20 p-4">
                <div className="text-xs uppercase tracking-[0.24em] text-stone-500">Tracked</div>
                <div className="mt-2 text-lg font-semibold text-stone-100">{latest.subnet_count}</div>
              </div>
              <div className="rounded-3xl border border-white/10 bg-black/20 p-4">
                <div className="text-xs uppercase tracking-[0.24em] text-stone-500">Backtest observations</div>
                <div className="mt-2 text-lg font-semibold text-stone-100">{backtests.observations}</div>
              </div>
              <div className="rounded-3xl border border-white/10 bg-black/20 p-4">
                <div className="text-xs uppercase tracking-[0.24em] text-stone-500">Signal-led names</div>
                <div className="mt-2 text-lg font-semibold text-stone-100">{investableWithSignals.length}</div>
              </div>
            </div>
          </div>

          <div className="grid gap-4 sm:grid-cols-3 lg:grid-cols-1">
            {leaderboard.top.slice(0, 3).map((subnet) => (
              <a key={subnet.netuid} href={`/subnets/${subnet.netuid}`} className="rounded-3xl border border-white/10 bg-black/25 p-5 transition-transform hover:-translate-y-1">
                <div className="mb-4 flex items-center justify-between">
                  <span className="text-xs uppercase tracking-[0.24em] text-stone-500">SN{subnet.netuid}</span>
                  <span className="rounded-full border border-amber-300/20 bg-amber-200/10 px-2.5 py-1 text-xs text-amber-100">
                    {subnet.label ?? 'Under Review'}
                  </span>
                </div>
                <div className="flex items-center gap-4">
                  <ScoreGauge score={subnet.score} />
                  <div className="min-w-0 flex-1">
                    <div className="break-words text-lg font-semibold text-stone-100">{subnet.name ?? `Subnet ${subnet.netuid}`}</div>
                    <div className="mt-1 text-sm text-stone-400">{subnet.thesis ?? 'No thesis available yet.'}</div>
                    {subnet.primary_outputs && (
                      <div className="mt-3 grid grid-cols-2 gap-2 text-xs text-stone-300">
                        <span>FQ {subnet.primary_outputs.fundamental_quality.toFixed(0)}</span>
                        <span>MP {subnet.primary_outputs.mispricing_signal.toFixed(0)}</span>
                        <span>FR {subnet.primary_outputs.fragility_risk.toFixed(0)}</span>
                        <span>CF {subnet.primary_outputs.signal_confidence.toFixed(0)}</span>
                      </div>
                    )}
                  </div>
                </div>
              </a>
            ))}
          </div>
        </div>
      </section>

      <section className="space-y-4">
        <div>
          <h2 className="text-sm font-semibold uppercase tracking-[0.24em] text-stone-400">Signal-Led Views</h2>
          <p className="mt-2 max-w-3xl text-sm text-stone-500">
            The same universe now looks different depending on whether we care about structural quality, valuation gap, fragility, or confidence.
          </p>
        </div>
        <PrimarySignalBoard subnets={investableWithSignals} />
      </section>

      <section className="grid gap-6 xl:grid-cols-[1.2fr_0.8fr]">
        <div className="rounded-[2rem] border border-white/10 bg-white/5 p-6">
          <div className="mb-4 flex items-center justify-between">
            <div>
              <h2 className="text-sm font-semibold uppercase tracking-[0.24em] text-stone-400">Backtest Readout</h2>
              <p className="mt-2 text-sm text-stone-500">Forward proxies for relative returns, drawdown, and market-structure deterioration.</p>
            </div>
          </div>
          <BacktestTable labels={backtests.labels.slice(0, 8)} />
        </div>

        <div className="rounded-[2rem] border border-white/10 bg-white/5 p-6">
          <h2 className="mb-4 text-sm font-semibold uppercase tracking-[0.24em] text-stone-400">Score Distribution</h2>
          <DistributionChart buckets={dist.buckets} />
        </div>
      </section>

      <section className="rounded-[2rem] border border-white/10 bg-white/5 p-6">
        <div className="mb-4">
          <h2 className="text-sm font-semibold uppercase tracking-[0.24em] text-stone-400">All Subnets</h2>
          <p className="mt-2 text-sm text-stone-500">Search across labels, theses, and market structure instead of scanning a flat leaderboard.</p>
        </div>
        <SubnetTable subnets={allSubnets} />
      </section>
    </div>
  )
}
