import React, { useEffect, useRef, useState, useMemo, useLayoutEffect } from 'react';
import * as d3 from 'd3';
import { FEATURE_COLORS, labelFeature } from '../constants/features';

function sentimentColor(s) {
  const t = (s || '').toLowerCase();
  if (t.includes('pos')) return '#2dd4bf'; // Refined Mint Teal
  if (t.includes('neg')) return '#fb7185'; // Refined Coral Rose
  return '#94a3b8'; // Slate
}

export default function GraphNetwork({
  graphData,
  activeFeature,
  selectedClusterId,
  onSelectNode,
  height = 420,
}) {
  const svgRef = useRef(null);
  const wrapRef = useRef(null);
  const zoomBehaviorRef = useRef(null);
  const [dims, setDims] = useState({ width: 800, height });
  const [tooltip, setTooltip] = useState(null);
  const [featureFilter, setFeatureFilter] = useState(activeFeature || 'all');

  // Track parent width responsively
  useLayoutEffect(() => {
    const el = wrapRef.current;
    if (!el) return;
    const ro = new ResizeObserver(([entry]) => {
      const w = entry.contentRect.width;
      if (w > 0) {
        setDims({ width: w, height });
      }
    });
    ro.observe(el);
    return () => ro.disconnect();
  }, [height]);

  // Sync prop changes
  useEffect(() => {
    if (activeFeature) {
      setFeatureFilter(activeFeature);
    }
  }, [activeFeature]);

  // Extract and memoize nodes and links
  const { nodes, links, batchCount, systemicCount, healthyCount, availableFeatures } = useMemo(() => {
    const rawNodes = Array.isArray(graphData?.nodes) ? graphData.nodes : [];
    const rawEdges = Array.isArray(graphData?.edges) ? graphData.edges : [];

    const feats = new Set();
    rawNodes.forEach((n) => {
      if (n.feature) feats.add(n.feature);
    });

    // Filter by feature if not 'all'
    const filteredNodes = featureFilter && featureFilter !== 'all'
      ? rawNodes.filter((n) => {
          const tags = Array.isArray(n.features) ? n.features : [];
          return n.feature === featureFilter || tags.includes(featureFilter);
        })
      : rawNodes;

    const idSet = new Set(filteredNodes.map((n) => n.id));
    const edges = [];

    for (const e of rawEdges) {
      const sId = typeof e.source === 'object' && e.source !== null ? e.source.id : e.source;
      const tId = typeof e.target === 'object' && e.target !== null ? e.target.id : e.target;
      if (idSet.has(sId) && idSet.has(tId)) {
        edges.push({
          source: sId,
          target: tId,
          weight: typeof e.weight === 'number' ? e.weight : 0.65,
        });
      }
    }

    const clonedNodes = filteredNodes.map((n) => ({ ...n }));

    let bCount = 0;
    let sCount = 0;
    let hCount = 0;
    for (const n of clonedNodes) {
      if (n.cluster_type === 'batch') bCount++;
      else if (n.cluster_type === 'systemic') sCount++;
      else hCount++;
    }

    return {
      nodes: clonedNodes,
      links: edges,
      batchCount: bCount,
      systemicCount: sCount,
      healthyCount: hCount,
      availableFeatures: Array.from(feats),
    };
  }, [graphData, featureFilter]);

  const { width } = dims;

  // D3 Force Graph Simulation
  useEffect(() => {
    const svgEl = svgRef.current;
    if (!svgEl || !nodes.length) {
      if (svgEl) svgEl.innerHTML = '';
      return;
    }

    const svg = d3.select(svgEl);
    svg.selectAll('*').remove();

    // Defs for glowing filter and markers
    const defs = svg.append('defs');
    const filter = defs.append('filter')
      .attr('id', 'graph-glow')
      .attr('x', '-50%')
      .attr('y', '-50%')
      .attr('width', '200%')
      .attr('height', '200%');
    filter.append('feGaussianBlur').attr('stdDeviation', '2.5').attr('result', 'blur');
    filter.append('feMerge').selectAll('feMergeNode')
      .data(['blur', 'SourceGraphic'])
      .join('feMergeNode')
      .attr('in', (d) => d);

    const gRoot = svg.append('g');

    // Pan & Zoom
    const zoom = d3
      .zoom()
      .scaleExtent([0.3, 4])
      .on('zoom', (ev) => {
        gRoot.attr('transform', ev.transform);
      });

    svg.call(zoom);
    zoomBehaviorRef.current = zoom;

    // Simulation setup
    const simulation = d3
      .forceSimulation(nodes)
      .force(
        'link',
        d3
          .forceLink(links)
          .id((d) => d.id)
          .distance((d) => 30 + (1 - Math.min(1, d.weight || 0.65)) * 40)
          .strength((d) => 0.75 + (d.weight || 0.65) * 0.25)
      )
      .force('charge', d3.forceManyBody().strength(-90))
      .force('center', d3.forceCenter(width / 2, height / 2))
      .force('collision', d3.forceCollide().radius(14));

    // Links
    const link = gRoot
      .append('g')
      .attr('stroke', '#334155')
      .attr('stroke-opacity', 0.5)
      .selectAll('line')
      .data(links)
      .join('line')
      .attr('stroke-width', (d) => Math.max(1, (d.weight || 0.5) * 2));

    // Halos for Batch Anomalies
    const batchHalo = gRoot
      .append('g')
      .selectAll('circle')
      .data(nodes.filter((n) => n.cluster_type === 'batch'))
      .join('circle')
      .attr('r', 14)
      .attr('fill', 'rgba(251, 113, 133, 0.12)')
      .attr('stroke', '#fb7185')
      .attr('stroke-width', 1.5)
      .attr('stroke-dasharray', '3,2');

    // Halos for Systemic Anomalies
    const systemicHalo = gRoot
      .append('g')
      .selectAll('circle')
      .data(nodes.filter((n) => n.cluster_type === 'systemic'))
      .join('circle')
      .attr('r', 12)
      .attr('fill', 'rgba(245, 158, 11, 0.10)')
      .attr('stroke', '#f59e0b')
      .attr('stroke-width', 1.2)
      .attr('stroke-dasharray', '2,2');

    // Halos for Selected Cluster / Feature
    const selectedHalo = gRoot
      .append('g')
      .selectAll('circle')
      .data(nodes.filter((n) => selectedClusterId && (n.cluster_id === selectedClusterId || n.id === selectedClusterId)))
      .join('circle')
      .attr('r', 17)
      .attr('fill', 'rgba(56, 189, 248, 0.2)')
      .attr('stroke', '#38bdf8')
      .attr('stroke-width', 2)
      .attr('stroke-dasharray', '4,2');

    // Nodes
    const node = gRoot
      .append('g')
      .selectAll('circle')
      .data(nodes)
      .join('circle')
      .attr('r', (d) => (d.cluster_id === selectedClusterId ? 8 : 6))
      .attr('stroke', (d) => (d.feature ? FEATURE_COLORS[d.feature] || '#94a3b8' : '#94a3b8'))
      .attr('stroke-width', 2)
      .attr('fill', (d) => sentimentColor(d.sentiment))
      .style('cursor', 'pointer')
      .call(
        d3
          .drag()
          .on('start', (ev, d) => {
            if (!ev.active) simulation.alphaTarget(0.3).restart();
            d.fx = d.x;
            d.fy = d.y;
          })
          .on('drag', (ev, d) => {
            d.fx = ev.x;
            d.fy = ev.y;
          })
          .on('end', (ev, d) => {
            if (!ev.active) simulation.alphaTarget(0);
            d.fx = null;
            d.fy = null;
          })
      )
      .on('mouseenter', (ev, d) => {
        const rect = svgEl.getBoundingClientRect();
        setTooltip({
          x: ev.clientX - rect.left,
          y: ev.clientY - rect.top,
          id: d.id,
          feature: d.feature,
          allFeatures: Array.isArray(d.features) ? d.features : [d.feature],
          sentiment: d.sentiment,
          week: d.week,
          clusterType: d.cluster_type,
          clusterId: d.cluster_id,
        });
      })
      .on('mousemove', (ev) => {
        const rect = svgEl.getBoundingClientRect();
        setTooltip((t) => (t ? { ...t, x: ev.clientX - rect.left, y: ev.clientY - rect.top } : null));
      })
      .on('mouseleave', () => setTooltip(null))
      .on('click', (ev, d) => {
        if (onSelectNode) {
          onSelectNode(d);
        }
      });

    simulation.on('tick', () => {
      link
        .attr('x1', (d) => d.source.x)
        .attr('y1', (d) => d.source.y)
        .attr('x2', (d) => d.target.x)
        .attr('y2', (d) => d.target.y);
      batchHalo.attr('cx', (d) => d.x).attr('cy', (d) => d.y);
      systemicHalo.attr('cx', (d) => d.x).attr('cy', (d) => d.y);
      selectedHalo.attr('cx', (d) => d.x).attr('cy', (d) => d.y);
      node.attr('cx', (d) => d.x).attr('cy', (d) => d.y);
    });

    simulation.alpha(1).restart();
    const t = window.setTimeout(() => simulation.alphaTarget(0), 2200);

    return () => {
      clearTimeout(t);
      simulation.stop();
    };
  }, [nodes, links, width, height, selectedClusterId, onSelectNode]);

  function handleResetZoom() {
    if (svgRef.current && zoomBehaviorRef.current) {
      d3.select(svgRef.current)
        .transition()
        .duration(500)
        .call(zoomBehaviorRef.current.transform, d3.zoomIdentity);
    }
  }

  function handleZoomIn() {
    if (svgRef.current && zoomBehaviorRef.current) {
      d3.select(svgRef.current)
        .transition()
        .duration(300)
        .call(zoomBehaviorRef.current.scaleBy, 1.3);
    }
  }

  function handleZoomOut() {
    if (svgRef.current && zoomBehaviorRef.current) {
      d3.select(svgRef.current)
        .transition()
        .duration(300)
        .call(zoomBehaviorRef.current.scaleBy, 0.75);
    }
  }

  if (!nodes.length) {
    return (
      <div className="p-8 rounded-2xl bg-[#09090b] border border-white/10 text-center text-xs text-slate-400">
        Loading semantic network topology from backend SQLite database...
      </div>
    );
  }

  return (
    <div ref={wrapRef} className="relative rounded-2xl bg-[#09090b] border border-white/10 overflow-hidden shadow-2xl">
      {/* Top Controls & Telemetry Header */}
      <div className="flex flex-wrap items-center justify-between gap-3 p-4 border-b border-white/10 bg-black/40">
        <div className="flex items-center gap-3">
          <div>
            <div className="flex items-center gap-2">
              <span className="text-[10px] font-bold font-mono uppercase tracking-wider text-cyan-400">
                Network Topology
              </span>
              <span className="px-2 py-0.5 rounded text-[10px] font-mono text-slate-300 bg-white/5 border border-white/10">
                {nodes.length} Nodes · {links.length} Edges
              </span>
            </div>
            <h2 className="text-sm font-bold text-white mt-0.5">
              Semantic Issue Graph &amp; Defect Clusters
            </h2>
          </div>
        </div>

        {/* Badges & Zoom Buttons */}
        <div className="flex flex-wrap items-center gap-2">
          {/* Classification Counts */}
          <div className="flex items-center gap-1.5 text-[11px] font-mono">
            <span className="px-2 py-0.5 rounded-full bg-rose-500/10 text-rose-300 border border-rose-500/20 flex items-center gap-1.5 font-medium">
              <span className="w-1.5 h-1.5 rounded-full bg-rose-400 animate-pulse" />
              Batch ({batchCount})
            </span>
            <span className="px-2 py-0.5 rounded-full bg-amber-500/10 text-amber-300 border border-amber-500/20 flex items-center gap-1.5 font-medium">
              <span className="w-1.5 h-1.5 rounded-full bg-amber-400" />
              Systemic ({systemicCount})
            </span>
            <span className="px-2 py-0.5 rounded-full bg-teal-500/10 text-teal-300 border border-teal-500/20 flex items-center gap-1.5 font-medium">
              <span className="w-1.5 h-1.5 rounded-full bg-teal-400" />
              Healthy ({healthyCount})
            </span>
          </div>

          {/* Feature Filter Dropdown */}
          {availableFeatures.length > 0 && (
            <select
              value={featureFilter}
              onChange={(e) => setFeatureFilter(e.target.value)}
              className="bg-black/60 border border-white/15 rounded-lg px-2.5 py-1 text-xs text-white font-mono focus:outline-none focus:border-cyan-500"
            >
              <option value="all">All Features ({availableFeatures.length})</option>
              {availableFeatures.map((f) => (
                <option key={f} value={f}>
                  {labelFeature(f)}
                </option>
              ))}
            </select>
          )}

          {/* Zoom controls */}
          <div className="flex items-center gap-1 bg-black/60 border border-white/10 rounded-lg p-0.5">
            <button
              type="button"
              onClick={handleZoomIn}
              className="px-2 py-0.5 hover:bg-white/10 text-slate-300 text-xs rounded transition-colors"
              title="Zoom In"
              aria-label="Zoom in"
            >
              +
            </button>
            <button
              type="button"
              onClick={handleZoomOut}
              className="px-2 py-0.5 hover:bg-white/10 text-slate-300 text-xs rounded transition-colors"
              title="Zoom Out"
              aria-label="Zoom out"
            >
              -
            </button>
            <button
              type="button"
              onClick={handleResetZoom}
              className="px-2 py-0.5 hover:bg-white/10 text-slate-400 hover:text-white text-[11px] rounded transition-colors"
              title="Reset View"
            >
              Reset
            </button>
          </div>
        </div>
      </div>

      {/* SVG Canvas */}
      <div className="relative bg-[#05070f] overflow-hidden">
        <svg
          ref={svgRef}
          width={width}
          height={height}
          className="w-full block touch-none cursor-grab active:cursor-grabbing"
          role="img"
          aria-label="Interactive Semantic Graph"
        />

        {/* Canvas Background Grid Subtle Overlay */}
        <div
          className="absolute inset-0 pointer-events-none opacity-20"
          style={{
            backgroundImage: 'radial-gradient(rgba(255, 255, 255, 0.15) 1px, transparent 1px)',
            backgroundSize: '24px 24px',
          }}
        />

        {/* Legend Overlay at bottom-left */}
        <div className="absolute bottom-3 left-3 pointer-events-none bg-black/70 backdrop-blur-md border border-white/10 rounded-lg px-3 py-2 text-[10px] space-y-1 font-mono text-slate-300">
          <div className="flex items-center gap-2">
            <span className="w-2.5 h-2.5 rounded-full bg-teal-400" />
            <span>Positive Sentiment</span>
            <span className="text-slate-600">·</span>
            <span className="w-2.5 h-2.5 rounded-full bg-rose-400" />
            <span>Negative Defect</span>
          </div>
          <div className="text-slate-400 font-sans">
            Click any node to focus its root-cause diagnosis
          </div>
        </div>
      </div>

      {/* Floating Interactive Tooltip */}
      {tooltip && (
        <div
          className="pointer-events-none absolute z-50 max-w-xs rounded-xl border border-white/20 bg-[#0e0e12]/95 backdrop-blur-lg p-3 text-xs shadow-2xl text-slate-100"
          style={{
            left: Math.min(width - 240, Math.max(12, tooltip.x + 14)),
            top: Math.min(height - 120, Math.max(12, tooltip.y + 14)),
          }}
        >
          <div className="flex items-center justify-between gap-2 mb-1">
            <span className="text-[10px] font-mono text-slate-400 truncate max-w-[120px]">
              {tooltip.id.slice(0, 8)}...
            </span>
            <span
              className={`px-1.5 py-0.2 rounded text-[9px] font-bold uppercase ${
                tooltip.clusterType === 'batch'
                  ? 'bg-rose-500/20 text-rose-300 border border-rose-500/30'
                  : tooltip.clusterType === 'systemic'
                  ? 'bg-amber-500/20 text-amber-300 border border-amber-500/30'
                  : 'bg-teal-500/20 text-teal-300 border border-teal-500/30'
              }`}
            >
              {tooltip.clusterType === 'batch'
                ? 'Batch Defect'
                : tooltip.clusterType === 'systemic'
                ? 'Systemic'
                : 'Feature Cluster'}
            </span>
          </div>

          <div className="font-bold text-white capitalize text-sm">
            {labelFeature(tooltip.feature)}
          </div>

          {tooltip.allFeatures?.length > 1 && (
            <div className="text-[11px] text-slate-400 mt-1">
              Co-occurrences: {tooltip.allFeatures.map(labelFeature).join(', ')}
            </div>
          )}

          <div className="flex items-center justify-between text-[11px] pt-2 mt-2 border-t border-white/10 font-mono">
            <span className="text-slate-400">
              Sentiment:{' '}
              <strong
                className={tooltip.sentiment === 'negative' ? 'text-rose-400' : 'text-teal-400'}
              >
                {tooltip.sentiment}
              </strong>
            </span>
            <span className="text-slate-500">{tooltip.week || '2026-W21'}</span>
          </div>
        </div>
      )}
    </div>
  );
}
