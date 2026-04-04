function activeStep(score: number | null | undefined): number {
  if (score == null || !Number.isFinite(score)) return 3
  return Math.max(0, Math.min(6, Math.round((score / 100) * 6)))
}

function stepClass(index: number, activeIndex: number): string {
  if (index > activeIndex) {
    return 'bg-[color:rgba(148,163,184,0.14)]'
  }

  if (activeIndex <= 1) {
    return 'bg-[linear-gradient(180deg,rgba(244,114,182,0.96),rgba(251,146,60,0.92))]'
  }
  if (activeIndex === 2) {
    return 'bg-[color:rgba(250,204,21,0.88)]'
  }
  if (activeIndex === 3) {
    return 'bg-[color:rgba(148,163,184,0.72)]'
  }
  if (activeIndex <= 5) {
    return 'bg-[linear-gradient(180deg,rgba(74,222,128,0.9),rgba(45,212,191,0.82))]'
  }
  return 'bg-[linear-gradient(180deg,rgba(45,212,191,0.96),rgba(125,184,255,0.88))]'
}

export default function MicroSentimentScale({ score }: { score: number | null }) {
  const highlightedStep = activeStep(score)

  return (
    <div className="flex min-w-[112px] items-center justify-end gap-1.5" aria-hidden="true">
      {Array.from({ length: 7 }).map((_, index) => (
        <span
          key={index}
          className={`h-2 w-3.5 rounded-full transition-colors duration-150 sm:w-4 ${stepClass(index, highlightedStep)}`}
        />
      ))}
    </div>
  )
}
