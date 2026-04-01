import {
  AnalysisPreview,
  ConditioningInfo,
  ExplanationContributor,
  KeyUncertainty,
  PrimaryOutputs,
  SubnetDetail,
  SubnetSummary,
} from '@/lib/api'

export type SignalTone = 'quality' | 'mispricing' | 'fragility' | 'confidence' | 'warning' | 'neutral'

export interface SignalStat {
  key: keyof PrimaryOutputs
  label: string
  shortLabel: string
  tone: SignalTone
  value: number | null
  invert?: boolean
}

export interface ResearchHint {
  label: string
  tone: SignalTone
}

export interface UniverseLens {
  id: string
  title: string
  description: string
  emptyMessage: string
}

export interface UniverseRowViewModel {
  id: number
  href: string
  name: string
  netuidLabel: string
  label: string
  thesisLine: string
  decisionLine: string
  signals: SignalStat[]
  positives: ResearchHint[]
  negatives: ResearchHint[]
  warnings: ResearchHint[]
  trustLabel: string
  compareLabel: string
  metrics: { label: string; value: string }[]
  awaitingRun: boolean
}

export interface MemoSectionItem {
  title: string
  body: string
  tone?: SignalTone
  score?: number | null
  meta?: string
}

export interface DetailMemoViewModel {
  name: string
  netuidLabel: string
  href: string
  label: string
  thesis: string
  decisionLine: string
  updatedLabel: string
  rankLabel: string
  percentileLabel: string
  signals: SignalStat[]
  interesting: MemoSectionItem[]
  interestingContributors: Record<string, MemoSectionItem[]>
  blockScores: MemoSectionItem[]
  breaks: MemoSectionItem[]
  fragilityContributors: MemoSectionItem[]
  confidenceItems: MemoSectionItem[]
  uncertainties: MemoSectionItem[]
  conditioningItems: MemoSectionItem[]
  visibilityItems: MemoSectionItem[]
  stressItems: MemoSectionItem[]
  scenarioItems: MemoSectionItem[]
  rawContext: MemoSectionItem[]
  links: { label: string; href: string }[]
  awaitingRun: boolean
}

export const UNIVERSE_LENSES: UniverseLens[] = [
  {
    id: 'all',
    title: 'All investable',
    description: 'Broad universe view for manual screening.',
    emptyMessage: 'No subnet matches the current filters.',
  },
  {
    id: 'high-mispricing-confidence',
    title: 'High mispricing, good confidence',
    description: 'Expectation gaps where the evidence quality is still usable.',
    emptyMessage: 'No clean mispricing setups found in this slice.',
  },
  {
    id: 'strong-quality',
    title: 'Strong quality, acceptable fragility',
    description: 'Structural quality without letting fragility dominate the read.',
    emptyMessage: 'No quality-led setups cleared the fragility filter.',
  },
  {
    id: 'compounders',
    title: 'Low fragility compounders',
    description: 'Names that hold together better under stress.',
    emptyMessage: 'No resilient compounder profile surfaced here.',
  },
  {
    id: 'low-confidence',
    title: 'Interesting but low-confidence',
    description: 'Potential upside that still needs better telemetry.',
    emptyMessage: 'No low-confidence upside names in this slice.',
  },
  {
    id: 'under-review',
    title: 'Telemetry-gap / under-review',
    description: 'Awaiting runs, repaired data, or evidence still under review.',
    emptyMessage: 'No telemetry-gap cases right now.',
  },
]

const SIGNAL_META: Record<keyof PrimaryOutputs, Omit<SignalStat, 'value'>> = {
  fundamental_quality: { key: 'fundamental_quality', label: 'Quality', shortLabel: 'QLTY', tone: 'quality' },
  mispricing_signal: { key: 'mispricing_signal', label: 'Mispricing', shortLabel: 'MISP', tone: 'mispricing' },
  fragility_risk: { key: 'fragility_risk', label: 'Fragility', shortLabel: 'FRAG', tone: 'fragility', invert: true },
  signal_confidence: { key: 'signal_confidence', label: 'Confidence', shortLabel: 'CONF', tone: 'confidence' },
}

