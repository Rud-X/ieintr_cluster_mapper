import { useState, useMemo } from 'react'
import { Routes, Route, useNavigate, useLocation, Navigate } from 'react-router-dom'
import SplitPanel from './components/layout/SplitPanel'
import LeftPanel from './components/layout/LeftPanel'
import DetailPanel from './components/layout/DetailPanel'
import CompaniesTable from './components/table/CompaniesTable'
import FlowsTable from './components/table/FlowsTable'
import StreamsTable from './components/table/StreamsTable'
import ComponentsTable from './components/table/ComponentsTable'
import { useCompanies } from './hooks/useCompanies'
import CompanyDetail from './components/detail/CompanyDetail'
import FlowDetail from './components/detail/FlowDetail'
import StreamDetail from './components/detail/StreamDetail'
import ComponentDetail from './components/detail/ComponentDetail'
import CarbonFAB from './components/co2/CarbonFAB'
import CarbonPanel from './components/co2/CarbonPanel'
import ClusterGraph from './components/graph/ClusterGraph'
import ThemeFAB from './components/theme/ThemeFAB'
import { ThemeProvider } from './lib/ThemeContext'

function AppShell() {
  const navigate = useNavigate()
  const location = useLocation()
  const [view, setView] = useState('table')
  const [carbonOpen, setCarbonOpen] = useState(false)
  const [onlyIncluded, setOnlyIncluded] = useState(false)

  const { companies, loading: companiesLoading, error: companiesError, toggleIncluded } = useCompanies()
  const includedIds = useMemo(
    () => new Set(companies.filter(c => c.included).map(c => c.company_id)),
    [companies]
  )

  // Derive active tab from URL
  const pathSegments = location.pathname.split('/').filter(Boolean)
  const pathRoot = pathSegments[0] || 'companies'
  const tabMap = { companies: 'Companies', flows: 'Flows', streams: 'Streams', components: 'Components' }
  const tab = tabMap[pathRoot] || 'Companies'
  const hasDetail = pathSegments.length >= 2

  const handleTabChange = (newTab) => {
    navigate('/' + newTab.toLowerCase())
  }

  const handleViewChange = (newView) => {
    setView(newView)
    // When switching to table, ensure URL reflects current tab so the right table loads
    if (newView === 'table' && location.pathname === '/') {
      navigate('/companies')
    }
  }

  return (
    <div style={{ position: 'relative', height: '100vh', overflow: 'hidden' }}>
      <SplitPanel
        showRight={hasDetail}
        left={
          <LeftPanel view={view} onViewChange={handleViewChange} tab={tab} onTabChange={handleTabChange}
          onlyIncluded={onlyIncluded} onToggleIncluded={() => setOnlyIncluded(v => !v)}>
            {view === 'graph' ? (
              <ClusterGraph />
            ) : (
              <Routes>
                <Route path="/companies/*" element={
                  <CompaniesTable
                    companies={companies} loading={companiesLoading} error={companiesError}
                    toggleIncluded={toggleIncluded}
                    onlyIncluded={onlyIncluded} includedIds={includedIds}
                  />
                } />
                <Route path="/flows/*" element={<FlowsTable onlyIncluded={onlyIncluded} includedIds={includedIds} />} />
                <Route path="/streams/*" element={<StreamsTable onlyIncluded={onlyIncluded} includedIds={includedIds} />} />
                <Route path="/components/*" element={<ComponentsTable />} />
                <Route path="*" element={<Navigate to="/companies" replace />} />
              </Routes>
            )}
          </LeftPanel>
        }
        right={hasDetail ? (
          <DetailPanel onClose={() => navigate('/' + pathRoot)}>
            <Routes>
              <Route path="/companies/:id" element={<CompanyDetail />} />
              <Route path="/flows/:id" element={<FlowDetail />} />
              <Route path="/streams/:id" element={<StreamDetail />} />
              <Route path="/components/:id" element={<ComponentDetail />} />
            </Routes>
          </DetailPanel>
        ) : null}
      />
      <ThemeFAB />
      <CarbonFAB onClick={() => setCarbonOpen(o => !o)} />
      {carbonOpen && <CarbonPanel onClose={() => setCarbonOpen(false)} />}
    </div>
  )
}

export default function App() {
  return (
    <ThemeProvider>
      <Routes>
        <Route path="/*" element={<AppShell />} />
      </Routes>
    </ThemeProvider>
  )
}
