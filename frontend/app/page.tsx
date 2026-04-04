import { unstable_cache } from 'next/cache'

import DiscoverWorkspace from '@/features/discover/components/DiscoverWorkspace'
import { fetchDiscoverBootstrap } from '@/lib/api'

export const dynamic = 'force-dynamic'

function DiscoverUnavailable({ message }: { message: string }) {
  return (
    <div className="space-y-6 pb-20">
      <section className="surface-panel p-6 sm:p-8">
        <div className="max-w-3xl">
          <div className="eyebrow">Service status</div>
          <h1 className="mt-3 text-3xl font-semibold tracking-tight text-[color:var(--text-primary)] sm:text-4xl">
            Discover data is temporarily unavailable
          </h1>
          <p className="mt-4 text-base leading-7 text-[color:var(--text-secondary)]">{message}</p>
          <p className="mt-3 text-sm leading-6 text-[color:var(--text-tertiary)]">
            The homepage avoids rendering misleading empty leaderboard data when the backend cannot be reached.
          </p>
        </div>
      </section>
    </div>
  )
}

const getHomepagePayload = unstable_cache(
  async () => {
    const payload = await fetchDiscoverBootstrap(200, 365)
    return {
      subnets: payload.subnets,
      lastRun: payload.last_score_run,
      market: payload.market,
    }
  },
  ['discover-homepage-payload'],
  { revalidate: 300 },
)

export default async function HomePage() {
  let payload
  try {
    payload = await getHomepagePayload()
  } catch {
    return (
      <DiscoverUnavailable message="The frontend could not refresh the discover dataset for this request. Once the backend connection stabilizes, the ranked subnet list and market summary will load normally." />
    )
  }

  return (
    <DiscoverWorkspace
      subnets={payload.subnets}
      lastRun={payload.lastRun}
      market={payload.market}
    />
  )
}
