import React, { useEffect, useMemo, useRef } from 'react';
import * as d3 from 'd3';

const StreamChart = ({ data }) => {
  const svgRef = useRef(null);
  const simulationRef = useRef(null);
  const rootGRef = useRef(null);
  const linksGRef = useRef(null);
  const nodesGRef = useRef(null);
  const dims = useMemo(() => ({ width: 1000, height: 700 }), []);

  // 明亮主题配色
  const colors = {
    node: '#0d9488',
    nodeStroke: '#ffffff',
    nodeGlow: 'rgba(13, 148, 136, 0.3)',
    link: '#d6d3d1',
    text: '#57534e',
    textBg: 'rgba(255, 255, 255, 0.9)',
  };

  useEffect(() => {
    const svg = d3.select(svgRef.current);
    svg.attr('viewBox', `0 0 ${dims.width} ${dims.height}`);

    // 添加发光滤镜
    const defs = svg.append('defs');
    const glow = defs.append('filter').attr('id', 'sv-glow');
    glow.append('feGaussianBlur').attr('stdDeviation', '3').attr('result', 'coloredBlur');
    const feMerge = glow.append('feMerge');
    feMerge.append('feMergeNode').attr('in', 'coloredBlur');
    feMerge.append('feMergeNode').attr('in', 'SourceGraphic');

    // 添加阴影滤镜
    const shadow = defs.append('filter').attr('id', 'sv-shadow');
    shadow.append('feDropShadow').attr('dx', 0).attr('dy', 2).attr('stdDeviation', 3).attr('flood-opacity', 0.1);

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
            .attr('stroke', colors.link)
            .attr('stroke-width', 2),
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
            .attr('r', 12)
            .attr('fill', colors.node)
            .attr('stroke', colors.nodeStroke)
            .attr('stroke-width', 2)
            .attr('filter', 'url(#sv-shadow)');
          g.append('text')
            .attr('x', 18)
            .attr('y', 4)
            .attr('font-size', 12)
            .attr('fill', colors.text)
            .attr('font-weight', 500)
            .attr('font-family', '"Inter", system-ui, sans-serif')
            .style('text-shadow', `0 1px 2px ${colors.textBg}`);
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