const BLOCK_LABELS: Record<string, string> = {
  intrinsic_quality: 'Intrinsic quality',
  economic_sustainability: 'Economic sustainability',
  reflexivity: 'Reflexivity',
  stress_robustness: 'Stress robustness',
  opportunity_gap: 'Opportunity gap',
}

const RELIABILITY_LABELS: Record<string, string> = {
  market_data_reliability: 'Market data reliability',
  validator_data_reliability: 'Validator evidence',
  history_data_reliability: 'Historical depth',
  external_data_reliability: 'External corroboration',
}

function toDisplayName(name: string | null | undefined, netuid: number): string {
  return name?.trim() || `Subnet ${netuid}`
}

export function formatDateTime(iso: string | null | undefined): string {
  if (!iso) return 'No completed run'
  return new Date(iso).toLocaleString('en-US', {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
    timeZone: 'UTC',
    timeZoneName: 'short',
  })
}

export function formatCompactNumber(value: number | null | undefined, digits = 0): string {
  if (value == null) return 'n/a'
  return value.toLocaleString('en-US', {
    maximumFractionDigits: digits,
    minimumFractionDigits: digits,
  })
}

export function formatPrice(value: number | null | undefined): string {
  if (value == null) return 'n/a'
  return value < 0.001 ? `t${value.toExponential(2)}` : `t${value.toFixed(4)}`
}

export function formatPercent(value: number | null | undefined): string {
  if (value == null) return 'n/a'
  return `${value.toFixed(1)}%`
}

function clip(items: string[], limit = 3): string[] {
  return items.filter(Boolean).slice(0, limit)
}

function contributorLabel(item: ExplanationContributor): string {
  return item.short_explanation || item.metric || item.name || item.source_block || 'Unspecified contributor'
}

function contributorTitle(item: ExplanationContributor): string {
  return item.metric || item.name || item.source_block || 'Contributor'
}

function uncertaintyLabel(item: KeyUncertainty): string {
  return item.short_explanation || item.name.replaceAll('_', ' ')
}

function visibilityCount(conditioning: ConditioningInfo | undefined, bucket: string): number {
  return conditioning?.visibility?.[bucket]?.length ?? 0
}

export function getSignalStats(outputs: PrimaryOutputs | null | undefined): SignalStat[] {
  return (Object.keys(SIGNAL_META) as (keyof PrimaryOutputs)[]).map((key) => ({
    ...SIGNAL_META[key],
    value: outputs?.[key] ?? null,
  }))
}

function confidenceValue(subnet: SubnetSummary): number {
  return subnet.primary_outputs?.signal_confidence ?? -1
}

function fragilityValue(subnet: SubnetSummary): number {
  return subnet.primary_outputs?.fragility_risk ?? 101
}

function qualityValue(subnet: SubnetSummary): number {
  return subnet.primary_outputs?.fundamental_quality ?? -1
}

function mispricingValue(subnet: SubnetSummary): number {
  return subnet.primary_outputs?.mispricing_signal ?? -1
}

function summaryHints(preview: AnalysisPreview | null | undefined, tone: SignalTone, source: 'positive' | 'negative'): ResearchHint[] {
  const items =
    source === 'positive' ? preview?.top_positive_drivers ?? [] : preview?.top_negative_drags ?? []
  return items.slice(0, 3).map((item) => ({
    label: contributorLabel(item),
    tone,
  }))
}

function summaryWarnings(subnet: SubnetSummary): ResearchHint[] {
  const preview = subnet.analysis_preview
  const warnings = (preview?.key_uncertainties ?? []).slice(0, 2).map((item) => ({
    label: uncertaintyLabel(item),
    tone: 'warning' as const,
  }))

  if (!subnet.primary_outputs) {
    warnings.unshift({ label: 'Awaiting V2 run output', tone: 'warning' })
  } else if (confidenceValue(subnet) < 50) {
    warnings.unshift({ label: 'Low-confidence evidence mix', tone: 'warning' })
  }

  if (visibilityCount(preview?.conditioning, 'reconstructed') > 0) {
    warnings.push({ label: 'Conditioning repaired some inputs', tone: 'warning' })
  }
  if (visibilityCount(preview?.conditioning, 'discarded') > 0) {
    warnings.push({ label: 'Some inputs were discarded', tone: 'warning' })
  }

  return clip(warnings.map((item) => item.label), 3).map((label) => ({ label, tone: 'warning' }))
}

