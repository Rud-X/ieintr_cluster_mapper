import { SC } from '../lib/constants';

export default function ScoreBar({ label, value }) {
  const p = Math.round(value * 100);
  return (
    <div style={{ marginBottom: 6 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 11, marginBottom: 2 }}>
        <span style={{ color: '#5f6577' }}>{label}</span>
        <span style={{ fontWeight: 600, fontVariantNumeric: 'tabular-nums' }}>{(value * 100).toFixed(1)}%</span>
      </div>
      <div style={{ height: 6, borderRadius: 3, background: '#0f1117', overflow: 'hidden' }}>
        <div style={{ height: '100%', width: `${p}%`, borderRadius: 3, background: SC(value), transition: 'width 0.3s' }} />
      </div>
    </div>
  );
}
