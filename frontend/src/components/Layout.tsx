import type { ReactNode } from 'react'

interface LayoutProps {
  children: ReactNode
  activeTab: string
  onTabChange: (tab: string) => void
  onClear: () => void
}

export default function Layout({ children, activeTab, onTabChange, onClear }: LayoutProps) {
  const tabs = ['Score lookup', 'Audit log', 'Pending review', 'Reports']

  return (
    <div className="min-h-screen flex flex-col" style={{ background: '#F4F6F9' }}>
      <div style={{ background: '#002856', color: '#CFE0F5', fontSize: 12, padding: '7px 28px', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <b style={{ color: '#fff', fontWeight: 600 }}>Financial Health Score</b>
          <span style={{ width: 5, height: 5, borderRadius: '50%', background: '#C8A951', display: 'inline-block' }} />
          Team DistributedMinds
          <span style={{ width: 5, height: 5, borderRadius: '50%', background: '#C8A951', display: 'inline-block' }} />
          IDBI Innovate 2026 · Track 03
        </div>
        <div style={{ color: '#9FB6D6' }}>Submitted · Jul 9, 2026</div>
      </div>

      <div style={{ background: '#003D7C', color: '#fff', padding: '14px 28px', display: 'grid', gridTemplateColumns: 'auto 1fr auto auto', alignItems: 'center', gap: 20 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
          <div style={{ width: 38, height: 38, borderRadius: 8, background: '#fff', display: 'flex', alignItems: 'center', justifyContent: 'center', fontWeight: 700, color: '#003D7C', fontSize: 14, flexShrink: 0 }}>IDBI</div>
          <div>
            <div style={{ fontWeight: 600, fontSize: 16, lineHeight: 1.2 }}>IDBI Bank</div>
            <div style={{ fontSize: 12, color: '#B9CDE8', lineHeight: 1.2 }}>Credit Operations</div>
          </div>
        </div>
        <div style={{ fontSize: 15, fontWeight: 500, color: '#DCE7F7' }}>Underwriter Console</div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 6, background: 'rgba(200,169,81,.16)', border: '1px solid #C8A951', color: '#C8A951', padding: '6px 12px', borderRadius: 20, fontSize: 12, fontWeight: 600, letterSpacing: '.02em' }}>
          <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M12 2 L14 9 L21 12 L14 15 L12 22 L10 15 L3 12 L10 9 Z" /></svg>
          AI-Assisted Scoring
        </div>
        <div style={{ width: 34, height: 34, borderRadius: '50%', background: '#002856', border: '1px solid rgba(255,255,255,.3)', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 12, fontWeight: 600 }}>RS</div>
      </div>

      <div style={{ background: '#002856', display: 'flex', gap: 4, padding: '0 24px' }}>
        {tabs.map(tab => (
          <button
            key={tab}
            onClick={() => {
              onTabChange(tab)
              if (tab !== 'Score lookup') {
                onClear()
              }
            }}
            style={{
              background: 'none', border: 'none', fontFamily: 'inherit',
              fontSize: 13.5, fontWeight: 500, padding: '12px 16px', cursor: 'pointer',
              borderBottom: activeTab === tab ? '2.5px solid #C8A951' : '2.5px solid transparent',
              color: activeTab === tab ? '#fff' : '#AFC3DE',
              transition: '.15s',
            }}
          >
            {tab}
          </button>
        ))}
      </div>

      <main style={{ maxWidth: 1180, margin: '0 auto', padding: '24px 24px 60px', width: '100%' }}>
        {children}
      </main>
    </div>
  )
}
