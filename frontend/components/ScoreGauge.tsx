'use client'

interface Props {
  score: number
  signalsWithData?: number | null
}

function scoreColor(score: number): string {
  if (score >= 70) return 'text-green-400'
  if (score >= 40) return 'text-yellow-400'
  return 'text-red-400'
}

function scoreLabel(score: number): string {
  if (score >= 70) return 'Strong'
  if (score >= 40) return 'Moderate'
  return 'Weak'
}

function confidenceLabel(n: number | null | undefined): string {
  if (n == null) return '?'
  if (n >= 4) return 'High'
  if (n >= 2) return 'Medium'
  return 'Low'
}

function confidenceColor(n: number | null | undefined): string {
  if (n == null) return 'text-slate-500'
  if (n >= 4) return 'text-green-400'
  if (n >= 2) return 'text-yellow-400'
  return 'text-red-400'
}

export default function ScoreGauge({ score, signalsWithData }: Props) {
  const pct = Math.min(100, Math.max(0, score))
  const circumference = 2 * Math.PI * 54
  const dash = (pct / 100) * circumference

  return (
    <div className="flex flex-col items-center gap-2">
      <div className="relative h-36 w-36">
        <svg className="h-36 w-36 -rotate-90" viewBox="0 0 120 120">
          <circle cx="60" cy="60" r="54" fill="none" stroke="#1e293b" strokeWidth="10" />
          <circle
            cx="60"
            cy="60"
            r="54"
            fill="none"
            stroke={score >= 70 ? '#4ade80' : score >= 40 ? '#facc15' : '#f87171'}
            strokeWidth="10"
            strokeDasharray={`${dash} ${circumference}`}
            strokeLinecap="round"
          />
        </svg>
        <div className="absolute inset-0 flex flex-col items-center justify-center">
          <span className={`text-4xl font-bold tabular-nums ${scoreColor(score)}`}>{Math.round(score)}</span>
          <span className="mt-0.5 text-xs text-slate-500">/ 100</span>
        </div>
      </div>

      <span className={`text-sm font-semibold ${scoreColor(score)}`}>{scoreLabel(score)}</span>

      {signalsWithData !== undefined && (
        <span className={`text-xs ${confidenceColor(signalsWithData)}`}>
          Confidence: {confidenceLabel(signalsWithData)}
          {signalsWithData != null && ` (${signalsWithData}/4 primary signals)`}
        </span>
      )}
    </div>
  )
}
