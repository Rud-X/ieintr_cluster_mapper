// Client-side scoring — mirrors analysis/match_candidates.py score_pair()
// Used by ManualPairing for on-the-fly evaluation without a server round-trip.

export function scorePair(out, inp) {
  const oC = {}, iC = {};
  (out.components || []).forEach(c => { if (!c.is_trace) oC[c.component_id] = c; });
  (inp.components || []).forEach(c => { if (!c.is_trace) iC[c.component_id] = c; });

  const oK = new Set(Object.keys(oC));
  const iK = new Set(Object.keys(iC));
  const shared = [...oK].filter(k => iK.has(k));
  const union  = new Set([...oK, ...iK]);

  const co = union.size > 0 ? shared.length / union.size : 0;

  let fs = 0;
  if (shared.length) {
    const d = shared.map(k => Math.abs((oC[k].fraction || 0) - (iC[k].fraction || 0)));
    fs = 1 - d.reduce((a, b) => a + b, 0) / d.length;
  }

  const fO = out.flow_kton_per_year || 0;
  const fI = inp.flow_kton_per_year || 0;
  const fc = (fO > 0 && fI > 0) ? Math.min(fO, fI) / Math.max(fO, fI) : 0;

  const tp = (out.temperature_c != null && inp.temperature_c != null)
    ? 1 / (1 + Math.abs(out.temperature_c - inp.temperature_c) / 100)
    : 0.5;

  const pp = (out.pressure_bar != null && inp.pressure_bar != null)
    ? 1 / (1 + Math.abs(out.pressure_bar - inp.pressure_bar) / 10)
    : 0.5;

  const cs = co * 0.35 + fs * 0.25 + fc * 0.20 + tp * 0.10 + pp * 0.10;

  const sc = shared
    .map(k => ({ name: oC[k].name, hazardous: oC[k].hazardous, fraction_out: oC[k].fraction, fraction_in: iC[k].fraction }))
    .sort((a, b) => (b.fraction_out || 0) - (a.fraction_out || 0));

  const r = v => Math.round(v * 10000) / 10000;
  return {
    composite_score:      r(cs),
    component_overlap:    r(co),
    fraction_similarity:  r(fs),
    flow_compatibility:   r(fc),
    temperature_proximity: r(tp),
    pressure_proximity:   r(pp),
    shared_components:    sc,
    has_hazardous:        sc.some(c => c.hazardous === 1),
  };
}
