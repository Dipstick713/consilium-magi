import { useEffect, useMemo, useRef, useState } from 'react'
import type { AgentKey, FullMagiConfig, MagiAgentConfig } from '../types'
import { AGENT_CONFIG, AGENT_KEYS } from '../agents'
import {
  ARCHETYPE_DESCRIPTIONS,
  ARCHETYPE_KEYS,
  agentDisplayId,
  buildSystemPrompt,
} from '../lib/promptBuilder'

// ── Defaults ───────────────────────────────────────────────────────────────────

const DEFAULT_CONFIG: FullMagiConfig = {
  MELCHIOR:  { name: 'Melchior',  archetype: 'Scientist', aggression: 50, verbosity: 50, signature_phrase: '', custom_prompt: '' },
  BALTHASAR: { name: 'Balthasar', archetype: 'Mother',    aggression: 50, verbosity: 50, signature_phrase: '', custom_prompt: '' },
  CASPAR:    { name: 'Caspar',    archetype: 'Woman',     aggression: 50, verbosity: 50, signature_phrase: '', custom_prompt: '' },
}

// ── Props ──────────────────────────────────────────────────────────────────────

interface Props {
  open: boolean
  config: FullMagiConfig
  onClose: () => void
  onSave: (config: FullMagiConfig) => Promise<void>
}

// ── Component ──────────────────────────────────────────────────────────────────

export default function CustomizePanel({ open, config, onClose, onSave }: Props) {
  const [draft, setDraft] = useState<FullMagiConfig>(() => structuredClone(config))
  const [activeTab, setActiveTab] = useState<AgentKey>('MELCHIOR')
  const [saving, setSaving] = useState(false)
  const [saved, setSaved] = useState(false)
  const panelRef = useRef<HTMLDivElement>(null)

  // Sync draft when panel opens with fresh config
  useEffect(() => {
    if (open) {
      setDraft(structuredClone(config))
      setSaved(false)
    }
  }, [open, config])

  // Trap focus + close on Escape
  useEffect(() => {
    if (!open) return
    const onKey = (e: KeyboardEvent) => { if (e.key === 'Escape') onClose() }
    document.addEventListener('keydown', onKey)
    return () => document.removeEventListener('keydown', onKey)
  }, [open, onClose])

  if (!open) return null

  const patchAgent = (key: AgentKey, patch: Partial<MagiAgentConfig>) =>
    setDraft(prev => ({ ...prev, [key]: { ...prev[key], ...patch } }))

  const handleReset = () =>
    patchAgent(activeTab, { ...DEFAULT_CONFIG[activeTab] })

  const handleSave = async () => {
    setSaving(true)
    try {
      await onSave(draft)
      setSaved(true)
      setTimeout(onClose, 600)
    } finally {
      setSaving(false)
    }
  }

  const agentColor = AGENT_CONFIG[activeTab].color

  return (
    <>
      {/* Backdrop */}
      <div
        className="fixed inset-0 z-50 bg-black/75"
        onClick={onClose}
      />

      {/* Panel */}
      <div
        ref={panelRef}
        className="fixed inset-0 z-50 flex items-start justify-center pointer-events-none py-6 px-4 overflow-y-auto"
      >
        <div className="pointer-events-auto w-full max-w-2xl bg-[#050505] border border-nerv-border relative">

          {/* Top chromatic accent bar */}
          <div
            className="h-[2px]"
            style={{
              background: 'linear-gradient(90deg, #FFB000 0%, #00FF41 50%, #9B59B6 100%)',
            }}
          />

          {/* Header */}
          <div className="px-6 py-5 border-b border-nerv-border flex items-start justify-between">
            <div>
              <div className="text-[0.5em] tracking-[5px] text-red-600/30 mb-1">
                NERV — ARTIFICIAL EVOLUTION LABORATORY
              </div>
              <div className="text-[0.82em] tracking-[5px] text-[#c8c8c8]">
                MAGI CONFIGURATION TERMINAL
              </div>
              <div className="text-[0.55em] tracking-[3px] text-nerv-dim mt-1">
                MODIFY FRAGMENT PERSONALITY — CHANGES PERSIST ACROSS SESSIONS
              </div>
            </div>
            <button
              onClick={onClose}
              className="text-[#2a2a2a] hover:text-[#666] transition-colors text-xs mt-0.5 shrink-0"
              title="Close"
            >
              ✕
            </button>
          </div>

          {/* Agent tabs */}
          <div className="flex border-b border-nerv-border">
            {AGENT_KEYS.map(key => {
              const color = AGENT_CONFIG[key].color
              const isActive = activeTab === key
              return (
                <button
                  key={key}
                  onClick={() => setActiveTab(key)}
                  className="flex-1 py-3 px-3 text-[0.6em] tracking-[3px] transition-colors border-b-2"
                  style={{
                    color: isActive ? color : '#2a2a2a',
                    borderColor: isActive ? color : 'transparent',
                    background: 'none',
                  }}
                >
                  <div>{agentDisplayId(key, draft[key].name)}</div>
                  <div
                    className="text-[0.85em] tracking-[2px] mt-0.5"
                    style={{ color: isActive ? `${color}70` : '#1a1a1a' }}
                  >
                    [{draft[key].archetype.toUpperCase()}]
                  </div>
                </button>
              )
            })}
          </div>

          {/* Form body */}
          <div className="px-6 py-6 space-y-6">
            <AgentForm
              key={activeTab}
              agentKey={activeTab}
              config={draft[activeTab]}
              color={agentColor}
              onChange={patch => patchAgent(activeTab, patch)}
            />
          </div>

          {/* Footer */}
          <div className="px-6 py-4 border-t border-nerv-border flex items-center justify-between gap-4">
            <button
              onClick={handleReset}
              className="text-[0.6em] tracking-[3px] text-[#2a2a2a] hover:text-[#666] transition-colors"
              style={{ background: 'none', border: 'none', padding: 0 }}
            >
              ⟲  RESET FRAGMENT TO DEFAULTS
            </button>

            <button
              onClick={handleSave}
              disabled={saving}
              className="text-[0.65em] tracking-[3px] border px-4 py-2 transition-colors disabled:opacity-40"
              style={{
                color: saved ? '#00FF41' : agentColor,
                borderColor: saved ? '#00FF4140' : `${agentColor}40`,
                background: 'none',
              }}
            >
              {saving ? '▓ SAVING…' : saved ? '✓ SAVED' : '⊞  SAVE CONFIGURATION'}
            </button>
          </div>
        </div>
      </div>
    </>
  )
}

