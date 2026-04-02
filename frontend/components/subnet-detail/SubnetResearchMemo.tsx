'use client'

import Link from 'next/link'
import { useEffect, useRef, useState } from 'react'

import { DetailMemoViewModel, MemoSectionItem } from '@/lib/view-models/research'
import { Breadcrumb, MemoList, MetricGrid, ResearchPanel, SignalPill, StatusBadge, cn } from '@/components/shared/research-ui'

const SECTIONS = [
  { id: 'summary', label: 'Summary' },
  { id: 'interesting', label: 'Why Interesting' },
  { id: 'breaks', label: 'What Breaks It' },
  { id: 'confidence', label: 'Confidence' },
  { id: 'stress', label: 'Stress' },
  { id: 'raw', label: 'Raw Context' },
] as const

function MetricList({ items }: { items: MemoSectionItem[] }) {
  return (
    <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
      {items.map((item) => (
        <div key={`${item.title}-${item.body}`} className="rounded-2xl border border-white/10 bg-stone-950 p-4">
          <div className="text-[11px] uppercase tracking-[0.24em] text-stone-500">{item.title}</div>
          <div className="mt-2 text-lg font-semibold text-stone-100">{item.body}</div>
          {item.meta ? <div className="mt-1 text-xs text-stone-500">{item.meta}</div> : null}
        </div>
      ))}
    </div>
  )
}

function useSectionTracker(sectionIds: readonly string[]) {
  const [activeId, setActiveId] = useState(sectionIds[0])

  useEffect(() => {
    const observer = new IntersectionObserver(
      (entries) => {
        const visible = entries.filter((e) => e.isIntersecting).sort((a, b) => a.boundingClientRect.top - b.boundingClientRect.top)
        if (visible.length > 0) {
          setActiveId(visible[0].target.id)
        }
      },
      { rootMargin: '-80px 0px -60% 0px', threshold: 0 },
    )

    sectionIds.forEach((id) => {
      const el = document.getElementById(id)
      if (el) observer.observe(el)
    })

    return () => observer.disconnect()
  }, [sectionIds])

  return activeId
}

