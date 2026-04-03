import {
  AnalysisPreview,
  ConfidenceRationale,
  ConditioningInfo,
  ExplanationContributor,
  KeyUncertainty,
  PrimaryOutputs,
  ResearchSummary,
  SubnetDetail,
  SubnetSummary,
} from '@/lib/api'
import { formatCompactNumber, formatDateTime, formatPercent, formatPrice, isStale, parseTimestamp } from '@/lib/formatting'

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

export type UniverseSortId = 'rank' | 'score' | 'mispricing' | 'quality' | 'confidence' | 'fragility' | 'updated'

export interface UniverseSortOption {
  id: UniverseSortId
  label: string
}

export interface RowFlag {
  label: string
  tone: SignalTone
}

export interface InvestabilityBadge {
  label: string
  tone: SignalTone
}

export interface UniverseRowViewModel {
  id: number
  href: string
  name: string
  netuidLabel: string
  modelLabel: string
  modelLabelTone: SignalTone
  thesisLine: string
  decisionLine: string
  signals: SignalStat[]
  opportunityNotes: ResearchHint[]
  riskNotes: ResearchHint[]
  uncertaintyNotes: ResearchHint[]
  statusFlags: RowFlag[]
  metricReasons: {
    strength: string
    upside: string
    risk: string
    evidence: string
  }
  scoreLabel: string
  investability: InvestabilityBadge
  warningFlags: RowFlag[]
  opportunityRead: string
  qualityRead: string
  fragilityRead: string
  confidenceRead: string
  rankLabel: string
  percentileLabel: string
  updatedLabel: string
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

export interface ResearchSummaryViewModel {
  setupStatus: { value: ResearchSummary['setup_status']; label: string; tone: SignalTone }
  marketCapacity: { value: ResearchSummary['market_capacity']; label: string; tone: SignalTone }
  evidenceStrength: { value: ResearchSummary['evidence_strength']; label: string; tone: SignalTone }
  setupRead: string
  whyNow: string
  mainConstraint: string
  breakCondition: string
  relativePeerContext: string
}

export interface MemoSummaryItem {
  label: 'Setup Read' | 'Why Now' | 'Main Constraint' | 'Break Condition'
  body: string
  tone: SignalTone
}

export interface MemoContextItem {
  label: 'Market Capacity' | 'Evidence Strength' | 'Peer Rank' | 'Last Updated'
  value: string
  tone?: SignalTone
}

export interface MemoInsightItem {
  label: string
  value: string
  body: string
  tone: SignalTone
}

export interface ScoreExplanationItem {
  title: string
  value?: string
  body: string
  tone: SignalTone
}

export interface DetailMemoViewModel {
  name: string
  netuidLabel: string
  href: string
  scoreLabel: string
  modelLabel: string
  modelLabelTone: SignalTone
  headerSubtitle: string
  researchSummary: ResearchSummaryViewModel
  updatedLabel: string
  rankLabel: string
  percentileLabel: string
  signals: SignalStat[]
  primaryTag: InvestabilityBadge
  secondaryTag?: InvestabilityBadge | null
  executiveSummary: MemoSummaryItem[]
  contextRow: MemoContextItem[]
  marketStructure: MemoInsightItem[]
  evidenceItems: MemoInsightItem[]
  topSupports: ScoreExplanationItem[]
  topDrags: ScoreExplanationItem[]
  blockScores: MemoSectionItem[]
  breaks: MemoSectionItem[]
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
    title: 'Evidence limited / telemetry-gap',
    description: 'Low-confidence names, repaired inputs, discarded inputs, or partial outputs.',
    emptyMessage: 'No evidence-limited or telemetry-gap names are visible in the current universe.',
  },
]

export const UNIVERSE_SORTS: UniverseSortOption[] = [
  { id: 'rank', label: 'Rank' },
  { id: 'score', label: 'Score' },
  { id: 'mispricing', label: 'Opportunity' },
  { id: 'quality', label: 'Quality' },
  { id: 'confidence', label: 'Confidence' },
  { id: 'fragility', label: 'Lowest risk' },
  { id: 'updated', label: 'Updated' },
]