function trustLabel(subnet: SubnetSummary): string {
  if (!subnet.primary_outputs) return 'Awaiting run'
  if (visibilityCount(subnet.analysis_preview?.conditioning, 'discarded') > 0) return 'Visibility gaps'
  if (visibilityCount(subnet.analysis_preview?.conditioning, 'reconstructed') > 0) return 'Repaired telemetry'
  if (confidenceValue(subnet) < 50) return 'Low confidence'
  if (confidenceValue(subnet) < 65) return 'Adequate confidence'
  return 'Clean enough'
}

function decisionLineFromOutputs(outputs: PrimaryOutputs | null | undefined): string {
  if (!outputs) return 'Research blocked until the latest run produces V2 outputs.'
  if (outputs.mispricing_signal >= 70 && outputs.signal_confidence >= 60 && outputs.fragility_risk <= 45) {
    return 'Upside is visible and the evidence is good enough to underwrite a real thesis.'
  }
  if (outputs.fundamental_quality >= 70 && outputs.fragility_risk <= 40) {
    return 'Quality carries the story, but the entry still depends on how much mispricing remains.'
  }
  if (outputs.fragility_risk >= 65) {
    return 'Any upside case is fragile enough that execution and position sizing have to dominate the call.'
  }
  if (outputs.signal_confidence < 50) {
    return 'Interesting signals exist, but data trust is too soft for a high-conviction read.'
  }
  return 'The setup is investable only if the positive signal mix survives a stricter stress and trust check.'
}

function compareLabel(subnet: SubnetSummary): string {
  if (!subnet.primary_outputs) return 'Add for later'
  return 'Compare'
}

export function toUniverseRow(subnet: SubnetSummary): UniverseRowViewModel {
  const positives = summaryHints(subnet.analysis_preview, 'quality', 'positive')
  const negatives = summaryHints(subnet.analysis_preview, 'fragility', 'negative')
  return {
    id: subnet.netuid,
    href: `/subnets/${subnet.netuid}`,
    name: toDisplayName(subnet.name, subnet.netuid),
    netuidLabel: `SN${subnet.netuid}`,
    label: subnet.label ?? 'Under review',
    thesisLine: subnet.thesis ?? 'No concise thesis has been produced for this run yet.',
    decisionLine: decisionLineFromOutputs(subnet.primary_outputs),
    signals: getSignalStats(subnet.primary_outputs),
    positives,
    negatives,
    warnings: summaryWarnings(subnet),
    trustLabel: trustLabel(subnet),
    compareLabel: compareLabel(subnet),
    metrics: [
      { label: 'Pool', value: formatCompactNumber(subnet.tao_in_pool, 0) },
      { label: 'Price', value: formatPrice(subnet.alpha_price_tao) },
      { label: 'APY', value: formatPercent(subnet.staking_apy) },
      { label: 'Rank', value: subnet.rank ? `#${subnet.rank}` : 'n/a' },
    ],
    awaitingRun: !subnet.primary_outputs,
  }
}

