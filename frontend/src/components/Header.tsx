interface Props {
  apiKey: string
  onApiKeyChange: (key: string) => void
}

export default function Header({ apiKey, onApiKeyChange }: Props) {
  return (
    <header className="border-b border-nerv-border mb-8">
      <div className="max-w-[1400px] mx-auto px-6 py-5 flex items-center gap-8">
        {/* Title */}
        <div className="flex-1 text-center">
          <div className="text-[0.58em] tracking-[6px] text-red-600/40 mb-1">
            GEHIRN ARTIFICIAL EVOLUTION LABORATORY  ⬡  CLASSIFIED
          </div>
          <h1 className="nerv-flicker text-[1.9em] tracking-[10px] text-[#c8c8c8] font-normal leading-none">
            CONSILIUM MAGI
          </h1>
          <div className="text-[0.57em] tracking-[5px] text-nerv-dim mt-1">
            MELCHIOR-1  ⬡  BALTHASAR-2  ⬡  CASPAR-3
          </div>
        </div>

        {/* API key */}
        <div className="w-52 shrink-0">
          <label className="block text-[0.58em] tracking-[3px] text-nerv-dim mb-1.5">
            GROQ API KEY
          </label>
          <input
            type="password"
            value={apiKey}
            onChange={e => onApiKeyChange(e.target.value)}
            placeholder="gsk_… (or set env var)"
            className="
              w-full bg-nerv-surface border border-nerv-border text-nerv-text
              text-[0.75em] tracking-wider px-3 py-2
              outline-none focus:border-[#FFB000] transition-colors
              placeholder:text-nerv-dim
            "
          />
        </div>
      </div>
    </header>
  )
}