const SIGNAL_META: Record<keyof PrimaryOutputs, Omit<SignalStat, 'value'>> = {
  fundamental_quality: { key: 'fundamental_quality', label: 'Quality', shortLabel: 'QLTY', tone: 'quality' },
  mispricing_signal: { key: 'mispricing_signal', label: 'Opportunity', shortLabel: 'OPP', tone: 'mispricing' },
  fragility_risk: { key: 'fragility_risk', label: 'Risk', shortLabel: 'RISK', tone: 'fragility', invert: true },
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

function clipHints(items: ResearchHint[], limit: number): ResearchHint[] {
  return items.filter((item) => item.label).slice(0, limit)
}

function contributorLabel(item: ExplanationContributor): string {
  return item.short_explanation || item.metric || item.name || item.source_block || 'Unspecified contributor'
}

function contributorKey(item: ExplanationContributor): string {
  return item.name || item.metric || ''
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

function modelLabelValue(subnet: Pick<SubnetSummary, 'label'>): string {
  return subnet.label?.trim() || 'Evidence Limited'
}

function modelLabelTone(label: string): SignalTone {
  if (label === 'Compounding Quality' || label === 'Underpriced Quality' || label === 'Quality Leader') {
    return 'quality'
  }
  if (label === 'Crowded Reflexive' || label === 'Fragile Yield' || label === 'Overrewarded' || label === 'Dereg Risk') {
    return 'fragility'
  }
  if (label === 'Evidence Limited' || label === 'Consensus Hollow') {
    return 'warning'
  }
  return 'neutral'
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

function cleanSentence(value: string | undefined | null): string {
  return (value ?? '').replace(/\s+/g, ' ').trim()
}

function metricPhrase(name: string | undefined | null): string {
  switch (name) {
    case 'fragility':
      return 'downside and liquidity stress remain contained'
    case 'fundamental_health':
      return 'core operating quality is holding up'
    case 'thesis_confidence':
      return 'the broader thesis still hangs together'
    case 'market_confidence':
      return 'market structure is good enough to underwrite the setup'
    case 'confidence_factor':
      return 'the evidence stack is coherent enough for a first-pass read'
    case 'base_opportunity':
      return 'the market is still leaving some valuation upside on the table'
    case 'data_confidence':
      return 'data coverage is good enough to support the case'
    case 'reserve_change':
      return 'reserve growth has not yet translated into a stronger market response'
    case 'liquidity_improvement_rate':
      return 'liquidity is not improving fast enough to widen the upside case'
    case 'reserve_growth_without_price':
      return 'fundamental improvement is not yet being rewarded in price'
    case 'quality_acceleration':
      return 'quality is solid, but the rate of improvement is not accelerating'
    case 'price_response_lag_to_quality_shift':
      return 'the rerating window may be narrower than the quality trend suggests'
    case 'expected_price_response_gap':
      return 'the price-response gap is not as wide as in the strongest rerating setups'
    case 'emission_to_sticky_usage_conversion':
      return 'emissions are not yet converting cleanly into sticky usage'
    case 'post_incentive_retention':
      return 'retention still needs to hold once incentives are less supportive'
    case 'emission_efficiency':
      return 'capital is not converting into usage efficiently enough'
    case 'cohort_quality_edge':
      return 'quality leadership versus peers is not overwhelming'
    case 'discarded_inputs':
      return 'part of the history had to be discarded, so visibility is incomplete'
    case 'external_data_reliability':
      return 'external corroboration is still thin'
    default:
      return ''
  }
}

function contributorName(item: ExplanationContributor | undefined | null): string {
  return contributorKey(item ?? {}) || ''
}

function sentenceCase(text: string): string {
  if (!text) return text
  return text.charAt(0).toUpperCase() + text.slice(1)
}

function formatScore(value: number | null | undefined): string {
  if (value == null || !Number.isFinite(value)) return 'n/a'
  return value.toFixed(1)
}

function joinClauses(items: string[]): string {
  const cleaned = items.map((item) => cleanSentence(item)).filter(Boolean)
  if (!cleaned.length) return ''
  if (cleaned.length === 1) return cleaned[0]
  if (cleaned.length === 2) return `${cleaned[0]} and ${cleaned[1]}`
  return `${cleaned.slice(0, -1).join(', ')}, and ${cleaned[cleaned.length - 1]}`
}

function driverSupportClause(name: string): string {
  switch (name) {
    case 'fundamental_health':
      return 'the underlying business looks durable and operationally healthy'
    case 'structural_validity':
      return 'the market structure still looks investable instead of distorted'
    case 'market_legitimacy':
      return 'the subnet already looks credible enough to attract sustained attention'
    case 'confidence_factor':
      return 'the evidence stack is coherent enough for a usable first-pass read'
    case 'thesis_confidence':
      return 'the broader investment case hangs together better than most peers'
    case 'market_confidence':
      return 'market behavior is supportive enough to back the thesis'
    case 'data_confidence':
      return 'data coverage is strong enough to support the read'
    case 'base_opportunity':
    case 'opportunity_underreaction':
      return 'the market still seems to underrate part of the setup'
    case 'quality_acceleration':
      return 'quality is still improving rather than merely holding steady'
    case 'fragility':
      return 'downside and liquidity stress are staying contained'
    default: {
      const phrase = metricPhrase(name)
      if (phrase) return phrase
      return `${name.replace(/_/g, ' ')} is helping the case`
    }
  }
}

function driverDragClause(name: string): string {
  switch (name) {
    case 'reserve_change':
      return 'reserve growth is not yet translating into a stronger market response'
    case 'liquidity_improvement_rate':
      return 'liquidity is not improving fast enough to widen the upside case'
    case 'reserve_growth_without_price':
      return 'fundamental improvement is still not being fully rewarded in price'
    case 'quality_acceleration':
      return 'quality looks solid, but the rate of improvement has cooled'
    case 'price_response_lag_to_quality_shift':
      return 'the market may already be catching up to the quality trend'
    case 'expected_price_response_gap':
      return 'the rerating gap is smaller than in the strongest upside setups'
    case 'emission_to_sticky_usage_conversion':
      return 'emissions are not yet converting cleanly into sticky, lasting usage'
    case 'post_incentive_retention':
      return 'the case still needs to prove users remain after incentives fade'
    case 'emission_efficiency':
      return 'capital is not converting into usage efficiently enough'
    case 'cohort_quality_edge':
      return 'its quality lead over peers is not overwhelming'
    case 'fragility':
      return 'stress behavior can still dominate the case under pressure'
    case 'discarded_inputs':
      return 'part of the history had to be discarded, so visibility is incomplete'
    case 'external_data_reliability':
      return 'third-party corroboration is still thin'
    default: {
      const phrase = metricPhrase(name)
      if (phrase) return phrase
      return `${name.replace(/_/g, ' ')} is still acting as a headwind`
    }
  }
}

function uncertaintyClause(name: string): string {
  switch (name) {
    case 'discarded_inputs':
      return 'some unusable inputs were removed during conditioning, so the read still has blind spots'
    case 'external_data_reliability':
      return 'external corroboration remains limited, so the memo leans heavily on internal market evidence'
    case 'validator_data_reliability':
      return 'validator-side evidence is thinner than ideal'
    case 'history_data_reliability':
      return 'the historical record is not as deep or clean as you would want'
    default:
      return driverDragClause(name)
  }
}

function plainEnglishReason(name: string, mode: 'positive' | 'negative' | 'uncertainty'): string {
  switch (name) {
    case 'fundamental_health':
      return mode === 'positive'
        ? 'the subnet looks more durable and useful than most peers'
        : 'the business quality is not as durable as the best names'
    case 'market_legitimacy':
      return mode === 'positive'
        ? 'the market already treats it like a credible network'
        : 'the market still does not fully treat it like a proven network'
    case 'structural_validity':
      return mode === 'positive'
        ? 'the setup still looks investable rather than distorted'
        : 'the setup still has structural weak points'
    case 'confidence_factor':
      return mode === 'positive'
        ? 'the main signals broadly point in the same direction'
        : 'the evidence does not line up cleanly yet'
    case 'thesis_confidence':
      return mode === 'positive'
        ? 'the overall story hangs together without too many leaps'
        : 'the overall story still relies on assumptions that need proving'
    case 'market_confidence':
      return mode === 'positive'
        ? 'price and market behavior are not fighting the thesis'
        : 'market behavior is not giving much confirmation yet'
    case 'data_confidence':
      return mode === 'positive'
        ? 'there is enough clean data to form a usable view'
        : 'the data picture is still too patchy'
    case 'opportunity_underreaction':
    case 'base_opportunity':
      return mode === 'positive'
        ? 'the market still seems to be underestimating part of the story'
        : 'the market is not giving much of a discount right now'
    case 'fragility':
      return mode === 'positive'
        ? 'the subnet is holding up reasonably well under pressure'
        : 'the setup can still break under stress'
    case 'reserve_change':
      return 'more capital is not yet leading to a clearly better market response'
    case 'liquidity_improvement_rate':
      return 'trading conditions are not improving fast enough yet'
    case 'reserve_growth_without_price':
      return 'better fundamentals are not yet clearly showing up in price'
    case 'quality_acceleration':
      return mode === 'positive'
        ? 'quality is still moving in the right direction'
        : 'improvement has slowed and is no longer accelerating'
    case 'price_response_lag_to_quality_shift':
      return 'the market may already be catching up to the improvement'
    case 'expected_price_response_gap':
      return 'the rerating gap is smaller than in the best upside names'
    case 'emission_to_sticky_usage_conversion':
      return 'token emissions are not yet turning into lasting usage'
    case 'post_incentive_retention':
      return 'it is still unclear whether users stay once incentives fade'
    case 'emission_efficiency':
      return 'new emissions are not producing enough real usage'
    case 'cohort_quality_edge':
      return 'it does not have a big lead over comparable subnets'
    case 'discarded_inputs':
      return mode === 'uncertainty'
        ? 'some messy inputs had to be thrown out, so the picture is incomplete'
        : 'some messy inputs had to be thrown out'
    case 'external_data_reliability':
      return 'there is still not much outside evidence to confirm the story'
    case 'validator_data_reliability':
      return 'validator-side evidence is thinner than ideal'
    case 'history_data_reliability':
      return 'the historical record is still shallower than you would want'
    default: {
      const fallback = metricPhrase(name)
      return fallback || `${name.replace(/_/g, ' ')} is affecting the read`
    }
  }
}

function shortMetricReason(subnet: SubnetSummary, metric: 'strength' | 'upside' | 'risk' | 'evidence'): string {
  const positives = subnet.analysis_preview?.top_positive_drivers ?? []
  const drags = subnet.analysis_preview?.top_negative_drags ?? []
  const uncertainties = subnet.analysis_preview?.key_uncertainties ?? []
  const outputs = subnet.primary_outputs

  if (!outputs) return 'Awaiting a fresh model run.'

  if (metric === 'strength') {
    const support =
      positives.find((item) =>
        ['fundamental_health', 'market_legitimacy', 'structural_validity', 'quality_acceleration'].includes(contributorName(item)),
      ) ?? positives[0]
    const drag =
      drags.find((item) =>
        ['quality_acceleration', 'cohort_quality_edge', 'reserve_growth_without_price'].includes(contributorName(item)),
      ) ?? drags[0]
    const parts = []
    if (support) parts.push(sentenceCase(plainEnglishReason(contributorName(support), 'positive')))
    if (outputs.fundamental_quality < 55 && drag) parts.push(`Held back because ${plainEnglishReason(contributorName(drag), 'negative')}.`)
    return parts.join('. ') || 'Business quality looks middle-of-the-pack right now.'
  }

  if (metric === 'upside') {
    const support =
      positives.find((item) =>
        ['opportunity_underreaction', 'base_opportunity', 'confidence_factor'].includes(contributorName(item)),
      ) ?? positives[0]
    const drag =
      drags.find((item) =>
        ['reserve_change', 'liquidity_improvement_rate', 'reserve_growth_without_price', 'expected_price_response_gap'].includes(
          contributorName(item),
        ),
      ) ?? drags[0]
    const parts = []
    if (support) parts.push(sentenceCase(plainEnglishReason(contributorName(support), 'positive')))
    if (drag) parts.push(`The gap is smaller because ${plainEnglishReason(contributorName(drag), 'negative')}.`)
    return parts.join('. ') || 'There is some upside, but not a big disconnect.'
  }

  if (metric === 'risk') {
    const support =
      positives.find((item) => ['fragility', 'structural_validity', 'market_legitimacy'].includes(contributorName(item))) ??
      positives[0]
    const drag =
      drags.find((item) =>
        ['fragility', 'emission_to_sticky_usage_conversion', 'post_incentive_retention', 'emission_efficiency'].includes(
          contributorName(item),
        ),
      ) ?? drags[0]
    if (outputs.fragility_risk <= 35 && support) {
      return `${sentenceCase(plainEnglishReason(contributorName(support), 'positive'))}.`
    }
    if (drag) {
      return `${sentenceCase(plainEnglishReason(contributorName(drag), 'negative'))}.`
    }
    return 'Risk looks manageable, but not especially low.'
  }

  const support =
    positives.find((item) =>
      ['confidence_factor', 'data_confidence', 'market_confidence', 'thesis_confidence'].includes(contributorName(item)),
    ) ?? positives[0]
  const uncertainty =
    uncertainties.find((item) =>
      ['discarded_inputs', 'external_data_reliability', 'validator_data_reliability', 'history_data_reliability'].includes(item.name),
    ) ?? uncertainties[0]

  if (outputs.signal_confidence >= 55 && support) {
    return `${sentenceCase(plainEnglishReason(contributorName(support), 'positive'))}.`
  }
  if (uncertainty) {
    return `${sentenceCase(plainEnglishReason(uncertainty.name, 'uncertainty'))}.`
  }
  return 'The read is usable, but not fully clean.'
}

function metricProfile(outputs: PrimaryOutputs): string {
  const quality = outputs.fundamental_quality
  const mispricing = outputs.mispricing_signal
  const fragility = outputs.fragility_risk
  const confidence = outputs.signal_confidence

  if (quality >= 70 && mispricing >= 55 && fragility <= 30) {
    return 'This is one of the cleaner combinations of business quality, upside, and controlled downside in the list.'
  }
  if (quality >= 70 && fragility <= 30) {
    return 'This reads primarily as a strong operator with controlled downside, not as a pure deep-value rerating trade.'
  }
  if (mispricing >= 60 && confidence >= 55) {
    return 'This ranks well because there is still a real rerating case and the evidence is good enough to act on.'
  }
  if (confidence < 50) {
    return 'The model sees enough here to keep it relevant, but the score is still being discounted by a softer evidence base.'
  }
  if (fragility >= 60) {
    return 'The upside case is being held back because the downside profile is still too easy to break under stress.'
  }
  return 'The name stays near the top because it is balanced across the main dimensions without a fatal weak spot.'
}

function strongestBlock(blockScores: Record<string, number> | undefined, keys: string[]): string | null {
  if (!blockScores) return null
  let bestKey: string | null = null
  let bestValue = -Infinity
  for (const key of keys) {
    const value = blockScores[key]
    if (typeof value === 'number' && value > bestValue) {
      bestValue = value
      bestKey = key
    }
  }
  return bestKey
}

function weakestBlock(blockScores: Record<string, number> | undefined, keys: string[]): string | null {
  if (!blockScores) return null
  let worstKey: string | null = null
  let worstValue = Infinity
  for (const key of keys) {
    const value = blockScores[key]
    if (typeof value === 'number' && value < worstValue) {
      worstValue = value
      worstKey = key
    }
  }
  return worstKey
}

function supportSentence(subnet: SubnetSummary): string {
  const blocks = subnet.analysis_preview?.block_scores
  const primarySupport =
    strongestBlock(blocks, ['fundamental_health', 'structural_validity', 'market_legitimacy', 'confidence_factor']) ??
    subnet.analysis_preview?.top_positive_drivers?.[0]?.name

  switch (primarySupport) {
    case 'fundamental_health':
      return 'The rank is being earned by strong underlying quality rather than by a speculative rerating.'
    case 'structural_validity':
      return 'It ranks well because the market structure still looks investable instead of fragile or crowded.'
    case 'market_legitimacy':
      return 'It is screening well because the network already looks credible enough to carry institutional attention.'
    case 'confidence_factor':
      return 'It holds a high rank because the evidence stack is coherent enough to support the thesis.'
    default:
      return 'It ranks well because the model sees a credible quality base with manageable downside.'
  }
}

function headwindSentence(subnet: SubnetSummary): string {
  const drag =
    subnet.analysis_preview?.top_negative_drags?.find((item) => metricPhrase(contributorKey(item))) ??
    subnet.analysis_preview?.key_uncertainties?.find((item) => metricPhrase(item.name))

  const dragKey = drag ? ('metric' in drag ? contributorKey(drag) : drag.name) : ''
  const dragText = metricPhrase(dragKey)
  if (!dragText) return ''

  if (dragKey === 'discarded_inputs') {
    return `The main caveat is that ${dragText}.`
  }

  return `The current limiter is that ${dragText}.`
}

function rankingHeadline(subnet: SubnetSummary): string {
  const outputs = subnet.primary_outputs

  if (!outputs) {
    return 'The ranking is provisional because the latest scored output is still missing.'
  }
  const positives = subnet.analysis_preview?.top_positive_drivers ?? []
  const primarySupport = contributorName(positives[0])
  const secondarySupport = contributorName(positives[1])
  const supportLead = driverSupportClause(primarySupport)
  const supportFollow = secondarySupport && secondarySupport !== primarySupport ? driverSupportClause(secondarySupport) : ''

  const quality = formatScore(outputs.fundamental_quality)
  const upside = formatScore(outputs.mispricing_signal)
  const risk = formatScore(outputs.fragility_risk)
  const evidence = formatScore(outputs.signal_confidence)

  const supportSentenceText = supportLead
    ? `${sentenceCase(supportLead)}.`
    : `${supportSentence(subnet)}`

  const supportFollowSentence = supportFollow
    ? `It is also getting help from the fact that ${supportFollow}.`
    : ''

  return [
    `${subnet.name?.trim() || `Subnet ${subnet.netuid}`} ranks ${subnet.rank ? `#${subnet.rank}` : 'near the top'} because ${supportLead || 'the model sees a credible mix of strength and manageable downside'}.`,
    `Strength is ${quality}, Risk is ${risk}, Upside Gap is ${upside}, and Evidence Quality is ${evidence}. ${metricProfile(outputs)}`,
    supportFollowSentence || supportSentenceText,
  ]
    .filter(Boolean)
    .join(' ')
}

function rankingCatalystLine(subnet: SubnetSummary): string {
  const outputs = subnet.primary_outputs
  const positives = subnet.analysis_preview?.top_positive_drivers ?? []
  const drags = subnet.analysis_preview?.top_negative_drags ?? []
  const uncertainties = subnet.analysis_preview?.key_uncertainties ?? []

  const supportClauses = positives
    .slice(0, 2)
    .map((item) => driverSupportClause(contributorName(item)))
    .filter(Boolean)
  const dragClauses = drags
    .slice(0, 2)
    .map((item) => driverDragClause(contributorName(item)))
    .filter(Boolean)

  const leadUncertainty = uncertainties[0] ? uncertaintyClause(uncertainties[0].name) : ''

  if (!outputs) {
    return decisionLineFromOutputs(outputs)
  }

  const upsideSentence =
    outputs.mispricing_signal >= 60
      ? 'The market still appears to be leaving enough upside on the table for a rerating case.'
      : outputs.mispricing_signal >= 45
        ? 'There is still some upside, but it is no longer a clean deep-discount setup.'
        : 'The current limitation is that the valuation gap is modest, so the case needs continued execution to work.'

  const riskSentence =
    outputs.fragility_risk <= 30
      ? 'On the downside, stress is currently well contained.'
      : outputs.fragility_risk <= 50
        ? 'On the downside, risk is manageable but not trivial.'
        : 'On the downside, the stress profile is strong enough to matter in position sizing.'

  const supportSentenceText = supportClauses.length
    ? `The score is being supported by ${joinClauses(supportClauses)}.`
    : ''
  const dragSentenceText = dragClauses.length
    ? `What is holding it back is that ${joinClauses(dragClauses)}.`
    : headwindSentence(subnet)
  const uncertaintySentence = leadUncertainty
    ? `The main caveat is that ${leadUncertainty}.`
    : outputs.signal_confidence < 50
      ? 'The main caveat is that the evidence base is still softer than you would want for a full-conviction memo.'
      : ''

  return [supportSentenceText, upsideSentence, riskSentence, dragSentenceText, uncertaintySentence]
    .filter(Boolean)
    .join(' ')
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

function warningFlagLabel(flag: string): RowFlag | null {
  switch (flag) {
    case 'low_confidence':
      return { label: 'Low confidence', tone: 'confidence' }
    case 'thin_liquidity':
      return { label: 'Thin liquidity', tone: 'fragility' }
    case 'concentration':
      return { label: 'Concentration', tone: 'fragility' }
    case 'fragility':
      return { label: 'High fragility', tone: 'fragility' }
    case 'telemetry_gap':
      return { label: 'Telemetry gap', tone: 'warning' }
    case 'reconstructed_inputs':
      return { label: 'Reconstructed inputs', tone: 'warning' }
    case 'weak_market_structure':
      return { label: 'Weak structure', tone: 'warning' }
    default:
      return null
  }
}

function investabilityBadge(status: string | null | undefined): InvestabilityBadge {
  switch (status) {
    case 'investable':
      return { label: 'Investable', tone: 'quality' }
    case 'speculative':
      return { label: 'Speculative', tone: 'mispricing' }
    case 'constrained':
      return { label: 'Constrained', tone: 'warning' }
    case 'uninvestable':
      return { label: 'Uninvestable', tone: 'fragility' }
    default:
      return { label: 'Under review', tone: 'warning' }
  }
}

function compareLabel(subnet: SubnetSummary): string {
  if (!subnet.primary_outputs) return 'Track for compare'
  return 'Add to compare'
}

export function toUniverseRow(subnet: SubnetSummary): UniverseRowViewModel {
  const positives = clipHints(summaryHints(subnet.analysis_preview, 'quality', 'positive'), 2)
  const negatives = clipHints(summaryHints(subnet.analysis_preview, 'fragility', 'negative'), 2)
  const warnings = clipHints(summaryWarnings(subnet), 2)
  const warningFlags = subnet.warning_flags.map(warningFlagLabel).filter((item): item is RowFlag => Boolean(item))
  return {
    id: subnet.netuid,
    href: `/subnets/${subnet.netuid}`,
    name: toDisplayName(subnet.name, subnet.netuid),
    netuidLabel: `SN${subnet.netuid}`,
    modelLabel: modelLabelValue(subnet),
    modelLabelTone: modelLabelTone(modelLabelValue(subnet)),
    thesisLine: rankingHeadline(subnet),
    decisionLine: rankingCatalystLine(subnet),
    signals: getSignalStats(subnet.primary_outputs),
    opportunityNotes: positives,
    riskNotes: negatives,
    uncertaintyNotes: warnings,
    statusFlags: buildStatusFlags(subnet),
    metricReasons: {
      strength: shortMetricReason(subnet, 'strength'),
      upside: shortMetricReason(subnet, 'upside'),
      risk: shortMetricReason(subnet, 'risk'),
      evidence: shortMetricReason(subnet, 'evidence'),
    },
    scoreLabel: subnet.score.toFixed(1),
    investability: investabilityBadge(subnet.investability_status),
    warningFlags,
    opportunityRead: opportunityRead(subnet),
    qualityRead: qualityRead(subnet),
    fragilityRead: fragilityRead(subnet),
    confidenceRead: confidenceRead(subnet),
    rankLabel: subnet.rank ? `#${subnet.rank}` : 'n/a',
    percentileLabel: subnet.percentile != null ? `${subnet.percentile.toFixed(1)}th` : 'n/a',
    updatedLabel: formatDateTime(subnet.computed_at),
    compareLabel: compareLabel(subnet),
    awaitingRun: !subnet.primary_outputs,
    updatedAtMs: parseTimestamp(subnet.computed_at),
    sortValues: {
      rank: -(subnet.rank ?? 9999),
      score: subnet.score,
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
      return aRank - bRank || a.id - b.id
    }
    return a.sortValues[sortId] - b.sortValues[sortId] || a.id - b.id
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

function setupStatusMeta(value: ResearchSummary['setup_status']): ResearchSummaryViewModel['setupStatus'] {
  switch (value) {
    case 'strong_setup':
      return { value, label: 'Strong setup', tone: 'quality' }
    case 'improving_setup':
      return { value, label: 'Improving setup', tone: 'mispricing' }
    case 'fragile_setup':
      return { value, label: 'Fragile setup', tone: 'warning' }
    default:
      return { value, label: 'Not investable', tone: 'fragility' }
  }
}

function marketCapacityMeta(value: ResearchSummary['market_capacity']): ResearchSummaryViewModel['marketCapacity'] {
  switch (value) {
    case 'high':
      return { value, label: 'High', tone: 'quality' }
    case 'medium':
      return { value, label: 'Medium', tone: 'mispricing' }
    case 'low':
      return { value, label: 'Low', tone: 'warning' }
    default:
      return { value, label: 'Very low', tone: 'fragility' }
  }
}

function evidenceStrengthMeta(value: ResearchSummary['evidence_strength']): ResearchSummaryViewModel['evidenceStrength'] {
  switch (value) {
    case 'high':
      return { value, label: 'High', tone: 'confidence' }
    case 'medium':
      return { value, label: 'Medium', tone: 'warning' }
    default:
      return { value, label: 'Low', tone: 'fragility' }
  }
}

function fallbackResearchSummary(
  subnet: SubnetDetail,
  summary: UniverseRowViewModel,
  stressDrawdown: number | null | undefined,
): ResearchSummary {
  const outputs = subnet.primary_outputs ?? subnet.analysis?.primary_outputs ?? null
  const analysis = subnet.analysis
  const firstBreak = analysis?.thesis_breakers?.[0]
  const firstPositive = analysis?.top_positive_drivers?.[0]
  const firstNegative = (analysis?.top_negative_drags ?? analysis?.top_negative_drivers ?? [])[0]
  const firstUncertainty = analysis?.key_uncertainties?.[0]

  let setupStatus: ResearchSummary['setup_status'] = 'not_investable'
  if (outputs) {
    if (
      (subnet.investability_status === 'investable' || subnet.investability_status === 'speculative') &&
      outputs.fundamental_quality >= 65 &&
      outputs.mispricing_signal >= 55 &&
      outputs.fragility_risk <= 45 &&
      outputs.signal_confidence >= 55
    ) {
      setupStatus = 'strong_setup'
    } else if (outputs.fundamental_quality >= 55 && outputs.signal_confidence >= 45 && outputs.fragility_risk <= 60) {
      setupStatus = 'improving_setup'
    } else if (outputs.signal_confidence >= 35 && outputs.fragility_risk <= 75) {
      setupStatus = 'fragile_setup'
    }
  }

  const marketCap = subnet.market_cap_tao ?? 0
  const poolDepth = subnet.tao_in_pool ?? 0
  const marketCapacity: ResearchSummary['market_capacity'] =
    marketCap >= 250000 || poolDepth >= 25000
      ? 'high'
      : marketCap >= 75000 || poolDepth >= 7500
        ? 'medium'
        : marketCap >= 15000 || poolDepth >= 1500
          ? 'low'
          : 'very_low'

  const evidenceStrength: ResearchSummary['evidence_strength'] =
    (outputs?.signal_confidence ?? 0) >= 65
      ? 'high'
      : (outputs?.signal_confidence ?? 0) >= 45
        ? 'medium'
        : 'low'

  return {
    setup_status: setupStatus,
    setup_read: summary.decisionLine,
    why_now: firstPositive ? `Why now: ${cleanSentence(contributorLabel(firstPositive))}.` : summary.thesisLine,
    main_constraint: firstNegative
      ? `The main constraint is ${cleanSentence(contributorLabel(firstNegative)).toLowerCase()}.`
      : summary.fragilityRead,
    break_condition: firstBreak
      ? cleanSentence(firstBreak)
      : stressDrawdown != null
        ? `The setup breaks if stress behavior worsens materially from the current ${stressDrawdown.toFixed(1)}% drawdown path.`
        : 'The setup breaks if the current positive drivers stop improving or the evidence layer weakens further.',
    market_capacity: marketCapacity,
    evidence_strength: evidenceStrength,
    relative_peer_context: firstUncertainty
      ? `${summary.rankLabel !== 'n/a' ? `It currently ranks ${summary.rankLabel}. ` : ''}${cleanSentence(uncertaintyLabel(firstUncertainty))}`
      : `${summary.rankLabel !== 'n/a' ? `It currently ranks ${summary.rankLabel}. ` : ''}${summary.metricReasons.strength}`,
  }
}

function buildResearchSummaryViewModel(
  researchSummary: ResearchSummary | null | undefined,
  subnet: SubnetDetail,
  summary: UniverseRowViewModel,
  stressDrawdown: number | null | undefined,
): ResearchSummaryViewModel {
  const resolved = researchSummary ?? fallbackResearchSummary(subnet, summary, stressDrawdown)
  return {
    setupStatus: setupStatusMeta(resolved.setup_status),
    marketCapacity: marketCapacityMeta(resolved.market_capacity),
    evidenceStrength: evidenceStrengthMeta(resolved.evidence_strength),
    setupRead: resolved.setup_read,
    whyNow: resolved.why_now,
    mainConstraint: resolved.main_constraint,
    breakCondition: resolved.break_condition,
    relativePeerContext: resolved.relative_peer_context,
  }
}

function compactText(value: string | null | undefined, fallback: string): string {
  const cleaned = cleanSentence(value)
  if (!cleaned) return fallback
  return cleaned.replace(/^(why now|setup read|main constraint|break condition)\s*:\s*/i, '')
}

function compactSentence(value: string | null | undefined, fallback: string): string {
  const text = compactText(value, fallback)
  const firstSentence = text.split(/(?<=[.!?])\s+/)[0] ?? text
  const trimmed = firstSentence.replace(/\s+/g, ' ').trim()
  if (!trimmed) return fallback
  return /[.!?]$/.test(trimmed) ? trimmed : `${trimmed}.`
}

function formatAbsoluteScore(value: number | null | undefined): string | undefined {
  if (value == null || !Number.isFinite(value)) return undefined
  return value.toFixed(1)
}

function percentValue(value: number | null | undefined): string {
  if (value == null || !Number.isFinite(value)) return 'n/a'
  return `${value.toFixed(1)}%`
}

function confidenceLabel(value: number | null | undefined): string {
  if (value == null || !Number.isFinite(value)) return 'Limited'
  if (value >= 65) return 'High'
  if (value >= 45) return 'Medium'
  return 'Low'
}

function reliabilityLabel(value: number | null | undefined): string {
  if (value == null || !Number.isFinite(value)) return 'Limited'
  if (value >= 0.7) return 'High'
  if (value >= 0.5) return 'Medium'
  return 'Low'
}

function insightBodyFromContributor(
  item: ExplanationContributor | undefined | null,
  fallback: string,
  mode: 'positive' | 'negative' | 'uncertainty',
): string {
  const name = contributorName(item)
  const mapped = plainEnglishReason(name, mode)
  if (mapped) return compactSentence(mapped, fallback)
  const text = item ? contributorLabel(item) : ''
  return compactSentence(text, fallback)
}

function confidenceMetricLabel(name: string): string {
  switch (name) {
    case 'data_confidence':
      return 'Data Reliability'
    case 'market_confidence':
      return 'Market Reliability'
    case 'thesis_confidence':
      return 'Thesis Reliability'
    default:
      return sentenceCase(name.replace(/_/g, ' '))
  }
}

function buildExecutiveSummary(researchSummary: ResearchSummaryViewModel): MemoSummaryItem[] {
  return [
    {
      label: 'Setup Read',
      body: compactSentence(researchSummary.setupRead, 'The setup still lacks a clean read.'),
      tone: researchSummary.setupStatus.tone,
    },
    {
      label: 'Why Now',
      body: compactSentence(researchSummary.whyNow, 'There is no active timing signal yet.'),
      tone: 'mispricing',
    },
    {
      label: 'Main Constraint',
      body: compactSentence(researchSummary.mainConstraint, 'No single execution constraint stands out yet.'),
      tone: 'warning',
    },
    {
      label: 'Break Condition',
      body: compactSentence(researchSummary.breakCondition, 'The setup breaks if the current support stops holding.'),
      tone: 'fragility',
    },
  ]
}

function buildContextRow(
  researchSummary: ResearchSummaryViewModel,
  summary: UniverseRowViewModel,
  updatedLabel: string,
  stale: boolean,
): MemoContextItem[] {
  return [
    {
      label: 'Market Capacity',
      value: researchSummary.marketCapacity.label,
      tone: researchSummary.marketCapacity.tone,
    },
    {
      label: 'Evidence Strength',
      value: researchSummary.evidenceStrength.label,
      tone: researchSummary.evidenceStrength.tone,
    },
    {
      label: 'Peer Rank',
      value: summary.rankLabel === 'n/a' ? summary.percentileLabel : `${summary.rankLabel}${summary.percentileLabel === 'n/a' ? '' : ` · ${summary.percentileLabel}`}`,
    },
    {
      label: 'Last Updated',
      value: updatedLabel,
      tone: stale ? 'warning' : undefined,
    },
  ]
}

function buildMarketStructureItems(
  subnet: SubnetDetail,
  researchSummary: ResearchSummaryViewModel,
  analysis: SubnetDetail['analysis'],
): MemoInsightItem[] {
  const fragilityContributor = analysis?.primary_signal_contributors?.fragility_risk?.[0]
  const marketDrag = analysis?.top_negative_drags?.find((item) =>
    ['reserve_change', 'liquidity_improvement_rate', 'reserve_growth_without_price', 'fragility', 'cohort_quality_edge'].includes(contributorName(item)),
  )
  const concentrationSignal = analysis?.top_negative_drags?.find((item) =>
    contributorName(item).includes('concentration'),
  )

  return [
    {
      label: 'Liquidity',
      value: formatCompactNumber(subnet.tao_in_pool, 0),
      body: compactSentence(
        insightBodyFromContributor(
          marketDrag,
          'Trading depth is still the main execution constraint.',
          'negative',
        ),
        'Trading depth is still the main execution constraint.',
      ),
      tone: researchSummary.marketCapacity.tone,
    },
    {
      label: 'Concentration',
      value: concentrationSignal ? 'Watch' : 'Contained',
      body: compactSentence(
        insightBodyFromContributor(
          concentrationSignal,
          'No concentration shock is dominating the read right now.',
          concentrationSignal ? 'negative' : 'uncertainty',
        ),
        'No concentration shock is dominating the read right now.',
      ),
      tone: concentrationSignal ? 'warning' : 'neutral',
    },
    {
      label: 'Market Capacity',
      value: researchSummary.marketCapacity.label,
      body: compactSentence(
        `Current capacity reads ${researchSummary.marketCapacity.label.toLowerCase()} for larger flows.`,
        'Current capacity is still forming.',
      ),
      tone: researchSummary.marketCapacity.tone,
    },
    {
      label: 'Fragility',
      value: analysis?.fragility_class ? sentenceCase(analysis.fragility_class.toLowerCase()) : 'Unknown',
      body: compactSentence(
        insightBodyFromContributor(
          fragilityContributor,
          'Stress behavior remains part of the execution check.',
          'negative',
        ),
        'Stress behavior remains part of the execution check.',
      ),
      tone: analysis?.stress_drawdown != null && analysis.stress_drawdown >= 30 ? 'fragility' : 'warning',
    },
  ]
}

function buildEvidenceItems(
  researchSummary: ResearchSummaryViewModel,
  reliabilityEntries: MemoSectionItem[],
  uncertainties: MemoSectionItem[],
  confidence: ConfidenceRationale | undefined,
): MemoInsightItem[] {
  const historyDepth = reliabilityEntries.find((item) => item.title === 'Historical depth')
  const dataReliability = reliabilityEntries.find((item) => item.title === 'Market data reliability')
  const uncertainty = uncertainties[0]

  return [
    {
      label: 'Evidence Strength',
      value: researchSummary.evidenceStrength.label,
      body: compactSentence(
        `The current read is supported by ${researchSummary.evidenceStrength.label.toLowerCase()} evidence strength.`,
        'The current evidence stack is still limited.',
      ),
      tone: researchSummary.evidenceStrength.tone,
    },
    {
      label: 'History Depth',
      value: historyDepth ? historyDepth.body : confidenceLabel(confidence?.thesis_confidence),
      body: compactSentence(historyDepth?.meta || historyDepth?.body, 'The historical record is still thin.'),
      tone: historyDepth?.tone ?? 'warning',
    },
    {
      label: 'Data Reliability',
      value: dataReliability ? dataReliability.body : reliabilityLabel(confidence?.data_confidence != null ? confidence.data_confidence / 100 : null),
      body: compactSentence(
        dataReliability?.meta || dataReliability?.body,
        'The data layer is usable, but not fully clean.',
      ),
      tone: dataReliability?.tone ?? 'warning',
    },
    {
      label: 'Key Uncertainty',
      value: uncertainty ? sentenceCase(uncertainty.title) : 'None flagged',
      body: compactSentence(uncertainty?.body, 'No single uncertainty dominates the read yet.'),
      tone: uncertainty?.tone ?? 'neutral',
    },
  ]
}

function buildScoreExplanationItems(
  items: ExplanationContributor[] | undefined,
  tone: SignalTone,
  fallback: string,
  mode: 'positive' | 'negative',
): ScoreExplanationItem[] {
  return (items ?? [])
    .slice(0, 3)
    .map((item) => ({
      title: sentenceCase(contributorTitle(item).replace(/_/g, ' ')),
      value: formatAbsoluteScore(typeof item.signed_contribution === 'number' ? Math.abs(item.signed_contribution) * 100 : null),
      body: compactSentence(insightBodyFromContributor(item, fallback, mode), fallback),
      tone,
    }))
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
    investability_status: subnet.investability_status,
    warning_flags: subnet.warning_flags,
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
  const researchSummary = buildResearchSummaryViewModel(subnet.research_summary, subnet, summary, analysis?.stress_drawdown)
  const updatedLabel = formatDateTime(subnet.computed_at)
  const stale = isStale(subnet.computed_at)

  const reliabilityEntries: MemoSectionItem[] = Object.entries(conditioning?.reliability ?? {}).map(([key, value]) => ({
    title: RELIABILITY_LABELS[key] ?? key.replace(/_/g, ' '),
    body: `${(value * 100).toFixed(1)} / 100`,
    tone: reliabilityTone(value),
    meta:
      key === 'history_data_reliability'
        ? 'How much clean history is available.'
        : key === 'market_data_reliability'
          ? 'How stable the market-side telemetry looks.'
          : key === 'validator_data_reliability'
            ? 'How much validator-side evidence is visible.'
            : 'How much outside corroboration is available.',
  }))

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

  const executiveSummary = buildExecutiveSummary(researchSummary)
  const contextRow = buildContextRow(researchSummary, summary, updatedLabel, stale)
  const marketStructure = buildMarketStructureItems(subnet, researchSummary, analysis)
  const evidenceItems = buildEvidenceItems(researchSummary, reliabilityEntries, toUncertaintyItems(analysis?.key_uncertainties), confidence)
  const topSupports = buildScoreExplanationItems(
    analysis?.top_positive_drivers,
    'quality',
    'No clear support is carrying the setup yet.',
    'positive',
  )
  const topDrags = buildScoreExplanationItems(
    analysis?.top_negative_drags ?? analysis?.top_negative_drivers,
    'fragility',
    'No single drag dominates the setup yet.',
    'negative',
  )
  const setupTag = investabilityBadge(subnet.investability_status)
  const secondaryTag: InvestabilityBadge | null =
    researchSummary.evidenceStrength.value === 'high'
      ? { label: 'Evidence high', tone: researchSummary.evidenceStrength.tone }
      : researchSummary.evidenceStrength.value === 'medium'
        ? { label: 'Evidence medium', tone: researchSummary.evidenceStrength.tone }
        : { label: 'Evidence limited', tone: researchSummary.evidenceStrength.tone }

  return {
    name: toDisplayName(subnet.name, subnet.netuid),
    netuidLabel: `SN${subnet.netuid}`,
    href: `/subnets/${subnet.netuid}`,
    scoreLabel: subnet.score.toFixed(1),
    modelLabel: summary.modelLabel,
    modelLabelTone: summary.modelLabelTone,
    headerSubtitle: compactSentence(
      researchSummary.setupRead !== summary.decisionLine ? researchSummary.setupRead : subnet.thesis ?? analysis?.thesis ?? summary.decisionLine,
      summary.decisionLine,
    ),
    researchSummary,
    updatedLabel,
    rankLabel: subnet.rank ? `#${subnet.rank}` : 'n/a',
    percentileLabel: subnet.percentile != null ? `${subnet.percentile.toFixed(1)}th` : 'n/a',
    signals: getSignalStats(outputs),
    primaryTag: {
      label: researchSummary.setupStatus.label,
      tone: researchSummary.setupStatus.tone,
    },
    secondaryTag,
    executiveSummary,
    contextRow,
    marketStructure,
    evidenceItems,
    topSupports,
    topDrags,
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
