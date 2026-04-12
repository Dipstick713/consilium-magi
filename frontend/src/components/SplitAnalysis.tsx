import type { SplitAnalysis as SplitAnalysisType } from '../types'
import { AGENT_CONFIG } from '../agents'

interface Props {
  analysis: SplitAnalysisType
}

export default function SplitAnalysis({ analysis }: Props) {
  const agent = AGENT_CONFIG[analysis.dissenterKey]
  const { color } = agent

  return (
    <div className="mt-6">
      {/* Divider with label */}
      <div className="flex items-center gap-3 mb-4">
        <div className="h-px flex-1" style={{ background: `linear-gradient(90deg, transparent, ${color}30)` }} />
        <div className="text-[0.58em] tracking-[4px] shrink-0" style={{ color: `${color}60` }}>
          ⬡ MINORITY REPORT
        </div>
        <div className="h-px flex-1" style={{ background: `linear-gradient(90deg, ${color}30, transparent)` }} />
      </div>

      {/* Dissenter identity */}
      <div className="mb-3">
        <span
          className="text-[0.6em] tracking-[3px] border px-2 py-0.5"
          style={{ color, borderColor: `${color}30` }}
        >
          {agent.id}  [{agent.role}]  —  DISSENTING VOICE
        </span>
      </div>

      {/* Analysis text */}
      <blockquote
        className="text-[0.85em] leading-[1.9] whitespace-pre-wrap m-0 pl-3 italic"
        style={{
          color: `${color}cc`,
          borderLeft: `2px solid ${color}30`,
        }}
      >
        {analysis.text}
        {analysis.streaming && (
          <span className="animate-pulse opacity-40 not-italic">▌</span>
        )}
      </blockquote>
    </div>
  )
}
