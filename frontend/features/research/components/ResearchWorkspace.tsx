import Link from 'next/link'

import PageHeader from '@/components/ui/PageHeader'
import SignalBar from '@/components/ui/SignalBar'
import StatusChip from '@/components/ui/StatusChip'
import { DetailMemoViewModel, MemoSectionItem } from '@/lib/view-models/research'

function pickMetric(
  memo: DetailMemoViewModel,
  label: string,
): { label: string; value: string; tone?: string; meta?: string } | null {
  return memo.summaryMetrics.find((item) => item.label === label) ?? null
}

function toHeaderTone(tone: string | undefined): 'default' | 'warning' | 'success' {
  if (tone === 'warning' || tone === 'fragility') return 'warning'
  if (tone === 'quality' || tone === 'confidence') return 'success'
  return 'default'
}

function sentenceParts(items: MemoSectionItem[], limit = 2): string[] {
  return items
    .slice(0, limit)
    .map((item) => item.body.trim())
    .filter(Boolean)
}

function normalizeKey(value: string | undefined): string {
  return (value ?? '')
    .trim()
    .toLowerCase()
    .replace(/\s+/g, '_')
}

function signalNumber(memo: DetailMemoViewModel, key: string): string {
  const signal = memo.signals.find((item) => item.key === key)
  return signal?.value == null ? 'n/a' : signal.value.toFixed(1)
}

function buildInvestmentRead(memo: DetailMemoViewModel): string {
  const positive = sentenceParts(memo.interesting, 1)[0]
  const risk = sentenceParts(memo.breaks, 1)[0]
  const uncertainty = sentenceParts(memo.uncertainties, 1)[0]

  const parts = [memo.decisionLine]
  if (positive) parts.push(`What supports that read today: ${positive}`)
  if (risk) parts.push(`What still needs to be respected: ${risk}`)
  if (uncertainty) parts.push(`What can still move the memo: ${uncertainty}`)
  return parts.join(' ')
}

function cleanText(value: string): string {
  return value.replace(/\s+/g, ' ').trim()
}

function sentenceCase(value: string): string {
  const text = cleanText(value)
  if (!text) return text
  return text.charAt(0).toUpperCase() + text.slice(1)
}

function contributorPlainEnglish(key: string): string {
  switch (normalizeKey(key)) {
    case 'fundamental_health':
      return 'the subnet is doing a good job turning activity into something durable and useful'
    case 'market_legitimacy':
      return 'the market already treats it like a serious network instead of a speculative side story'
    case 'structural_validity':
      return 'the setup still looks investable and not artificially propped up'
    case 'confidence_factor':
      return 'most of the important signals point in the same direction'
    case 'thesis_confidence':
      return 'the overall story makes sense and does not rely on one fragile assumption'
    case 'market_confidence':
      return 'price and market behavior are not contradicting the thesis'
    case 'data_confidence':
      return 'there is enough clean data to form a usable view'
    case 'base_opportunity':
    case 'opportunity_underreaction':
      return 'the market still seems to be underestimating part of the story'
    case 'quality_acceleration':
      return 'quality is still improving, not just staying flat'
    case 'fragility':
      return 'the subnet is holding up reasonably well under pressure'
    case 'reserve_change':
      return 'more capital in the pool is not yet leading to a meaningfully better market response'
    case 'liquidity_improvement_rate':
      return 'trading conditions are not improving fast enough yet'
    case 'reserve_growth_without_price':
      return 'better fundamentals are not yet showing up clearly in the price'
    case 'price_response_lag_to_quality_shift':
      return 'the market may already be catching up to the improvement'
    case 'expected_price_response_gap':
      return 'the rerating gap is smaller than in the best upside names'
    case 'emission_to_sticky_usage_conversion':
      return 'token emissions are not yet turning into lasting, sticky usage'
    case 'post_incentive_retention':
      return 'it is still unclear whether users stay once incentives cool off'
    case 'emission_efficiency':
      return 'new emissions are not producing enough real usage'
    case 'cohort_quality_edge':
      return 'it does not have an overwhelming lead over peers'
    case 'discarded_inputs':
      return 'some messy inputs had to be thrown out, so the picture is not fully complete'
    case 'external_data_reliability':
      return 'there is not much outside evidence yet to confirm the story'
    case 'validator_data_reliability':
      return 'validator-side evidence is thinner than ideal'
    case 'history_data_reliability':
      return 'the historical record is still shallower than you would want'
    default:
      return ''
  }
}

