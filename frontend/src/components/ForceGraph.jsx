import { useEffect, useRef, useMemo } from 'react';
import * as d3 from 'd3';
import { SC } from '../lib/constants';

export default function ForceGraph({ companies, candidates, flows, active, cMap, onEdge }) {
  const ref = useRef(null);

  const fCands = useMemo(() =>
    candidates.filter(c => active.has(c.from_company_id) && active.has(c.to_company_id)),
    [candidates, active]);

  const fConf = useMemo(() =>
    flows.filter(f => f.status === 'confirmed' && active.has(f.from_company_id) && active.has(f.to_company_id)),
    [flows, active]);

  const fComps = useMemo(() =>
    companies.filter(c => active.has(c.company_id)),
    [companies, active]);

  useEffect(() => {
    if (!ref.current) return;
    const svg = d3.select(ref.current);
    svg.selectAll('*').remove();

    const w = ref.current.clientWidth;
    const h = ref.current.clientHeight;

    const defs = svg.append('defs');
    defs.append('marker').attr('id', 'ac').attr('viewBox', '0 -5 10 10').attr('refX', 28).attr('refY', 0).attr('markerWidth', 6).attr('markerHeight', 6).attr('orient', 'auto').append('path').attr('d', 'M0,-5L10,0L0,5').attr('fill', '#5f6577');
    defs.append('marker').attr('id', 'af').attr('viewBox', '0 -5 10 10').attr('refX', 28).attr('refY', 0).attr('markerWidth', 7).attr('markerHeight', 7).attr('orient', 'auto').append('path').attr('d', 'M0,-5L10,0L0,5').attr('fill', '#4ade80');

    const g = svg.append('g');
    svg.call(d3.zoom().scaleExtent([0.3, 4]).on('zoom', e => g.attr('transform', e.transform)));

    // Best candidate edge per company pair
    const eMap = new Map();
    fCands.forEach(c => {
      const k = `${c.from_company_id}→${c.to_company_id}`;
      if (!eMap.has(k) || c.composite_score > eMap.get(k).composite_score) eMap.set(k, c);
    });
    const cfMap = new Set();
    fConf.forEach(f => cfMap.add(`${f.from_company_id}→${f.to_company_id}`));

    const nodes = fComps.map(c => ({ ...c, id: c.company_id }));
    const links = [];
    eMap.forEach((c, k) => {
      if (!cfMap.has(k)) links.push({ source: c.from_company_id, target: c.to_company_id, score: c.composite_score, type: 'cand', data: c });
    });
    fConf.forEach(f => links.push({ source: f.from_company_id, target: f.to_company_id, score: 1, type: 'conf', data: f }));

    const sim = d3.forceSimulation(nodes)
      .force('link', d3.forceLink(links).id(d => d.id).distance(160))
      .force('charge', d3.forceManyBody().strength(-600))
      .force('center', d3.forceCenter(w / 2, h / 2))
      .force('collision', d3.forceCollide(50));

    const link = g.append('g').selectAll('line').data(links).join('line')
      .attr('stroke', d => d.type === 'conf' ? '#4ade80' : SC(d.score))
      .attr('stroke-width', d => d.type === 'conf' ? 4 : 1.5 + d.score * 3)
      .attr('stroke-opacity', d => d.type === 'conf' ? 0.85 : 0.45)
      .attr('stroke-dasharray', d => d.type === 'conf' ? 'none' : '6 3')
      .attr('marker-end', d => d.type === 'conf' ? 'url(#af)' : 'url(#ac)')
      .style('cursor', 'pointer')
      .on('click', (_, d) => { if (d.type === 'cand') onEdge(d.data); });

    const lbl = g.append('g').selectAll('text').data(links).join('text')
      .text(d => d.type === 'conf' ? '✓' : `${(d.score * 100).toFixed(0)}%`)
      .attr('font-size', d => d.type === 'conf' ? '12px' : '10px')
      .attr('fill', d => d.type === 'conf' ? '#4ade80' : '#5f6577')
      .attr('text-anchor', 'middle').attr('dy', -8)
      .style('pointer-events', 'none');

    const node = g.append('g').selectAll('g').data(nodes).join('g')
      .style('cursor', 'grab')
      .call(d3.drag()
        .on('start', (e, d) => { if (!e.active) sim.alphaTarget(0.3).restart(); d.fx = d.x; d.fy = d.y; })
        .on('drag',  (e, d) => { d.fx = e.x; d.fy = e.y; })
        .on('end',   (e, d) => { if (!e.active) sim.alphaTarget(0); d.fx = null; d.fy = null; }));

    node.append('circle').attr('r', 24).attr('fill', d => cMap[d.company_id]).attr('stroke', '#181b23').attr('stroke-width', 2.5);
    node.append('text')
      .text(d => d.name.split(' ').map(w => w[0]).join(''))
      .attr('text-anchor', 'middle').attr('dy', '0.35em')
      .attr('font-size', '11px').attr('font-weight', '700').attr('fill', '#fff')
      .style('pointer-events', 'none');
    node.append('text')
      .text(d => d.name)
      .attr('text-anchor', 'middle').attr('dy', 40)
      .attr('font-size', '11px').attr('fill', '#e8eaed')
      .style('pointer-events', 'none');

    sim.on('tick', () => {
      link.attr('x1', d => d.source.x).attr('y1', d => d.source.y).attr('x2', d => d.target.x).attr('y2', d => d.target.y);
      lbl.attr('x', d => (d.source.x + d.target.x) / 2).attr('y', d => (d.source.y + d.target.y) / 2);
      node.attr('transform', d => `translate(${d.x},${d.y})`);
    });

    return () => sim.stop();
  }, [fComps, fCands, fConf, cMap, onEdge]);

  return <svg ref={ref} style={{ width: '100%', height: '100%' }} />;
}
