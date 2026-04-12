import type { AgentKey, AgentState, VoteResult } from '../types'
import { AGENT_CONFIG, AGENT_KEYS } from '../agents'

interface Props {
  agents: Record<AgentKey, AgentState>
}

export default function VotingProgress({ agents }: Props) {
  const votesCast = AGENT_KEYS.filter(k => agents[k].vote.vote !== null).length

  return (
    <div className="mt-8 relative overflow-hidden border border-nerv-border bg-nerv-surface">
      {/* Scanline overlay */}
      <div
        className="pointer-events-none absolute inset-0 z-10 opacity-[0.03]"
        style={{
          backgroundImage: 'repeating-linear-gradient(0deg, #fff 0px, #fff 1px, transparent 1px, transparent 4px)',
        }}
      />

      <div className="relative z-20 px-8 py-7">
        {/* ── Header ──────────────────────────────────────────────── */}
        <div className="text-center mb-7">
          <div className="text-[0.52em] tracking-[5px] text-red-600/30 mb-2">
            MAGI CONSENSUS PROTOCOL
          </div>

          {/* Blinking title */}
          <div
            className="text-[1.05em] tracking-[7px] text-[#c8c8c8]"
            style={{ animation: 'slow-blink 1.1s step-end infinite' }}
          >
            MAGI VOTING IN PROGRESS
          </div>

          <div className="text-[0.55em] tracking-[3px] text-[#2a2a2a] mt-2.5">
            {votesCast}/3 VOTES CAST — 2-OF-3 THRESHOLD ACTIVE
          </div>
        </div>

        {/* ── Agent rows ───────────────────────────────────────────── */}
        <div className="space-y-4 mb-7">
          {AGENT_KEYS.map(key => (
            <AgentRow key={key} agentKey={key} voteState={agents[key].vote} />
          ))}
        </div>

        {/* ── Footer ──────────────────────────────────────────────── */}
        <div
          className="text-center text-[0.58em] tracking-[4px] text-[#1e1e1e]"
          style={{ animation: 'march 2.4s ease-in-out infinite' }}
        >
          ▓  DELIBERATING  ▓
        </div>
      </div>
    </div>
  )
}

// ── Single agent row ───────────────────────────────────────────────────────────

interface RowProps {
  agentKey: AgentKey
  voteState: AgentState['vote']
}

function AgentRow({ agentKey, voteState }: RowProps) {
  const agent = AGENT_CONFIG[agentKey]
  const { color } = agent

  const phase: 'awaiting' | 'casting' | 'voted' =
    voteState.vote !== null ? 'voted'
    : voteState.streaming || voteState.done ? 'casting'
    : 'awaiting'

  const resultColor =
    voteState.vote === 'APPROVE' ? '#00FF41'
    : voteState.vote === 'REJECT' ? '#FF4444'
    : color

  return (
    <div className="flex items-center gap-4">
      {/* Agent label */}
      <div className="w-36 shrink-0">
        <div className="text-[0.65em] tracking-[2px]" style={{ color }}>
          {agent.id}
        </div>
        <div className="text-[0.52em] tracking-[3px]" style={{ color: `${color}40` }}>
          [{agent.role}]
        </div>
      </div>

      {/* Progress bar */}
      <div className="flex-1 h-[3px] bg-[#111] relative overflow-hidden">
        {phase === 'awaiting' && (
          /* Dim dotted line */
          <div
            className="absolute inset-0"
            style={{
              backgroundImage: `repeating-linear-gradient(90deg, #1e1e1e 0px, #1e1e1e 4px, transparent 4px, transparent 8px)`,
            }}
          />
        )}

        {phase === 'casting' && (
          <>
            {/* Dim base */}
            <div className="absolute inset-0" style={{ background: `${color}18` }} />
            {/* Sweeping highlight */}
            <div
              className="absolute inset-y-0 w-1/3"
              style={{
                background: `linear-gradient(90deg, transparent, ${color}, transparent)`,
                animation: 'bar-sweep 1.1s ease-in-out infinite',
              }}
            />
          </>
        )}

        {phase === 'voted' && (
          /* Solid filled bar in vote color */
          <div className="absolute inset-0" style={{ background: resultColor }} />
        )}
      </div>

      {/* Status label */}
      <div className="w-28 shrink-0 text-right">
        <StatusLabel phase={phase} result={voteState.vote} color={color} resultColor={resultColor} />
      </div>
    </div>
  )
}

// ── Status label ───────────────────────────────────────────────────────────────

function StatusLabel({
  phase,
  result,
  color,
  resultColor,
}: {
  phase: 'awaiting' | 'casting' | 'voted'
  result: VoteResult | null
  color: string
  resultColor: string
}) {
  if (phase === 'awaiting') {
    return (
      <span className="text-[0.58em] tracking-[2px] text-[#252525]">
        AWAITING
      </span>
    )
  }

  if (phase === 'casting') {
    return (
      <span
        className="text-[0.58em] tracking-[2px]"
        style={{ color: `${color}88`, animation: 'slow-blink 0.9s step-end infinite' }}
      >
        ▓ CASTING…
      </span>
    )
  }

  return (
    <span
      className="text-[0.65em] tracking-[3px] font-bold"
      style={{ color: resultColor }}
    >
      {result}
    </span>
  )
}
