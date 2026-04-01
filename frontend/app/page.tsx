import PrimarySignalBoard from '@/components/PrimarySignalBoard'
import SubnetTable from '@/components/SubnetTable'
import { MetricGrid, ResearchPanel, StatusBadge } from '@/components/shared/research-ui'
import { fetchLatestRun, fetchSubnets } from '@/lib/api'
import { formatDateTime } from '@/lib/view-models/research'

export const dynamic = 'force-dynamic'

export default async function HomePage() {
  const [{ subnets }, latest] = await Promise.all([
    fetchSubnets(200).catch(() => ({ subnets: [], total: 0 })),
    fetchLatestRun().catch(() => ({ last_score_run: null, subnet_count: 0 })),
  ])

  const scored = subnets.filter((subnet) => subnet.primary_outputs)
  const focusedUniverse = scored.filter(
    (subnet) => (subnet.tao_in_pool ?? 0) >= 7_500 && (subnet.primary_outputs?.signal_confidence ?? 0) >= 50,
  )
  const lowConfidenceCount = scored.filter((subnet) => (subnet.primary_outputs?.signal_confidence ?? 0) < 50).length
  const awaitingRunCount = subnets.length - scored.length

  return (
    <div className="space-y-6">
      <section className="rounded-[2rem] border border-white/10 bg-white/[0.04] p-5 sm:p-6">
        <div className="flex flex-col gap-5 xl:flex-row xl:items-start xl:justify-between">
          <div className="space-y-3">
            <div className="flex flex-wrap items-center gap-2">
              <StatusBadge tone="neutral">Universe / Screening</StatusBadge>
              <StatusBadge tone={latest.last_score_run ? 'confidence' : 'warning'}>
                {latest.last_score_run ? 'Run complete' : 'Awaiting run'}
              </StatusBadge>
            </div>
            <div>
              <h1 className="text-3xl font-semibold tracking-tight text-stone-50 sm:text-4xl">V2 research terminal</h1>
              <p className="mt-2 max-w-3xl text-sm leading-6 text-stone-400">
                Screen the universe by primary signals, then open the research memo to understand the positive case, the failure conditions, and how much trust the conditioning layer deserves.
              </p>
            </div>
          </div>
          <div className="min-w-0 rounded-3xl border border-white/10 bg-black/20 p-4 xl:max-w-sm">
            <div className="text-[11px] uppercase tracking-[0.24em] text-stone-500">Last scored run</div>
            <div className="mt-2 text-lg font-semibold text-stone-100">{formatDateTime(latest.last_score_run)}</div>
            <p className="mt-2 text-sm leading-6 text-stone-500">
              Focus on the result list first. Signal boards below are secondary research lenses, not the main workflow.
            </p>
          </div>
        </div>

        <div className="mt-5">
          <MetricGrid
            items={[
              { label: 'Tracked universe', value: String(latest.subnet_count || subnets.length) },
              { label: 'Focused universe', value: String(focusedUniverse.length) },
              { label: 'Low-confidence names', value: String(lowConfidenceCount) },
              { label: 'Awaiting run', value: String(awaitingRunCount) },
            ]}
          />
        </div>
      </section>

      <ResearchPanel
        title="Screening Workspace"
        subtitle="The result list is the main surface. Saved views, filters, and compare selection sit around it as research controls rather than hero messaging."
      >
        <SubnetTable subnets={subnets} />
      </ResearchPanel>

      <ResearchPanel
        title="Secondary Views"
        subtitle="These are fast research lenses for idea discovery, but they should lead back into the memo and compare flow."
      >
        <PrimarySignalBoard subnets={scored} />
      </ResearchPanel>
    </div>
  )
}
