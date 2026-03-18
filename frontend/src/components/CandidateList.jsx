import { SC } from '../lib/constants';

export default function CandidateList({ candidates, flows, cMap, companyName, onSelect }) {
  const inFlows = (fromSid, toSid) => flows.some(f => f.from_stream_id === fromSid && f.to_stream_id === toSid);

  if (candidates.length === 0) {
    return (
      <div style={{ padding: 20, textAlign: 'center', color: '#5f6577', fontSize: 12 }}>
        No candidates match current filters.
      </div>
    );
  }

  return (
    <div style={{ padding: 12 }}>
      {candidates.map((c, i) => {
        const inf = inFlows(c.from_stream_id, c.to_stream_id);
        return (
          <div
            key={i}
            onClick={() => onSelect(c)}
            style={{ padding: '10px 12px', borderRadius: 8, marginBottom: 6, cursor: 'pointer', background: '#181b23', border: '1px solid #2a2e3a', transition: 'border-color 0.15s' }}
            onMouseEnter={e => e.currentTarget.style.borderColor = SC(c.composite_score)}
            onMouseLeave={e => e.currentTarget.style.borderColor = '#2a2e3a'}
          >
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 4 }}>
              <span style={{ fontSize: 13, fontWeight: 600, color: SC(c.composite_score) }}>
                {(c.composite_score * 100).toFixed(0)}%
              </span>
              <div style={{ display: 'flex', gap: 4, alignItems: 'center' }}>
                {inf && <span style={{ fontSize: 9, padding: '1px 6px', borderRadius: 9999, background: '#4ade8022', color: '#4ade80' }}>in flows</span>}
                {c.has_hazardous && <span style={{ fontSize: 10, color: '#f87171' }}>⚠</span>}
              </div>
            </div>
            <div style={{ fontSize: 11 }}>
              <span style={{ color: cMap[c.from_company_id], fontWeight: 500 }}>{companyName(c.from_company_id)}</span>
              <span style={{ color: '#5f6577' }}> → </span>
              <span style={{ color: cMap[c.to_company_id], fontWeight: 500 }}>{companyName(c.to_company_id)}</span>
            </div>
            <div style={{ fontSize: 10, color: '#5f6577', marginTop: 2 }}>
              {c.from_stream_name} → {c.to_stream_name}
            </div>
            <div style={{ fontSize: 10, color: '#5f6577', marginTop: 2 }}>
              {c.shared_components.map(sc => sc.name).join(', ')}
            </div>
          </div>
        );
      })}
    </div>
  );
}
