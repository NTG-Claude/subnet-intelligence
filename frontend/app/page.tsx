import { fetchSubnets, fetchLeaderboard, fetchDistribution, fetchLatestRun } from '@/lib/api'
import SubnetTable from '@/components/SubnetTable'
import ScoreGauge from '@/components/ScoreGauge'
import DistributionChart from '@/components/DistributionChart'

export const dynamic = 'force-dynamic'

function formatDate(iso: string | null): string {
  if (!iso) return 'Never'
  return new Date(iso).toLocaleString('en-US', {
    month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit',
    timeZone: 'UTC', timeZoneName: 'short',
  })
}

export default async function HomePage() {
  const [{ subnets: allSubnets }, leaderboard, dist, latest] = await Promise.all([
    fetchSubnets(200).catch(() => ({ subnets: [], total: 0 })),
    fetchLeaderboard().catch(() => ({ top: [], bottom: [] })),
    fetchDistribution().catch(() => ({ buckets: [], total_subnets: 0 })),
    fetchLatestRun().catch(() => ({ last_score_run: null, subnet_count: 0 })),
  ])

  const { top, bottom } = leaderboard

  return (
    <div className="space-y-10">
      {/* Hero */}
      <div className="flex flex-col sm:flex-row sm:items-end justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-100">Subnet Leaderboard</h1>
          <p className="text-slate-400 mt-1 text-sm">
            Composite score (0–100) from 5 on-chain signals · Updated daily at 06:00 UTC
          </p>
        </div>
        <div className="text-right text-xs text-slate-500 shrink-0">
          <div>Last run: <span className="text-slate-400">{formatDate(latest.last_score_run)}</span></div>
          <div>Subnets tracked: <span className="text-slate-400">{latest.subnet_count}</span></div>
        </div>
      </div>

      {/* Top 3 Gauges */}
      {top.length > 0 && (
        <section>
          <h2 className="text-sm font-semibold text-slate-400 uppercase tracking-wider mb-4">Top 3</h2>
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            {top.slice(0, 3).map((s) => (
              <a
                key={s.netuid}
                href={`/subnets/${s.netuid}`}
                className="bg-slate-900 border border-slate-800 rounded-xl p-6 flex flex-col items-center gap-3 hover:border-green-500/40 transition-colors"
              >
                <span className="text-xs text-slate-500 font-mono">SN{s.netuid}</span>
                <ScoreGauge score={s.score} />
                <span className="text-sm font-semibold text-slate-300">
                  {s.name ?? `Subnet ${s.netuid}`}
                </span>
              </a>
            ))}
          </div>
        </section>
      )}

      {/* Distribution Chart */}
      {dist.buckets.length > 0 && (
        <section>
          <h2 className="text-sm font-semibold text-slate-400 uppercase tracking-wider mb-4">
            Score Distribution
          </h2>
          <div className="bg-slate-900 border border-slate-800 rounded-xl p-4">
            <DistributionChart buckets={dist.buckets} />
          </div>
        </section>
      )}

      {/* Full table */}
      <section>
        <h2 className="text-sm font-semibold text-slate-400 uppercase tracking-wider mb-4">
          All Subnets
        </h2>
        <SubnetTable subnets={allSubnets} />
      </section>

      {/* Zombie warning */}
      {bottom.length > 0 && (
        <section>
          <h2 className="text-sm font-semibold text-red-400 uppercase tracking-wider mb-4">
            ⚠ Zombie Warning · Bottom 5
          </h2>
          <div className="bg-red-950/30 border border-red-900/50 rounded-xl overflow-hidden">
            <table className="w-full text-sm">
              <tbody className="divide-y divide-red-900/30">
                {bottom.map((s) => (
                  <tr key={s.netuid} className="flex items-center px-4 py-3 gap-4">
                    <span className="text-red-400 font-mono text-xs w-10">SN{s.netuid}</span>
                    <span className="flex-1 text-slate-300">{s.name ?? `Subnet ${s.netuid}`}</span>
                    <a
                      href={`/subnets/${s.netuid}`}
                      className="text-xs text-slate-500 hover:text-slate-300 transition-colors"
                    >
                      Score: {s.score.toFixed(1)} →
                    </a>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      )}
    </div>
  )
}
