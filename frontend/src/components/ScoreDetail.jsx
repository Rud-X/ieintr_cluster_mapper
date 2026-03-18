import ScoreBar from './ScoreBar';
import { SC, SL } from '../lib/constants';

export default function ScoreDetail({ r, children }) {
  return (
    <>
      <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 12 }}>
        <span style={{ fontSize: 22, fontWeight: 700, color: SC(r.composite_score) }}>
          {(r.composite_score * 100).toFixed(0)}%
        </span>
        <span style={{ fontSize: 12, padding: '2px 8px', borderRadius: 9999, background: SC(r.composite_score) + '22', color: SC(r.composite_score), fontWeight: 600 }}>
          {SL(r.composite_score)}
        </span>
        {r.has_hazardous && (
          <span style={{ fontSize: 11, padding: '2px 6px', borderRadius: 4, background: '#f871711a', color: '#f87171', fontWeight: 600 }}>
            HAZARDOUS
          </span>
        )}
      </div>

      <ScoreBar label="Component Overlap"   value={r.component_overlap} />
      <ScoreBar label="Fraction Similarity" value={r.fraction_similarity} />
      <ScoreBar label="Flow Compatibility"  value={r.flow_compatibility} />
      <ScoreBar label="Temperature Match"   value={r.temperature_proximity} />
      <ScoreBar label="Pressure Match"      value={r.pressure_proximity} />

      {(r.shared_components || []).length > 0 && (
        <div style={{ marginTop: 10 }}>
          <div style={{ fontSize: 11, color: '#5f6577', textTransform: 'uppercase', letterSpacing: 1, marginBottom: 4 }}>
            Shared Components
          </div>
          {r.shared_components.map((sc, i) => (
            <div key={i} style={{ display: 'flex', justifyContent: 'space-between', padding: '3px 0', borderBottom: '1px solid #2a2e3a', fontSize: 12 }}>
              <span>
                {sc.name}
                {sc.hazardous === 1 && <span style={{ color: '#f87171', marginLeft: 4 }}>⚠</span>}
              </span>
              <span style={{ color: '#5f6577', fontVariantNumeric: 'tabular-nums' }}>
                {((sc.fraction_out || 0) * 100).toFixed(1)}% → {((sc.fraction_in || 0) * 100).toFixed(1)}%
              </span>
            </div>
          ))}
        </div>
      )}

      {children}
    </>
  );
}
