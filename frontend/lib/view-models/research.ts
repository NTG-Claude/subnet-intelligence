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

export type UniverseSortId = 'rank' | 'mispricing' | 'quality' | 'confidence' | 'fragility' | 'updated'

export interface UniverseSortOption {
  id: UniverseSortId
  label: string
}

export interface RowFlag {
  label: string
  tone: SignalTone
}

export interface UniverseRowViewModel {
  id: number
  href: string
  name: string
  netuidLabel: string
  thesisLine: string
  decisionLine: string
  signals: SignalStat[]
  opportunityNotes: ResearchHint[]
  riskNotes: ResearchHint[]
  uncertaintyNotes: ResearchHint[]
  statusFlags: RowFlag[]
  opportunityRead: string
  qualityRead: string
  fragilityRead: string
  confidenceRead: string
  rankLabel: string
  percentileLabel: string
  updatedLabel: string
  trustLabel: string
  compareLabel: string
  awaitingRun: boolean
  updatedAtMs: number
  sortValues: Record<UniverseSortId, number>
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
  thesis: string
  decisionLine: string
  updatedLabel: string
  rankLabel: string
  percentileLabel: string
  signals: SignalStat[]
  summaryFlags: RowFlag[]
  summaryMetrics: { label: string; value: string; tone?: SignalTone; meta?: string }[]
  interesting: MemoSectionItem[]
  signalContributorSections: { title: string; tone: SignalTone; items: MemoSectionItem[] }[]
  blockScores: MemoSectionItem[]
  breaks: MemoSectionItem[]
  fragilityContributors: MemoSectionItem[]
  confidenceHeadline: { label: string; value: string; tone?: SignalTone; meta?: string }[]
  confidenceItems: MemoSectionItem[]
  uncertainties: MemoSectionItem[]
  visibilityItems: MemoSectionItem[]
  stressItems: MemoSectionItem[]
  scenarioItems: MemoSectionItem[]
  rawContext: MemoSectionItem[]
  links: { label: string; href: string }[]
  awaitingRun: boolean
}

function numericValues(subnets: SubnetSummary[], pick: (subnet: SubnetSummary) => number): number[] {
  return subnets
    .map(pick)
    .filter((value) => Number.isFinite(value) && value >= 0)
    .sort((left, right) => left - right)
}

function quantile(values: number[], q: number, fallback: number): number {
  if (!values.length) return fallback
  const idx = Math.min(values.length - 1, Math.max(0, Math.floor((values.length - 1) * q)))
  return values[idx]
}

export const UNIVERSE_LENSES: UniverseLens[] = [
  {
    id: 'all',
    title: 'All investable',
    description: 'Broad universe view for manual screening and compare prep.',
    emptyMessage: 'No subnet matches the active search and filter stack.',
  },
  {
    id: 'high-mispricing-confidence',
    title: 'High mispricing + adequate confidence',
    description: 'Expectation gaps where the confidence layer is still sturdy enough to matter.',
    emptyMessage: 'No high-mispricing setups cleared the confidence floor.',
  },
  {
    id: 'strong-quality',
    title: 'Strong quality + acceptable fragility',
    description: 'Quality-led names where fragility does not dominate the read.',
    emptyMessage: 'No strong-quality names survived the fragility screen.',
  },
  {
    id: 'compounders',
    title: 'Low-fragility compounders',
    description: 'Resilient profiles where quality and stress behavior line up.',
    emptyMessage: 'No compounder-style profiles surfaced in this slice.',
  },
  {
    id: 'low-confidence',
    title: 'Low-confidence cases',
    description: 'Interesting signals that still need better telemetry or cleaner evidence.',
    emptyMessage: 'No low-confidence upside cases surfaced right now.',
  },
  {
    id: 'under-review',
    title: 'Under review / telemetry-gap',
    description: 'Awaiting runs, repaired inputs, discarded inputs, or partial outputs.',
    emptyMessage: 'No under-review names are visible in the current universe.',
  },
]

