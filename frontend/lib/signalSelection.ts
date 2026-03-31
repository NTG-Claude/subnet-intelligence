import { PrimaryOutputs, SubnetSummary } from '@/lib/api'

type SignalKey = keyof PrimaryOutputs

function valueOf(subnet: SubnetSummary, keyName: SignalKey): number {
  return subnet.primary_outputs?.[keyName] ?? 0
}

export function selectSignalLeaders(
  subnets: SubnetSummary[],
  keyName: SignalKey,
  invert = false,
  limit = 5,
): SubnetSummary[] {
  return [...subnets]
    .filter((subnet) => !!subnet.primary_outputs)
    .sort((left, right) => {
      const a = valueOf(left, keyName)
      const b = valueOf(right, keyName)
      return invert ? a - b : b - a
    })
    .slice(0, limit)
}
