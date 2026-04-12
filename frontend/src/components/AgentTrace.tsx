import { useState } from 'react'
import type { TraceEntry } from '../types'

interface Props {
  trace: TraceEntry[]
  color: string
  isLive?: boolean
}

export default function AgentTrace({ trace, color, isLive = false }: Props) {
  const [open, setOpen] = useState(false)

  if (trace.length === 0 && !isLive) return null

  return (
    <div className="mb-3">
      {/* Toggle button */}
      <button
        onClick={() => setOpen(v => !v)}
        className="flex items-center gap-1.5 text-[0.55em] tracking-[3px] cursor-pointer select-none mb-1"
        style={{ color: `${color}50`, background: 'none', border: 'none', padding: 0 }}
      >
        <span>{open ? '▾' : '▸'}</span>
        <span>AGENT TRACE</span>
        {isLive && !open && (
          <span className="animate-pulse" style={{ color: `${color}70` }}>●</span>
        )}
        {trace.length > 0 && (
          <span style={{ color: `${color}30` }}>({trace.length} steps)</span>
        )}
      </button>

      {open && (
        <div
          className="ml-2 pl-2 space-y-1.5"
          style={{ borderLeft: `1px solid ${color}18` }}
        >
          {trace.map((entry, i) => (
            <TraceRow key={i} entry={entry} color={color} />
          ))}
          {isLive && (
            <div className="text-[0.5em] tracking-[2px] animate-pulse" style={{ color: `${color}40` }}>
              ▓ processing…
            </div>
          )}
        </div>
      )}
    </div>
  )
}

function TraceRow({ entry, color }: { entry: TraceEntry; color: string }) {
  if (entry.kind === 'thought') {
    return (
      <div>
        <span className="text-[0.5em] tracking-[2px]" style={{ color: `${color}45` }}>THINK  </span>
        <span className="text-[0.62em] leading-[1.7] italic" style={{ color: `${color}70` }}>
          {entry.text}
        </span>
      </div>
    )
  }

  if (entry.kind === 'action') {
    const argsStr = Object.entries(entry.args)
      .map(([k, v]) => `${k}=${JSON.stringify(v)}`)
      .join(' ')
    return (
      <div>
        <span className="text-[0.5em] tracking-[2px]" style={{ color: `${color}45` }}>ACT    </span>
        <span className="text-[0.62em] font-bold" style={{ color: `${color}90` }}>
          {entry.tool}
        </span>
        {argsStr && (
          <span className="text-[0.55em] ml-1.5" style={{ color: `${color}50` }}>
            {argsStr}
          </span>
        )}
      </div>
    )
  }

  // obs
  return (
    <div>
      <span className="text-[0.5em] tracking-[2px]" style={{ color: `${color}45` }}>OBS    </span>
      <span
        className="text-[0.62em] leading-[1.7]"
        style={{ color: `${color}55` }}
      >
        {entry.text.length > 200 ? entry.text.slice(0, 200) + '…' : entry.text}
      </span>
    </div>
  )
}
