import ScoreDetail from './ScoreDetail';
import AiEval from './AiEval';

export default function CandidateDetail({ sel, streams, companies, flows, scales, companyName, setScale, addFlow, onBack }) {
  const inFlows = (fromSid, toSid) => flows.some(f => f.from_stream_id === fromSid && f.to_stream_id === toSid);
  const already = inFlows(sel.from_stream_id, sel.to_stream_id);

  const fromScale = scales[sel.from_company_id] || 1;
  const toScale   = scales[sel.to_company_id]   || 1;

  const sAvail = (sel.available_flow_kton || 0) * fromScale;
  const sReq   = (sel.required_flow_kton  || 0) * toScale;

  const matchSupplierFactor = sel.available_flow_kton > 0
    ? (sel.required_flow_kton * toScale) / sel.available_flow_kton
    : 1;
  const matchReceiverFactor = sel.required_flow_kton > 0
    ? (sel.available_flow_kton * fromScale) / sel.required_flow_kton
    : 1;

  const outStream = streams.find(s => s.stream_id === sel.from_stream_id);
  const inStream  = streams.find(s => s.stream_id === sel.to_stream_id);
  const fromCo    = companies.find(c => c.company_id === sel.from_company_id);
  const toCo      = companies.find(c => c.company_id === sel.to_company_id);

  return (
    <div>
      <button
        onClick={onBack}
        style={{ padding: '8px 16px', fontSize: 11, background: 'none', border: 'none', color: '#5B9BD5', cursor: 'pointer', fontFamily: 'inherit' }}
      >
        ← Back to list
      </button>

      <div style={{ padding: 16 }}>
        {/* Stream pair header */}
        <div style={{ display: 'grid', gridTemplateColumns: '1fr auto 1fr', gap: 8, alignItems: 'center', marginBottom: 12, padding: 12, borderRadius: 8, background: '#0f1117' }}>
          <div>
            <div style={{ fontSize: 10, color: '#5f6577', textTransform: 'uppercase', letterSpacing: 1 }}>Output</div>
            <div style={{ fontWeight: 600, fontSize: 13 }}>{companyName(sel.from_company_id)}</div>
            <div style={{ fontSize: 12, color: '#9aa0ad' }}>{sel.from_stream_name}</div>
            <div style={{ fontSize: 11, color: '#5f6577' }}>
              {fromScale !== 1
                ? <><span style={{ textDecoration: 'line-through', opacity: 0.5 }}>{sel.available_flow_kton}</span>{' '}<span style={{ color: '#e8eaed', fontWeight: 600 }}>{sAvail.toFixed(1)}</span></>
                : sel.available_flow_kton} kt/yr
            </div>
          </div>
          <div style={{ fontSize: 20, color: '#5f6577' }}>→</div>
          <div style={{ textAlign: 'right' }}>
            <div style={{ fontSize: 10, color: '#5f6577', textTransform: 'uppercase', letterSpacing: 1 }}>Input</div>
            <div style={{ fontWeight: 600, fontSize: 13 }}>{companyName(sel.to_company_id)}</div>
            <div style={{ fontSize: 12, color: '#9aa0ad' }}>{sel.to_stream_name}</div>
            <div style={{ fontSize: 11, color: '#5f6577' }}>
              {toScale !== 1
                ? <><span style={{ textDecoration: 'line-through', opacity: 0.5 }}>{sel.required_flow_kton}</span>{' '}<span style={{ color: '#e8eaed', fontWeight: 600 }}>{sReq.toFixed(1)}</span></>
                : sel.required_flow_kton} kt/yr
            </div>
          </div>
        </div>

        {/* Scale buttons */}
        <div style={{ display: 'flex', gap: 6, marginBottom: 14 }}>
          <button
            onClick={() => setScale(sel.from_company_id, Math.round(matchSupplierFactor * 100) / 100)}
            style={{ flex: 1, padding: '7px 6px', borderRadius: 6, border: '1px solid #2a2e3a', background: '#181b23', color: '#e8eaed', fontSize: 10, cursor: 'pointer', fontFamily: 'inherit', lineHeight: 1.3, textAlign: 'center' }}
            title={`Set ${companyName(sel.from_company_id)} scale to ×${matchSupplierFactor.toFixed(2)}`}
          >
            Scale supplier<br />
            <span style={{ color: '#5B9BD5', fontWeight: 600 }}>×{matchSupplierFactor.toFixed(2)}</span>
          </button>
          <button
            onClick={() => setScale(sel.to_company_id, Math.round(matchReceiverFactor * 100) / 100)}
            style={{ flex: 1, padding: '7px 6px', borderRadius: 6, border: '1px solid #2a2e3a', background: '#181b23', color: '#e8eaed', fontSize: 10, cursor: 'pointer', fontFamily: 'inherit', lineHeight: 1.3, textAlign: 'center' }}
            title={`Set ${companyName(sel.to_company_id)} scale to ×${matchReceiverFactor.toFixed(2)}`}
          >
            Scale receiver<br />
            <span style={{ color: '#5B9BD5', fontWeight: 600 }}>×{matchReceiverFactor.toFixed(2)}</span>
          </button>
        </div>

        <ScoreDetail r={sel}>
          <button
            onClick={() => !already && addFlow({
              from_company_id: sel.from_company_id,
              to_company_id:   sel.to_company_id,
              from_stream_id:  sel.from_stream_id,
              to_stream_id:    sel.to_stream_id,
              from_stream_name: sel.from_stream_name,
              to_stream_name:   sel.to_stream_name,
              flow_kton_per_year: Math.min(sel.available_flow_kton || 0, sel.required_flow_kton || 0),
              composite_score: sel.composite_score,
            })}
            disabled={already}
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

          {outStream && inStream && (
            <AiEval outStream={outStream} inStream={inStream} fromCo={fromCo} toCo={toCo} />
          )}
        </ScoreDetail>
      </div>
    </div>
  );
}
