import type { DebateRecord } from '../types'
import { AGENT_CONFIG } from '../agents'

interface Props {
  open: boolean
  records: DebateRecord[]
  onClose: () => void
  onCustomize: () => void
}

export default function HistorySidebar({ open, records, onClose, onCustomize }: Props) {
  return (
    <>
      {/* Sidebar panel */}
      <aside
        className="fixed left-0 top-0 h-full z-40 flex flex-col bg-[#050505] border-r border-nerv-border transition-[width] duration-200 overflow-hidden"
        style={{ width: open ? '17rem' : 0 }}
      >
        {/* Header */}
        <div className="flex items-start justify-between px-4 pt-5 pb-4 border-b border-nerv-border shrink-0">
          <div>
            <div className="text-[0.52em] tracking-[4px] text-red-600/30 mb-1">NERV DATABASE</div>
            <div className="text-[0.72em] tracking-[3px] text-[#666]">DELIBERATION ARCHIVE</div>
            <div className="text-[0.52em] tracking-[2px] text-nerv-dim mt-0.5">
              {records.length} RECORD{records.length !== 1 ? 'S' : ''}
            </div>
          </div>
          <button
            onClick={onClose}
            className="text-[#2a2a2a] hover:text-[#666] transition-colors text-xs mt-0.5"
            title="Close archive"
          >
            ✕
          </button>
        </div>

        {/* Record list */}
        <div className="flex-1 overflow-y-auto">
          {records.length === 0 ? (
            <div className="px-4 py-10 text-center text-[0.6em] tracking-[3px] text-[#1e1e1e]">
              NO RECORDS
            </div>
          ) : (
            records.map(r => <HistoryItem key={r.id} record={r} />)
          )}
        </div>

        {/* Footer: Customize button */}
        <div className="shrink-0 px-4 py-3 border-t border-nerv-border">
          <button
            onClick={onCustomize}
            className="w-full text-[0.6em] tracking-[3px] border border-nerv-border px-3 py-2.5 transition-colors hover:border-[#9B59B6] hover:text-[#9B59B6] text-[#2a2a2a]"
            style={{ background: 'none' }}
          >
            ⬡  CUSTOMIZE MAGI
          </button>
        </div>
      </aside>

      {/* Backdrop (mobile / accidental click) */}
      {open && (
        <div className="fixed inset-0 z-30" onClick={onClose} />
      )}
    </>
  )
}

// ── Single record row ──────────────────────────────────────────────────────────

function HistoryItem({ record }: { record: DebateRecord }) {
  const approved   = record.verdict === 'APPROVE'
  const verdictColor = approved ? '#00FF41' : '#FF4444'
  const verdictLabel = approved ? 'APPROVED' : 'REJECTED'

  const agentVotes: [string, string | null][] = [
    ['MELCHIOR',  record.melchior_vote],
    ['BALTHASAR', record.balthasar_vote],
    ['CASPAR',    record.caspar_vote],
  ]

  return (
    <div className="px-4 py-3 border-b border-[#0e0e0e] hover:bg-[#0a0a0a] transition-colors group">
      {/* Topic */}
      <p className="text-[0.68em] text-[#4a4a4a] group-hover:text-[#666] leading-snug mb-2 line-clamp-2 transition-colors">
        {record.topic}
      </p>

      {/* Verdict + votes + date */}
      <div className="flex items-center gap-2">
        <span
          className="text-[0.56em] tracking-[2px] font-bold shrink-0"
          style={{ color: verdictColor }}
        >
          {verdictLabel}
        </span>

        {/* Agent vote dots */}
        <span className="flex gap-1 items-center">
          {agentVotes.map(([key, vote]) => {
            const agentColor = AGENT_CONFIG[key as keyof typeof AGENT_CONFIG].color
            const vc = vote === 'APPROVE' ? '#00FF41' : vote === 'REJECT' ? '#FF4444' : '#1e1e1e'
            return (
              <span
                key={key}
                className="text-[0.52em] leading-none"
                style={{ color: vc }}
                title={`${key}: ${vote ?? '—'}`}
              >
                {vote === 'APPROVE' ? '✓' : vote === 'REJECT' ? '✗' : '·'}
              </span>
            )
          })}
        </span>

        <span className="text-[0.52em] text-[#222] ml-auto shrink-0 tabular-nums">
          {record.created_at}
        </span>
      </div>
    </div>
  )
}