// ── Per-agent form ─────────────────────────────────────────────────────────────

interface FormProps {
  agentKey: AgentKey
  config: MagiAgentConfig
  color: string
  onChange: (patch: Partial<MagiAgentConfig>) => void
}

function AgentForm({ agentKey, config, color, onChange }: FormProps) {
  const [previewOpen, setPreviewOpen] = useState(false)

  const previewPrompt = useMemo(
    () => buildSystemPrompt(agentKey, config),
    [agentKey, config],
  )

  return (
    <div className="space-y-5">

      {/* Name */}
      <FieldRow label="DESIGNATION" color={color}>
        <NervInput
          value={config.name}
          onChange={v => onChange({ name: v })}
          placeholder="e.g. Melchior"
          color={color}
        />
      </FieldRow>

      {/* Archetype */}
      <FieldRow label="ARCHETYPE" color={color}>
        <NervSelect
          value={config.archetype}
          options={ARCHETYPE_KEYS.map(k => ({ value: k, label: `${k}  —  ${ARCHETYPE_DESCRIPTIONS[k]}` }))}
          onChange={v => onChange({ archetype: v as MagiAgentConfig['archetype'] })}
          color={color}
        />
      </FieldRow>

      {/* Custom prompt — only when archetype is Custom */}
      {config.archetype === 'Custom' && (
        <FieldRow label="SYSTEM PROMPT" color={color}>
          <textarea
            value={config.custom_prompt}
            onChange={e => onChange({ custom_prompt: e.target.value })}
            placeholder="Enter a full system prompt for this fragment…"
            rows={6}
            className="w-full bg-nerv-surface border border-nerv-border text-[0.75em] tracking-wider px-3 py-2 outline-none resize-y transition-colors placeholder:text-nerv-dim leading-relaxed"
            style={{
              color: `${color}cc`,
              fontFamily: 'inherit',
              // eslint-disable-next-line @typescript-eslint/no-explicit-any
              '--tw-border-opacity': '1',
            } as React.CSSProperties}
            onFocus={e => { e.target.style.borderColor = color }}
            onBlur={e => { e.target.style.borderColor = '' }}
          />
        </FieldRow>
      )}

      {/* Aggression slider */}
      <SliderRow
        label="AGGRESSION"
        leftLabel="MEASURED"
        rightLabel="RUTHLESS"
        value={config.aggression}
        color={color}
        onChange={v => onChange({ aggression: v })}
      />

      {/* Verbosity slider */}
      <SliderRow
        label="VERBOSITY"
        leftLabel="TERSE"
        rightLabel="ELABORATE"
        value={config.verbosity}
        color={color}
        onChange={v => onChange({ verbosity: v })}
      />

      {/* Signature phrase */}
      <FieldRow label="SIGNATURE PHRASE" color={color}>
        <NervInput
          value={config.signature_phrase}
          onChange={v => onChange({ signature_phrase: v })}
          placeholder="A line they always end with — or leave blank"
          color={color}
        />
      </FieldRow>

      {/* Live preview */}
      <div>
        <button
          onClick={() => setPreviewOpen(v => !v)}
          className="flex items-center gap-2 text-[0.58em] tracking-[3px] transition-colors mb-2"
          style={{
            color: previewOpen ? `${color}80` : '#252525',
            background: 'none',
            border: 'none',
            padding: 0,
          }}
        >
          <span>{previewOpen ? '▾' : '▸'}</span>
          <span>PREVIEW GENERATED PROMPT</span>
        </button>

        {previewOpen && (
          <pre
            className="text-[0.6em] leading-[1.9] whitespace-pre-wrap break-words m-0 px-4 py-3 border overflow-auto max-h-64"
            style={{
              color: `${color}55`,
              borderColor: `${color}18`,
              background: '#020202',
              fontFamily: 'inherit',
            }}
          >
            {previewPrompt}
          </pre>
        )}
      </div>
    </div>
  )
}