function itemExplanation(item: MemoSectionItem | undefined): string {
  if (!item) return ''
  const mapped = contributorPlainEnglish(item.title)
  if (mapped) return mapped
  return cleanText(item.body)
}

function explainScoreLevel(metric: 'strength' | 'upside' | 'risk' | 'evidence', value: number): string {
  if (metric === 'strength') {
    if (value >= 70) return 'That is a strong reading and puts it above most peers on basic business quality.'
    if (value >= 55) return 'That is respectable, but not strong enough to carry the case by itself.'
    return 'That is a weak reading, which means the business quality still needs to prove itself.'
  }
  if (metric === 'upside') {
    if (value >= 60) return 'That suggests the market may still be missing a meaningful part of the upside.'
    if (value >= 45) return 'That suggests there is some upside left, but not a dramatic disconnect.'
    return 'That suggests the market is not giving a large discount right now.'
  }
  if (metric === 'risk') {
    if (value <= 30) return 'That is a healthy risk reading and suggests the downside is relatively contained for now.'
    if (value <= 50) return 'That is manageable, but there is still enough fragility to matter.'
    return 'That is elevated and means the story can break faster than the headline rank suggests.'
  }
  if (value >= 60) return 'That is a solid evidence reading and means the model has enough clean information to lean on.'
  if (value >= 45) return 'That is usable, but it still deserves some caution.'
  return 'That is a soft evidence reading, so the conclusion should be treated carefully.'
}

function buildStrengthNarrative(memo: DetailMemoViewModel, strengthItems: MemoSectionItem[], breaks: MemoSectionItem[]): string {
  const value = Number(signalNumber(memo, 'fundamental_quality'))
  const supportA = itemExplanation(strengthItems[0])
  const supportB = itemExplanation(strengthItems[1])
  const limiter = itemExplanation(breaks[0])

  return [
    `Strength is ${value.toFixed(1)}. ${explainScoreLevel('strength', value)}`,
    supportA ? `What is working: ${sentenceCase(supportA)}.` : '',
    supportB ? `Also helping: ${sentenceCase(supportB)}.` : '',
    limiter ? `Why it is not higher: ${sentenceCase(limiter)}.` : '',
  ]
    .filter(Boolean)
    .join(' ')
}

function buildUpsideNarrative(memo: DetailMemoViewModel, upsideItems: MemoSectionItem[], breaks: MemoSectionItem[]): string {
  const value = Number(signalNumber(memo, 'mispricing_signal'))
  const supportA = itemExplanation(upsideItems[0])
  const supportB = itemExplanation(upsideItems[1])
  const limiter = itemExplanation(breaks[0])

  return [
    `Upside Gap is ${value.toFixed(1)}. ${explainScoreLevel('upside', value)}`,
    supportA ? `Why there is still upside: ${sentenceCase(supportA)}.` : '',
    supportB ? `Also supportive: ${sentenceCase(supportB)}.` : '',
    limiter ? `Why the gap is not larger: ${sentenceCase(limiter)}.` : '',
  ]
    .filter(Boolean)
    .join(' ')
}

function buildRiskNarrative(
  memo: DetailMemoViewModel,
  riskItems: MemoSectionItem[],
  stressDrawdown: string | undefined,
  fragilityClass: string | undefined,
): string {
  const value = Number(signalNumber(memo, 'fragility_risk'))
  const riskA = itemExplanation(riskItems[0])
  const riskB = itemExplanation(riskItems[1])

  return [
    `Risk is ${value.toFixed(1)}. ${explainScoreLevel('risk', value)}`,
    riskA ? `What keeps risk in check: ${sentenceCase(riskA)}.` : '',
    riskB ? `What still needs respect: ${sentenceCase(riskB)}.` : '',
    stressDrawdown ? `Stress test: the setup still drops about ${stressDrawdown.toLowerCase()}.` : '',
    fragilityClass ? `Current read: ${sentenceCase(fragilityClass.toLowerCase())}.` : '',
  ]
    .filter(Boolean)
    .join(' ')
}

