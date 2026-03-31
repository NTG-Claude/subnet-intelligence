import { SubnetSummary } from '@/lib/api'

export interface SignalView {
  id: string
  title: string
  subtitle: string
  accent: string
  subnets: SubnetSummary[]
}

function outputsOf(subnet: SubnetSummary) {
  return subnet.primary_outputs
}

function withSignals(subnets: SubnetSummary[]): SubnetSummary[] {
  return subnets.filter((subnet) => !!outputsOf(subnet))
}

function sortByScore(
  subnets: SubnetSummary[],
  scorer: (subnet: SubnetSummary) => number,
  limit = 5,
): SubnetSummary[] {
  return [...subnets].sort((left, right) => scorer(right) - scorer(left)).slice(0, limit)
}

function confidenceAdjustedMispricing(subnet: SubnetSummary): number {
  const outputs = outputsOf(subnet)
  if (!outputs) return 0
  return outputs.mispricing_signal * (0.55 + 0.45 * (outputs.signal_confidence / 100))
}

export function buildSignalViews(subnets: SubnetSummary[], limit = 5): SignalView[] {
  const candidates = withSignals(subnets)

  return [
    {
      id: 'mispricing-confidence',
      title: 'Highest Mispricing, High Confidence',
      subtitle: 'Expectation gaps with cleaner evidence quality.',
      accent: 'from-sky-400 to-cyan-300',
      subnets: sortByScore(
        candidates,
        (subnet) => {
          const outputs = outputsOf(subnet)!
          return confidenceAdjustedMispricing(subnet) - 0.12 * outputs.fragility_risk
        },
        limit,
      ),
    },
    {
      id: 'quality-resilience',
      title: 'Strong Fundamentals, Low Fragility',
      subtitle: 'Earned quality that is less exposed under stress.',
      accent: 'from-emerald-400 to-lime-300',
      subnets: sortByScore(
        candidates,
        (subnet) => {
          const outputs = outputsOf(subnet)!
          return 0.6 * outputs.fundamental_quality + 0.4 * (100 - outputs.fragility_risk)
        },
        limit,
      ),
    },
    {
      id: 'upside-low-confidence',
      title: 'High Upside, Low Confidence',
      subtitle: 'Potentially interesting, but evidence quality is weaker.',
      accent: 'from-violet-400 to-fuchsia-300',
      subnets: sortByScore(
        candidates.filter((subnet) => (outputsOf(subnet)?.signal_confidence ?? 0) < 55),
        (subnet) => {
          const outputs = outputsOf(subnet)!
          return outputs.mispricing_signal - 0.35 * outputs.signal_confidence
        },
        limit,
      ),
    },
    {
      id: 'fragility-traps',
      title: 'Fragility Traps',
      subtitle: 'Setups where reflexivity and thin structure dominate.',
      accent: 'from-amber-300 to-orange-400',
      subnets: sortByScore(
        candidates,
        (subnet) => {
          const outputs = outputsOf(subnet)!
          return outputs.fragility_risk + 0.2 * outputs.mispricing_signal
        },
        limit,
      ),
    },
    {
      id: 'crowded-quality',
      title: 'Crowded Quality Names',
      subtitle: 'Quality that may already be heavily owned or reflexive.',
      accent: 'from-rose-300 to-fuchsia-400',
      subnets: sortByScore(
        candidates.filter((subnet) => (subnet.label ?? '').includes('Reflexive Crowded Trade')),
        (subnet) => {
          const outputs = outputsOf(subnet)!
          return 0.65 * outputs.fundamental_quality + 0.35 * outputs.signal_confidence
        },
        limit,
      ),
    },
  ]
}
