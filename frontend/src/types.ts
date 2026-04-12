export type AgentKey = 'MELCHIOR' | 'BALTHASAR' | 'CASPAR'
export type Round = 'r1' | 'r2' | 'vote'
export type VoteResult = 'APPROVE' | 'REJECT'
export type DebateStatus = 'idle' | 'running' | 'complete' | 'error'

export interface AgentRound {
  text: string
  streaming: boolean
  done: boolean
}

export interface AgentVote extends AgentRound {
  vote: VoteResult | null
  reason: string
}

export interface AgentState {
  r1: AgentRound
  r2: AgentRound
  vote: AgentVote
}

export interface DebateState {
  status: DebateStatus
  topic: string
  agents: Record<AgentKey, AgentState>
  approveCount: number
  verdict: VoteResult | null
  override: VoteResult | null
  error: string | null
}

export type Action =
  | { type: 'START'; topic: string }
  | { type: 'AGENT_START'; agent: AgentKey; round: Round }
  | { type: 'TOKEN'; agent: AgentKey; round: Round; text: string }
  | { type: 'AGENT_DONE'; agent: AgentKey; round: Round }
  | { type: 'VOTE'; agent: AgentKey; vote: VoteResult; reason: string }
  | { type: 'VERDICT'; approveCount: number; verdict: VoteResult }
  | { type: 'DONE' }
  | { type: 'ERROR'; message: string }
  | { type: 'OVERRIDE'; vote: VoteResult | null }
  | { type: 'RESET' }