function buildEvidenceNarrative(
  memo: DetailMemoViewModel,
  evidenceItems: MemoSectionItem[],
  uncertainties: MemoSectionItem[],
): string {
  const value = Number(signalNumber(memo, 'signal_confidence'))
  const evidenceA = itemExplanation(evidenceItems[0])
  const evidenceB = itemExplanation(evidenceItems[1])
  const uncertainty = itemExplanation(uncertainties[0])

  return [
    `Evidence Quality is ${value.toFixed(1)}. ${explainScoreLevel('evidence', value)}`,
    evidenceA ? `What the model can trust: ${sentenceCase(evidenceA)}.` : '',
    evidenceB ? `Also visible: ${sentenceCase(evidenceB)}.` : '',
    uncertainty ? `What keeps confidence lower: ${sentenceCase(uncertainty)}.` : '',
  ]
    .filter(Boolean)
    .join(' ')
}

function NarrativeSection({
  title,
  body,
}: {
  title: string
  body: string
}) {
  return (
    <div className="surface-subtle p-4">
      <div className="eyebrow">{title}</div>
      <p className="mt-2 text-sm leading-7 text-[color:var(--text-secondary)]">{body}</p>
    </div>
  )
}

export default function ResearchWorkspace({ memo }: { memo: DetailMemoViewModel }) {
  const rankMetric = pickMetric(memo, 'Rank')
  const updatedMetric = pickMetric(memo, 'Updated')
  const confidenceMetric = memo.confidenceHeadline.find((item) => item.label === 'Signal confidence') ?? null

  const strengthItems =
    memo.signalContributorSections.find((section) => section.title === 'Quality contributors')?.items ??
    memo.interesting
  const upsideItems =
    memo.signalContributorSections.find((section) => section.title === 'Mispricing contributors')?.items ??
    memo.interesting
  const riskItems = memo.fragilityContributors.length ? memo.fragilityContributors : memo.breaks
  const evidenceItems = memo.uncertainties.length ? memo.uncertainties : memo.confidenceItems
  const stressDrawdown = memo.stressItems.find((item) => item.title === 'Stress drawdown')?.body
  const fragilityClass = memo.stressItems.find((item) => item.title === 'Fragility class')?.body

  const strengthNarrative = buildStrengthNarrative(memo, strengthItems, memo.breaks)
  const upsideNarrative = buildUpsideNarrative(memo, upsideItems, memo.breaks)
  const riskNarrative = buildRiskNarrative(memo, riskItems, stressDrawdown, fragilityClass)
  const evidenceNarrative = buildEvidenceNarrative(memo, evidenceItems, memo.uncertainties)

  return (
    <div className="space-y-6 pb-12">
      <Link href="/" className="button-secondary">
        Back to discover
      </Link>

      <PageHeader
        title={memo.name}
        subtitle={memo.thesis}
        variant="research"
        actions={
          <div className="flex flex-wrap gap-2">
            <StatusChip tone="neutral">{memo.netuidLabel}</StatusChip>
            {rankMetric ? <StatusChip tone="neutral">{rankMetric.value}</StatusChip> : null}
          </div>
        }
        stats={[
          ...(updatedMetric ? [{ label: 'Updated', value: updatedMetric.value }] : []),
          ...(confidenceMetric ? [{ label: 'Evidence quality', value: confidenceMetric.value, tone: toHeaderTone(confidenceMetric.tone) }] : []),
        ]}
      />

      <section className="surface-panel p-5 sm:p-6">
        <div className="space-y-5">
          <div className="surface-subtle p-4">
            <div className="eyebrow text-[color:var(--mispricing-strong)]">Investment read</div>
            <p className="mt-2 text-base leading-7 text-[color:var(--text-secondary)]">{buildInvestmentRead(memo)}</p>
          </div>

          <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
            {memo.signals.map((signal) => (
              <SignalBar key={signal.key} signal={signal} />
            ))}
          </div>

          <div className="grid gap-4 xl:grid-cols-2">
            <NarrativeSection
              title="Why Strength Looks Like This"
              body={strengthNarrative}
            />
            <NarrativeSection
              title="Why Upside Gap Looks Like This"
              body={upsideNarrative}
            />
            <NarrativeSection
              title="Why Risk Looks Like This"
              body={riskNarrative}
            />
            <NarrativeSection
              title="Why Evidence Quality Looks Like This"
              body={evidenceNarrative}
            />
          </div>
        </div>
      </section>
    </div>
  )
}
