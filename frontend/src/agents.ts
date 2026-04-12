import type { AgentKey } from './types'

export interface AgentConfig {
  id: string
  role: string
  color: string
}

export const AGENT_KEYS: AgentKey[] = ['MELCHIOR', 'BALTHASAR', 'CASPAR']

export const AGENT_CONFIG: Record<AgentKey, AgentConfig> = {
  MELCHIOR: { id: 'MELCHIOR-1', role: 'SCIENTIST', color: '#FFB000' },
  BALTHASAR: { id: 'BALTHASAR-2', role: 'MOTHER',    color: '#00FF41' },
  CASPAR:    { id: 'CASPAR-3',    role: 'WOMAN',      color: '#9B59B6' },
}
