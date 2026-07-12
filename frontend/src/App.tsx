import { useState, useCallback } from 'react'
import Layout from './components/Layout'
import SearchBar from './components/SearchBar'
import ScoreOverview from './components/ScoreOverview'
import ScoreDetail from './components/ScoreDetail'
import AuditTrail from './components/AuditTrail'
import { fetchScore, NotFoundError, ServiceDegradedError } from './api/client'
import type { AppState, Status } from './types'

const INITIAL: AppState = { status: 'idle', customerId: '', result: null, profile: null, error: null }

export default function App() {
  const [state, setState] = useState<AppState>(INITIAL)
  const [searchId, setSearchId] = useState('')
  const [enableSeasonality, setEnableSeasonality] = useState(false)
  const [activeTab, setActiveTab] = useState('Score lookup')

  const handleSearch = useCallback(async (customerId: string) => {
    if (!customerId.trim()) return
    setState({ status: 'loading', customerId, result: null, profile: null, error: null })
    try {
      const score = await fetchScore(customerId, enableSeasonality)
      const status: Status = score.source === 'cache-fallback' ? 'stale' : 'success'
      setState({ status, customerId, result: score, profile: null, error: null })
    } catch (e) {
      if (e instanceof NotFoundError) {
        setState({ status: 'notFound', customerId, result: null, profile: null, error: e.message })
      } else if (e instanceof ServiceDegradedError) {
        setState({ status: 'serviceDegraded', customerId, result: null, profile: null, error: e.message })
      } else {
        setState({ status: 'error', customerId, result: null, profile: null, error: e instanceof Error ? e.message : 'An unexpected error occurred' })
      }
    }
  }, [enableSeasonality])

  const handleClear = useCallback(() => {
    setState(INITIAL)
    setSearchId('')
  }, [])

  const handleTabChange = useCallback((tab: string) => {
    setActiveTab(tab)
  }, [])

  const { status, customerId, result, error } = state
  const hasResults = result != null && (status === 'success' || status === 'stale')

  return (
    <Layout activeTab={activeTab} onTabChange={handleTabChange} onClear={handleClear}>
      <SearchBar
        customerId={searchId}
        onCustomerIdChange={setSearchId}
        onFetch={() => handleSearch(searchId)}
        onClear={handleClear}
        disabled={status === 'loading'}
        enableSeasonality={enableSeasonality}
        onEnableSeasonalityChange={setEnableSeasonality}
      />

      {status === 'stale' && result?.stale_since && (
        <div style={{ display: 'flex', alignItems: 'center', gap: 10, background: '#FEF9ED', border: '1px solid #F5D98A', color: '#B86B00', padding: '10px 16px', borderRadius: 10, fontSize: 13, fontWeight: 500, marginBottom: 20 }}>
          ⚠ Showing cached result — live scoring service is temporarily unavailable. Data may be up to{' '}
          {(() => {
            const diff = Date.now() - new Date(result.stale_since).getTime()
            const hours = Math.floor(diff / 3600000)
            return `${hours} hour${hours !== 1 ? 's' : ''}`
          })()} old.
        </div>
      )}

      {status === 'loading' && (
        <div style={{ textAlign: 'center', padding: '70px 20px', color: '#5B6675' }}>
          <div style={{ width: 32, height: 32, border: '4px solid #003D7C', borderTopColor: 'transparent', borderRadius: '50%', margin: '0 auto 12px', animation: 'spin 0.8s linear infinite' }} />
          <div style={{ fontSize: 15, fontWeight: 600, color: '#1A2430', marginBottom: 6 }}>Scoring customer {customerId}...</div>
          <div style={{ fontSize: 13 }}>Fetching data from ML service and computing financial health score.</div>
          <style>{'@keyframes spin { to { transform: rotate(360deg) } }'}</style>
        </div>
      )}

      {status === 'idle' && !hasResults && (
        <div style={{ textAlign: 'center', padding: '70px 20px', color: '#5B6675' }}>
          <div style={{ fontSize: 15, fontWeight: 600, color: '#1A2430', marginBottom: 6 }}>No customer loaded</div>
          <div style={{ fontSize: 13 }}>Enter a customer ID above or pick a demo profile to see a score.</div>
        </div>
      )}

      {status === 'notFound' && (
        <div style={{ textAlign: 'center', padding: '70px 20px', color: '#5B6675' }}>
          <div style={{ fontSize: 15, fontWeight: 600, color: '#1A2430', marginBottom: 6 }}>No profile found for "{customerId}"</div>
          <div style={{ fontSize: 13 }}>Try one of the demo customer IDs.</div>
        </div>
      )}

      {status === 'serviceDegraded' && (
        <div style={{ textAlign: 'center', padding: '70px 20px', color: '#5B6675' }}>
          <div style={{ fontSize: 15, fontWeight: 600, color: '#1A2430', marginBottom: 6 }}>Service Unavailable</div>
          <div style={{ fontSize: 13, marginBottom: 16 }}>The scoring service is temporarily unavailable. Please try again.</div>
          <button onClick={() => handleSearch(customerId)} style={{ padding: '10px 20px', borderRadius: 7, border: 'none', fontFamily: 'inherit', fontSize: 13.5, fontWeight: 600, cursor: 'pointer', background: '#003D7C', color: '#fff' }}>
            Retry Now
          </button>
        </div>
      )}

      {status === 'error' && (
        <div style={{ textAlign: 'center', padding: '70px 20px', color: '#5B6675' }}>
          <div style={{ fontSize: 15, fontWeight: 600, color: '#1A2430', marginBottom: 6 }}>Something went wrong</div>
          <div style={{ fontSize: 13, marginBottom: 16 }}>{error}</div>
          <button onClick={() => handleSearch(customerId)} style={{ padding: '10px 20px', borderRadius: 7, border: 'none', fontFamily: 'inherit', fontSize: 13.5, fontWeight: 600, cursor: 'pointer', background: '#003D7C', color: '#fff' }}>
            Try Again
          </button>
        </div>
      )}

      {hasResults && result && (
        <>
          <ScoreOverview result={result} />
          <ScoreDetail result={result} customerId={customerId} />
          <AuditTrail customerId={customerId} />
        </>
      )}
    </Layout>
  )
}
