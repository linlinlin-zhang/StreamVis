import React, { useEffect, useMemo, useRef } from 'react';
import * as d3 from 'd3';

const StreamPlot = ({ data }) => {
  const svgRef = useRef(null);
  const points = useMemo(() => (Array.isArray(data?.points) ? data.points : []), [data]);

  // 明亮主题配色
  const colors = {
    axis: '#a8a29e',
    axisText: '#57534e',
    grid: '#e7e5e4',
    line: '#0d9488',
    lineArea: 'rgba(13, 148, 136, 0.1)',
    bar: '#0d9488',
    barHover: '#0f766e',
    dot: '#0d9488',
    dotStroke: '#ffffff',
    title: '#1c1917',
    subtitle: '#78716c',
  };

  useEffect(() => {
    const svgEl = svgRef.current;
    if (!svgEl) return;

    const svg = d3.select(svgEl);
    const width = 980;
    const height = 620;
    const margin = { top: 64, right: 40, bottom: 64, left: 72 };

    svg.attr('viewBox', `0 0 ${width} ${height}`);
    svg.selectAll('*').remove();

    const innerW = width - margin.left - margin.right;
    const innerH = height - margin.top - margin.bottom;

    const g = svg.append('g').attr('transform', `translate(${margin.left},${margin.top})`);

    const xDomain = points.map((p) => p.x);
    const yMax = d3.max(points, (p) => p.y) ?? 1;
    const yMin = d3.min(points, (p) => p.y) ?? 0;

    const x = d3.scalePoint().domain(xDomain).range([0, innerW]).padding(0.5);
    const y = d3
      .scaleLinear()
      .domain([Math.min(0, yMin), yMax])
      .nice()
      .range([innerH, 0]);

    // 网格线
    g.append('g')
      .attr('class', 'grid')
      .call(d3.axisLeft(y).ticks(6).tickSize(-innerW).tickFormat(''))
      .call((sel) => sel.selectAll('line').attr('stroke', colors.grid).attr('stroke-dasharray', '3,3'))
      .call((sel) => sel.selectAll('path').remove());

    // X轴
    g.append('g')
      .attr('transform', `translate(0,${innerH})`)
      .call(d3.axisBottom(x))
      .call((sel) => sel.selectAll('path,line').attr('stroke', colors.axis))
      .call((sel) => sel.selectAll('text').attr('fill', colors.axisText).attr('font-size', 12).attr('font-family', '"Inter", sans-serif'));

    // Y轴
    g.append('g')
      .call(d3.axisLeft(y).ticks(6))
      .call((sel) => sel.selectAll('path,line').attr('stroke', colors.axis))
      .call((sel) => sel.selectAll('text').attr('fill', colors.axisText).attr('font-size', 12).attr('font-family', '"Inter", sans-serif'));

    if (data?.chart_type === 'bar') {
      const band = d3.scaleBand().domain(xDomain).range([0, innerW]).padding(0.3);
      
      // 移除X轴重新渲染
      g.selectAll('.x-axis').remove();
      g.append('g')
        .attr('class', 'x-axis')
        .attr('transform', `translate(0,${innerH})`)
        .call(d3.axisBottom(band))
        .call((sel) => sel.selectAll('path,line').attr('stroke', colors.axis))
        .call((sel) => sel.selectAll('text').attr('fill', colors.axisText).attr('font-size', 12).attr('font-family', '"Inter", sans-serif'));

      // 柱状图
      g.selectAll('.bar')
        .data(points)
        .enter()
        .append('rect')
        .attr('class', 'bar')
        .attr('x', (d) => band(d.x))
        .attr('y', (d) => y(Math.max(0, d.y)))
        .attr('width', band.bandwidth())
        .attr('height', (d) => Math.abs(y(d.y) - y(0)))
        .attr('fill', colors.bar)
        .attr('rx', 4)
        .attr('ry', 4)
        .style('cursor', 'pointer')
        .on('mouseover', function() {
          d3.select(this).attr('fill', colors.barHover);
        })
        .on('mouseout', function() {
          d3.select(this).attr('fill', colors.bar);
        });
    } else {
      // 折线图
      const line = d3
        .line()
        .x((d) => x(d.x) ?? 0)
        .y((d) => y(d.y))
        .curve(d3.curveMonotoneX);

      // 面积填充
      const area = d3
        .area()
        .x((d) => x(d.x) ?? 0)
        .y0(innerH)
        .y1((d) => y(d.y))
        .curve(d3.curveMonotoneX);

      g.append('path')
        .datum(points)
        .attr('fill', colors.lineArea)
        .attr('d', area);

      g.append('path')
        .datum(points)
        .attr('fill', 'none')
        .attr('stroke', colors.line)
        .attr('stroke-width', 2.5)
        .attr('d', line);

      // 数据点
      g.selectAll('.dot')
        .data(points)
        .enter()
        .append('circle')
        .attr('class', 'dot')
        .attr('cx', (d) => x(d.x) ?? 0)
        .attr('cy', (d) => y(d.y))
        .attr('r', 5)
        .attr('fill', colors.dot)
        .attr('stroke', colors.dotStroke)
        .attr('stroke-width', 2)
        .style('cursor', 'pointer')
        .on('mouseover', function() {
          d3.select(this).attr('r', 7);
        })
        .on('mouseout', function() {
          d3.select(this).attr('r', 5);
        });
    }

    // 标题
    svg
      .append('text')
      .attr('x', margin.left)
      .attr('y', 32)
      .attr('fill', colors.title)
      .attr('font-size', 16)
      .attr('font-weight', 600)
      .attr('font-family', '"Inter", sans-serif')
      .text(data?.title || '图表');

    // 副标题
    svg
      .append('text')
      .attr('x', margin.left)
      .attr('y', 52)
      .attr('fill', colors.subtitle)
      .attr('font-size', 12)
      .attr('font-family', '"Inter", sans-serif')
      .text(`${data?.y_label || '值'} vs ${data?.x_label || '维度'}`);
  }, [data, points]);

  if (!points.length) {
    return (
      <div className="viz-empty">
        <div className="viz-empty-card">
          <h3 className="viz-empty-title">📊 图表视图</h3>
          <p className="viz-empty-desc">在对话中提供可解析的数值序列（如 Q1 X=120），系统会生成趋势图。</p>
        </div>
      </div>
    );
  }

  return <svg ref={svgRef} className="chart-svg" />;
};

export default StreamPlot;
