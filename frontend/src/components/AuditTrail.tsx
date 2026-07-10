import { useState } from 'react'
import { fetchAudit } from '../api/client'
import type { ScoreResponse } from '../types'

interface AuditTrailProps {
  customerId: string
}

export default function AuditTrail({ customerId }: AuditTrailProps) {
  const [open, setOpen] = useState(false)
  const [entries, setEntries] = useState<ScoreResponse[] | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const handleToggle = async () => {
    if (open) {
      setOpen(false)
      return
    }
    setOpen(true)
    if (entries) return
    setLoading(true)
    setError(null)
    try {
      const data = await fetchAudit(customerId)
      setEntries(data)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to load audit history')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div style={{ background: '#fff', border: '1px solid #E2E6EC', borderRadius: 10, overflow: 'hidden' }}>
      <div onClick={handleToggle} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '16px 20px', cursor: 'pointer' }}>
        <p style={{ fontSize: 11.5, fontWeight: 700, textTransform: 'uppercase', letterSpacing: '.06em', color: '#5B6675', margin: 0 }}>Audit trail</p>
        <span style={{ transition: '.2s', color: '#5B6675', fontSize: 12 }}>{open ? '▲' : '▼'}</span>
      </div>
      {open && (
        <div style={{ padding: '0 20px 18px' }}>
          {loading && <div style={{ fontSize: 13, color: '#5B6675', padding: '8px 0' }}>Loading...</div>}
          {error && <div style={{ fontSize: 13, color: '#C41E3A', padding: '8px 0' }}>{error}</div>}
          {entries && entries.length === 0 && <div style={{ fontSize: 13, color: '#5B6675', padding: '8px 0' }}>No previous scores recorded.</div>}
          {entries && entries.length > 0 && (
            <div style={{ overflowX: 'auto' }}>
              <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 12.5 }}>
                <thead>
                  <tr>
                    <th style={{ textAlign: 'left', color: '#5B6675', fontWeight: 600, fontSize: 11, textTransform: 'uppercase', letterSpacing: '.04em', padding: '8px 10px', borderBottom: '1.5px solid #E2E6EC' }}>Scored at</th>
                    <th style={{ textAlign: 'left', color: '#5B6675', fontWeight: 600, fontSize: 11, textTransform: 'uppercase', letterSpacing: '.04em', padding: '8px 10px', borderBottom: '1.5px solid #E2E6EC' }}>Bucket</th>
                    <th style={{ textAlign: 'left', color: '#5B6675', fontWeight: 600, fontSize: 11, textTransform: 'uppercase', letterSpacing: '.04em', padding: '8px 10px', borderBottom: '1.5px solid #E2E6EC' }}>Confidence</th>
                    <th style={{ textAlign: 'left', color: '#5B6675', fontWeight: 600, fontSize: 11, textTransform: 'uppercase', letterSpacing: '.04em', padding: '8px 10px', borderBottom: '1.5px solid #E2E6EC' }}>Source</th>
                  </tr>
                </thead>
                <tbody>
                  {entries.map((entry) => (
                    <tr key={entry.request_id}>
                      <td style={{ padding: '10px 10px', borderBottom: '1px solid #E2E6EC', fontFamily: "'IBM Plex Mono', monospace", fontSize: 12 }}>{new Date(entry.scored_at).toLocaleString()}</td>
                      <td style={{ padding: '10px 10px', borderBottom: '1px solid #E2E6EC' }}>{entry.bucket}</td>
                      <td style={{ padding: '10px 10px', borderBottom: '1px solid #E2E6EC' }}>{(entry.probability * 100).toFixed(1)}%</td>
                      <td style={{ padding: '10px 10px', borderBottom: '1px solid #E2E6EC' }}>{entry.source}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