export default function SubnetResearchMemo({ memo }: { memo: DetailMemoViewModel }) {
  const sectionIds = SECTIONS.map((s) => s.id)
  const activeSection = useSectionTracker(sectionIds)
  const navRef = useRef<HTMLDivElement>(null)

  const scrollToSection = (id: string) => {
    const el = document.getElementById(id)
    if (el) el.scrollIntoView({ behavior: 'smooth', block: 'start' })
  }

  // Auto-scroll nav to keep active item visible on mobile
  useEffect(() => {
    if (!navRef.current) return
    const activeBtn = navRef.current.querySelector(`[data-section="${activeSection}"]`) as HTMLElement | null
    if (activeBtn) {
      activeBtn.scrollIntoView({ behavior: 'smooth', block: 'nearest', inline: 'center' })
    }
  }, [activeSection])

  return (
    <div className="space-y-4 page-enter">
      <Breadcrumb
        items={[
          { label: 'Universe', href: '/' },
          { label: `${memo.netuidLabel} ${memo.name}` },
        ]}
      />

      {/* Sticky section nav */}
      <div
        ref={navRef}
        className="sticky top-16 z-20 -mx-4 flex items-center gap-1 overflow-x-auto bg-stone-950/90 px-4 py-2 backdrop-blur-xl sm:-mx-6 sm:px-6 lg:-mx-8 lg:px-8 scrollbar-none"
        style={{ scrollbarWidth: 'none' }}
      >
        {SECTIONS.map((section) => (
          <button
            key={section.id}
            data-section={section.id}
            onClick={() => scrollToSection(section.id)}
            className={cn(
              'focus-ring shrink-0 rounded-lg px-3 py-1.5 text-xs font-medium transition-colors',
              activeSection === section.id
                ? 'bg-white/[0.08] text-stone-100'
                : 'text-stone-500 hover:text-stone-300',
            )}
          >
            {section.label}
          </button>
        ))}
      </div>

      <section id="summary" className="rounded-[2rem] border border-white/10 bg-[#10151b] p-5 sm:p-6 scroll-mt-28">
        <div className="grid gap-6 xl:grid-cols-[minmax(0,1.15fr)_340px]">
          <div className="space-y-5">
            <div className="flex flex-wrap items-center gap-2">
              <StatusBadge tone="neutral">{memo.netuidLabel}</StatusBadge>
              {memo.summaryFlags.map((flag) => (
                <StatusBadge key={flag.label} tone={flag.tone}>
                  {flag.label}
                </StatusBadge>
              ))}
            </div>

            <div className="space-y-3">
              <div className="flex flex-wrap items-end gap-4">
                <h1 className="text-3xl font-semibold tracking-tight text-stone-50 sm:text-4xl">{memo.name}</h1>
                <div className="text-sm text-stone-500">Updated {memo.updatedLabel}</div>
              </div>
              <p className="max-w-4xl text-base leading-7 text-stone-300">{memo.thesis}</p>
              <div className="max-w-4xl text-sm leading-6 text-stone-400">{memo.decisionLine}</div>
            </div>

            <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
              {memo.signals.map((signal) => (
                <SignalPill key={signal.key} signal={signal} />
              ))}
            </div>
          </div>

          <div className="rounded-3xl border border-white/10 bg-stone-950 p-4">
            <div className="text-[11px] uppercase tracking-[0.24em] text-stone-500">Investment summary</div>
            <div className="mt-4">
              <MetricGrid items={memo.summaryMetrics} />
            </div>
          </div>
        </div>
      </section>

      <ResearchPanel
        id="interesting"
        title="Why This Is Interesting"
        subtitle="Top positive drivers, primary signal contributors, and block scores that support the case."
        className="bg-[#10151b] scroll-mt-28"
      >
        <div className="space-y-5">
          <MemoList items={memo.interesting} empty="No top positive drivers were emitted for this subnet." />
          <div className="grid gap-5 xl:grid-cols-2">
            {memo.signalContributorSections.map((section) => (
              <div key={section.title}>
                <div className="mb-3 text-[11px] uppercase tracking-[0.24em] text-stone-500">{section.title}</div>
                <MemoList items={section.items} empty={`No ${section.title.toLowerCase()} surfaced.`} />
              </div>
            ))}
          </div>
          <div>
            <div className="mb-3 text-[11px] uppercase tracking-[0.24em] text-stone-500">Block scores</div>
            <MetricList items={memo.blockScores} />
          </div>
        </div>
      </ResearchPanel>

      <ResearchPanel
        id="breaks"
        title="What Breaks The Thesis"
        subtitle="Negative drags, thesis breakers, and fragility contributors that can invalidate the setup."
        className="bg-[#10151b] scroll-mt-28"
      >
        <div className="grid gap-5 xl:grid-cols-[minmax(0,1.1fr)_minmax(0,0.9fr)]">
          <div>
            <div className="mb-3 text-[11px] uppercase tracking-[0.24em] text-stone-500">Failure modes</div>
            <MemoList items={memo.breaks} empty="No explicit failure modes were emitted for this subnet." />
          </div>
          <div>
            <div className="mb-3 text-[11px] uppercase tracking-[0.24em] text-stone-500">Fragility contributors</div>
            <MemoList items={memo.fragilityContributors} empty="No fragility contributors surfaced." />
          </div>
        </div>
      </ResearchPanel>

      <ResearchPanel
        id="confidence"
        title="Confidence And Data Trust"
        subtitle="Confidence profile, conditioning reliability, reconstructed or discarded inputs, and the uncertainties that can still move the memo."
        className="bg-[#10151b] scroll-mt-28"
      >
        <div className="space-y-5">
          <MetricGrid items={memo.confidenceHeadline} />
          <div className="grid gap-5 xl:grid-cols-[minmax(0,0.95fr)_minmax(0,1.05fr)]">
            <div>
              <div className="mb-3 text-[11px] uppercase tracking-[0.24em] text-stone-500">Conditioning reliability</div>
              <MemoList items={memo.confidenceItems} empty="No conditioning reliability data was emitted." />
            </div>
            <div>
              <div className="mb-3 text-[11px] uppercase tracking-[0.24em] text-stone-500">Key uncertainties</div>
              <MemoList items={memo.uncertainties} empty="No key uncertainties were emitted." />
            </div>
          </div>
          <div>
            <div className="mb-3 text-[11px] uppercase tracking-[0.24em] text-stone-500">Conditioning visibility</div>
            <MetricList items={memo.visibilityItems} />
          </div>
        </div>
      </ResearchPanel>

      <ResearchPanel
        id="stress"
        title="Stress And Execution"
        subtitle="Fragility class, drawdown scenarios, and the raw execution context once the thesis meets real market structure."
        className="bg-[#10151b] scroll-mt-28"
      >
        <div className="space-y-5">
          <MetricList items={memo.stressItems} />
          <div>
            <div className="mb-3 text-[11px] uppercase tracking-[0.24em] text-stone-500">Stress scenarios</div>
            <MemoList items={memo.scenarioItems} empty="No stress scenarios were provided for this subnet." />
          </div>
        </div>
      </ResearchPanel>

      <ResearchPanel
        id="raw"
        title="Raw Context"
        subtitle="Classic market fields stay available, but only after the thesis, break risk, and trust sections."
        className="bg-[#10151b] scroll-mt-28"
      >
        <div className="space-y-5">
          <MetricList items={memo.rawContext} />
          <div className="flex flex-wrap gap-2">
            {memo.links.map((link) => (
              <a
                key={link.href}
                href={link.href}
                target="_blank"
                rel="noreferrer"
                className="focus-ring rounded-2xl border border-white/10 bg-stone-950 px-3 py-2 text-sm text-stone-300 transition-colors hover:bg-white/[0.08]"
              >
                {link.label}
              </a>
            ))}
          </div>
        </div>
      </ResearchPanel>
    </div>
  )
}
