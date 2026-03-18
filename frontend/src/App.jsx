import { useState, useEffect, useRef, useCallback, useMemo } from 'react';
import { COLORS } from './lib/constants';
import { fetchData, updateCompany, createFlow, updateFlow, deleteFlow } from './lib/api';

import ForceGraph      from './components/ForceGraph';
import CandidateList   from './components/CandidateList';
import CandidateDetail from './components/CandidateDetail';
import ManualPairing   from './components/ManualPairing';
import FlowsManager    from './components/FlowsManager';

export default function App() {
  // ── Remote data ────────────────────────────────────────────────────────────
  const [data,    setData]    = useState(null);
  const [loading, setLoading] = useState(true);
  const [error,   setError]   = useState(null);

  // ── UI state ───────────────────────────────────────────────────────────────
  const [companies, setCompanies] = useState([]);
  const [flows,     setFlows]     = useState([]);
  const [sel,  setSel]  = useState(null);
  const [tab,  setTab]  = useState('candidates');
  const [sf,   setSf]   = useState(0.15);

  const scaleTimers = useRef({});

  // ── Bootstrap ──────────────────────────────────────────────────────────────
  useEffect(() => {
    fetchData()
      .then(d => {
        setData(d);
        setCompanies(d.companies);
        setFlows(d.flows);
        setLoading(false);
      })
      .catch(e => { setError(e.message); setLoading(false); });
  }, []);

  // ── Derived ────────────────────────────────────────────────────────────────
  const active = useMemo(
    () => new Set(companies.filter(c => c.included === 1).map(c => c.company_id)),
    [companies],
  );

  const scales = useMemo(() => {
    const m = {};
    companies.forEach(c => { m[c.company_id] = c.scaling_factor ?? 1; });
    return m;
  }, [companies]);

  const cMap = useMemo(() => {
    if (!data) return {};
    const m = {};
    data.companies.forEach((c, i) => { m[c.company_id] = COLORS[i % COLORS.length]; });
    return m;
  }, [data]);

  const fCands = useMemo(() => {
    if (!data) return [];
    return data.candidates
      .filter(c => active.has(c.from_company_id) && active.has(c.to_company_id))
      .filter(c => c.composite_score >= sf)
      .sort((a, b) => b.composite_score - a.composite_score);
  }, [data, active, sf]);

  const companyName = useCallback(
    (id) => companies.find(c => c.company_id === id)?.name || id,
    [companies],
  );

  const cc = flows.filter(f => f.status === 'confirmed').length;

  // ── Company mutations ──────────────────────────────────────────────────────
  const toggle = useCallback((id) => {
    setCompanies(prev => {
      const next = prev.map(c => c.company_id === id ? { ...c, included: c.included === 1 ? 0 : 1 } : c);
      const co = next.find(c => c.company_id === id);
      updateCompany(id, { included: co.included }).catch(console.error);
      return next;
    });
  }, []);

  const setScale = useCallback((id, value) => {
    setCompanies(prev => prev.map(c => c.company_id === id ? { ...c, scaling_factor: value } : c));
    clearTimeout(scaleTimers.current[id]);
    scaleTimers.current[id] = setTimeout(() => {
      updateCompany(id, { scaling_factor: value }).catch(console.error);
    }, 300);
  }, []);

  const resetScales = useCallback(() => {
    setCompanies(prev => {
      prev.forEach(c => {
        if ((c.scaling_factor ?? 1) !== 1) {
          clearTimeout(scaleTimers.current[c.company_id]);
          scaleTimers.current[c.company_id] = setTimeout(() => {
            updateCompany(c.company_id, { scaling_factor: 1.0 }).catch(console.error);
          }, 300);
        }
      });
      return prev.map(c => ({ ...c, scaling_factor: 1.0 }));
    });
  }, []);

  const setAllIncluded = useCallback((val) => {
    setCompanies(prev => {
      const next = prev.map(c => ({ ...c, included: val }));
      next.forEach(c => updateCompany(c.company_id, { included: val }).catch(console.error));
      return next;
    });
  }, []);

  // ── Flow mutations ─────────────────────────────────────────────────────────
  const addFlow = useCallback(async (fd) => {
    try {
      const created = await createFlow({
        from_company_id:    fd.from_company_id,
        to_company_id:      fd.to_company_id,
        from_stream_id:     fd.from_stream_id,
        to_stream_id:       fd.to_stream_id,
        flow_kton_per_year: fd.flow_kton_per_year,
        status: 'candidate',
        notes: '',
      });
      setFlows(prev => [...prev, {
        ...created,
        from_stream_name: fd.from_stream_name,
        to_stream_name:   fd.to_stream_name,
        composite_score:  fd.composite_score,
      }]);
      setTab('flows');
    } catch (e) { console.error('addFlow:', e); }
  }, []);

  const handleUpdateFlow = useCallback(async (id, updates) => {
    try {
      const updated = await updateFlow(id, updates);
      setFlows(prev => prev.map(f => f.flow_id === id ? { ...f, ...updated } : f));
    } catch (e) { console.error('updateFlow:', e); }
  }, []);

  const handleRemoveFlow = useCallback(async (id) => {
    try {
      await deleteFlow(id);
      setFlows(prev => prev.filter(f => f.flow_id !== id));
    } catch (e) { console.error('deleteFlow:', e); }
  }, []);

  const exportFlows = useCallback(() => {
    const b = new Blob([JSON.stringify(flows, null, 2)], { type: 'application/json' });
    const u = URL.createObjectURL(b);
    const a = document.createElement('a');
    a.href = u; a.download = 'flows_export.json'; a.click();
    URL.revokeObjectURL(u);
  }, [flows]);

  // ── Loading / error screens ────────────────────────────────────────────────
  if (loading) return (
    <div style={{ background: '#0f1117', color: '#5f6577', height: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center', fontFamily: "'JetBrains Mono',monospace", fontSize: 13 }}>
      Loading cluster data...
    </div>
  );
  if (error) return (
    <div style={{ background: '#0f1117', color: '#f87171', height: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center', fontFamily: "'JetBrains Mono',monospace", fontSize: 13 }}>
      Error: {error}
    </div>
  );

  // ── Main render ────────────────────────────────────────────────────────────
  return (
    <div style={{ background: '#0f1117', color: '#e8eaed', fontFamily: "'JetBrains Mono','SF Mono','Fira Code',monospace", height: '100vh', display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>

      {/* ── Header ── */}
      <div style={{ padding: '12px 20px', borderBottom: '1px solid #2a2e3a', display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexShrink: 0 }}>
        <div>
          <h1 style={{ margin: 0, fontSize: 16, fontWeight: 700, letterSpacing: -0.3 }}>SYMBIOSIS MATCHER</h1>
          <span style={{ fontSize: 11, color: '#5f6577' }}>
            {data.metadata.total_companies} companies · {fCands.length} candidates · {cc} confirmed flow{cc !== 1 ? 's' : ''}
          </span>
        </div>
        <div style={{ display: 'flex', gap: 6, alignItems: 'center' }}>
          <span style={{ fontSize: 10, color: '#5f6577', marginRight: 4 }}>MIN SCORE</span>
          <input type="range" min="0" max="0.9" step="0.05" value={sf} onChange={e => setSf(parseFloat(e.target.value))} style={{ width: 80, accentColor: '#5B9BD5' }} />
          <span style={{ fontSize: 11, fontVariantNumeric: 'tabular-nums', width: 32 }}>{(sf * 100).toFixed(0)}%</span>
        </div>
      </div>

      {/* ── Body ── */}
      <div style={{ flex: 1, display: 'flex', overflow: 'hidden' }}>

        {/* Left — Companies */}
        <div style={{ width: 200, borderRight: '1px solid #2a2e3a', flexShrink: 0, display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
          <div style={{ padding: '10px 12px', borderBottom: '1px solid #2a2e3a', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <span style={{ fontSize: 10, color: '#5f6577', textTransform: 'uppercase', letterSpacing: 1, fontWeight: 600 }}>Companies</span>
            <div style={{ display: 'flex', gap: 4 }}>
              <button onClick={() => setAllIncluded(1)}   style={{ fontSize: 10, background: 'none', border: 'none', color: '#5B9BD5', cursor: 'pointer', padding: '2px 4px', fontFamily: 'inherit' }}>All</button>
              <button onClick={() => setAllIncluded(0)}   style={{ fontSize: 10, background: 'none', border: 'none', color: '#5f6577', cursor: 'pointer', padding: '2px 4px', fontFamily: 'inherit' }}>None</button>
              <button onClick={resetScales} style={{ fontSize: 10, background: 'none', border: 'none', color: '#5f6577', cursor: 'pointer', padding: '2px 4px', fontFamily: 'inherit' }}>×1</button>
            </div>
          </div>

          <div style={{ flex: 1, overflow: 'auto', padding: '6px 0' }}>
            {companies.map(c => (
              <div key={c.company_id} style={{ padding: '7px 12px', transition: 'background 0.1s', background: active.has(c.company_id) ? '#181b23' : 'transparent', opacity: active.has(c.company_id) ? 1 : 0.4 }}>
                <div onClick={() => toggle(c.company_id)} style={{ display: 'flex', alignItems: 'center', gap: 8, cursor: 'pointer' }}>
                  <div style={{ width: 10, height: 10, borderRadius: '50%', background: active.has(c.company_id) ? cMap[c.company_id] : '#2a2e3a', flexShrink: 0 }} />
                  <div>
                    <div style={{ fontSize: 12, fontWeight: 500 }}>{c.name}</div>
                    <div style={{ fontSize: 10, color: '#5f6577' }}>{c.sector || c.company_id}</div>
                  </div>
                </div>
                {active.has(c.company_id) && (
                  <div style={{ marginTop: 4, marginLeft: 18, display: 'flex', alignItems: 'center', gap: 4 }} onClick={e => e.stopPropagation()}>
                    <span style={{ fontSize: 9, color: '#5f6577', width: 14, textAlign: 'right', flexShrink: 0 }}>×</span>
                    <input
                      type="range" min="0.1" max="5" step="0.05"
                      value={c.scaling_factor ?? 1}
                      onChange={e => setScale(c.company_id, parseFloat(e.target.value))}
                      style={{ width: 80, accentColor: cMap[c.company_id], height: 12 }}
                    />
                    <span style={{ fontSize: 10, fontVariantNumeric: 'tabular-nums', width: 32, color: (c.scaling_factor ?? 1) !== 1 ? '#e8eaed' : '#5f6577', fontWeight: (c.scaling_factor ?? 1) !== 1 ? 600 : 400 }}>
                      {(c.scaling_factor ?? 1).toFixed(2)}
                    </span>
                    {(c.scaling_factor ?? 1) !== 1 && (
                      <button onClick={() => setScale(c.company_id, 1)} style={{ fontSize: 8, background: 'none', border: '1px solid #2a2e3a', color: '#5f6577', borderRadius: 3, cursor: 'pointer', padding: '1px 4px', fontFamily: 'inherit', lineHeight: 1 }}>↺</button>
                    )}
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>

        {/* Center — Graph */}
        <div style={{ flex: 1, position: 'relative', background: '#0f1117' }}>
          <ForceGraph
            companies={companies}
            candidates={fCands}
            flows={flows}
            active={active}
            cMap={cMap}
            onEdge={e => { setSel(e); setTab('candidates'); }}
          />
          <div style={{ position: 'absolute', bottom: 12, left: 12, display: 'flex', gap: 10, fontSize: 10, color: '#5f6577' }}>
            {[{ c: '#4ade80', l: 'Confirmed' }, { c: '#facc15', l: '>50%' }, { c: '#fb923c', l: '>30%' }, { c: '#f87171', l: '<30%' }].map(x => (
              <div key={x.l} style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
                <div style={{ width: 14, height: x.l === 'Confirmed' ? 4 : 2, borderRadius: 2, background: x.c }} />
                {x.l}
              </div>
            ))}
            <div style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
              <div style={{ width: 14, height: 0, borderTop: '2px dashed #5f6577' }} /> Candidate
            </div>
          </div>
        </div>

        {/* Right — Tabs */}
        <div style={{ width: 340, borderLeft: '1px solid #2a2e3a', flexShrink: 0, display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
          <div style={{ display: 'flex', borderBottom: '1px solid #2a2e3a', flexShrink: 0 }}>
            {[['candidates', 'Candidates'], ['manual', 'Manual Pair'], ['flows', `Flows (${flows.length})`]].map(([k, l]) => (
              <button key={k} onClick={() => { setTab(k); setSel(null); }} style={{ flex: 1, padding: '10px 0', fontSize: 11, fontWeight: 600, background: 'none', border: 'none', cursor: 'pointer', color: tab === k ? '#5B9BD5' : '#5f6577', borderBottom: tab === k ? '2px solid #5B9BD5' : '2px solid transparent', fontFamily: 'inherit' }}>
                {l}
              </button>
            ))}
          </div>

          <div style={{ flex: 1, overflow: 'auto' }}>
            {tab === 'candidates' && !sel && (
              <CandidateList
                candidates={fCands}
                flows={flows}
                cMap={cMap}
                companyName={companyName}
                onSelect={setSel}
              />
            )}
            {tab === 'candidates' && sel && (
              <CandidateDetail
                sel={sel}
                streams={data.streams}
                companies={companies}
                flows={flows}
                scales={scales}
                companyName={companyName}
                setScale={setScale}
                addFlow={addFlow}
                onBack={() => setSel(null)}
              />
            )}

            {tab === 'manual' && (
              <ManualPairing
                streams={data.streams}
                companies={companies}
                active={active}
                flows={flows}
                companyName={companyName}
                addFlow={addFlow}
              />
            )}

            {tab === 'flows' && (
              <FlowsManager
                flows={flows}
                companies={companies}
                onUpdate={handleUpdateFlow}
                onRemove={handleRemoveFlow}
                onExport={exportFlows}
              />
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
