import { useState, type FormEvent } from 'react'

interface Props {
  onSubmit: (topic: string) => void
  disabled: boolean
}

export default function TopicInput({ onSubmit, disabled }: Props) {
  const [topic, setTopic] = useState('')

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault()
    const trimmed = topic.trim()
    if (trimmed && !disabled) onSubmit(trimmed)
  }

  return (
    <form onSubmit={handleSubmit} className="flex gap-3 items-stretch">
      <input
        type="text"
        value={topic}
        onChange={e => setTopic(e.target.value)}
        placeholder="Submit the question for MAGI deliberation..."
        disabled={disabled}
        className="
          flex-1 bg-nerv-surface border border-nerv-border text-[#999]
          text-sm tracking-wider px-4 py-3
          outline-none focus:border-[#FFB000] transition-colors
          placeholder:text-nerv-dim
          disabled:opacity-30 disabled:cursor-not-allowed
        "
      />
      <button
        type="submit"
        disabled={!topic.trim() || disabled}
        className="
          px-6 text-[0.7em] tracking-[3px] whitespace-nowrap
          border border-nerv-border text-nerv-text bg-nerv-surface
          hover:border-[#FFB000] hover:text-[#FFB000] transition-colors
          disabled:opacity-20 disabled:cursor-not-allowed
        "
      >
        {disabled ? 'DELIBERATING…' : 'INITIATE DELIBERATION'}
      </button>
    </form>
  )
}
