import { CURATED_IDS } from '../config/demo-ids'

interface SearchBarProps {
  customerId: string
  onCustomerIdChange: (id: string) => void
  onFetch: () => void
  onClear: () => void
  disabled: boolean
  enableSeasonality: boolean
  onEnableSeasonalityChange: (v: boolean) => void
}

export default function SearchBar({ customerId, onCustomerIdChange, onFetch, onClear, disabled, enableSeasonality, onEnableSeasonalityChange }: SearchBarProps) {
  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') {
      e.preventDefault()
      onFetch()
    }
  }

  return (
    <div style={{ background: '#fff', border: '1px solid #E2E6EC', borderRadius: 10, padding: 16, display: 'grid', gridTemplateColumns: '1fr auto auto auto', gap: 12, alignItems: 'end', marginBottom: 20 }}>
      <div>
        <label style={{ display: 'block', fontSize: 11.5, fontWeight: 600, textTransform: 'uppercase', letterSpacing: '.05em', color: '#5B6675', marginBottom: 6 }}>Customer ID</label>
        <input
          type="text"
          value={customerId}
          onChange={e => onCustomerIdChange(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="e.g. CUST00042"
          maxLength={20}
          disabled={disabled}
          style={{ width: '100%', padding: '10px 12px', border: '1px solid #E2E6EC', borderRadius: 7, fontFamily: 'inherit', fontSize: 14, color: '#1A2430', background: '#fff', outline: 'none', boxSizing: 'border-box' }}
        />
      </div>
      <div style={{ display: 'flex', alignItems: 'end', gap: 6 }}>
        <label style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 12.5, fontWeight: 500, color: '#5B6675', cursor: 'pointer', padding: '10px 0', whiteSpace: 'nowrap' }}>
          <input
            type="checkbox"
            checked={enableSeasonality}
            onChange={e => onEnableSeasonalityChange(e.target.checked)}
            disabled={disabled}
            style={{ accentColor: '#003D7C' }}
          />
          Seasonality
        </label>
      </div>
      <button onClick={onFetch} disabled={disabled || !customerId.trim()} style={{ padding: '10px 20px', borderRadius: 7, border: 'none', fontFamily: 'inherit', fontSize: 13.5, fontWeight: 600, cursor: 'pointer', height: 41, background: disabled || !customerId.trim() ? '#C7CDD6' : '#003D7C', color: '#fff' }}>
        Fetch score
      </button>
      <button onClick={onClear} style={{ padding: '10px 20px', borderRadius: 7, border: '1px solid #E2E6EC', fontFamily: 'inherit', fontSize: 13.5, fontWeight: 600, cursor: 'pointer', height: 41, background: '#fff', color: '#5B6675' }}>
        Clear
      </button>
      <div style={{ gridColumn: '1 / -1', display: 'flex', alignItems: 'center', gap: 8, fontSize: 12, color: '#5B6675', marginTop: 2 }}>
        Demo profiles:
        {CURATED_IDS.map(({ id, label }) => (
          <button
            key={id}
            onClick={() => {
              onCustomerIdChange(id)
              setTimeout(() => onFetch(), 50)
            }}
            style={{ background: '#F4F6F9', border: '1px solid #E2E6EC', borderRadius: 5, padding: '3px 9px', fontFamily: "'IBM Plex Mono', monospace", fontSize: 11.5, cursor: 'pointer', color: '#003D7C' }}
            title={label}
          >
            {id}
          </button>
        ))}
      </div>
    </div>
  )
}
