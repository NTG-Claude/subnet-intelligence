import PrimarySignalBoard from '@/components/PrimarySignalBoard'
import SubnetTable from '@/components/SubnetTable'
import { fetchLatestRun, fetchSubnets } from '@/lib/api'
import { buildSignalViews } from '@/lib/signalSelection'

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
  const [{ subnets: allSubnets }, latest] = await Promise.all([
    fetchSubnets(200).catch(() => ({ subnets: [], total: 0 })),
    fetchLatestRun().catch(() => ({ last_score_run: null, subnet_count: 0 })),
  ])

  const investableWithSignals = allSubnets.filter((subnet) => subnet.primary_outputs)
  const focusedUniverse = investableWithSignals.filter(
    (subnet) =>
      (subnet.tao_in_pool ?? 0) >= 7_500 &&
      ((subnet.staking_apy ?? 0) <= 250 || subnet.staking_apy == null),
  )

  const signalLeaders = buildSignalViews(investableWithSignals, 1).slice(0, 3).map((view) => ({
    title: view.title,
    subnet: view.subnets[0],
    accent: 'text-stone-200',
  }))

  return (
    <div className="space-y-10">
      <section className="relative overflow-hidden rounded-[2rem] border border-white/10 bg-[radial-gradient(circle_at_top_left,_rgba(196,181,253,0.24),_transparent_30%),radial-gradient(circle_at_bottom_right,_rgba(163,230,53,0.18),_transparent_35%),linear-gradient(135deg,_rgba(28,25,23,0.95),_rgba(12,10,9,0.92))] p-8 shadow-[0_30px_120px_rgba(0,0,0,0.45)]">
        <div className="grid gap-8 lg:grid-cols-[1.2fr_0.8fr]">
          <div className="space-y-5">
            <div className="inline-flex rounded-full border border-lime-200/20 bg-lime-200/10 px-3 py-1 text-xs uppercase tracking-[0.3em] text-lime-100">
              Investment Framework
            </div>
            <div>
              <h1 className="max-w-3xl text-4xl font-semibold tracking-tight text-stone-50 sm:text-5xl">
                Signal-led subnet research, not one-number ranking.
              </h1>
              <p className="mt-4 max-w-2xl text-base leading-7 text-stone-300">
                Read structural quality, valuation gap, fragility, and confidence as separate signals, then inspect the thesis and break risks before forming an investment view.
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
                <div className="text-xs uppercase tracking-[0.24em] text-stone-500">Primary outputs</div>
                <div className="mt-2 text-lg font-semibold text-stone-100">4 signals</div>
              </div>
              <div className="rounded-3xl border border-white/10 bg-black/20 p-4">
                <div className="text-xs uppercase tracking-[0.24em] text-stone-500">Focused universe</div>
                <div className="mt-2 text-lg font-semibold text-stone-100">{focusedUniverse.length}</div>
              </div>
            </div>

            <div className="grid gap-3 sm:grid-cols-2">
              <div className="rounded-3xl border border-white/10 bg-black/20 p-5">
                <div className="text-xs uppercase tracking-[0.24em] text-stone-500">How To Read It</div>
                <div className="mt-3 space-y-2 text-sm text-stone-300">
                  <div>Start with mispricing and quality together.</div>
                  <div>Use fragility to reject unstable setups.</div>
                  <div>Use confidence to discount weak evidence.</div>
                </div>
              </div>
              <div className="rounded-3xl border border-white/10 bg-black/20 p-5">
                <div className="text-xs uppercase tracking-[0.24em] text-stone-500">Screening Priority</div>
                <div className="mt-3 flex flex-wrap gap-2 text-xs">
                  <span className="rounded-full border border-sky-300/20 bg-sky-300/10 px-3 py-1 text-sky-100">Mispricing with confidence</span>
                  <span className="rounded-full border border-amber-300/20 bg-amber-300/10 px-3 py-1 text-amber-100">Fundamentals vs fragility</span>
                  <span className="rounded-full border border-fuchsia-300/20 bg-fuchsia-300/10 px-3 py-1 text-fuchsia-100">High upside, low trust</span>
                  <span className="rounded-full border border-emerald-300/20 bg-emerald-300/10 px-3 py-1 text-emerald-100">Fragility traps</span>
                </div>
              </div>
            </div>
          </div>

          <div className="space-y-4">
            <div>
              <div className="text-xs uppercase tracking-[0.24em] text-stone-500">Current Screens</div>
              <h2 className="mt-2 text-2xl font-semibold text-stone-50">Three entry points into the research flow</h2>
              <p className="mt-2 text-sm leading-6 text-stone-400">
                These are not different versions of the same score. Each card highlights a different research lens to open a subnet and inspect the full memo.
              </p>
            </div>

            {signalLeaders.map(({ title, subnet, accent }) =>
              subnet ? (
                <a
                  key={`${title}-${subnet.netuid}`}
                  href={`/subnets/${subnet.netuid}`}
                  className="rounded-3xl border border-white/10 bg-black/25 p-5 transition-transform hover:-translate-y-1"
                >
                  <div className="mb-4 flex items-center justify-between gap-3">
                    <span className="text-xs uppercase tracking-[0.24em] text-stone-500">{title}</span>
                    <span className="rounded-full border border-amber-300/20 bg-amber-200/10 px-2.5 py-1 text-xs text-amber-100">
                      {subnet.label ?? 'Under Review'}
                    </span>
                  </div>
                  <div className="min-w-0">
                    <div className="break-words text-xl font-semibold text-stone-100">{subnet.name ?? `Subnet ${subnet.netuid}`}</div>
                    <div className="mt-2 text-sm leading-6 text-stone-400">{subnet.thesis ?? 'No thesis available yet.'}</div>
                    {subnet.primary_outputs && (
                      <div className={`mt-4 flex flex-wrap gap-2 text-xs ${accent}`}>
                        <span className="rounded-full border border-white/10 bg-white/5 px-2.5 py-1">
                          FQ {subnet.primary_outputs.fundamental_quality.toFixed(0)}
                        </span>
                        <span className="rounded-full border border-white/10 bg-white/5 px-2.5 py-1">
                          MP {subnet.primary_outputs.mispricing_signal.toFixed(0)}
                        </span>
                        <span className="rounded-full border border-white/10 bg-white/5 px-2.5 py-1">
                          FR {subnet.primary_outputs.fragility_risk.toFixed(0)}
                        </span>
                        <span className="rounded-full border border-white/10 bg-white/5 px-2.5 py-1">
                          CF {subnet.primary_outputs.signal_confidence.toFixed(0)}
                        </span>
                      </div>
                    )}
                    <div className="mt-4 flex flex-wrap gap-4 text-xs text-stone-500">
                      <span>Pool {(subnet.tao_in_pool ?? 0).toLocaleString('en-US', { maximumFractionDigits: 0 })}</span>
                      <span>APY {subnet.staking_apy != null ? `${subnet.staking_apy.toFixed(1)}%` : 'n/a'}</span>
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
          <h2 className="text-sm font-semibold uppercase tracking-[0.24em] text-stone-400">Signal Boards</h2>
          <p className="mt-2 max-w-3xl text-sm text-stone-500">
            These boards are thematic research views built from the same underlying universe as the table below.
          </p>
        </div>
        <PrimarySignalBoard subnets={investableWithSignals} />
      </section>

      <section className="rounded-[2rem] border border-white/10 bg-white/5 p-6">
        <div className="mb-4">
          <h2 className="text-sm font-semibold uppercase tracking-[0.24em] text-stone-400">Research Universe</h2>
          <p className="mt-2 max-w-3xl text-sm text-stone-500">
            Use the four primary outputs to screen. Then open the detail page for the actual thesis, stress map, and failure conditions.
          </p>
        </div>
        <SubnetTable subnets={allSubnets} />
      </section>
    </div>
  )
}