export const UNIVERSE_SORTS: UniverseSortOption[] = [
  { id: 'rank', label: 'Rank' },
  { id: 'mispricing', label: 'Mispricing' },
  { id: 'quality', label: 'Quality' },
  { id: 'confidence', label: 'Confidence' },
  { id: 'fragility', label: 'Lowest fragility' },
  { id: 'updated', label: 'Updated' },
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

const CONTRIBUTOR_SECTION_META: Record<string, { title: string; tone: SignalTone }> = {
  fundamental_quality: { title: 'Quality contributors', tone: 'quality' },
  mispricing_signal: { title: 'Mispricing contributors', tone: 'mispricing' },
  fragility_risk: { title: 'Fragility contributors', tone: 'fragility' },
  signal_confidence: { title: 'Confidence contributors', tone: 'confidence' },
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

function clipHints(items: ResearchHint[], limit: number): ResearchHint[] {
  return items.filter((item) => item.label).slice(0, limit)
}

function contributorLabel(item: ExplanationContributor): string {
  return item.short_explanation || item.metric || item.name || item.source_block || 'Unspecified contributor'
}

function contributorTitle(item: ExplanationContributor): string {
  return item.metric || item.name || item.source_block || 'Contributor'
}

function uncertaintyLabel(item: KeyUncertainty): string {
  return item.short_explanation || item.name.replace(/_/g, ' ')
}

function visibilityCount(conditioning: ConditioningInfo | undefined, bucket: string): number {
  return conditioning?.visibility?.[bucket]?.length ?? 0
}

function parseTimestamp(iso: string | null | undefined): number {
  const parsed = iso ? Date.parse(iso) : Number.NaN
  return Number.isFinite(parsed) ? parsed : 0
}

function isStale(iso: string | null | undefined, staleHours = 36): boolean {
  const timestamp = parseTimestamp(iso)
  if (!timestamp) return false
  return Date.now() - timestamp > staleHours * 60 * 60 * 1000
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
  const items = source === 'positive' ? preview?.top_positive_drivers ?? [] : preview?.top_negative_drags ?? []
  return items.slice(0, 3).map((item) => ({
    label: contributorLabel(item),
    tone,
  }))
}

function summaryWarnings(subnet: SubnetSummary): ResearchHint[] {
  const preview = subnet.analysis_preview
  const warnings: ResearchHint[] = (preview?.key_uncertainties ?? []).slice(0, 3).map((item) => ({
    label: uncertaintyLabel(item),
    tone: 'warning',
  }))

  if (!subnet.primary_outputs) {
    warnings.unshift({ label: 'Awaiting V2 run output', tone: 'warning' })
  } else if (confidenceValue(subnet) < 50) {
    warnings.unshift({ label: 'Low-confidence evidence mix', tone: 'warning' })
  }

  if (visibilityCount(preview?.conditioning, 'reconstructed') > 0) {
    warnings.push({ label: 'Some inputs were reconstructed', tone: 'warning' })
  }
  if (visibilityCount(preview?.conditioning, 'discarded') > 0) {
    warnings.push({ label: 'Some inputs were discarded', tone: 'warning' })
  }
  if (isStale(subnet.computed_at)) {
    warnings.push({ label: 'Run may be stale', tone: 'warning' })
  }

  return clipHints(warnings, 3)
}

function trustLabel(subnet: SubnetSummary): string {
  if (!subnet.primary_outputs) return 'Awaiting run'
  if (visibilityCount(subnet.analysis_preview?.conditioning, 'discarded') > 0) return 'Visibility gaps'
  if (visibilityCount(subnet.analysis_preview?.conditioning, 'reconstructed') > 0) return 'Repaired telemetry'
  if (confidenceValue(subnet) < 45) return 'Low confidence'
  if (confidenceValue(subnet) < 65) return 'Adequate confidence'
  return 'Usable confidence'
}

function decisionLineFromOutputs(outputs: PrimaryOutputs | null | undefined): string {
  if (!outputs) return 'Research is blocked until the latest run emits V2 outputs.'
  if (outputs.mispricing_signal >= 70 && outputs.signal_confidence >= 60 && outputs.fragility_risk <= 45) {
    return 'Mispricing is visible, confidence is usable, and fragility is not yet crowding out the idea.'
  }
  if (outputs.fundamental_quality >= 70 && outputs.fragility_risk <= 45) {
    return 'Quality is doing the heavy lifting, so the entry depends on whether enough mispricing remains.'
  }
  if (outputs.fragility_risk >= 65) {
    return 'The upside case is fragile enough that stress behavior and execution discipline dominate the read.'
  }
  if (outputs.signal_confidence < 50) {
    return 'Signals are interesting, but the trust layer is still too soft for a clean high-conviction memo.'
  }
  return 'The setup is investable only if the positive case survives a harder trust and fragility check.'
}

function opportunityRead(subnet: SubnetSummary): string {
  if (!subnet.primary_outputs) return 'No active opportunity read until the subnet is rescored.'
  if (mispricingValue(subnet) >= 70) return 'The model still sees a large expectation gap worth active research.'
  if (mispricingValue(subnet) >= 55) return 'There is still some upside gap, but it is no longer a clean dislocation.'
  return 'Opportunity is muted unless new evidence changes the read.'
}

function qualityRead(subnet: SubnetSummary): string {
  if (!subnet.primary_outputs) return 'Quality cannot be underwritten until the V2 outputs land.'
  if (qualityValue(subnet) >= 70) return 'Quality support is robust enough to anchor the thesis.'
  if (qualityValue(subnet) >= 55) return 'Quality is acceptable, but not dominant enough to carry the full case.'
  return 'Quality evidence is thin, so upside depends on weaker footing.'
}

function fragilityRead(subnet: SubnetSummary): string {
  if (!subnet.primary_outputs) return 'Fragility is unknown until the latest run completes.'
  if (fragilityValue(subnet) <= 40) return 'Stress behavior looks manageable relative to the current upside case.'
  if (fragilityValue(subnet) <= 60) return 'Fragility is acceptable, but it can still narrow the range of valid entries.'
  return 'Fragility is high enough that the thesis can break quickly under stress or poor execution.'
}

function confidenceRead(subnet: SubnetSummary): string {
  const warnings = summaryWarnings(subnet)
  if (!subnet.primary_outputs) return 'No trust read yet because the subnet is still awaiting a full V2 output.'
  if (!warnings.length && confidenceValue(subnet) >= 65) return 'Data trust is relatively clean for a first-pass investment memo.'
  if (confidenceValue(subnet) >= 50) return 'Confidence is usable, but the conditioning layer deserves a quick check.'
  return 'Confidence is weak enough that repaired telemetry or missing evidence can change the memo materially.'
}

function buildStatusFlags(subnet: SubnetSummary): RowFlag[] {
  const flags: RowFlag[] = []
  if (!subnet.primary_outputs) {
    flags.push({ label: 'Awaiting run', tone: 'warning' })
    return flags
  }
  if (isStale(subnet.computed_at)) {
    flags.push({ label: 'Stale run', tone: 'warning' })
  }
  if (visibilityCount(subnet.analysis_preview?.conditioning, 'discarded') > 0) {
    flags.push({ label: 'Incomplete telemetry', tone: 'warning' })
  } else if (visibilityCount(subnet.analysis_preview?.conditioning, 'reconstructed') > 0) {
    flags.push({ label: 'Reconstructed inputs', tone: 'warning' })
  }
  if (confidenceValue(subnet) < 45) {
    flags.push({ label: 'Low confidence', tone: 'confidence' })
  }
  return flags.slice(0, 3)
}

function compareLabel(subnet: SubnetSummary): string {
  if (!subnet.primary_outputs) return 'Track for compare'
  return 'Add to compare'
}

export function toUniverseRow(subnet: SubnetSummary): UniverseRowViewModel {
  const positives = clipHints(summaryHints(subnet.analysis_preview, 'quality', 'positive'), 2)
  const negatives = clipHints(summaryHints(subnet.analysis_preview, 'fragility', 'negative'), 2)
  const warnings = clipHints(summaryWarnings(subnet), 2)
  return {
    id: subnet.netuid,
    href: `/subnets/${subnet.netuid}`,
    name: toDisplayName(subnet.name, subnet.netuid),
    netuidLabel: `SN${subnet.netuid}`,
    thesisLine: subnet.thesis ?? 'No concise thesis has been produced for this run yet.',
    decisionLine: decisionLineFromOutputs(subnet.primary_outputs),
    signals: getSignalStats(subnet.primary_outputs),
    opportunityNotes: positives,
    riskNotes: negatives,
    uncertaintyNotes: warnings,
    statusFlags: buildStatusFlags(subnet),
    opportunityRead: opportunityRead(subnet),
    qualityRead: qualityRead(subnet),
    fragilityRead: fragilityRead(subnet),
    confidenceRead: confidenceRead(subnet),
    rankLabel: subnet.rank ? `#${subnet.rank}` : 'n/a',
    percentileLabel: subnet.percentile != null ? `${subnet.percentile.toFixed(1)}th` : 'n/a',
    updatedLabel: formatDateTime(subnet.computed_at),
    trustLabel: trustLabel(subnet),
    compareLabel: compareLabel(subnet),
    awaitingRun: !subnet.primary_outputs,
    updatedAtMs: parseTimestamp(subnet.computed_at),
    sortValues: {
      rank: -(subnet.rank ?? 9999),
      mispricing: mispricingValue(subnet),
      quality: qualityValue(subnet),
      confidence: confidenceValue(subnet),
      fragility: subnet.primary_outputs ? 100 - fragilityValue(subnet) : -1,
      updated: parseTimestamp(subnet.computed_at),
    },
  }
}

export function sortUniverseRows(rows: UniverseRowViewModel[], sortId: UniverseSortId): UniverseRowViewModel[] {
  return [...rows].sort((a, b) => {
    if (sortId === 'rank') {
      const aRank = a.rankLabel === 'n/a' ? 9999 : Number(a.rankLabel.replace('#', ''))
      const bRank = b.rankLabel === 'n/a' ? 9999 : Number(b.rankLabel.replace('#', ''))
      return aRank - bRank || b.sortValues.confidence - a.sortValues.confidence
    }
    return b.sortValues[sortId] - a.sortValues[sortId] || a.id - b.id
  })
}

export function applyUniverseLens(subnets: SubnetSummary[], lensId: string): SubnetSummary[] {
  const investable = [...subnets]
  const qualityCut = quantile(numericValues(investable, qualityValue), 0.7, 65)
  const mispricingCut = quantile(numericValues(investable, mispricingValue), 0.75, 60)
  const confidenceCut = quantile(numericValues(investable, confidenceValue), 0.65, 55)
  const lowConfidenceCut = quantile(numericValues(investable, confidenceValue), 0.35, 45)
  const resilientCut = quantile(numericValues(investable, fragilityValue), 0.35, 40)
  const acceptableFragilityCut = quantile(numericValues(investable, fragilityValue), 0.55, 60)
  switch (lensId) {
    case 'high-mispricing-confidence':
      return investable
        .filter(
          (subnet) =>
            mispricingValue(subnet) >= mispricingCut &&
            confidenceValue(subnet) >= confidenceCut &&
            fragilityValue(subnet) <= acceptableFragilityCut,
        )
        .sort((a, b) => mispricingValue(b) + confidenceValue(b) - mispricingValue(a) - confidenceValue(a))
    case 'strong-quality':
      return investable
        .filter((subnet) => qualityValue(subnet) >= qualityCut && fragilityValue(subnet) <= acceptableFragilityCut)
        .sort((a, b) => qualityValue(b) - qualityValue(a))
    case 'compounders':
      return investable
        .filter(
          (subnet) =>
            qualityValue(subnet) >= quantile(numericValues(investable, qualityValue), 0.6, 55) &&
            fragilityValue(subnet) <= resilientCut &&
            confidenceValue(subnet) >= quantile(numericValues(investable, confidenceValue), 0.5, 50),
        )
        .sort((a, b) => fragilityValue(a) - fragilityValue(b) || qualityValue(b) - qualityValue(a))
    case 'low-confidence':
      return investable
        .filter(
          (subnet) =>
            mispricingValue(subnet) >= mispricingCut &&
            confidenceValue(subnet) > -1 &&
            confidenceValue(subnet) <= lowConfidenceCut,
        )
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
        .sort((a, b) => Number(!b.primary_outputs) - Number(!a.primary_outputs))
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

function toUncertaintyItems(items: KeyUncertainty[] | undefined): MemoSectionItem[] {
  return (items ?? []).map((item) => ({
    title: item.name.replace(/_/g, ' '),
    body: uncertaintyLabel(item),
    tone: 'warning',
    score: typeof item.signed_contribution === 'number' ? Math.abs(item.signed_contribution) * 100 : null,
    meta: item.source_block,
  }))
}

function confidenceTone(value: number | null | undefined): SignalTone {
  if (value == null) return 'neutral'
  if (value >= 65) return 'confidence'
  if (value >= 45) return 'warning'
  return 'fragility'
}

function reliabilityTone(value: number): SignalTone {
  if (value >= 0.7) return 'confidence'
  if (value >= 0.5) return 'warning'
  return 'fragility'
}

export function buildDetailMemo(subnet: SubnetDetail): DetailMemoViewModel {
  const analysis = subnet.analysis
  const outputs = subnet.primary_outputs ?? analysis?.primary_outputs ?? null
  const conditioning = analysis?.conditioning
  const confidence = analysis?.confidence_rationale
  const summary = toUniverseRow({
    netuid: subnet.netuid,
    name: subnet.name,
    score: subnet.score,
    primary_outputs: outputs,
    rank: subnet.rank,
    percentile: subnet.percentile,
    computed_at: subnet.computed_at,
    score_version: subnet.score_version,
    alpha_price_tao: subnet.alpha_price_tao,
    tao_in_pool: subnet.tao_in_pool,
    market_cap_tao: subnet.market_cap_tao,
    staking_apy: subnet.staking_apy,
    label: subnet.label ?? analysis?.label ?? null,
    thesis: subnet.thesis ?? analysis?.thesis ?? null,
    analysis_preview: {
      top_positive_drivers: analysis?.top_positive_drivers,
      top_negative_drags: analysis?.top_negative_drags ?? analysis?.top_negative_drivers,
      key_uncertainties: analysis?.key_uncertainties,
      conditioning,
      block_scores: analysis?.block_scores,
    },
  })

  const reliabilityEntries: MemoSectionItem[] = Object.entries(conditioning?.reliability ?? {}).map(([key, value]) => ({
    title: RELIABILITY_LABELS[key] ?? key.replace(/_/g, ' '),
    body: `${(value * 100).toFixed(1)} / 100`,
    tone: reliabilityTone(value),
  }))

  const contributorSections = Object.entries(analysis?.primary_signal_contributors ?? {})
    .map(([key, items]) => {
      const meta = CONTRIBUTOR_SECTION_META[key] ?? { title: key.replace(/_/g, ' '), tone: 'neutral' as const }
      return {
        title: meta.title,
        tone: meta.tone,
        items: toMemoItems(items, meta.tone).slice(0, 4),
      }
    })
    .filter((section) => section.items.length > 0)

  const visibilityItems: MemoSectionItem[] = [
    {
      title: 'Reconstructed inputs',
      body: String(visibilityCount(conditioning, 'reconstructed')),
      tone: visibilityCount(conditioning, 'reconstructed') > 0 ? 'warning' : 'neutral',
      meta: conditioning?.visibility?.reconstructed?.slice(0, 6).join(', '),
    },
    {
      title: 'Discarded inputs',
      body: String(visibilityCount(conditioning, 'discarded')),
      tone: visibilityCount(conditioning, 'discarded') > 0 ? 'warning' : 'neutral',
      meta: conditioning?.visibility?.discarded?.slice(0, 6).join(', '),
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
      meta: conditioning?.visibility?.bounded?.slice(0, 6).join(', '),
    },
  ]

  return {
    name: toDisplayName(subnet.name, subnet.netuid),
    netuidLabel: `SN${subnet.netuid}`,
    href: `/subnets/${subnet.netuid}`,
    thesis: subnet.thesis ?? analysis?.thesis ?? 'No concise thesis generated yet.',
    decisionLine: summary.decisionLine,
    updatedLabel: formatDateTime(subnet.computed_at),
    rankLabel: subnet.rank ? `#${subnet.rank}` : 'n/a',
    percentileLabel: subnet.percentile != null ? `${subnet.percentile.toFixed(1)}th` : 'n/a',
    signals: getSignalStats(outputs),
    summaryFlags: summary.statusFlags,
    summaryMetrics: [
      { label: 'Rank', value: subnet.rank ? `#${subnet.rank}` : 'n/a' },
      { label: 'Percentile', value: subnet.percentile != null ? `${subnet.percentile.toFixed(1)}th` : 'n/a' },
      { label: 'Updated', value: formatDateTime(subnet.computed_at), tone: isStale(subnet.computed_at) ? 'warning' : 'neutral' },
      { label: 'Read state', value: summary.trustLabel, tone: summary.awaitingRun ? 'warning' : 'confidence' },
    ],
    interesting: toMemoItems(analysis?.top_positive_drivers, 'quality'),
    signalContributorSections: contributorSections,
    blockScores: Object.entries(analysis?.block_scores ?? {}).map(([key, value]) => ({
      title: BLOCK_LABELS[key] ?? key.replace(/_/g, ' '),
      body: `${value.toFixed(1)}`,
      tone: value >= 65 ? 'quality' : value <= 45 ? 'warning' : 'neutral',
      score: value,
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
    confidenceHeadline: [
      {
        label: 'Signal confidence',
        value: outputs ? outputs.signal_confidence.toFixed(1) : 'n/a',
        tone: confidenceTone(outputs?.signal_confidence),
      },
      {
        label: 'Data confidence',
        value: confidence?.data_confidence != null ? confidence.data_confidence.toFixed(1) : 'n/a',
        tone: confidenceTone(confidence?.data_confidence),
      },
      {
        label: 'Market confidence',
        value: confidence?.market_confidence != null ? confidence.market_confidence.toFixed(1) : 'n/a',
        tone: confidenceTone(confidence?.market_confidence),
      },
      {
        label: 'Thesis confidence',
        value: confidence?.thesis_confidence != null ? confidence.thesis_confidence.toFixed(1) : 'n/a',
        tone: confidenceTone(confidence?.thesis_confidence),
      },
    ],
    confidenceItems: reliabilityEntries,
    uncertainties: toUncertaintyItems(analysis?.key_uncertainties),
    visibilityItems,
    stressItems: [
      { title: 'Fragility class', body: analysis?.fragility_class ?? 'unknown', tone: 'fragility' },
      {
        title: 'Stress drawdown',
        body: analysis?.stress_drawdown != null ? `${analysis.stress_drawdown.toFixed(1)}%` : 'n/a',
        tone: analysis?.stress_drawdown != null && analysis.stress_drawdown >= 30 ? 'fragility' : 'warning',
      },
      { title: 'Pool depth', body: formatCompactNumber(subnet.tao_in_pool, 0), tone: 'neutral' },
      { title: 'Market cap', body: formatCompactNumber(subnet.market_cap_tao, 0), tone: 'neutral' },
      { title: 'Alpha price', body: formatPrice(subnet.alpha_price_tao), tone: 'neutral' },
      { title: 'Staking APY', body: formatPercent(subnet.staking_apy), tone: 'neutral' },
    ],
    scenarioItems: (analysis?.stress_scenarios ?? []).map((scenario) => ({
      title: scenario.name,
      body: `${scenario.drawdown.toFixed(1)}% drawdown`,
      tone: scenario.drawdown >= 30 ? 'fragility' : scenario.drawdown >= 18 ? 'warning' : 'neutral',
      meta: `Score after ${scenario.score_after.toFixed(1)}`,
      score: scenario.drawdown,
    })),
    rawContext: [
      { title: 'Score version', body: subnet.score_version || 'v2' },
      { title: 'Score delta 7d', body: subnet.score_delta_7d == null ? 'n/a' : `${subnet.score_delta_7d.toFixed(1)} pts` },
      { title: 'Pool depth', body: formatCompactNumber(subnet.tao_in_pool, 0) },
      { title: 'Market cap', body: formatCompactNumber(subnet.market_cap_tao, 0) },
      { title: 'Alpha price', body: formatPrice(subnet.alpha_price_tao) },
      { title: 'Staking APY', body: formatPercent(subnet.staking_apy) },
    ],
    links: [
      { label: 'Taostats', href: `https://taostats.io/subnet/${subnet.netuid}` },
      ...(subnet.metadata?.github_url ? [{ label: 'GitHub', href: subnet.metadata.github_url }] : []),
      ...(subnet.metadata?.website ? [{ label: 'Website', href: subnet.metadata.website }] : []),
    ],
    awaitingRun: !outputs,
  }
}
