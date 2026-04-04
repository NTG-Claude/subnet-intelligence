import { notFound } from 'next/navigation'

import ResearchWorkspace from '@/features/research/components/ResearchWorkspace'
import { fetchSubnet, fetchSubnetSignalHistory } from '@/lib/api'
import { buildDetailMemo } from '@/lib/view-models/research'

interface Props {
  params: Promise<{ netuid: string }>
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
      fetchSubnetSignalHistory(netuid, 120).catch(() => null),
    ])
  } catch {
    notFound()
  }

  return <ResearchWorkspace memo={buildDetailMemo(subnet)} netuid={netuid} initialSignalHistory={signalHistory} />
}
