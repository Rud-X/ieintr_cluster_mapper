import { useState } from 'react';
import { SS } from '../lib/constants';

const cycle = { candidate: 'confirmed', confirmed: 'rejected', rejected: 'candidate' };

export default function FlowsManager({ flows, companies, onUpdate, onRemove, onExport }) {
  const [editId, setEditId] = useState(null);
  const [note,   setNote]   = useState('');

  const cn = id => companies.find(c => c.company_id === id)?.name || id;

  const ct = {
    candidate: flows.filter(f => f.status === 'candidate').length,
    confirmed:  flows.filter(f => f.status === 'confirmed').length,
    rejected:   flows.filter(f => f.status === 'rejected').length,
  };

  return (
    <div style={{ padding: 12 }}>
      {/* Summary bar */}
      <div style={{ display: 'flex', gap: 8, marginBottom: 12, flexWrap: 'wrap' }}>
        {['candidate', 'confirmed', 'rejected'].map(s => (
          <div key={s} style={{ padding: '4px 10px', borderRadius: 6, background: SS[s].bg, color: SS[s].c, fontSize: 11, fontWeight: 600 }}>
            {ct[s]} {SS[s].l}
          </div>
        ))}
      </div>

      {flows.length === 0 && (
        <div style={{ padding: 24, textAlign: 'center', color: '#5f6577', fontSize: 12, lineHeight: 1.6 }}>
          No flows yet. Add stream pairs from the Candidates or Manual Pair tabs.
        </div>
      )}

      {flows.map(f => {
        const s = SS[f.status];
        return (
          <div
            key={f.flow_id}
            style={{
              padding: 12, borderRadius: 8, marginBottom: 8, background: '#181b23',
              border: `1px solid ${f.status === 'confirmed' ? '#4ade8044' : f.status === 'rejected' ? '#f8717133' : '#2a2e3a'}`,
            }}
          >
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'start', marginBottom: 6 }}>
              <div style={{ flex: 1 }}>
                <div style={{ fontSize: 11, fontWeight: 600 }}>
                  <span>{cn(f.from_company_id)}</span>
                  <span style={{ color: '#5f6577' }}> → </span>
                  <span>{cn(f.to_company_id)}</span>
                </div>
                <div style={{ fontSize: 10, color: '#9aa0ad', marginTop: 2 }}>
                  {f.from_stream_name} → {f.to_stream_name}
                </div>
                <div style={{ fontSize: 10, color: '#5f6577', marginTop: 2 }}>
                  {f.flow_kton_per_year} kt/yr · Score: {((f.composite_score || 0) * 100).toFixed(0)}%
                </div>
              </div>
              <div style={{ display: 'flex', gap: 4, alignItems: 'center', flexShrink: 0 }}>
                <button
                  onClick={() => onUpdate(f.flow_id, { status: cycle[f.status] })}
                  title={`Click → ${SS[cycle[f.status]].l}`}
                  style={{ padding: '3px 10px', borderRadius: 9999, border: 'none', background: s.bg, color: s.c, fontSize: 10, fontWeight: 600, cursor: 'pointer', fontFamily: 'inherit' }}
                >
                  {s.l}
                </button>
                <button
                  onClick={() => onRemove(f.flow_id)}
                  title="Remove"
                  style={{ padding: '3px 8px', borderRadius: 6, border: 'none', background: '#f871711a', color: '#f87171', fontSize: 10, cursor: 'pointer', fontFamily: 'inherit' }}
                >
                  ✕
                </button>
              </div>
            </div>

            {editId === f.flow_id ? (
              <div style={{ marginTop: 6 }}>
                <textarea
                  value={note}
                  onChange={e => setNote(e.target.value)}
                  placeholder="Add notes..."
                  style={{ width: '100%', padding: 8, borderRadius: 6, border: '1px solid #2a2e3a', background: '#0f1117', color: '#e8eaed', fontSize: 11, fontFamily: 'inherit', resize: 'vertical', minHeight: 50, boxSizing: 'border-box' }}
                />
                <div style={{ display: 'flex', gap: 4, marginTop: 4 }}>
                  <button
                    onClick={() => { onUpdate(f.flow_id, { notes: note }); setEditId(null); }}
                    style={{ padding: '4px 12px', borderRadius: 6, border: 'none', background: '#5B9BD5', color: '#fff', fontSize: 10, fontWeight: 600, cursor: 'pointer', fontFamily: 'inherit' }}
                  >
                    Save
                  </button>
                  <button
                    onClick={() => setEditId(null)}
                    style={{ padding: '4px 12px', borderRadius: 6, border: 'none', background: '#2a2e3a', color: '#9aa0ad', fontSize: 10, cursor: 'pointer', fontFamily: 'inherit' }}
                  >
                    Cancel
                  </button>
                </div>
              </div>
            ) : (
              <div
                onClick={() => { setEditId(f.flow_id); setNote(f.notes || ''); }}
                style={{ marginTop: 6, fontSize: 10, color: f.notes ? '#9aa0ad' : '#5f6577', cursor: 'pointer', fontStyle: f.notes ? 'normal' : 'italic', padding: '4px 0' }}
              >
                {f.notes || 'Click to add notes...'}
              </div>
            )}
          </div>
        );
      })}

      {flows.length > 0 && (
        <button
          onClick={onExport}
          style={{ marginTop: 12, width: '100%', padding: '10px 16px', borderRadius: 8, border: '1px solid #5B9BD5', background: 'transparent', color: '#5B9BD5', fontWeight: 600, fontSize: 12, cursor: 'pointer', fontFamily: 'inherit' }}
        >
          Export Flows as JSON
        </button>
      )}
    </div>
  );
}