export function applyUniverseLens(subnets: SubnetSummary[], lensId: string): SubnetSummary[] {
  const investable = [...subnets]
  switch (lensId) {
    case 'high-mispricing-confidence':
      return investable
        .filter((subnet) => mispricingValue(subnet) >= 60 && confidenceValue(subnet) >= 55 && fragilityValue(subnet) <= 60)
        .sort((a, b) => mispricingValue(b) + confidenceValue(b) - mispricingValue(a) - confidenceValue(a))
    case 'strong-quality':
      return investable
        .filter((subnet) => qualityValue(subnet) >= 65 && fragilityValue(subnet) <= 60)
        .sort((a, b) => qualityValue(b) - qualityValue(a))
    case 'compounders':
      return investable
        .filter((subnet) => qualityValue(subnet) >= 55 && fragilityValue(subnet) <= 40 && confidenceValue(subnet) >= 50)
        .sort((a, b) => fragilityValue(a) - fragilityValue(b) || qualityValue(b) - qualityValue(a))
    case 'low-confidence':
      return investable
        .filter((subnet) => mispricingValue(subnet) >= 55 && confidenceValue(subnet) > -1 && confidenceValue(subnet) < 50)
        .sort((a, b) => mispricingValue(b) - mispricingValue(a))
    case 'under-review':
      return investable
        .filter(
          (subnet) =>
            !subnet.primary_outputs ||
            confidenceValue(subnet) < 45 ||
            visibilityCount(subnet.analysis_preview?.conditioning, 'reconstructed') > 0 ||
            visibilityCount(subnet.analysis_preview?.conditioning, 'discarded') > 0,
        )
        .sort((a, b) => Number(!a.primary_outputs) - Number(!b.primary_outputs))
    default:
      return investable.sort((a, b) => (a.rank ?? 9999) - (b.rank ?? 9999))
  }
}

function toMemoItems(items: ExplanationContributor[] | undefined, fallbackTone: SignalTone): MemoSectionItem[] {
  return (items ?? []).map((item) => ({
    title: contributorTitle(item),
    body: contributorLabel(item),
    tone: fallbackTone,
    score: typeof item.signed_contribution === 'number' ? Math.abs(item.signed_contribution) * 100 : null,
    meta: item.source_block || item.category,
  }))
}

function toDriverItems(items: KeyUncertainty[] | undefined): MemoSectionItem[] {
  return (items ?? []).map((item) => ({
    title: item.name.replaceAll('_', ' '),
    body: uncertaintyLabel(item),
    tone: 'warning',
    score: typeof item.signed_contribution === 'number' ? Math.abs(item.signed_contribution) * 100 : null,
    meta: item.source_block,
  }))
}

