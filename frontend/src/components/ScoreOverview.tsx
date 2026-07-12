import type { ScoreResponse } from '../types'
import { BUCKET_COLORS, FLAG_STYLE } from '../types'

interface ScoreOverviewProps {
  result: ScoreResponse
}

function formatLoan(amount: number | null): string {
  if (amount == null) return '—'
  return '₹' + amount.toLocaleString('en-IN')
}

function formatConfidence(prob: number): number {
  return Math.round(prob * 100)
}

function formatScore(score: number): number {
  return Math.round(Math.min(1, Math.max(0, score)) * 100)
}

export default function ScoreOverview({ result }: ScoreOverviewProps) {
  const cfg = BUCKET_COLORS[result.bucket] || BUCKET_COLORS['no-to-go']
  const score = formatScore(result.composite_score)
  const confidence = formatConfidence(result.probability)
  const circumference = 301.6
  const fill = (score / 100 * circumference).toFixed(1)
  const gap = (circumference - score / 100 * circumference).toFixed(1)
  const capFlag = result.flags.capacity_flag
  const epfoFlag = result.flags.epfo_plausibility

  const f = result.features || {} as Record<string, number>
  const factors = [
    { name: 'Payment regularity', val: f.payment_regularity?.toFixed(2) ?? '—', pct: Math.min(100, Math.round((f.payment_regularity ?? 0) * 100)) },
    { name: 'Financial capacity', val: f.financial_capacity_proxy?.toFixed(2) ?? '—', pct: Math.min(100, Math.round((f.financial_capacity_proxy ?? 0) * 100)) },
    { name: 'Business longevity', val: f.business_longevity?.toFixed(2) ?? '—', pct: Math.min(100, Math.round((f.business_longevity ?? 0) * 100)) },
    { name: 'Data coverage', val: f.data_coverage?.toFixed(2) ?? '—', pct: Math.min(100, Math.round((f.data_coverage ?? 0) * 100)) },
    { name: 'Evidence confidence', val: f.evidence_confidence?.toFixed(2) ?? '—', pct: Math.min(100, Math.round((f.evidence_confidence ?? 0) * 100)) },
  ]

  return (
    <div style={{ display: 'grid', gridTemplateColumns: '1fr 1.1fr 1fr', gap: 20, marginBottom: 20 }}>
      <div style={{ background: '#fff', border: '1px solid #E2E6EC', borderRadius: 10, padding: 20 }}>
        <p style={{ fontSize: 11.5, fontWeight: 700, textTransform: 'uppercase', letterSpacing: '.06em', color: '#5B6675', margin: '0 0 16px' }}>Customer</p>
        <p style={{ fontSize: 17, fontWeight: 600, margin: '0 0 4px' }}>{result.business_name || '—'}</p>
        <p style={{ fontSize: 13, color: '#5B6675', margin: '0 0 14px' }}>{result.customerId} · {result.business_type || '—'}</p>
        {result.flags.is_blank_slate && (
          <span style={{ display: 'inline-block', fontSize: 11, fontWeight: 600, padding: '3px 10px', borderRadius: 12, background: '#F5EDD0', color: '#8A6D1B', border: '1px solid #C8A951', marginBottom: 12 }}>
            Blank-slate applicant
          </span>
        )}
        <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 13, padding: '8px 0', borderTop: '1px solid #E2E6EC' }}>
          <span style={{ color: '#5B6675' }}>Business type</span>
          <span style={{ fontWeight: 600 }}>{result.business_type || '—'}</span>
        </div>
        <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 13, padding: '8px 0', borderTop: '1px solid #E2E6EC' }}>
          <span style={{ color: '#5B6675' }}>State</span>
          <span style={{ fontWeight: 600 }}>{result.state || '—'}</span>
        </div>
        <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 13, padding: '8px 0', borderTop: '1px solid #E2E6EC' }}>
          <span style={{ color: '#5B6675' }}>Loan requested</span>
          <span style={{ fontWeight: 600 }}>{formatLoan(result.requested_loan_amount)}</span>
        </div>
      </div>

      <div style={{ background: '#fff', border: '1px solid #E2E6EC', borderRadius: 10, padding: 20, display: 'flex', flexDirection: 'column', alignItems: 'center', textAlign: 'center' }}>
        <p style={{ fontSize: 11.5, fontWeight: 700, textTransform: 'uppercase', letterSpacing: '.06em', color: '#5B6675', margin: '0 0 16px', alignSelf: 'flex-start' }}>Score</p>
        <div style={{ position: 'relative', width: 150, height: 150, margin: '4px 0 14px' }}>
          <svg width="150" height="150" viewBox="0 0 110 110" style={{ transform: 'rotate(-90deg)' }}>
            <circle cx="55" cy="55" r="48" fill="none" stroke="#EDEFF3" strokeWidth="9" />
            <circle cx="55" cy="55" r="48" fill="none" stroke={cfg.color} strokeWidth="9" strokeLinecap="round" strokeDasharray={`${fill} ${gap}`} />
          </svg>
          <div style={{ position: 'absolute', inset: 0, display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center' }}>
            <div style={{ fontSize: 34, fontWeight: 700, lineHeight: 1, color: cfg.color }}>{score}</div>
            <div style={{ fontSize: 11, color: '#5B6675', marginTop: 2 }}>/ 100</div>
          </div>
        </div>
        <div style={{ fontSize: 13, fontWeight: 700, padding: '6px 18px', borderRadius: 20, background: cfg.bg, color: cfg.color, border: `1px solid ${cfg.border}`, marginBottom: 14 }}>{cfg.label}</div>
        <div style={{ width: '100%' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 11.5, color: '#5B6675', marginBottom: 5 }}>
            <span>Model confidence</span>
            <span>{confidence}%</span>
          </div>
          <div style={{ width: '100%', height: 6, background: '#E2E6EC', borderRadius: 4, overflow: 'hidden' }}>
            <div style={{ height: '100%', borderRadius: 4, background: cfg.color, width: `${confidence}%` }} />
          </div>
        </div>
        <div style={{ fontSize: 12, color: '#5B6675', marginTop: 14, lineHeight: 1.5, borderTop: '1px solid #E2E6EC', paddingTop: 12 }}>
          {(() => {
            const coverage = Object.values(result.features || {}).filter(v => v > 0).length
            const total = Object.keys(result.features || {}).length
            const pct = total > 0 ? Math.round(coverage / total * 100) : 0
            if (result.flags.is_blank_slate) {
              return `Blank-slate — GST/UPI below threshold. ${coverage}/${total} signals active (${pct}% feature coverage). Score derived from alternative data.`
            }
            return `Full-data — ${coverage}/${total} signals active (${pct}% feature coverage). Mix of traditional and alternative data.`
          })()}
        </div>
      </div>

      <div style={{ background: '#fff', border: '1px solid #E2E6EC', borderRadius: 10, padding: 20 }}>
        <p style={{ fontSize: 11.5, fontWeight: 700, textTransform: 'uppercase', letterSpacing: '.06em', color: '#5B6675', margin: '0 0 16px' }}>Key factors</p>
        {factors.map((f, i) => (
          <div key={i} style={{ marginBottom: i < factors.length - 1 ? 14 : 0 }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 12.5, marginBottom: 5 }}>
              <span style={{ color: '#1A2430', fontWeight: 500 }}>{f.name}</span>
              <span style={{ color: '#5B6675' }}>{f.val}</span>
            </div>
            <div style={{ width: '100%', height: 6, background: '#E2E6EC', borderRadius: 4, overflow: 'hidden' }}>
              <div style={{ height: '100%', borderRadius: 4, background: '#1B5FA8', width: `${f.pct}%` }} />
            </div>
          </div>
        ))}
        <div style={{ marginTop: 16, paddingTop: 14, borderTop: '1px solid #E2E6EC', display: 'flex', flexDirection: 'column', gap: 8 }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', fontSize: 12.5 }}>
            <span style={{ color: '#5B6675' }}>Loan-to-capacity</span>
            <span style={{
              fontSize: 11, fontWeight: 700, padding: '2px 9px', borderRadius: 10,
              background: (FLAG_STYLE[capFlag.flag] || FLAG_STYLE.unavailable).bg,
              color: (FLAG_STYLE[capFlag.flag] || FLAG_STYLE.unavailable).color,
            }}>
              {(FLAG_STYLE[capFlag.flag] || FLAG_STYLE.unavailable).label}
            </span>
          </div>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', fontSize: 12.5 }}>
            <span style={{ color: '#5B6675' }}>EPFO plausibility</span>
            <span style={{
              fontSize: 11, fontWeight: 700, padding: '2px 9px', borderRadius: 10,
              background: (FLAG_STYLE[epfoFlag.flag] || FLAG_STYLE.unavailable).bg,
              color: (FLAG_STYLE[epfoFlag.flag] || FLAG_STYLE.unavailable).color,
            }}>
              {(FLAG_STYLE[epfoFlag.flag] || FLAG_STYLE.unavailable).label}
            </span>
          </div>
          {result.seasonality_adjustment?.enabled && result.seasonality_adjustment.seasonality_adjusted_score != null && (
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', fontSize: 12.5, borderTop: '1px solid #E2E6EC', paddingTop: 8 }}>
              <span style={{ color: '#5B6675' }}>Seasonality adj.</span>
              <span style={{ fontSize: 11, fontWeight: 700, padding: '2px 9px', borderRadius: 10, background: '#FEF9ED', color: '#B86B00' }}>
                {result.seasonality_adjustment.cap_applied ? 'Capped' : 'Applied'}
              </span>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