// ── Shared sub-components ──────────────────────────────────────────────────────

function FieldRow({
  label,
  color,
  children,
}: {
  label: string
  color: string
  children: React.ReactNode
}) {
  return (
    <div>
      <div
        className="text-[0.55em] tracking-[3px] mb-1.5"
        style={{ color: `${color}50` }}
      >
        {label}
      </div>
      {children}
    </div>
  )
}

function NervInput({
  value,
  onChange,
  placeholder,
  color,
}: {
  value: string
  onChange: (v: string) => void
  placeholder?: string
  color: string
}) {
  return (
    <input
      type="text"
      value={value}
      onChange={e => onChange(e.target.value)}
      placeholder={placeholder}
      className="w-full bg-nerv-surface border border-nerv-border text-[0.75em] tracking-wider px-3 py-2 outline-none transition-colors placeholder:text-nerv-dim"
      style={{ color: `${color}cc`, fontFamily: 'inherit' }}
      onFocus={e => { e.target.style.borderColor = color }}
      onBlur={e => { e.target.style.borderColor = '' }}
    />
  )
}

function NervSelect({
  value,
  options,
  onChange,
  color,
}: {
  value: string
  options: { value: string; label: string }[]
  onChange: (v: string) => void
  color: string
}) {
  return (
    <select
      value={value}
      onChange={e => onChange(e.target.value)}
      className="w-full bg-nerv-surface border border-nerv-border text-[0.72em] tracking-wider px-3 py-2 outline-none transition-colors appearance-none cursor-pointer"
      style={{ color: `${color}cc`, fontFamily: 'inherit' }}
      onFocus={e => { e.target.style.borderColor = color }}
      onBlur={e => { e.target.style.borderColor = '' }}
    >
      {options.map(o => (
        <option key={o.value} value={o.value} style={{ background: '#0d0d0d' }}>
          {o.label}
        </option>
      ))}
    </select>
  )
}

function SliderRow({
  label,
  leftLabel,
  rightLabel,
  value,
  color,
  onChange,
}: {
  label: string
  leftLabel: string
  rightLabel: string
  value: number
  color: string
  onChange: (v: number) => void
}) {
  // Determine which zone we're in for the fill display
  const pct = value + '%'

  return (
    <div>
      <div className="flex items-center justify-between mb-1.5">
        <span className="text-[0.55em] tracking-[3px]" style={{ color: `${color}50` }}>
          {label}
        </span>
        <span className="text-[0.55em] tracking-[2px] tabular-nums" style={{ color: `${color}40` }}>
          {value}
        </span>
      </div>

      {/* Track + thumb */}
      <div className="relative h-[14px] flex items-center">
        {/* Background track */}
        <div className="absolute inset-x-0 h-[2px] bg-[#111]" />
        {/* Filled portion */}
        <div
          className="absolute left-0 h-[2px] transition-[width]"
          style={{ width: pct, background: `${color}60` }}
        />
        <input
          type="range"
          min={0}
          max={100}
          value={value}
          onChange={e => onChange(Number(e.target.value))}
          className="nerv-slider relative w-full"
          style={{ '--thumb-color': color } as React.CSSProperties}
        />
      </div>

      <div className="flex justify-between mt-1">
        <span className="text-[0.5em] tracking-[2px] text-[#1e1e1e]">{leftLabel}</span>
        <span className="text-[0.5em] tracking-[2px] text-[#1e1e1e]">{rightLabel}</span>
      </div>
    </div>
  )
}

