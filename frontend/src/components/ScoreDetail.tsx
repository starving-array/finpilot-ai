import { useState } from 'react'
import type { ScoreResponse, FeatureRank } from '../types'
import { submitDecision } from '../api/client'

interface ScoreDetailProps {
  result: ScoreResponse
  customerId: string
}

export default function ScoreDetail({ result, customerId }: ScoreDetailProps) {
  const [selectedDecision, setSelectedDecision] = useState<string | null>(null)
  const [remarks, setRemarks] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [confirmed, setConfirmed] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [remarksError, setRemarksError] = useState(false)

  const reasons: FeatureRank[] = result.shap_explanation?.feature_ranking || []

  const handleSubmit = async () => {
    if (!selectedDecision) return
    if (!remarks.trim()) {
      setRemarksError(true)
      return
    }
    setSubmitting(true)
    setError(null)
    try {
      const decisionMap: Record<string, string> = {
        accept: 'APPROVE',
        review: 'REVIEW',
        reject: 'REJECT',
      }
      await submitDecision({
        customer_id: customerId,
        decision: decisionMap[selectedDecision] || selectedDecision.toUpperCase(),
        remarks: remarks.trim(),
      })
      setConfirmed(true)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to submit decision')
    } finally {
      setSubmitting(false)
    }
  }

  const handleReset = () => {
    setSelectedDecision(null)
    setRemarks('')
    setConfirmed(false)
    setError(null)
    setRemarksError(false)
  }

  if (confirmed) {
    return (
      <div className="detail-row" style={{ display: 'grid', gridTemplateColumns: '1.4fr 1fr', gap: 20, marginBottom: 20, alignItems: 'start' }}>
        <div style={{ background: '#fff', border: '1px solid #E2E6EC', borderRadius: 10, padding: 20 }}>
          <p style={{ fontSize: 11.5, fontWeight: 700, textTransform: 'uppercase', letterSpacing: '.06em', color: '#5B6675', margin: '0 0 16px' }}>Reasons (SHAP-derived)</p>
          {reasons.length === 0 && <p style={{ fontSize: 13, color: '#5B6675' }}>No SHAP explanation available.</p>}
          {reasons.map((r, i) => (
            <div key={r.feature_name} style={{ display: 'grid', gridTemplateColumns: '22px 1fr auto', gap: 10, alignItems: 'center', padding: i === 0 ? '0 0 11px' : '11px 0', borderTop: i > 0 ? '1px solid #E2E6EC' : 'none' }}>
              <div style={{
                width: 22, height: 22, borderRadius: '50%', display: 'flex', alignItems: 'center', justifyContent: 'center',
                fontSize: 13, fontWeight: 700, flexShrink: 0,
                background: r.shap_value >= 0 ? '#E8F5EE' : '#FEE8EC',
                color: r.shap_value >= 0 ? '#1B6B3A' : '#C41E3A',
              }}>
                {r.shap_value >= 0 ? '↑' : '↓'}
              </div>
              <div style={{ fontSize: 13, lineHeight: 1.4 }}>{r.business_description}</div>
              <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-end', gap: 4 }}>
                <span style={{
                  fontSize: 10, fontWeight: 700, textTransform: 'uppercase', letterSpacing: '.03em',
                  padding: '2px 7px', borderRadius: 8,
                  background: r.source === 'standard' ? '#EDEDF2' : '#E6EEFA',
                  color: r.source === 'standard' ? '#54566B' : '#1B5FA8',
                }}>
                  {r.source}
                </span>
                <div style={{ width: 64, height: 4, background: '#E2E6EC', borderRadius: 3, overflow: 'hidden' }}>
                  <div style={{ height: '100%', background: '#C8A951', width: `${Math.min(100, Math.abs(r.shap_value) * 100)}%` }} />
                </div>
              </div>
            </div>
          ))}
        </div>
        <div style={{ background: '#fff', border: '1.5px solid #C8A951', borderRadius: 10, padding: 20 }}>
          <p style={{ fontSize: 11.5, fontWeight: 700, textTransform: 'uppercase', letterSpacing: '.06em', color: '#8A6D1B', margin: '0 0 16px' }}>Underwriter decision</p>
          <div style={{ marginTop: 12, background: '#E8F5EE', border: '1px solid #A8D5BA', color: '#1B6B3A', padding: '10px 12px', borderRadius: 7, fontSize: 12.5, fontWeight: 500 }}>
            Decision recorded — {customerId} marked as {selectedDecision ? selectedDecision.charAt(0).toUpperCase() + selectedDecision.slice(1) : ''}.
          </div>
          {error && <div style={{ marginTop: 8, color: '#C41E3A', fontSize: 12 }}>{error}</div>}
          <button onClick={handleReset} style={{ marginTop: 12, padding: '10px 20px', borderRadius: 7, border: '1px solid #E2E6EC', fontFamily: 'inherit', fontSize: 13.5, fontWeight: 600, cursor: 'pointer', background: '#fff', color: '#5B6675', width: '100%' }}>
            New decision
          </button>
        </div>
      </div>
    )
  }

  return (
    <div style={{ display: 'grid', gridTemplateColumns: '1.4fr 1fr', gap: 20, marginBottom: 20, alignItems: 'start' }}>
      <div style={{ background: '#fff', border: '1px solid #E2E6EC', borderRadius: 10, padding: 20 }}>
        <p style={{ fontSize: 11.5, fontWeight: 700, textTransform: 'uppercase', letterSpacing: '.06em', color: '#5B6675', margin: '0 0 16px' }}>Reasons (SHAP-derived)</p>
        <p style={{ fontSize: 11, color: '#8A6D1B', margin: '-8px 0 12px', lineHeight: 1.4 }}>SHAP explains the ML model's confidence direction, not the composite score breakdown. The composite score uses fixed weights (40% payment, 25% capacity, 20% longevity, 10% coverage, 5% confidence).</p>
        {reasons.length === 0 && <p style={{ fontSize: 13, color: '#5B6675' }}>No SHAP explanation available.</p>}
        {reasons.map((r, i) => (
          <div key={r.feature_name} style={{ display: 'grid', gridTemplateColumns: '22px 1fr auto', gap: 10, alignItems: 'center', padding: i === 0 ? '0 0 11px' : '11px 0', borderTop: i > 0 ? '1px solid #E2E6EC' : 'none' }}>
            <div style={{
              width: 22, height: 22, borderRadius: '50%', display: 'flex', alignItems: 'center', justifyContent: 'center',
              fontSize: 13, fontWeight: 700, flexShrink: 0,
              background: r.shap_value >= 0 ? '#E8F5EE' : '#FEE8EC',
              color: r.shap_value >= 0 ? '#1B6B3A' : '#C41E3A',
            }}>
              {r.shap_value >= 0 ? '↑' : '↓'}
            </div>
            <div style={{ fontSize: 13, lineHeight: 1.4 }}>{r.business_description}</div>
            <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-end', gap: 4 }}>
              <span style={{
                fontSize: 10, fontWeight: 700, textTransform: 'uppercase', letterSpacing: '.03em',
                padding: '2px 7px', borderRadius: 8,
                background: r.source === 'standard' ? '#EDEDF2' : '#E6EEFA',
                color: r.source === 'standard' ? '#54566B' : '#1B5FA8',
              }}>
                {r.source}
              </span>
                <div style={{ width: 64, height: 4, background: '#E2E6EC', borderRadius: 3, overflow: 'hidden' }}>
                  <div style={{ height: '100%', background: '#C8A951', width: `${Math.min(100, Math.abs(r.shap_value) * 100)}%` }} />
                </div>
            </div>
          </div>
        ))}
      </div>

      <div style={{ background: '#fff', border: '1.5px solid #C8A951', borderRadius: 10, padding: 20 }}>
        <p style={{ fontSize: 11.5, fontWeight: 700, textTransform: 'uppercase', letterSpacing: '.06em', color: '#8A6D1B', margin: '0 0 16px' }}>Underwriter decision</p>
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 8, marginBottom: 14 }}>
          {['accept', 'review', 'reject'].map(dec => (
            <button
              key={dec}
              onClick={() => { setSelectedDecision(dec); setRemarksError(false) }}
              style={{
                padding: '10px 6px', borderRadius: 7, border: '1.5px solid #E2E6EC',
                background: selectedDecision === dec
                  ? (dec === 'accept' ? '#E8F5EE' : dec === 'review' ? '#FEF9ED' : '#FEE8EC')
                  : '#fff',
                fontFamily: 'inherit', fontSize: 12.5, fontWeight: 600, cursor: 'pointer',
                color: selectedDecision === dec
                  ? (dec === 'accept' ? '#1B6B3A' : dec === 'review' ? '#B86B00' : '#C41E3A')
                  : '#5B6675',
                borderColor: selectedDecision === dec
                  ? (dec === 'accept' ? '#1B6B3A' : dec === 'review' ? '#B86B00' : '#C41E3A')
                  : '#E2E6EC',
                textAlign: 'center',
              }}
            >
              {dec.charAt(0).toUpperCase() + dec.slice(1)}
            </button>
          ))}
        </div>
        <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 11.5, fontWeight: 600, textTransform: 'uppercase', letterSpacing: '.05em', color: '#5B6675', marginBottom: 6 }}>
          <span>Remarks</span>
          <span style={{ fontWeight: 500, textTransform: 'none', letterSpacing: 0, color: remarks.length > 900 ? '#C41E3A' : '#5B6675' }}>{remarks.length} / 1000</span>
        </div>
        <textarea
          placeholder="Explain the decision for the audit record…"
          maxLength={1000}
          value={remarks}
          onChange={e => { setRemarks(e.target.value); setRemarksError(false) }}
          disabled={submitting}
          style={{ width: '100%', minHeight: 84, border: remarksError ? '2px solid #C41E3A' : '1px solid #E2E6EC', borderRadius: 7, padding: '10px 12px', fontFamily: 'inherit', fontSize: 13, resize: 'vertical', color: '#1A2430', outline: 'none', boxSizing: 'border-box' }}
        />
        {remarksError && <div style={{ color: '#C41E3A', fontSize: 12, marginTop: 6 }}>Remarks are required before submitting.</div>}
        {error && <div style={{ color: '#C41E3A', fontSize: 12, marginTop: 6 }}>{error}</div>}
        <div style={{ marginTop: 14 }}>
          <button
            onClick={handleSubmit}
            disabled={!selectedDecision || submitting}
            style={{ padding: '10px 20px', borderRadius: 7, border: 'none', fontFamily: 'inherit', fontSize: 13.5, fontWeight: 600, cursor: 'pointer', width: '100%', background: !selectedDecision || submitting ? '#C7CDD6' : '#003D7C', color: '#fff' }}
          >
            {submitting ? 'Submitting...' : 'Submit decision'}
          </button>
        </div>
      </div>
    </div>
  )
}
