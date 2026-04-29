export type AgentKey = 'MELCHIOR' | 'BALTHASAR' | 'CASPAR'

export type Archetype =
  | 'Scientist'
  | 'Mother'
  | 'Woman'
  | 'Philosopher'
  | "Devil's Advocate"
  | 'Optimist'
  | 'Historian'
  | 'Custom'

export interface MagiAgentConfig {
  name: string
  archetype: Archetype
  aggression: number   // 0–100
  verbosity: number    // 0–100
  signature_phrase: string
  custom_prompt: string
}

export type FullMagiConfig = Record<AgentKey, MagiAgentConfig>
export type Round = 'r1' | 'r2' | 'vote'
export type VoteResult = 'APPROVE' | 'REJECT'
export type DebateStatus = 'idle' | 'running' | 'complete' | 'error'
export type ReactionStance = 'agreement' | 'challenge' | 'synthesis'

export type TraceEntry =
  | { kind: 'thought'; text: string }
  | { kind: 'action';  tool: string; args: Record<string, unknown> }
  | { kind: 'obs';     text: string }

export interface ReactionEntry {
  reactor: AgentKey
  stance: ReactionStance
  text: string
}

export interface AgentRound {
  text: string
  streaming: boolean
  done: boolean
  searchQuery: string | null
  searchLive: boolean
  trace: TraceEntry[]
  reactions: ReactionEntry[]
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

export interface SplitAnalysis {
  dissenterKey: AgentKey
  text: string
  streaming: boolean
}

export interface DebateState {
  status: DebateStatus
  topic: string
  agents: Record<AgentKey, AgentState>
  approveCount: number
  verdict: VoteResult | null
  override: VoteResult | null
  splitAnalysis: SplitAnalysis | null
  error: string | null
}

export interface DebateRecord {
  id: number
  topic: string
  verdict: 'APPROVE' | 'REJECT'
  approve_count: number
  melchior_vote:    string | null
  balthasar_vote:   string | null
  caspar_vote:      string | null
  melchior_reason:  string | null
  balthasar_reason: string | null
  caspar_reason:    string | null
  created_at: string
}

export type Action =
  | { type: 'START'; topic: string }
  | { type: 'SEARCH_QUERY'; agent: AgentKey; round: Round; query: string; live: boolean }
  | { type: 'AGENT_START'; agent: AgentKey; round: Round }
  | { type: 'TOKEN'; agent: AgentKey; round: Round; text: string }
  | { type: 'AGENT_DONE'; agent: AgentKey; round: Round }
  | { type: 'VOTE'; agent: AgentKey; vote: VoteResult; reason: string }
  | { type: 'VERDICT'; approveCount: number; verdict: VoteResult }
  | { type: 'DONE' }
  | { type: 'ERROR'; message: string }
  | { type: 'SPLIT_START'; dissenterKey: AgentKey }
  | { type: 'SPLIT_TOKEN'; text: string }
  | { type: 'SPLIT_DONE' }
  | { type: 'OVERRIDE'; vote: VoteResult | null }
  | { type: 'RESET' }
  | { type: 'TRACE_THOUGHT'; agent: AgentKey; round: Round; text: string }
  | { type: 'TRACE_ACTION';  agent: AgentKey; round: Round; tool: string; args: Record<string, unknown> }
  | { type: 'TRACE_OBS';     agent: AgentKey; round: Round; text: string }
  | { type: 'REACTION';      agent: AgentKey; round: Round; reactor: AgentKey; stance: ReactionStance; text: string }
