import { PrimaryOutputs, SubnetSummary } from '@/lib/api'

type SignalKey = keyof PrimaryOutputs

const EXCLUDED_LABELS = new Set([
  'Dereg Candidate',
  'Overrewarded Structure',
  'Fragile Yield Trap',
])

function normalizedName(name: string | null): string {
  return (name ?? '').trim().toLowerCase()
}

function hasKnownName(subnet: SubnetSummary): boolean {
  const name = normalizedName(subnet.name)
  return !!name && name !== 'unknown' && name !== 'for sale'
}

function hasReasonableMarketStructure(subnet: SubnetSummary): boolean {
  const pool = subnet.tao_in_pool ?? 0
  const apy = subnet.staking_apy ?? 0
  return pool >= 7_500 && apy <= 250
}

function isBoardEligible(subnet: SubnetSummary): boolean {
  if (!subnet.primary_outputs) return false
  if (!hasKnownName(subnet)) return false
  if (subnet.label && EXCLUDED_LABELS.has(subnet.label)) return false
  if (!hasReasonableMarketStructure(subnet)) return false
  return true
}

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
    .filter(isBoardEligible)
    .sort((left, right) => {
      const a = valueOf(left, keyName)
      const b = valueOf(right, keyName)
      return invert ? a - b : b - a
    })
    .slice(0, limit)
}

