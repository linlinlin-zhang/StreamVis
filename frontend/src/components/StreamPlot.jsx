import React, { useEffect, useMemo, useRef } from 'react';
import * as d3 from 'd3';
import { BarChart3 } from 'lucide-react';

const StreamPlot = ({ data }) => {
  const svgRef = useRef(null);
  const points = useMemo(() => (Array.isArray(data?.points) ? data.points : []), [data]);

  // 明亮主题配色
  const colors = {
    primary: '#000000',
    primaryLight: '#374151',
    primaryDark: '#000000',
    axis: '#d1d5db',
    axisText: '#6b7280',
    grid: '#e5e7eb',
    title: '#111827',
    subtitle: '#6b7280',
    background: '#ffffff',
  };

  useEffect(() => {
    const svgEl = svgRef.current;
    if (!svgEl) return;

    const svg = d3.select(svgEl);
    const width = 980;
    const height = 620;
    const margin = { top: 80, right: 48, bottom: 72, left: 80 };

    svg.attr('viewBox', `0 0 ${width} ${height}`);
    svg.selectAll('*').remove();

    const innerW = width - margin.left - margin.right;
    const innerH = height - margin.top - margin.bottom;

    const g = svg.append('g').attr('transform', `translate(${margin.left},${margin.top})`);

    const xDomain = points.map((p) => p.x);
    const yMax = d3.max(points, (p) => p.y) ?? 1;
    const yMin = d3.min(points, (p) => p.y) ?? 0;

    const x = d3.scalePoint().domain(xDomain).range([0, innerW]).padding(0.4);
    const y = d3.scaleLinear().domain([Math.min(0, yMin), yMax]).nice().range([innerH, 0]);

    // 网格线
    const gridGroup = g.append('g').attr('class', 'grid');
    gridGroup
      .selectAll('line.horizontal')
      .data(y.ticks(6))
      .enter()
      .append('line')
      .attr('class', 'horizontal')
      .attr('x1', 0)
      .attr('x2', innerW)
      .attr('y1', (d) => y(d))
      .attr('y2', (d) => y(d))
      .attr('stroke', colors.grid)
      .attr('stroke-dasharray', '4,4');

    // X轴
    const xAxis = g.append('g').attr('transform', `translate(0,${innerH})`).call(d3.axisBottom(x).tickSize(0));
    xAxis.select('.domain').remove();
    xAxis.selectAll('text')
      .attr('fill', colors.axisText)
      .attr('font-size', 12)
      .attr('font-family', 'Inter, sans-serif')
      .attr('dy', '1.5em');

    // Y轴
    const yAxis = g.append('g').call(d3.axisLeft(y).ticks(6).tickSize(0));
    yAxis.select('.domain').remove();
    yAxis.selectAll('text')
      .attr('fill', colors.axisText)
      .attr('font-size', 12)
      .attr('font-family', 'Inter, sans-serif')
      .attr('dx', '-0.5em');

    // 渐变定义
    const defs = svg.append('defs');
    const gradient = defs.append('linearGradient')
      .attr('id', 'area-gradient')
      .attr('x1', '0%')
      .attr('y1', '0%')
      .attr('x2', '0%')
      .attr('y2', '100%');
    gradient.append('stop').attr('offset', '0%').attr('stop-color', colors.primary).attr('stop-opacity', 0.2);
    gradient.append('stop').attr('offset', '100%').attr('stop-color', colors.primary).attr('stop-opacity', 0.02);

    if (data?.chart_type === 'bar') {
      const band = d3.scaleBand().domain(xDomain).range([0, innerW]).padding(0.35);
      
      xAxis.remove();
      const newXAxis = g.append('g').attr('transform', `translate(0,${innerH})`).call(d3.axisBottom(band).tickSize(0));
      newXAxis.select('.domain').remove();
      newXAxis.selectAll('text')
        .attr('fill', colors.axisText)
        .attr('font-size', 12)
        .attr('font-family', 'Inter, sans-serif')
        .attr('dy', '1.5em');

      const bars = g.selectAll('.bar')
        .data(points)
        .enter()
        .append('rect')
        .attr('class', 'bar')
        .attr('x', (d) => band(d.x))
        .attr('y', innerH)
        .attr('width', band.bandwidth())
        .attr('height', 0)
        .attr('fill', colors.primary)
        .attr('rx', 6)
        .attr('ry', 6)
        .style('cursor', 'pointer');

      bars.transition()
        .duration(800)
        .delay((d, i) => i * 50)
        .ease(d3.easeBackOut)
        .attr('y', (d) => y(Math.max(0, d.y)))
        .attr('height', (d) => Math.abs(y(d.y) - y(0)));

      bars.on('mouseover', function() {
        d3.select(this).transition().duration(150).attr('fill', colors.primaryLight);
      }).on('mouseout', function() {
        d3.select(this).transition().duration(150).attr('fill', colors.primary);
      });

    } else {
      const area = d3.area()
        .x((d) => x(d.x) ?? 0)
        .y0(innerH)
        .y1((d) => y(d.y))
        .curve(d3.curveMonotoneX);

      g.append('path')
        .datum(points)
        .attr('fill', 'url(#area-gradient)')
        .attr('d', area);

      const line = d3.line()
        .x((d) => x(d.x) ?? 0)
        .y((d) => y(d.y))
        .curve(d3.curveMonotoneX);

      const linePath = g.append('path')
        .datum(points)
        .attr('fill', 'none')
        .attr('stroke', colors.primary)
        .attr('stroke-width', 2.5)
        .attr('stroke-linecap', 'round')
        .attr('stroke-linejoin', 'round')
        .attr('d', line);

      const totalLength = linePath.node().getTotalLength();
      linePath
        .attr('stroke-dasharray', totalLength + ' ' + totalLength)
        .attr('stroke-dashoffset', totalLength)
        .transition()
        .duration(1500)
        .ease(d3.easeCubicOut)
        .attr('stroke-dashoffset', 0);

      const dots = g.selectAll('.dot')
        .data(points)
        .enter()
        .append('circle')
        .attr('class', 'dot')
        .attr('cx', (d) => x(d.x) ?? 0)
        .attr('cy', (d) => y(d.y))
        .attr('r', 0)
        .attr('fill', colors.primary)
        .attr('stroke', colors.background)
        .attr('stroke-width', 2.5)
        .style('cursor', 'pointer');

      dots.transition()
        .delay((d, i) => 500 + i * 80)
        .duration(400)
        .ease(d3.easeBackOut)
        .attr('r', 5);

      dots.on('mouseover', function() {
        d3.select(this).transition().duration(150).attr('r', 7);
      }).on('mouseout', function() {
        d3.select(this).transition().duration(150).attr('r', 5);
      });
    }

    // 标题
    const titleGroup = svg.append('g').attr('class', 'title');
    
    titleGroup.append('text')
      .attr('x', margin.left)
      .attr('y', 42)
      .attr('fill', colors.title)
      .attr('font-size', 18)
      .attr('font-weight', 700)
      .attr('font-family', 'Inter, sans-serif')
      .text(data?.title || '数据图表');

    titleGroup.append('text')
      .attr('x', margin.left)
      .attr('y', 64)
      .attr('fill', colors.subtitle)
      .attr('font-size', 13)
      .attr('font-family', 'Inter, sans-serif')
      .text(`${data?.y_label || '数值'} · ${data?.x_label || '维度'}`);

  }, [data, points, colors]);

  if (!points.length) {
    return (
      <div className="empty-state">
        <div className="empty-icon" style={{ background: 'var(--bg-secondary)' }}>
          <BarChart3 size={32} style={{ color: 'var(--text-muted)' }} />
        </div>
        <h3 className="empty-title">图表视图</h3>
        <p className="empty-desc">
          在对话中提供可解析的数值数据<br />
          系统将自动生成对应的图表
        </p>
      </div>
    );
  }

  return <svg ref={svgRef} className="chart-svg" style={{ display: 'block' }} />;
};

export default StreamPlot;
