import React, { useEffect, useMemo, useRef } from 'react';
import * as d3 from 'd3';

const StreamChart = ({ data }) => {
  const svgRef = useRef(null);
  const simulationRef = useRef(null);
  const rootGRef = useRef(null);
  const linksGRef = useRef(null);
  const nodesGRef = useRef(null);
  const dims = useMemo(() => ({ width: 1000, height: 700 }), []);

  useEffect(() => {
    const svg = d3.select(svgRef.current);
    svg.attr('viewBox', `0 0 ${dims.width} ${dims.height}`);

    const defs = svg.append('defs');
    const glow = defs.append('filter').attr('id', 'sv-glow');
    glow.append('feGaussianBlur').attr('stdDeviation', '4').attr('result', 'coloredBlur');
    const feMerge = glow.append('feMerge');
    feMerge.append('feMergeNode').attr('in', 'coloredBlur');
    feMerge.append('feMergeNode').attr('in', 'SourceGraphic');

    const rootG = svg.append('g').attr('class', 'sv-root');
    const linksG = rootG.append('g').attr('class', 'sv-links');
    const nodesG = rootG.append('g').attr('class', 'sv-nodes');

    rootGRef.current = rootG;
    linksGRef.current = linksG;
    nodesGRef.current = nodesG;

    svg.call(
      d3
        .zoom()
        .scaleExtent([0.25, 2.5])
        .on('zoom', (event) => {
          rootG.attr('transform', event.transform);
        }),
    );

    simulationRef.current = d3
      .forceSimulation()
      .alphaDecay(0.04)
      .velocityDecay(0.35)
      .force('link', d3.forceLink().id((d) => d.id).distance(120).strength(0.22))
      .force('charge', d3.forceManyBody().strength(-420))
      .force('collide', d3.forceCollide().radius(22).strength(0.9))
      .force('center', d3.forceCenter(dims.width / 2, dims.height / 2));

    return () => {
      svg.selectAll('*').remove();
      simulationRef.current?.stop();
    };
  }, [dims.height, dims.width]);

  useEffect(() => {
    if (!simulationRef.current || !linksGRef.current || !nodesGRef.current) return;

    const simulation = simulationRef.current;
    const linkForce = simulation.force('link');
    const currentNodes = simulation.nodes();
    const nextNodes = data.nodes.map((n) => {
      const existing = currentNodes.find((en) => en.id === n.id);
      return existing ? Object.assign(existing, n) : { ...n };
    });

    simulation.nodes(nextNodes);
    if (linkForce) linkForce.links(data.links);

    const linksG = linksGRef.current;
    const nodesG = nodesGRef.current;

    const linkKey = (d) => d.id || `${typeof d.source === 'object' ? d.source.id : d.source}__${typeof d.target === 'object' ? d.target.id : d.target}`;

    const linkSel = linksG
      .selectAll('line')
      .data(data.links, linkKey)
      .join(
        (enter) =>
          enter
            .append('line')
            .attr('stroke', 'rgba(255, 255, 255, 0.22)')
            .attr('stroke-width', 1.5),
        (update) => update,
        (exit) => exit.remove(),
      );

    const nodeSel = nodesG
      .selectAll('g.sv-node')
      .data(nextNodes, (d) => d.id)
      .join(
        (enter) => {
          const g = enter.append('g').attr('class', 'sv-node').attr('cursor', 'grab');
          g.append('circle')
            .attr('r', 10)
            .attr('fill', 'rgba(20, 184, 166, 0.85)')
            .attr('stroke', 'rgba(255, 255, 255, 0.28)')
            .attr('stroke-width', 1.25)
            .attr('filter', 'url(#sv-glow)');
          g.append('text')
            .attr('x', 14)
            .attr('y', 4)
            .attr('font-size', 12)
            .attr('fill', 'rgba(255, 255, 255, 0.78)')
            .attr('font-family', '"Fira Code", ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace');
          return g;
        },
        (update) => update,
        (exit) => exit.remove(),
      );

    nodeSel.select('text').text((d) => (d.label ? String(d.label) : String(d.id)));

    const drag = d3
      .drag()
      .on('start', (event) => {
        if (!event.active) simulation.alphaTarget(0.25).restart();
        event.subject.fx = event.subject.x;
        event.subject.fy = event.subject.y;
      })
      .on('drag', (event) => {
        event.subject.fx = event.x;
        event.subject.fy = event.y;
      })
      .on('end', (event) => {
        if (!event.active) simulation.alphaTarget(0);
        event.subject.fx = null;
        event.subject.fy = null;
      });

    nodeSel.call(drag);

    simulation.on('tick', () => {
      linkSel
        .attr('x1', (d) => d.source.x)
        .attr('y1', (d) => d.source.y)
        .attr('x2', (d) => d.target.x)
        .attr('y2', (d) => d.target.y);

      nodeSel.attr('transform', (d) => `translate(${d.x},${d.y})`);
    });

    simulation.alpha(0.9).restart();
  }, [data]);

  return <svg ref={svgRef} width="100%" height="100%" role="img" aria-label="Streaming graph visualization" />;
};

export default StreamChart;
