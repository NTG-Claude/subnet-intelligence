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
  label: 'Market Size' | 'Read Trust' | 'Peer Rank' | 'Last Updated'
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

export interface MemoAnchorItem {
  label: 'Strongest support' | 'Main thing capping the score'
  value: string
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
  anchorInsights: MemoAnchorItem[]
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
  mispricing_signal: { key: 'mispricing_signal', label: 'Upside', shortLabel: 'UPSD', tone: 'mispricing' },
  fragility_risk: { key: 'fragility_risk', label: 'Downside', shortLabel: 'RISK', tone: 'fragility', invert: true },
  signal_confidence: { key: 'signal_confidence', label: 'Trust', shortLabel: 'TRST', tone: 'confidence' },
}

const BLOCK_LABELS: Record<string, string> = {
  intrinsic_quality: 'Business quality',
  economic_sustainability: 'Economic durability',
  reflexivity: 'Market reflexivity',
  stress_robustness: 'Stress resilience',
  opportunity_gap: 'Valuation gap',
}

const RELIABILITY_LABELS: Record<string, string> = {
  market_data_reliability: 'Market inputs',
  validator_data_reliability: 'Validator coverage',
  history_data_reliability: 'History coverage',
  external_data_reliability: 'Outside confirmation',
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

function normalizeContributorName(value: string | null | undefined): string {
  return (value ?? '').trim().toLowerCase().replace(/[\s-]+/g, '_')
}

function isGenericModelPhrase(value: string | null | undefined): boolean {
  const normalized = normalizeContributorName(value)
  return [
    'evidence_penalty',
    'confidence_drag',
    'valuation_gap',
    'controlled_downside',
    'thesis_coherence',
    'input_quality',
    'market_support',
    'market_confirmation',
    'aligned_evidence',
    'durable_quality',
    'interesting_setup',
  ].includes(normalized)
}

function contributorLabel(item: ExplanationContributor): string {
  const key = contributorKey(item)
  const mapped = plainEnglishReason(key, 'negative') || plainEnglishReason(key, 'positive') || plainEnglishReason(key, 'uncertainty')
  if (mapped) return mapped
  if (item.short_explanation && !isGenericModelPhrase(item.short_explanation)) return item.short_explanation
  return item.metric || item.name || item.source_block || 'Unspecified contributor'
}

function contributorKey(item: ExplanationContributor): string {
  return normalizeContributorName(item.name || item.metric || '')
}

function contributorTitle(item: ExplanationContributor): string {
  return item.metric || item.name || item.source_block || 'Contributor'
}

function contributorDisplayTitle(name: string | undefined | null, mode: 'positive' | 'negative' | 'neutral' = 'neutral'): string {
  switch (normalizeContributorName(name)) {
    case 'fundamental_health':
      return 'The subnet is doing real work'
    case 'structural_validity':
      return 'The market structure still looks tradable'
    case 'market_legitimacy':
      return 'The market is already taking it seriously'
    case 'confidence_factor':
      return 'The main signals are pointing the same way'
    case 'thesis_confidence':
      return 'The investment case does not rely on one fragile assumption'
    case 'market_confidence':
      return 'Price action is not fighting the thesis'
    case 'data_confidence':
      return 'The data behind this read is reasonably clean'
    case 'base_opportunity':
    case 'opportunity_underreaction':
      return 'The market may still be underpricing the subnet'
    case 'fragility':
      return mode === 'positive' ? 'It is holding up under stress' : 'The case can still break under stress'
    case 'reserve_change':
      return 'More capital is not yet changing the market response'
    case 'liquidity_improvement_rate':
      return 'Liquidity is not improving fast enough'
    case 'reserve_growth_without_price':
      return 'Operational improvement is not showing up in price'
    case 'quality_acceleration':
      return mode === 'negative' ? 'Improvement has slowed' : 'Execution is still improving'
    case 'price_response_lag_to_quality_shift':
      return 'Price may already be catching up'
    case 'expected_price_response_gap':
      return 'The upside gap is not very wide anymore'
    case 'emission_to_sticky_usage_conversion':
      return 'Incentives are not yet turning into lasting usage'
    case 'post_incentive_retention':
      return 'Users still need to stay after incentives fade'
    case 'emission_efficiency':
      return 'New emissions are not producing enough real usage'
    case 'cohort_quality_edge':
      return 'It does not clearly outclass comparable subnets'
    case 'discarded_inputs':
      return 'Parts of the evidence had to be dropped'
    case 'external_data_reliability':
      return 'Outside confirmation is still thin'
    case 'validator_data_reliability':
      return 'Validator-side coverage is thinner than ideal'
    case 'history_data_reliability':
      return 'The visible history is still shallow'
    default:
      return sentenceCase((name || 'Contributor').replace(/_/g, ' '))
  }
}

function uncertaintyLabel(item: KeyUncertainty): string {
  if (item.short_explanation && !isGenericModelPhrase(item.short_explanation)) return item.short_explanation
  const mapped = plainEnglishReason(item.name, 'uncertainty')
  if (mapped) return mapped
  return item.name.replace(/_/g, ' ')
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
  if (!outputs) return 'Fresh scored outputs are still missing, so this read is provisional.'
  if (outputs.mispricing_signal >= 70 && outputs.signal_confidence >= 60 && outputs.fragility_risk <= 45) {
    return 'The score is high because there still appears to be real upside, the evidence is strong enough to lean on, and the downside does not look out of control.'
  }
  if (outputs.fundamental_quality >= 70 && outputs.fragility_risk <= 45) {
    return 'The score is being earned mostly through operating quality and decent resilience, even if the upside gap is not extreme.'
  }
  if (outputs.fragility_risk >= 65) {
    return 'The score stays capped because the setup can weaken quickly if market conditions or participation deteriorate.'
  }
  if (outputs.signal_confidence < 50) {
    return 'The read remains cautious because the data foundation is not clean enough for a higher-conviction score.'
  }
  return 'The subnet has enough going for it to stay relevant, but not enough clean confirmation to score like a clear winner.'
}

function cleanSentence(value: string | undefined | null): string {
  return (value ?? '').replace(/\s+/g, ' ').trim()
}

function metricPhrase(name: string | undefined | null): string {
  switch (normalizeContributorName(name)) {
    case 'fragility':
      return 'it is still holding up reasonably well when the model applies stress'
    case 'fundamental_health':
      return 'activity and operating quality still look solid enough to support the case'
    case 'thesis_confidence':
      return 'the broader case still fits the evidence that is visible'
    case 'market_confidence':
      return 'price and market structure are not obviously contradicting the thesis'
    case 'confidence_factor':
      return 'the major signals broadly agree instead of cancelling each other out'
    case 'base_opportunity':
      return 'the market may still be leaving part of the improvement unpriced'
    case 'data_confidence':
      return 'enough of the data is visible to form a usable read'
    case 'reserve_change':
      return 'more capital in the system is not yet producing a stronger market response'
    case 'liquidity_improvement_rate':
      return 'trading depth is not improving fast enough to make the setup easier to own'
    case 'reserve_growth_without_price':
      return 'operational improvement is still not clearly being rewarded in price'
    case 'quality_acceleration':
      return 'execution is okay, but the rate of improvement is no longer accelerating'
    case 'price_response_lag_to_quality_shift':
      return 'part of the rerating may already have happened'
    case 'expected_price_response_gap':
      return 'the remaining upside gap is smaller than in the strongest rerating cases'
    case 'emission_to_sticky_usage_conversion':
      return 'incentives are not yet turning into durable usage'
    case 'post_incentive_retention':
      return 'the subnet still needs to prove users stay once incentives weaken'
    case 'emission_efficiency':
      return 'new emissions are not translating into enough real usage'
    case 'cohort_quality_edge':
      return 'it does not have a large quality lead over nearby peers'
    case 'discarded_inputs':
      return 'parts of the input history had to be discarded, so the read has blind spots'
    case 'external_data_reliability':
      return 'outside confirmation is still thin'
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
  switch (normalizeContributorName(name)) {
    case 'fundamental_health':
      return 'the subnet looks operationally healthier than most peers'
    case 'structural_validity':
      return 'the market structure still looks tradable instead of badly distorted'
    case 'market_legitimacy':
      return 'the market is already treating the network like a real, credible participant'
    case 'confidence_factor':
      return 'the main signals are lining up instead of sending conflicting messages'
    case 'thesis_confidence':
      return 'the thesis does not depend on one shaky assumption'
    case 'market_confidence':
      return 'price and market behavior are not undermining the thesis'
    case 'data_confidence':
      return 'the visible data is clean enough to support a real opinion'
    case 'base_opportunity':
    case 'opportunity_underreaction':
      return 'the market still may not be fully reflecting what has improved'
    case 'quality_acceleration':
      return 'execution is still improving instead of merely holding flat'
    case 'fragility':
      return 'the setup is holding together reasonably well under stress'
    default: {
      const phrase = metricPhrase(name)
      if (phrase) return phrase
      return `${name.replace(/_/g, ' ')} is helping the case in a visible way`
    }
  }
}

function driverDragClause(name: string): string {
  switch (normalizeContributorName(name)) {
    case 'reserve_change':
      return 'more reserves are not yet leading to stronger market follow-through'
    case 'liquidity_improvement_rate':
      return 'liquidity is not improving fast enough to make the setup easier to own'
    case 'reserve_growth_without_price':
      return 'better fundamentals are still not showing up clearly enough in price'
    case 'quality_acceleration':
      return 'execution still looks okay, but the rate of improvement has cooled'
    case 'price_response_lag_to_quality_shift':
      return 'the market may already have priced in part of the improvement'
    case 'expected_price_response_gap':
      return 'the remaining upside gap is smaller than in the best rerating setups'
    case 'emission_to_sticky_usage_conversion':
      return 'emissions are not yet converting into sticky, lasting usage'
    case 'post_incentive_retention':
      return 'the subnet still needs to prove users remain after incentives fade'
    case 'emission_efficiency':
      return 'new emissions are not turning into enough real usage'
    case 'cohort_quality_edge':
      return 'its edge over similar subnets is not large enough to be decisive'
    case 'fragility':
      return 'even moderate stress could still damage the thesis quickly'
    case 'discarded_inputs':
      return 'parts of the evidence had to be discarded, so the read is less reliable'
    case 'external_data_reliability':
      return 'outside confirmation is still thin'
    default: {
      const phrase = metricPhrase(name)
      if (phrase) return phrase
      return `${name.replace(/_/g, ' ')} is still holding the score back`
    }
  }
}

function uncertaintyClause(name: string): string {
  switch (normalizeContributorName(name)) {
    case 'discarded_inputs':
      return 'some inputs had to be thrown out during conditioning, so part of the picture is missing'
    case 'external_data_reliability':
      return 'there is still not much outside evidence confirming the read, so this relies heavily on internal signals'
    case 'validator_data_reliability':
      return 'validator-side evidence is thinner than ideal, so participation quality is harder to verify'
    case 'history_data_reliability':
      return 'the historical record is not deep or clean enough for a high-trust read'
    default:
      return driverDragClause(name)
  }
}

function plainEnglishReason(name: string, mode: 'positive' | 'negative' | 'uncertainty'): string {
  switch (normalizeContributorName(name)) {
    case 'fundamental_health':
      return mode === 'positive'
        ? 'the subnet looks more operationally durable and useful than most peers, which gives the score a stronger base'
        : 'the underlying operating quality is not strong enough to carry the rating on its own'
    case 'market_legitimacy':
      return mode === 'positive'
        ? 'the market already treats it like a credible network, which helps the score hold up'
        : 'the market still does not treat it like a fully proven network, which limits conviction'
    case 'structural_validity':
      return mode === 'positive'
        ? 'the setup still looks tradable rather than badly distorted, which helps contain downside risk'
        : 'the market structure still has weak points, so the setup can get worse quickly under pressure'
    case 'confidence_factor':
      return mode === 'positive'
        ? 'the main signals broadly point in the same direction, which makes the score easier to trust'
        : 'the evidence does not line up cleanly yet, so the score has to stay more cautious'
    case 'thesis_confidence':
      return mode === 'positive'
        ? 'the overall story hangs together without too many leaps, so the thesis is easier to defend'
        : 'the overall story still relies on assumptions that need proving, which weakens conviction'
    case 'market_confidence':
      return mode === 'positive'
        ? 'price and market behavior are not fighting the thesis, which helps the score stick'
        : 'market behavior is not giving much confirmation yet, so the thesis still needs more proof'
    case 'data_confidence':
      return mode === 'positive'
        ? 'there is enough clean data to form a usable view, so the read is more trustworthy'
        : 'the data picture is still too patchy, which makes the current read less reliable'
    case 'opportunity_underreaction':
    case 'base_opportunity':
      return mode === 'positive'
        ? 'the market still seems to be underestimating part of the story, leaving room for the score to improve'
        : 'the market is not giving much of a discount right now, so upside is harder to justify'
    case 'fragility':
      return mode === 'positive'
        ? 'the subnet is holding up reasonably well under pressure, which helps keep downside contained for now'
        : 'the setup can still break under stress, so the score cannot assume a smooth path'
    case 'reserve_change':
      return 'more capital is not yet leading to a clearly better market response, so the bullish case is still waiting for proof'
    case 'liquidity_improvement_rate':
      return 'trading conditions are not improving fast enough yet, which caps how much size this market can absorb'
    case 'reserve_growth_without_price':
      return 'better fundamentals are not yet clearly showing up in price, so the rerating case remains incomplete'
    case 'quality_acceleration':
      return mode === 'positive'
        ? 'quality is still moving in the right direction, which supports the current rating'
        : 'improvement has slowed and is no longer accelerating, which makes a higher score harder to justify'
    case 'price_response_lag_to_quality_shift':
      return 'the market may already be catching up to the improvement, so less upside may remain than before'
    case 'expected_price_response_gap':
      return 'the rerating gap is smaller than in the best upside names, so the ceiling is lower'
    case 'emission_to_sticky_usage_conversion':
      return 'token emissions are not yet turning into lasting usage, so the current support may fade if incentives cool'
    case 'post_incentive_retention':
      return 'it is still unclear whether users stay once incentives fade, which is a real break risk for the thesis'
    case 'emission_efficiency':
      return 'new emissions are not producing enough real usage, so growth quality is weaker than the headline spend'
    case 'cohort_quality_edge':
      return 'it does not have a big lead over comparable subnets, so peer competition still caps the score'
    case 'discarded_inputs':
      return mode === 'uncertainty'
        ? 'some messy inputs had to be thrown out, so the picture is incomplete and the read is less trustworthy'
        : 'some messy inputs had to be thrown out, which reduces trust in the current read'
    case 'external_data_reliability':
      return 'there is still not much outside evidence to confirm the story, so this read depends heavily on internal signals'
    case 'validator_data_reliability':
      return 'validator-side evidence is thinner than ideal, so participation quality is harder to confirm'
    case 'history_data_reliability':
      return 'the historical record is still shallower than you would want, so trend-based conclusions are less reliable'
    case 'evidence_penalty':
      return 'parts of the evidence base are still too thin, missing, or reconstructed, so the score has to stay more cautious'
    case 'confidence_drag':
      return 'the read is still less reliable than it should be for a higher score, so conviction is being held back'
    case 'valuation_gap':
      return mode === 'positive'
        ? 'the market still may be missing part of the story, leaving room for upside'
        : 'the valuation gap is not wide enough to justify a much stronger score on its own'
    case 'controlled_downside':
      return mode === 'negative'
        ? 'the setup still carries downside that cannot be ignored'
        : 'the downside still looks reasonably contained for now'
    case 'thesis_coherence':
      return mode === 'negative'
        ? 'the current thesis still has logical gaps or assumptions that need proving'
        : 'the main pieces of the thesis fit together well enough to support the read'
    case 'input_quality':
      return mode === 'negative'
        ? 'the input data is not clean enough yet for a higher-trust read'
        : 'the input data looks clean enough to support the current read'
    default: {
      const fallback = metricPhrase(name)
      return fallback || ''
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
    return parts.join('. ') || 'Business quality looks acceptable, but not strong enough to carry the score by itself.'
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
    return parts.join('. ') || 'There may still be upside, but it does not look like a major disconnect right now.'
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
    return 'Risk looks manageable, but not low enough to ignore.'
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
  return 'The read is directionally useful, but not clean enough for a high-trust call.'
}

function metricProfile(outputs: PrimaryOutputs): string {
  const quality = outputs.fundamental_quality
  const mispricing = outputs.mispricing_signal
  const fragility = outputs.fragility_risk
  const confidence = outputs.signal_confidence

  if (quality >= 70 && mispricing >= 55 && fragility <= 30) {
    return 'This is one of the cleaner mixes of quality, upside, and resilience in the current universe.'
  }
  if (quality >= 70 && fragility <= 30) {
    return 'This reads more like a solid operator with decent resilience than a pure deep-discount rerating trade.'
  }
  if (mispricing >= 60 && confidence >= 55) {
    return 'This ranks well because there still appears to be a real rerating case and the evidence is strong enough to matter.'
  }
  if (confidence < 50) {
    return 'The score stays tempered because the evidence base is softer than you would want for a stronger call.'
  }
  if (fragility >= 60) {
    return 'The upside case is being held back because the downside profile still looks too easy to break under stress.'
  }
  return 'The name stays competitive because none of the main dimensions is failing badly, even if none is perfect.'
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
      return 'The score is being earned by real operating quality, not just by hope for a rerating.'
    case 'structural_validity':
      return 'The score holds up because the market structure still looks tradable instead of fragile or overcrowded.'
    case 'market_legitimacy':
      return 'The network already looks credible enough to draw sustained attention, which helps support the score.'
    case 'confidence_factor':
      return 'The score benefits because the main signals tell a broadly consistent story.'
    default:
      return 'The score is being supported by a credible operating base and a downside profile that is not yet breaking the case.'
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

  return `The current cap on the score is that ${dragText}.`
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
    `${subnet.name?.trim() || `Subnet ${subnet.netuid}`} ranks ${subnet.rank ? `#${subnet.rank}` : 'near the top'} because ${supportLead || 'it combines enough quality, upside, and resilience to stay competitive'}.`,
    `The current read is Quality ${quality}, Upside ${upside}, Downside ${risk}, and Trust ${evidence}. ${metricProfile(outputs)}`,
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
      ? 'The score still gets help from a meaningful upside gap between current pricing and the operating picture.'
      : outputs.mispricing_signal >= 45
        ? 'There may still be upside, but this no longer looks like a major disconnect.'
        : 'The score is capped because the remaining upside gap looks modest, so the case depends more on continued execution.'

  const riskSentence =
    outputs.fragility_risk <= 30
      ? 'On the downside, stress looks reasonably contained right now.'
      : outputs.fragility_risk <= 50
        ? 'On the downside, risk is manageable but still real.'
        : 'On the downside, the stress profile is severe enough to matter for sizing and conviction.'

  const supportSentenceText = supportClauses.length
    ? `The score is being supported because ${joinClauses(supportClauses)}.`
    : ''
  const dragSentenceText = dragClauses.length
    ? `What is capping the score is that ${joinClauses(dragClauses)}.`
    : headwindSentence(subnet)
  const uncertaintySentence = leadUncertainty
    ? `Trust remains limited because ${leadUncertainty}.`
    : outputs.signal_confidence < 50
      ? 'Trust remains limited because the evidence base is still softer than you would want for a high-conviction read.'
      : ''

  return [supportSentenceText, upsideSentence, riskSentence, dragSentenceText, uncertaintySentence]
    .filter(Boolean)
    .join(' ')
}

function opportunityRead(subnet: SubnetSummary): string {
  if (!subnet.primary_outputs) return 'No active opportunity read until the subnet is rescored.'
  if (mispricingValue(subnet) >= 70) return 'There still appears to be a meaningful gap between what the subnet is doing and what the market is pricing.'
  if (mispricingValue(subnet) >= 55) return 'There may still be upside, but part of the improvement already looks reflected in price.'
  return 'The upside case looks modest unless new evidence materially improves the story.'
}

function qualityRead(subnet: SubnetSummary): string {
  if (!subnet.primary_outputs) return 'Quality cannot be underwritten until the V2 outputs land.'
  if (qualityValue(subnet) >= 70) return 'The subnet looks operationally solid enough to anchor the thesis even if the upside case changes.'
  if (qualityValue(subnet) >= 55) return 'The quality base is real, but not strong enough to carry the score without help from valuation or market structure.'
  return 'The quality base looks too weak or too thin to support a strong score on its own.'
}

function fragilityRead(subnet: SubnetSummary): string {
  if (!subnet.primary_outputs) return 'Fragility is unknown until the latest run completes.'
  if (fragilityValue(subnet) <= 40) return 'The setup still looks able to absorb ordinary stress without breaking the thesis.'
  if (fragilityValue(subnet) <= 60) return 'The downside is manageable, but it is still strong enough to limit how aggressive the score should be.'
  return 'The rating is being held back because the thesis can break quickly under stress or weaker execution.'
}

function confidenceRead(subnet: SubnetSummary): string {
  const warnings = summaryWarnings(subnet)
  if (!subnet.primary_outputs) return 'No trust read yet because the subnet is still awaiting a full V2 output.'
  if (!warnings.length && confidenceValue(subnet) >= 65) return 'This read looks fairly trustworthy because the inputs appear clean and the major signals agree.'
  if (confidenceValue(subnet) >= 50) return 'This read is directionally useful, but repaired inputs, thin history, or noisy telemetry still deserve a check.'
  return 'This read is not fully reliable yet because missing, repaired, or noisy inputs could still change the conclusion materially.'
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
    title: contributorDisplayTitle(contributorName(item)),
    body: contributorLabel(item),
    tone: fallbackTone,
    score: typeof item.signed_contribution === 'number' ? Math.abs(item.signed_contribution) * 100 : null,
    meta: item.source_block || item.category,
  }))
}

function toUncertaintyItems(items: KeyUncertainty[] | undefined): MemoSectionItem[] {
  return (items ?? []).map((item) => ({
    title: contributorDisplayTitle(item.name),
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
      return { value, label: 'Strong read', tone: 'quality' }
    case 'improving_setup':
      return { value, label: 'Improving read', tone: 'mispricing' }
    case 'fragile_setup':
      return { value, label: 'Fragile read', tone: 'warning' }
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
    why_now:
      firstPositive != null
        ? sentenceCase(plainEnglishReason(contributorName(firstPositive), 'positive'))
        : summary.metricReasons.upside,
    main_constraint:
      firstNegative != null
        ? sentenceCase(plainEnglishReason(contributorName(firstNegative), 'negative'))
        : summary.fragilityRead,
    break_condition: firstBreak
      ? cleanSentence(firstBreak)
      : stressDrawdown != null
        ? `The setup breaks if modeled drawdown pushes materially beyond ${stressDrawdown.toFixed(1)}%.`
        : 'The setup breaks if the current support fades or the evidence gets weaker.',
    market_capacity: marketCapacity,
    evidence_strength: evidenceStrength,
    relative_peer_context: firstUncertainty
      ? `${summary.rankLabel !== 'n/a' ? `Ranks ${summary.rankLabel}. ` : ''}${sentenceCase(plainEnglishReason(firstUncertainty.name, 'uncertainty'))}.`
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

function marketCapacityNarrative(label: string): string {
  switch (label.toLowerCase()) {
    case 'high':
      return 'This market looks deep enough that meaningful capital can move through it without immediately distorting price.'
    case 'medium':
      return 'Medium-sized flows can get through, but larger orders will still push the market around.'
    case 'low':
      return 'Liquidity is workable for small size, but it still becomes awkward quickly as position size grows.'
    default:
      return 'Liquidity is thin enough that this only really works for very small size.'
  }
}

function evidenceNarrative(label: string): string {
  switch (label.toLowerCase()) {
    case 'high':
      return 'The read looks trustworthy because the underlying inputs appear mostly clean and observed.'
    case 'medium':
      return 'The read is directionally useful, but gaps or noisy inputs still matter enough to cap conviction.'
    default:
      return 'Trust is capped because important parts of the history or telemetry are missing, repaired, or noisy.'
  }
}

function trimLeadIn(text: string): string {
  return text
    .replace(/^the setup breaks if\s*/i, '')
    .replace(/^the main constraint is that\s*/i, '')
    .replace(/^the main constraint is\s*/i, '')
    .replace(/^why now:\s*/i, '')
}

function cleanBreakCondition(value: string | null | undefined, fallback: string): string {
  const sentence = compactSentence(value, fallback)
  const trimmed = trimLeadIn(sentence).replace(/\.$/, '')
  return trimmed ? `${sentenceCase(trimmed)}.` : fallback
}

function buildHeaderSubtitle(
  researchSummary: ResearchSummaryViewModel,
  summary: UniverseRowViewModel,
  topDrag: ExplanationContributor | undefined,
): string {
  if (summary.awaitingRun) return 'Fresh scored outputs are missing, so this page is still waiting for a clean read.'

  const setup = compactSentence(researchSummary.setupRead, summary.decisionLine).replace(/\.$/, '')
  const drag = topDrag ? plainEnglishReason(contributorName(topDrag), 'negative') : ''
  if (drag) return `${sentenceCase(setup)} The score is not higher because ${drag}.`
  return `${sentenceCase(setup)}.`
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

function reliabilityNarrative(key: string, value: number): string {
  if (key === 'history_data_reliability') {
    return value >= 0.7
      ? 'Enough history is visible to judge whether this trend is persistent instead of just recent noise.'
      : 'History is missing or thin enough that trend-based conclusions are less trustworthy.'
  }
  if (key === 'market_data_reliability') {
    return value >= 0.7
      ? 'Market inputs look clean enough that price and liquidity signals can be trusted.'
      : 'Market inputs are noisy enough that price and liquidity conclusions need caution.'
  }
  if (key === 'validator_data_reliability') {
    return value >= 0.7
      ? 'Validator-side coverage is solid enough to support the participation read.'
      : 'Validator-side coverage is thin enough that participation quality is harder to confirm.'
  }
  return value >= 0.7
    ? 'Outside sources broadly point in the same direction as the internal read.'
    : 'There is still not much outside confirmation, so the read leans heavily on internal signals.'
}

function blockScoreNarrative(key: string, value: number): string {
  if (key === 'intrinsic_quality') {
    return value >= 65
      ? 'The operating base is strong enough to support the score even if the upside case cools.'
      : 'The operating base is not strong enough to carry the score without help from valuation or momentum.'
  }
  if (key === 'economic_sustainability') {
    return value >= 65
      ? 'The economics look durable enough that the current activity base matters.'
      : 'The economics still need to prove they can hold up without unusually favorable conditions.'
  }
  if (key === 'reflexivity') {
    return value >= 65
      ? 'Market behavior is reinforcing the setup instead of working against it.'
      : 'Market behavior is not giving the thesis much extra help right now.'
  }
  if (key === 'stress_robustness') {
    return value >= 65
      ? 'The setup still holds together reasonably well in modeled stress cases.'
      : 'Modeled stress losses are large enough to cap the score.'
  }
  return value >= 65
    ? 'There still appears to be a meaningful valuation gap for the market to close.'
    : 'The valuation gap looks too small to justify a much higher score by itself.'
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
      return 'Data cleanliness'
    case 'market_confidence':
      return 'Market confirmation'
    case 'thesis_confidence':
      return 'Thesis stability'
    default:
      return sentenceCase(name.replace(/_/g, ' '))
  }
}

function buildExecutiveSummary(researchSummary: ResearchSummaryViewModel): MemoSummaryItem[] {
  return [
    {
      label: 'Setup Read',
      body: compactSentence(researchSummary.setupRead, 'The current case is still too incomplete to summarize cleanly.'),
      tone: researchSummary.setupStatus.tone,
    },
    {
      label: 'Why Now',
      body: compactSentence(researchSummary.whyNow, 'There is no concrete near-term reason to get more interested yet.'),
      tone: 'mispricing',
    },
    {
      label: 'Main Constraint',
      body: compactSentence(researchSummary.mainConstraint, 'No single limiting factor stands out yet.'),
      tone: 'warning',
    },
    {
      label: 'Break Condition',
      body: cleanBreakCondition(researchSummary.breakCondition, 'The current support stops holding up.'),
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
      label: 'Market Size',
      value: researchSummary.marketCapacity.label,
      tone: researchSummary.marketCapacity.tone,
    },
    {
      label: 'Read Trust',
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
      label: 'How much size the market can take',
      value: formatCompactNumber(subnet.tao_in_pool, 0),
      body: compactSentence(
        insightBodyFromContributor(
          marketDrag,
          'Liquidity is enough for smaller positioning, but not deep enough for large size without moving the market.',
          'negative',
        ),
        'Liquidity is enough for smaller positioning, but not deep enough for large size without moving the market.',
      ),
      tone: researchSummary.marketCapacity.tone,
    },
    {
      label: 'Whether too few actors dominate the setup',
      value: concentrationSignal ? 'Watch' : 'Contained',
      body: compactSentence(
        insightBodyFromContributor(
          concentrationSignal,
          'Concentration is visible, but it does not look like the main structural weakness right now.',
          concentrationSignal ? 'negative' : 'uncertainty',
        ),
        'Concentration is visible, but it does not look like the main structural weakness right now.',
      ),
      tone: concentrationSignal ? 'warning' : 'neutral',
    },
    {
      label: 'What happens if bigger money shows up',
      value: researchSummary.marketCapacity.label,
      body: compactSentence(
        marketCapacityNarrative(researchSummary.marketCapacity.label),
        'Liquidity is too thin for larger flows.',
      ),
      tone: researchSummary.marketCapacity.tone,
    },
    {
      label: 'How well it holds up under stress',
      value: analysis?.fragility_class ? sentenceCase(analysis.fragility_class.toLowerCase()) : 'Unknown',
      body: compactSentence(
        insightBodyFromContributor(
          fragilityContributor,
          'Modeled downside is still a meaningful part of the trade plan.',
          'negative',
        ),
        'Modeled downside is still a meaningful part of the trade plan.',
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
  conditioning: ConditioningInfo | undefined,
): MemoInsightItem[] {
  const historyDepth = reliabilityEntries.find((item) => item.title === 'History coverage')
  const dataReliability = reliabilityEntries.find((item) => item.title === 'Market inputs')
  const validatorCoverage = reliabilityEntries.find((item) => item.title === 'Validator coverage')
  const uncertainty = uncertainties[0]
  const reconstructed = visibilityCount(conditioning, 'reconstructed')
  const discarded = visibilityCount(conditioning, 'discarded')
  const visibilityNotes = [
    reconstructed > 0 ? `${reconstructed} input${reconstructed === 1 ? '' : 's'} were reconstructed` : '',
    discarded > 0 ? `${discarded} input${discarded === 1 ? '' : 's'} were dropped` : '',
  ].filter(Boolean)
  const trustBody = [
    compactSentence(
      evidenceNarrative(researchSummary.evidenceStrength.label),
      'Trust is capped by limited evidence.',
    ).replace(/\.$/, ''),
    visibilityNotes.length ? `${sentenceCase(joinClauses(visibilityNotes))}, which makes the read less reliable than a fully observed subnet.` : '',
  ]
    .filter(Boolean)
    .join(' ') + '.'

  return [
    {
      label: 'How trustworthy this read is',
      value: researchSummary.evidenceStrength.label,
      body: trustBody,
      tone: researchSummary.evidenceStrength.tone,
    },
    {
      label: 'Whether enough history is visible',
      value: historyDepth?.score != null ? formatAbsoluteScore(historyDepth.score) ?? historyDepth.body : confidenceLabel(confidence?.thesis_confidence),
      body: compactSentence(historyDepth?.meta || 'Missing or repaired history limits conviction.', 'History is too thin for a strong read.'),
      tone: historyDepth?.tone ?? 'warning',
    },
    {
      label: 'How clean the current inputs really are',
      value:
        dataReliability?.score != null
          ? formatAbsoluteScore(dataReliability.score) ?? dataReliability.body
          : reliabilityLabel(confidence?.data_confidence != null ? confidence.data_confidence / 100 : null),
      body: compactSentence(
        dataReliability?.meta ||
          validatorCoverage?.meta ||
          'The read is directionally useful, but parts of the telemetry are noisy enough to matter.',
        'The read is directionally useful, but parts of the telemetry are noisy enough to matter.',
      ),
      tone: dataReliability?.tone ?? 'warning',
    },
    {
      label: 'What still needs to prove itself',
      value: uncertainty ? sentenceCase(uncertainty.title) : 'None flagged',
      body: compactSentence(uncertainty?.body, 'No single open question stands above the rest.'),
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
      title: contributorDisplayTitle(contributorName(item), mode === 'positive' ? 'positive' : 'negative'),
      value: formatAbsoluteScore(typeof item.signed_contribution === 'number' ? Math.abs(item.signed_contribution) * 100 : null),
      body: compactSentence(insightBodyFromContributor(item, fallback, mode), fallback),
      tone,
    }))
}

function buildAnchorInsights(
  supports: ScoreExplanationItem[],
  drags: ScoreExplanationItem[],
): MemoAnchorItem[] {
  return [
    {
      label: 'Strongest support',
      value: supports[0]?.title ? `${supports[0].title}. ${supports[0].body}` : 'No clear supporting factor stands out yet.',
      tone: supports[0]?.tone ?? 'quality',
    },
    {
      label: 'Main thing capping the score',
      value: drags[0]?.title ? `${drags[0].title}. ${drags[0].body}` : 'No single limiting factor stands out yet.',
      tone: drags[0]?.tone ?? 'warning',
    },
  ]
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
    body: reliabilityLabel(value),
    tone: reliabilityTone(value),
    score: value * 100,
    meta:
      reliabilityNarrative(key, value),
  }))

  const visibilityItems: MemoSectionItem[] = [
    {
      title: 'Rebuilt inputs',
      body: String(visibilityCount(conditioning, 'reconstructed')),
      tone: visibilityCount(conditioning, 'reconstructed') > 0 ? 'warning' : 'neutral',
      meta: conditioning?.visibility?.reconstructed?.slice(0, 4).join(', '),
    },
    {
      title: 'Dropped inputs',
      body: String(visibilityCount(conditioning, 'discarded')),
      tone: visibilityCount(conditioning, 'discarded') > 0 ? 'warning' : 'neutral',
      meta: conditioning?.visibility?.discarded?.slice(0, 4).join(', '),
    },
    {
      title: 'Clean inputs',
      body: String(visibilityCount(conditioning, 'original')),
      tone: 'neutral',
    },
    {
      title: 'Clipped inputs',
      body: String(visibilityCount(conditioning, 'bounded')),
      tone: visibilityCount(conditioning, 'bounded') > 0 ? 'warning' : 'neutral',
      meta: conditioning?.visibility?.bounded?.slice(0, 4).join(', '),
    },
  ]

  const executiveSummary = buildExecutiveSummary(researchSummary)
  const contextRow = buildContextRow(researchSummary, summary, updatedLabel, stale)
  const marketStructure = buildMarketStructureItems(subnet, researchSummary, analysis)
  const evidenceItems = buildEvidenceItems(
    researchSummary,
    reliabilityEntries,
    toUncertaintyItems(analysis?.key_uncertainties),
    confidence,
    conditioning,
  )
  const topSupports = buildScoreExplanationItems(
    analysis?.top_positive_drivers,
    'quality',
    'No clear support stands out yet.',
    'positive',
  )
  const topDrags = buildScoreExplanationItems(
    analysis?.top_negative_drags ?? analysis?.top_negative_drivers,
    'fragility',
    'No single limitation dominates yet.',
    'negative',
  )
  const anchorInsights = buildAnchorInsights(topSupports, topDrags)
  const setupTag = investabilityBadge(subnet.investability_status)
  const secondaryTag: InvestabilityBadge | null =
    researchSummary.evidenceStrength.value === 'high'
      ? { label: 'High trust', tone: researchSummary.evidenceStrength.tone }
      : researchSummary.evidenceStrength.value === 'medium'
        ? { label: 'Medium trust', tone: researchSummary.evidenceStrength.tone }
        : { label: 'Limited trust', tone: researchSummary.evidenceStrength.tone }

  return {
    name: toDisplayName(subnet.name, subnet.netuid),
    netuidLabel: `SN${subnet.netuid}`,
    href: `/subnets/${subnet.netuid}`,
    scoreLabel: subnet.score.toFixed(1),
    modelLabel: summary.modelLabel,
    modelLabelTone: summary.modelLabelTone,
    headerSubtitle: buildHeaderSubtitle(researchSummary, summary, (analysis?.top_negative_drags ?? analysis?.top_negative_drivers ?? [])[0]),
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
    anchorInsights,
    executiveSummary,
    contextRow,
    marketStructure,
    evidenceItems,
    topSupports,
    topDrags,
    blockScores: Object.entries(analysis?.block_scores ?? {}).map(([key, value]) => ({
      title: BLOCK_LABELS[key] ?? key.replace(/_/g, ' '),
      body: blockScoreNarrative(key, value),
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
        label: 'Overall conviction',
        value: outputs ? outputs.signal_confidence.toFixed(1) : 'n/a',
        tone: confidenceTone(outputs?.signal_confidence),
      },
      {
        label: confidenceMetricLabel('data_confidence'),
        value: confidence?.data_confidence != null ? confidence.data_confidence.toFixed(1) : 'n/a',
        tone: confidenceTone(confidence?.data_confidence),
      },
      {
        label: confidenceMetricLabel('market_confidence'),
        value: confidence?.market_confidence != null ? confidence.market_confidence.toFixed(1) : 'n/a',
        tone: confidenceTone(confidence?.market_confidence),
      },
      {
        label: confidenceMetricLabel('thesis_confidence'),
        value: confidence?.thesis_confidence != null ? confidence.thesis_confidence.toFixed(1) : 'n/a',
        tone: confidenceTone(confidence?.thesis_confidence),
      },
    ],
    confidenceItems: reliabilityEntries,
    uncertainties: toUncertaintyItems(analysis?.key_uncertainties),
    visibilityItems,
    stressItems: [
      { title: 'Stress profile', body: analysis?.fragility_class ?? 'unknown', tone: 'fragility' },
      {
        title: 'Modeled drawdown',
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
      meta: `Score after shock: ${scenario.score_after.toFixed(1)}`,
      score: scenario.drawdown,
    })),
    rawContext: [
      { title: 'Version', body: subnet.score_version || 'v2' },
      { title: '7d score change', body: subnet.score_delta_7d == null ? 'n/a' : `${subnet.score_delta_7d.toFixed(1)} pts` },
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
