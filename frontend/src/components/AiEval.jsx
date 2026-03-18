import { useState, useCallback } from 'react';

// API key loaded from .env.local: VITE_ANTHROPIC_API_KEY=sk-ant-...
const API_KEY = import.meta.env.VITE_ANTHROPIC_API_KEY || '';

export default function AiEval({ outStream, inStream, fromCo, toCo }) {
  const [res, setRes]         = useState(null);
  const [loading, setLoading] = useState(false);

  const ask = useCallback(async () => {
    setLoading(true);
    setRes(null);

    const p = `You are an industrial ecology expert evaluating a potential industrial symbiosis connection.\n\n**Supplier:** ${fromCo?.name} (${fromCo?.sector || 'unknown sector'})\n**Output stream:** ${outStream.stream_name} (${outStream.stream_type})\n- Flow: ${outStream.flow_kton_per_year} kton/year\n- Temperature: ${outStream.temperature_c ?? 'unknown'}°C, Pressure: ${outStream.pressure_bar ?? 'unknown'} bar\n- Composition: ${outStream.composition_raw || outStream.components?.map(c => `${c.name} (${(c.fraction * 100).toFixed(1)}%)`).join(', ')}\n\n**Receiver:** ${toCo?.name} (${toCo?.sector || 'unknown sector'})\n**Input stream:** ${inStream.stream_name} (${inStream.stream_type})\n- Flow: ${inStream.flow_kton_per_year} kton/year\n- Temperature: ${inStream.temperature_c ?? 'unknown'}°C, Pressure: ${inStream.pressure_bar ?? 'unknown'} bar\n- Composition: ${inStream.composition_raw || inStream.components?.map(c => `${c.name} (${(c.fraction * 100).toFixed(1)}%)`).join(', ')}\n\nProvide a concise evaluation (200 words max) covering:\n1. **Compatibility** — compositional match\n2. **Practical concerns** — temperature/pressure gaps, purification, hazards, contaminants\n3. **Flow balance** — can supply meet demand?\n4. **Recommendation** — viable, conditionally viable, or not viable`;

    try {
      const r = await fetch('https://api.anthropic.com/v1/messages', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'x-api-key': API_KEY,
          'anthropic-version': '2023-06-01',
          'anthropic-dangerous-request-source': 'user',
        },
        body: JSON.stringify({
          model: 'claude-sonnet-4-20250514',
          max_tokens: 1000,
          messages: [{ role: 'user', content: p }],
        }),
      });
      const d = await r.json();
      if (!r.ok) {
        setRes(`Error ${r.status}: ${d.error?.message || r.statusText}`);
      } else {
        setRes(d.content?.map(b => b.text || '').join('\n') || 'No response.');
      }
    } catch (e) {
      setRes(`Error: ${e.message}`);
    } finally {
      setLoading(false);
    }
  }, [outStream, inStream, fromCo, toCo]);

  return (
    <>
      <button
        onClick={ask}
        disabled={loading || !API_KEY}
        title={!API_KEY ? 'Set VITE_ANTHROPIC_API_KEY in frontend/.env.local' : undefined}
        style={{
          marginTop: 14, width: '100%', padding: '10px 16px', borderRadius: 8,
          border: '1px solid #5B9BD5',
          background: (loading || !API_KEY) ? '#0f1117' : '#5B9BD5',
          color: (loading || !API_KEY) ? '#5f6577' : '#fff',
          fontWeight: 600, fontSize: 13,
          cursor: (loading || !API_KEY) ? 'not-allowed' : 'pointer',
          fontFamily: 'inherit',
        }}
      >
        {loading ? 'Evaluating...' : !API_KEY ? 'Ask Claude (set API key)' : 'Ask Claude for Evaluation'}
      </button>
      {res && (
        <div style={{ marginTop: 12, padding: 12, borderRadius: 8, background: '#0f1117', fontSize: 12, lineHeight: 1.6, whiteSpace: 'pre-wrap', color: '#9aa0ad' }}>
          {res}
        </div>
      )}
    </>
  );
}
