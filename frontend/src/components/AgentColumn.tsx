import type { AgentKey, AgentState, AgentRound, AgentVote, VoteResult } from '../types'
import { AGENT_CONFIG } from '../agents'
import AgentTrace from './AgentTrace'

interface Props {
  agentKey: AgentKey
  agentState: AgentState
}

export default function AgentColumn({ agentKey, agentState }: Props) {
  const agent = AGENT_CONFIG[agentKey]
  const { color } = agent

  return (
    <div className="flex flex-col min-w-0">
      {/* Colored accent bar */}
      <div
        className="h-[2px] mb-3 shrink-0"
        style={{ background: `linear-gradient(90deg, ${color}, ${color}44, transparent)` }}
      />

      {/* Agent identity */}
      <div
        className="pb-2 mb-4 shrink-0"
        style={{ borderBottom: `1px solid ${color}18` }}
      >
        <div className="text-[0.58em] tracking-[4px] mb-0.5" style={{ color: `${color}55` }}>
          ⬡ {agent.id}
        </div>
        <div className="text-[0.92em] tracking-[4px]" style={{ color }}>
          {agent.role}
        </div>
      </div>

      {/* Rounds */}
      <RoundBlock label="ROUND 1 — OPENING"   round={agentState.r1}   color={color} />
      <RoundBlock label="ROUND 2 — RESPONSE"  round={agentState.r2}   color={color} />
      <VoteBlock  label="FORMAL VOTE"         round={agentState.vote} color={color} />
    </div>
  )
}

// ── Round block ────────────────────────────────────────────────────────────────

function RoundBlock({ label, round, color }: { label: string; round: AgentRound; color: string }) {
  return (
    <div className="mb-5">
      <div className="text-[0.58em] tracking-[3px] mb-1.5 text-nerv-dim">// {label}</div>
      <AgentTrace trace={round.trace} color={color} isLive={round.streaming && round.text === ''} />
      {round.searchQuery && (
        <SearchLine query={round.searchQuery} live={round.searchLive} color={color} />
      )}
      {round.text ? (
        <p className="text-[0.82em] leading-[1.85] whitespace-pre-wrap m-0 break-words" style={{ color }}>
          {round.text}
          {round.streaming && <Cursor />}
        </p>
      ) : (
        round.streaming && round.trace.length === 0 && <Cursor color={color} />
      )}
    </div>
  )
}

// ── Vote block ─────────────────────────────────────────────────────────────────

function VoteBlock({ label, round, color }: { label: string; round: AgentVote; color: string }) {
  const voteColor = voteResultColor(round.vote)

  return (
    <div className="mb-5">
      <div className="text-[0.58em] tracking-[3px] mb-1.5 text-nerv-dim">// {label}</div>
      {round.text ? (
        <p className="text-[0.82em] leading-[1.85] whitespace-pre-wrap m-0 break-words" style={{ color }}>
          {round.text}
          {round.streaming && <Cursor />}
        </p>
      ) : (
        round.streaming && <Cursor color={color} />
      )}
      {round.vote && voteColor && (
        <div
          className="mt-2 text-[0.68em] tracking-[4px] font-bold border px-2 py-0.5 inline-block"
          style={{ color: voteColor, borderColor: `${voteColor}40` }}
        >
          {round.vote}
        </div>
      )}
    </div>
  )
}

// ── Search line ────────────────────────────────────────────────────────────────

function SearchLine({ query, live, color }: { query: string; live: boolean; color: string }) {
  return (
    <div
      className="flex items-baseline gap-1.5 mb-2 text-[0.6em] tracking-wider leading-snug"
      style={{ color: `${color}40` }}
    >
      <span>{live ? '⟳' : '⊘'}</span>
      <span className="italic truncate" title={query}>
        {query}
      </span>
    </div>
  )
}

// ── Helpers ────────────────────────────────────────────────────────────────────

function Cursor({ color }: { color?: string }) {
  return (
    <span
      className="animate-pulse opacity-40"
      style={color ? { color } : undefined}
    >
      ▌
    </span>
  )
}

function voteResultColor(vote: VoteResult | null): string | null {
  if (vote === 'APPROVE') return '#00FF41'
  if (vote === 'REJECT')  return '#FF4444'
  return null
}
