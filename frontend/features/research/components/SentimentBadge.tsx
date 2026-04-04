import { IndicatorSentiment } from '@/lib/view-models/research'

const SENTIMENT_STYLES: Record<IndicatorSentiment, string> = {
  'Very Bearish':
    'border-[color:rgba(244,114,182,0.22)] bg-[color:rgba(244,114,182,0.1)] text-[color:rgba(251,182,206,0.98)]',
  Bearish:
    'border-[color:rgba(251,146,60,0.22)] bg-[color:rgba(251,146,60,0.1)] text-[color:rgba(253,186,116,0.98)]',
  'Slightly Bearish':
    'border-[color:rgba(250,204,21,0.18)] bg-[color:rgba(250,204,21,0.08)] text-[color:rgba(253,224,71,0.96)]',
  Neutral:
    'border-[color:rgba(148,163,184,0.18)] bg-[color:rgba(148,163,184,0.08)] text-[color:var(--text-secondary)]',
  'Slightly Bullish':
    'border-[color:rgba(74,222,128,0.16)] bg-[color:rgba(74,222,128,0.08)] text-[color:rgba(134,239,172,0.96)]',
  Bullish:
    'border-[color:rgba(74,222,128,0.22)] bg-[color:rgba(74,222,128,0.1)] text-[color:rgba(110,231,183,0.98)]',
  'Very Bullish':
    'border-[color:rgba(45,212,191,0.22)] bg-[color:rgba(45,212,191,0.1)] text-[color:rgba(153,246,228,0.98)]',
}

export default function SentimentBadge({ sentiment }: { sentiment: IndicatorSentiment }) {
  return (
    <span
      className={`inline-flex h-10 items-center justify-center rounded-full border px-4 text-[0.92rem] font-semibold tracking-[0.06em] ${SENTIMENT_STYLES[sentiment]}`}
    >
      {sentiment}
    </span>
  )
}
