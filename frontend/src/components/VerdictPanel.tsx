import type { AgentKey, AgentState, VoteResult } from '../types'
import { AGENT_KEYS, AGENT_CONFIG } from '../agents'

interface Props {
  agents: Record<AgentKey, AgentState>
  approveCount: number
  verdict: VoteResult
  override: VoteResult | null
  onOverride: (vote: VoteResult | null) => void
}

export default function VerdictPanel({ agents, approveCount, verdict, override, onOverride }: Props) {
  const active      = override ?? verdict
  const activeColor = active === 'APPROVE' ? '#00FF41' : '#FF4444'
  const activeLabel = active === 'APPROVE' ? 'APPROVED' : 'REJECTED'

  return (
    <div className="mt-8 border-t border-nerv-border pt-7">
      {/* Protocol label */}
      <div className="text-center text-[0.58em] tracking-[4px] text-[#1e1e1e] mb-5">
        MAGI CONSENSUS PROTOCOL — 2-OF-3 MAJORITY RULE
      </div>

      {/* Individual vote badges */}
      <div className="grid grid-cols-3 gap-5 mb-6">
        {AGENT_KEYS.map(key => {
          const agent     = AGENT_CONFIG[key]
          const voteState = agents[key].vote
          const vc        = voteState.vote === 'APPROVE' ? '#00FF41'
                          : voteState.vote === 'REJECT'  ? '#FF4444'
                          : '#333'
          return (
            <div
              key={key}
              className="text-center p-4 bg-nerv-surface"
              style={{ border: `1px solid ${agent.color}14` }}
            >
              <div className="text-[0.58em] tracking-[3px] mb-2" style={{ color: `${agent.color}70` }}>
                {agent.id}
              </div>
              <div className="text-[1.3em] tracking-[5px] font-bold" style={{ color: vc }}>
                {voteState.vote ?? '—'}
              </div>
              {voteState.reason && (
                <div className="text-[0.6em] mt-2 leading-relaxed text-[#2a2a2a] break-words">
                  {voteState.reason}
                </div>
              )}
            </div>
          )
        })}
      </div>

      {/* Main verdict */}
      {override ? (
        <div
          className="p-8 text-center mb-6"
          style={{ border: `2px solid ${activeColor}`, background: 'rgba(255,176,0,0.015)' }}
        >
          <div className="text-[0.58em] tracking-[5px] mb-3 text-[#FFB000]">
            ⚠  COMMANDER OVERRIDE ACTIVE
          </div>
          <div className="text-[2.8em] tracking-[8px]" style={{ color: activeColor }}>
            {activeLabel}
          </div>
          <div className="text-[0.58em] tracking-[3px] mt-3 text-[#1e1e1e]">
            MAGI CONSENSUS SUSPENDED — SUPREME COMMANDER AUTHORITY INVOKED
          </div>
        </div>
      ) : (
        <div
          className="p-8 text-center mb-6"
          style={{ border: `2px solid ${activeColor}`, background: `${activeColor}06` }}
        >
          <div className="text-[0.58em] tracking-[5px] mb-3 text-[#2a2a2a]">
            MAGI CONSENSUS — {approveCount} OF 3 APPROVE
          </div>
          <div className="text-[2.8em] tracking-[8px]" style={{ color: activeColor }}>
            {activeLabel}
          </div>
        </div>
      )}

      {/* Commander actions */}
      <div className="text-center text-[0.58em] tracking-[4px] text-[#1a1a1a] mb-3">
        COMMANDER ACTION
      </div>
      <div className="flex justify-center gap-4">
        {override ? (
          <TerminalButton
            onClick={() => onOverride(null)}
            hoverColor="#FFB000"
          >
            ⬡  RESCIND OVERRIDE
          </TerminalButton>
        ) : (
          <>
            <TerminalButton onClick={() => onOverride('APPROVE')} hoverColor="#00FF41">
              OVERRIDE: APPROVE
            </TerminalButton>
            <TerminalButton onClick={() => onOverride('REJECT')} hoverColor="#FF4444">
              OVERRIDE: REJECT
            </TerminalButton>
          </>
        )}
      </div>
    </div>
  )
}

function TerminalButton({
  children,
  onClick,
  hoverColor,
}: {
  children: React.ReactNode
  onClick: () => void
  hoverColor: string
}) {
  return (
    <button
      onClick={onClick}
      className="
        px-6 py-2 text-[0.68em] tracking-[3px]
        border border-nerv-border text-nerv-text bg-nerv-surface
        transition-colors duration-150
      "
      style={{
        ['--hover-color' as string]: hoverColor,
      }}
      onMouseEnter={e => {
        const el = e.currentTarget
        el.style.borderColor = hoverColor
        el.style.color = hoverColor
      }}
      onMouseLeave={e => {
        const el = e.currentTarget
        el.style.borderColor = ''
        el.style.color = ''
      }}
    >
      {children}
    </button>
  )
}
