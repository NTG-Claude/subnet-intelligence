import { notFound } from 'next/navigation'

import ResearchWorkspace from '@/features/research/components/ResearchWorkspace'
import { fetchSubnet, fetchSubnetSignalHistory } from '@/lib/api'
import { buildDetailMemo } from '@/lib/view-models/research'

const SIGNAL_HISTORY_SSR_TIMEOUT_MS = 650

interface Props {
  params: Promise<{ netuid: string }>
}

function withTimeout<T>(promise: Promise<T>, timeoutMs: number, fallback: T): Promise<T> {
  return new Promise((resolve) => {
    const timeoutId = setTimeout(() => resolve(fallback), timeoutMs)
    promise
      .then((value) => {
        clearTimeout(timeoutId)
        resolve(value)
      })
      .catch(() => {
        clearTimeout(timeoutId)
        resolve(fallback)
      })
  })
}

export default async function SubnetPage({ params }: Props) {
  const { netuid: netuidStr } = await params
  const netuid = Number.parseInt(netuidStr, 10)
  if (Number.isNaN(netuid)) notFound()

  let subnet
  let signalHistory = null
  try {
    ;[subnet, signalHistory] = await Promise.all([
      fetchSubnet(netuid),
      withTimeout(fetchSubnetSignalHistory(netuid, 120), SIGNAL_HISTORY_SSR_TIMEOUT_MS, null),
    ])
  } catch {
    notFound()
  }

  return <ResearchWorkspace memo={buildDetailMemo(subnet)} netuid={netuid} initialSignalHistory={signalHistory} />
}
