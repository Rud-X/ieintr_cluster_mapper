import { useState, useMemo, useCallback } from 'react';
import ScoreDetail from './ScoreDetail';
import AiEval from './AiEval';
import { scorePair } from '../lib/scoring';

const selStyle = {
  width: '100%', padding: '8px 10px', borderRadius: 6,
  border: '1px solid #2a2e3a', background: '#0f1117',
  color: '#e8eaed', fontSize: 12, fontFamily: 'inherit',
};

export default function ManualPairing({ streams, companies, active, flows, companyName, addFlow }) {
  const [outSid, setOutSid] = useState('');
  const [inSid,  setInSid]  = useState('');
  const [result, setResult] = useState(null);

  const outStreams = useMemo(() => streams.filter(s => s.direction === 'output' && active.has(s.company_id)), [streams, active]);
  const inStreams  = useMemo(() => streams.filter(s => s.direction === 'input'  && active.has(s.company_id)), [streams, active]);

  const doEval = useCallback(() => {
    const o = streams.find(s => s.stream_id === outSid);
    const i = streams.find(s => s.stream_id === inSid);
    if (!o || !i) return;
    setResult({
      ...scorePair(o, i),
      from_stream_name: o.stream_name,
      to_stream_name:   i.stream_name,
      available_flow_kton: o.flow_kton_per_year,
      required_flow_kton:  i.flow_kton_per_year,
    });
  }, [outSid, inSid, streams]);

  const mOut    = streams.find(s => s.stream_id === outSid);
  const mIn     = streams.find(s => s.stream_id === inSid);
  const fromCo  = mOut ? companies.find(c => c.company_id === mOut.company_id) : null;
  const toCo    = mIn  ? companies.find(c => c.company_id === mIn.company_id)  : null;

  const inFlows = (fromSid, toSid) => flows.some(f => f.from_stream_id === fromSid && f.to_stream_id === toSid);
  const already = inFlows(outSid, inSid);
  const ready   = !!(outSid && inSid);

  return (
    <div style={{ padding: 16 }}>
      <div style={{ marginBottom: 12 }}>
        <label style={{ fontSize: 11, color: '#5f6577', textTransform: 'uppercase', letterSpacing: 1, display: 'block', marginBottom: 4 }}>
          Output Stream (supplier)
        </label>
        <select value={outSid} onChange={e => { setOutSid(e.target.value); setResult(null); }} style={selStyle}>
          <option value="">Select an output stream...</option>
          {outStreams.map(s => (
            <option key={s.stream_id} value={s.stream_id}>
              {companyName(s.company_id)} — {s.stream_name} ({s.stream_type})
            </option>
          ))}
        </select>
      </div>

      <div style={{ marginBottom: 12 }}>
        <label style={{ fontSize: 11, color: '#5f6577', textTransform: 'uppercase', letterSpacing: 1, display: 'block', marginBottom: 4 }}>
          Input Stream (receiver)
        </label>
        <select value={inSid} onChange={e => { setInSid(e.target.value); setResult(null); }} style={selStyle}>
          <option value="">Select an input stream...</option>
          {inStreams.map(s => (
            <option key={s.stream_id} value={s.stream_id}>
              {companyName(s.company_id)} — {s.stream_name} ({s.stream_type})
            </option>
          ))}
        </select>
      </div>

      <button
        onClick={doEval}
        disabled={!ready}
        style={{
          width: '100%', padding: '10px 16px', borderRadius: 8, border: 'none',
          background: ready ? '#5B9BD5' : '#181b23',
          color: ready ? '#fff' : '#5f6577',
          fontWeight: 600, fontSize: 13,
          cursor: ready ? 'pointer' : 'not-allowed',
          fontFamily: 'inherit',
        }}
      >
        Evaluate Fit
      </button>

      {result && (
        <div style={{ marginTop: 16 }}>
          <ScoreDetail r={result}>
            {result.shared_components.length === 0 && (
              <div style={{ marginTop: 10, padding: 12, borderRadius: 8, background: '#f871711a', fontSize: 12, color: '#f87171' }}>
                No shared components found.
              </div>
            )}
            <button
              onClick={() => !already && mOut && mIn && addFlow({
                from_company_id: mOut.company_id,
                to_company_id:   mIn.company_id,
                from_stream_id:  outSid,
                to_stream_id:    inSid,
                from_stream_name: mOut.stream_name,
                to_stream_name:   mIn.stream_name,
                flow_kton_per_year: Math.min(mOut.flow_kton_per_year || 0, mIn.flow_kton_per_year || 0),
                composite_score: result.composite_score,
              })}
              disabled={already || !ready}
              style={{
                marginTop: 14, width: '100%', padding: '10px 16px', borderRadius: 8, border: 'none',
                background: already ? '#181b23' : '#4ade80',
                color: already ? '#5f6577' : '#0f1117',
                fontWeight: 600, fontSize: 13,
                cursor: already ? 'default' : 'pointer',
                fontFamily: 'inherit',
              }}
            >
              {already ? 'Already in Flows' : 'Add to Flows'}
            </button>
            {mOut && mIn && <AiEval outStream={mOut} inStream={mIn} fromCo={fromCo} toCo={toCo} />}
          </ScoreDetail>
        </div>
      )}
    </div>
  );
}
