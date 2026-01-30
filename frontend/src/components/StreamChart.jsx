import React, { useEffect, useMemo, useRef } from 'react';
import * as d3 from 'd3';

const StreamChart = ({ data }) => {
  const svgRef = useRef(null);
  const simulationRef = useRef(null);
  const rootGRef = useRef(null);
  const linksGRef = useRef(null);
  const nodesGRef = useRef(null);
  const dims = useMemo(() => ({ width: 1000, height: 700 }), []);

  // 现代化配色方案
  const colors = {
    // 节点颜色 - 使用 primary 色系的渐变
    node: {
      fill: '#0d9488',
      stroke: '#ffffff',
      strokeWidth: 2.5,
    },
    // 连线颜色
    link: {
      stroke: '#d6d3d1',
      strokeWidth: 1.5,
    },
    // 文字颜色
    text: {
      fill: '#57534e',
      fontSize: 12,
      fontWeight: 500,
    },
    // 高亮颜色
    highlight: '#14b8a6',
  };

  useEffect(() => {
    const svg = d3.select(svgRef.current);
    svg.attr('viewBox', `0 0 ${dims.width} ${dims.height}`);

    // 定义阴影滤镜
    const defs = svg.append('defs');
    
    // 节点阴影
    const dropShadow = defs.append('filter')
      .attr('id', 'node-shadow')
      .attr('x', '-50%')
      .attr('y', '-50%')
      .attr('width', '200%')
      .attr('height', '200%');
    dropShadow.append('feDropShadow')
      .attr('dx', 0)
      .attr('dy', 2)
      .attr('stdDeviation', 3)
      .attr('flood-color', 'rgba(0,0,0,0.15)');

    // 创建容器组
    const rootG = svg.append('g').attr('class', 'viz-root');
    const linksG = rootG.append('g').attr('class', 'viz-links');
    const nodesG = rootG.append('g').attr('class', 'viz-nodes');

    rootGRef.current = rootG;
    linksGRef.current = linksG;
    nodesGRef.current = nodesG;

    // 缩放功能
    const zoom = d3.zoom()
      .scaleExtent([0.3, 3])
      .on('zoom', (event) => {
        rootG.attr('transform', event.transform);
      });

    svg.call(zoom);

    // 创建力导向模拟
    simulationRef.current = d3.forceSimulation()
      .alphaDecay(0.02)
      .velocityDecay(0.3)
      .force('link', d3.forceLink().id((d) => d.id).distance(100).strength(0.5))
      .force('charge', d3.forceManyBody().strength(-300))
      .force('collide', d3.forceCollide().radius(25).strength(0.7))
      .force('center', d3.forceCenter(dims.width / 2, dims.height / 2))
      .force('x', d3.forceX(dims.width / 2).strength(0.05))
      .force('y', d3.forceY(dims.height / 2).strength(0.05));

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
    
    // 合并节点数据，保留位置信息
    const nextNodes = data.nodes.map((n) => {
      const existing = currentNodes.find((en) => en.id === n.id);
      return existing ? Object.assign(existing, n) : { ...n };
    });

    simulation.nodes(nextNodes);
    if (linkForce) linkForce.links(data.links);

    const linksG = linksGRef.current;
    const nodesG = nodesGRef.current;

    const linkKey = (d) => d.id || `${typeof d.source === 'object' ? d.source.id : d.source}__${typeof d.target === 'object' ? d.target.id : d.target}`;

    // 更新连线
    const linkSel = linksG
      .selectAll('line')
      .data(data.links, linkKey)
      .join(
        (enter) =>
          enter
            .append('line')
            .attr('stroke', colors.link.stroke)
            .attr('stroke-width', colors.link.strokeWidth)
            .attr('opacity', 0)
            .transition()
            .duration(300)
            .attr('opacity', 1),
        (update) => update,
        (exit) => exit.transition().duration(200).attr('opacity', 0).remove()
      );

    // 更新节点
    const nodeSel = nodesG
      .selectAll('g.viz-node')
      .data(nextNodes, (d) => d.id)
      .join(
        (enter) => {
          const g = enter.append('g')
            .attr('class', 'viz-node')
            .attr('cursor', 'grab')
            .call(d3.drag()
              .on('start', dragstarted)
              .on('drag', dragged)
              .on('end', dragended));

          // 节点圆圈
          g.append('circle')
            .attr('r', 0)
            .attr('fill', colors.node.fill)
            .attr('stroke', colors.node.stroke)
            .attr('stroke-width', colors.node.strokeWidth)
            .attr('filter', 'url(#node-shadow)')
            .transition()
            .duration(400)
            .ease(d3.easeBackOut)
            .attr('r', 12);

          // 节点文字
          g.append('text')
            .attr('x', 18)
            .attr('y', 4)
            .attr('font-size', colors.text.fontSize)
            .attr('font-weight', colors.text.fontWeight)
            .attr('fill', colors.text.fill)
            .attr('font-family', 'Inter, sans-serif')
            .style('pointer-events', 'none')
            .style('text-shadow', '0 1px 2px rgba(255,255,255,0.8)')
            .style('opacity', 0)
            .transition()
            .delay(200)
            .duration(300)
            .style('opacity', 1);

          return g;
        },
        (update) => update,
        (exit) => {
          exit.select('circle').transition().duration(200).attr('r', 0);
          exit.select('text').transition().duration(150).style('opacity', 0);
          exit.transition().delay(200).duration(100).remove();
        }
      );

    // 更新文字内容
    nodeSel.select('text').text((d) => d.label || d.id);

    // 拖拽函数
    function dragstarted(event, d) {
      if (!event.active) simulation.alphaTarget(0.3).restart();
      d.fx = d.x;
      d.fy = d.y;
      d3.select(this).select('circle').attr('stroke', colors.highlight);
    }

    function dragged(event, d) {
      d.fx = event.x;
      d.fy = event.y;
    }

    function dragended(event, d) {
      if (!event.active) simulation.alphaTarget(0);
      d.fx = null;
      d.fy = null;
      d3.select(this).select('circle').attr('stroke', colors.node.stroke);
    }

    // 模拟 tick
    simulation.on('tick', () => {
      linkSel
        .attr('x1', (d) => d.source.x)
        .attr('y1', (d) => d.source.y)
        .attr('x2', (d) => d.target.x)
        .attr('y2', (d) => d.target.y);

      nodeSel.attr('transform', (d) => `translate(${d.x},${d.y})`);
    });

    simulation.alpha(0.5).restart();
  }, [data]);

  return (
    <svg 
      ref={svgRef} 
      width="100%" 
      height="100%" 
      role="img" 
      aria-label="关系图谱可视化"
      style={{ display: 'block' }}
    />
  );
};

export default StreamChart;
