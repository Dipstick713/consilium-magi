import { useReducer, useRef, useState, useCallback } from 'react'
import type { DebateState, Action, AgentKey, Round, VoteResult } from './types'
import { AGENT_KEYS } from './agents'
import Header from './components/Header'
import TopicInput from './components/TopicInput'
import AgentColumn from './components/AgentColumn'
import VerdictPanel from './components/VerdictPanel'

// ── Initial state ──────────────────────────────────────────────────────────────

const emptyRound = () => ({ text: '', streaming: false, done: false })
const emptyAgent = () => ({
  r1:   emptyRound(),
  r2:   emptyRound(),
  vote: { ...emptyRound(), vote: null, reason: '' },
})

const initialState: DebateState = {
  status: 'idle',
  topic: '',
  agents: {
    MELCHIOR:  emptyAgent(),
    BALTHASAR: emptyAgent(),
    CASPAR:    emptyAgent(),
  },
  approveCount: 0,
  verdict: null,
  override: null,
  error: null,
}

// ── Reducer ────────────────────────────────────────────────────────────────────

function updateRound(
  state: DebateState,
  agent: AgentKey,
  round: Round,
  patch: Record<string, unknown>,
): DebateState {
  return {
    ...state,
    agents: {
      ...state.agents,
      [agent]: {
        ...state.agents[agent],
        [round]: { ...state.agents[agent][round], ...patch },
      },
    },
  }
}

function reducer(state: DebateState, action: Action): DebateState {
  switch (action.type) {
    case 'START':
      return { ...initialState, status: 'running', topic: action.topic }

    case 'AGENT_START':
      return updateRound(state, action.agent, action.round, { streaming: true })

    case 'TOKEN':
      return updateRound(state, action.agent, action.round, {
        text: state.agents[action.agent][action.round].text + action.text,
      })

    case 'AGENT_DONE':
      return updateRound(state, action.agent, action.round, { streaming: false, done: true })

    case 'VOTE':
      return {
        ...state,
        agents: {
          ...state.agents,
          [action.agent]: {
            ...state.agents[action.agent],
            vote: {
              ...state.agents[action.agent].vote,
              vote: action.vote,
              reason: action.reason,
            },
          },
        },
      }

    case 'VERDICT':
      return { ...state, approveCount: action.approveCount, verdict: action.verdict }

    case 'DONE':
      return { ...state, status: 'complete' }

    case 'ERROR':
      return { ...state, status: 'error', error: action.message }

    case 'OVERRIDE':
      return { ...state, override: action.vote }

    case 'RESET':
      return initialState

    default:
      return state
  }
}

// ── App ────────────────────────────────────────────────────────────────────────

export default function App() {
  const [state, dispatch] = useReducer(reducer, initialState)
  const [apiKey, setApiKey] = useState('')
  const abortRef = useRef<AbortController | null>(null)

  const startDebate = useCallback(async (topic: string) => {
    abortRef.current?.abort()
    abortRef.current = new AbortController()

    dispatch({ type: 'START', topic })

    try {
      const response = await fetch('/api/debate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ topic, api_key: apiKey }),
        signal: abortRef.current.signal,
      })

      if (!response.ok) {
        const err = await response.json().catch(() => ({ detail: 'Request failed' }))
        dispatch({ type: 'ERROR', message: err.detail ?? 'Request failed' })
        return
      }

      const reader = response.body!.getReader()
      const decoder = new TextDecoder()
      let buffer = ''

      while (true) {
        const { done, value } = await reader.read()
        if (done) break

        buffer += decoder.decode(value, { stream: true })
        const events = buffer.split('\n\n')
        buffer = events.pop() ?? ''

        for (const event of events) {
          const dataLine = event.split('\n').find(l => l.startsWith('data: '))
          if (!dataLine) continue
          try {
            const data = JSON.parse(dataLine.slice(6))
            switch (data.type as string) {
              case 'agent_start':
                dispatch({ type: 'AGENT_START', agent: data.agent as AgentKey, round: data.round as Round })
                break
              case 'token':
                dispatch({ type: 'TOKEN', agent: data.agent as AgentKey, round: data.round as Round, text: data.text })
                break
              case 'agent_done':
                dispatch({ type: 'AGENT_DONE', agent: data.agent as AgentKey, round: data.round as Round })
                break
              case 'vote':
                dispatch({ type: 'VOTE', agent: data.agent as AgentKey, vote: data.vote as VoteResult, reason: data.reason })
                break
              case 'verdict':
                dispatch({ type: 'VERDICT', approveCount: data.approve_count, verdict: data.verdict as VoteResult })
                break
              case 'done':
                dispatch({ type: 'DONE' })
                break
              case 'error':
                dispatch({ type: 'ERROR', message: data.message })
                break
            }
          } catch {
            // skip malformed event
          }
        }
      }
    } catch (err) {
      if (err instanceof Error && err.name !== 'AbortError') {
        dispatch({ type: 'ERROR', message: err.message })
      }
    }
  }, [apiKey])

  const isRunning = state.status === 'running'
  const showColumns = state.status !== 'idle'

  return (
    <div className="min-h-screen bg-nerv-bg text-nerv-text">
      <Header apiKey={apiKey} onApiKeyChange={setApiKey} />

      <main className="max-w-[1400px] mx-auto px-6 pb-20">
        <TopicInput onSubmit={startDebate} disabled={isRunning} />

        {state.status === 'error' && (
          <div className="mt-6 border border-red-900/40 bg-red-950/10 px-4 py-3 text-red-500/80 text-xs tracking-widest text-center">
            ⚠  MAGI SYSTEM ERROR — {state.error}
          </div>
        )}

        {showColumns && (
          <div className="mt-8 grid grid-cols-3 gap-5">
            {AGENT_KEYS.map(key => (
              <AgentColumn key={key} agentKey={key} agentState={state.agents[key]} />
            ))}
          </div>
        )}

        {state.verdict && (
          <VerdictPanel
            agents={state.agents}
            approveCount={state.approveCount}
            verdict={state.verdict}
            override={state.override}
            onOverride={vote => dispatch({ type: 'OVERRIDE', vote })}
          />
        )}
      </main>
    </div>
  )
}
