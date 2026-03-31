import BacktestTable from '@/components/BacktestTable'
import DistributionChart from '@/components/DistributionChart'
import PrimarySignalBoard from '@/components/PrimarySignalBoard'
import ScoreGauge from '@/components/ScoreGauge'
import SubnetTable from '@/components/SubnetTable'
import { fetchDistribution, fetchLabelBacktests, fetchLatestRun, fetchSubnets } from '@/lib/api'
import { selectSignalLeaders } from '@/lib/signalSelection'

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
  const [{ subnets: allSubnets }, dist, latest, backtests] = await Promise.all([
    fetchSubnets(200).catch(() => ({ subnets: [], total: 0 })),
    fetchDistribution().catch(() => ({ buckets: [], total_subnets: 0 })),
    fetchLatestRun().catch(() => ({ last_score_run: null, subnet_count: 0 })),
    fetchLabelBacktests(90).catch(() => ({ labels: [], observations: 0, examples: [], targets: [] })),
  ])

  const investableWithSignals = allSubnets.filter((subnet) => subnet.primary_outputs)
  const bestMispricing = selectSignalLeaders(investableWithSignals, 'mispricing_signal', false, 1)[0]
  const bestQuality = selectSignalLeaders(investableWithSignals, 'fundamental_quality', false, 1)[0]
  const lowestFragility = selectSignalLeaders(investableWithSignals, 'fragility_risk', true, 1)[0]
  const signalLeaders = [
    {
      title: 'Best Mispricing Setup',
      subnet: bestMispricing,
      accent: 'text-sky-300',
    },
    {
      title: 'Best Fundamental Quality',
      subnet: bestQuality,
      accent: 'text-emerald-300',
    },
    {
      title: 'Lowest Fragility',
      subnet: lowestFragility,
      accent: 'text-amber-200',
    },
  ]

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
                The live product now separates structural quality, valuation gap, fragility, and confidence instead of collapsing everything into one score.
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
            {signalLeaders.map(({ title, subnet, accent }) =>
              subnet ? (
                <a key={`${title}-${subnet.netuid}`} href={`/subnets/${subnet.netuid}`} className="rounded-3xl border border-white/10 bg-black/25 p-5 transition-transform hover:-translate-y-1">
                  <div className="mb-4 flex items-center justify-between">
                    <span className="text-xs uppercase tracking-[0.24em] text-stone-500">{title}</span>
                    <span className="rounded-full border border-amber-300/20 bg-amber-200/10 px-2.5 py-1 text-xs text-amber-100">
                      {subnet.label ?? 'Under Review'}
                    </span>
                  </div>
                  <div className="flex items-center gap-4">
                    <ScoreGauge score={subnet.score} signalsWithData={subnet.primary_outputs ? 4 : 0} />
                    <div className="min-w-0 flex-1">
                      <div className="break-words text-lg font-semibold text-stone-100">{subnet.name ?? `Subnet ${subnet.netuid}`}</div>
                      <div className="mt-1 text-sm text-stone-400">{subnet.thesis ?? 'No thesis available yet.'}</div>
                      {subnet.primary_outputs && (
                        <div className={`mt-3 text-xs ${accent}`}>
                          FQ {subnet.primary_outputs.fundamental_quality.toFixed(0)} · MP {subnet.primary_outputs.mispricing_signal.toFixed(0)} · FR {subnet.primary_outputs.fragility_risk.toFixed(0)} · CF {subnet.primary_outputs.signal_confidence.toFixed(0)}
                        </div>
                      )}
                    </div>
                  </div>
                </a>
              ) : null,
            )}
          </div>
        </div>
      </section>

      <section className="space-y-4">
        <div>
          <h2 className="text-sm font-semibold uppercase tracking-[0.24em] text-stone-400">Signal-Led Views</h2>
          <p className="mt-2 max-w-3xl text-sm text-stone-500">
            The same universe should look different depending on whether we care about quality, mispricing, fragility, or confidence.
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
          <h2 className="mb-4 text-sm font-semibold uppercase tracking-[0.24em] text-stone-400">Legacy Distribution</h2>
          <DistributionChart buckets={dist.buckets} />
        </div>
      </section>

      <section className="rounded-[2rem] border border-white/10 bg-white/5 p-6">
        <div className="mb-4">
          <h2 className="text-sm font-semibold uppercase tracking-[0.24em] text-stone-400">All Subnets</h2>
          <p className="mt-2 text-sm text-stone-500">Sort the live universe by mispricing, quality, fragility, confidence, or the legacy composite instead of relying on one dominant score.</p>
        </div>
        <SubnetTable subnets={allSubnets} />
      </section>
    </div>
  )
}