export function buildDetailMemo(subnet: SubnetDetail): DetailMemoViewModel {
  const analysis = subnet.analysis
  const outputs = subnet.primary_outputs ?? analysis?.primary_outputs ?? null
  const conditioning = analysis?.conditioning
  const confidence = analysis?.confidence_rationale
  const reliabilityEntries = Object.entries(conditioning?.reliability ?? {}).map(([key, value]) => ({
    title: RELIABILITY_LABELS[key] ?? key.replaceAll('_', ' '),
    body: `${(value * 100).toFixed(1)} / 100`,
    tone: value >= 0.65 ? 'confidence' : value >= 0.45 ? 'warning' : 'fragility',
  }))

  return {
    name: toDisplayName(subnet.name, subnet.netuid),
    netuidLabel: `SN${subnet.netuid}`,
    href: `/subnets/${subnet.netuid}`,
    label: subnet.label ?? analysis?.label ?? 'Under review',
    thesis: subnet.thesis ?? analysis?.thesis ?? 'No concise thesis generated yet.',
    decisionLine: decisionLineFromOutputs(outputs),
    updatedLabel: formatDateTime(subnet.computed_at),
    rankLabel: subnet.rank ? `#${subnet.rank}` : 'n/a',
    percentileLabel: subnet.percentile != null ? `${subnet.percentile.toFixed(1)}th` : 'n/a',
    signals: getSignalStats(outputs),
    interesting: toMemoItems(analysis?.top_positive_drivers, 'quality'),
    interestingContributors: {
      quality: toMemoItems(analysis?.primary_signal_contributors?.fundamental_quality, 'quality').slice(0, 4),
      mispricing: toMemoItems(analysis?.primary_signal_contributors?.mispricing_signal, 'mispricing').slice(0, 4),
    },
    blockScores: Object.entries(analysis?.block_scores ?? {}).map(([key, value]) => ({
      title: BLOCK_LABELS[key] ?? key.replaceAll('_', ' '),
      body: `${value.toFixed(1)}`,
      tone: value >= 65 ? 'quality' : value <= 45 ? 'warning' : 'neutral',
    })),
    breaks: [
      ...toMemoItems(analysis?.top_negative_drags ?? analysis?.top_negative_drivers, 'fragility'),
      ...(analysis?.thesis_breakers ?? []).map((item) => ({
        title: 'Thesis breaker',
        body: item,
        tone: 'fragility' as const,
      })),
    ],
    fragilityContributors: toMemoItems(analysis?.primary_signal_contributors?.fragility_risk, 'fragility').slice(0, 4),
    confidenceItems: [
      { title: 'Signal confidence', body: outputs ? outputs.signal_confidence.toFixed(1) : 'n/a', tone: 'confidence' },
      { title: 'Data confidence', body: confidence?.data_confidence != null ? confidence.data_confidence.toFixed(1) : 'n/a', tone: 'confidence' },
      { title: 'Market confidence', body: confidence?.market_confidence != null ? confidence.market_confidence.toFixed(1) : 'n/a', tone: 'confidence' },
      { title: 'Thesis confidence', body: confidence?.thesis_confidence != null ? confidence.thesis_confidence.toFixed(1) : 'n/a', tone: 'confidence' },
      ...reliabilityEntries,
    ],
    uncertainties: toDriverItems(analysis?.key_uncertainties),
    conditioningItems: reliabilityEntries,
    visibilityItems: [
      {
        title: 'Reconstructed inputs',
        body: String(visibilityCount(conditioning, 'reconstructed')),
        tone: visibilityCount(conditioning, 'reconstructed') > 0 ? 'warning' : 'neutral',
        meta: conditioning?.visibility?.reconstructed?.slice(0, 4).join(', '),
      },
      {
        title: 'Discarded inputs',
        body: String(visibilityCount(conditioning, 'discarded')),
        tone: visibilityCount(conditioning, 'discarded') > 0 ? 'warning' : 'neutral',
        meta: conditioning?.visibility?.discarded?.slice(0, 4).join(', '),
      },
      {
        title: 'Original inputs',
        body: String(visibilityCount(conditioning, 'original')),
        tone: 'neutral',
      },
      {
        title: 'Bounded inputs',
        body: String(visibilityCount(conditioning, 'bounded')),
        tone: visibilityCount(conditioning, 'bounded') > 0 ? 'warning' : 'neutral',
      },
    ],
    stressItems: [
      { title: 'Fragility class', body: analysis?.fragility_class ?? 'unknown', tone: 'fragility' },
      { title: 'Stress drawdown', body: analysis?.stress_drawdown != null ? `${analysis.stress_drawdown.toFixed(1)}%` : 'n/a', tone: 'fragility' },
      { title: 'Pool depth', body: formatCompactNumber(subnet.tao_in_pool, 0), tone: 'neutral' },
      { title: 'Market cap', body: formatCompactNumber(subnet.market_cap_tao, 0), tone: 'neutral' },
    ],
    scenarioItems: (analysis?.stress_scenarios ?? []).map((scenario) => ({
      title: scenario.name,
      body: `${scenario.drawdown.toFixed(1)}% drawdown`,
      tone: scenario.drawdown >= 30 ? 'fragility' : scenario.drawdown >= 18 ? 'warning' : 'neutral',
      meta: `Score after ${scenario.score_after.toFixed(1)}`,
      score: scenario.drawdown,
    })),
    rawContext: [
      { title: 'Alpha price', body: formatPrice(subnet.alpha_price_tao) },
      { title: 'Pool depth', body: formatCompactNumber(subnet.tao_in_pool, 0) },
      { title: 'Market cap', body: formatCompactNumber(subnet.market_cap_tao, 0) },
      { title: 'Staking APY', body: formatPercent(subnet.staking_apy) },
      { title: 'Score delta 7d', body: subnet.score_delta_7d == null ? 'n/a' : `${subnet.score_delta_7d.toFixed(1)} pts` },
      { title: 'Score version', body: subnet.score_version || 'v2' },
    ],
    links: [
      { label: 'Taostats', href: `https://taostats.io/subnet/${subnet.netuid}` },
      ...(subnet.metadata?.github_url ? [{ label: 'GitHub', href: subnet.metadata.github_url }] : []),
      ...(subnet.metadata?.website ? [{ label: 'Website', href: subnet.metadata.website }] : []),
    ],
    awaitingRun: !outputs,
  }
}
