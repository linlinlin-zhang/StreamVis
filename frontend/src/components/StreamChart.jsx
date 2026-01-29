import React, { useEffect, useRef } from 'react';
import * as d3 from 'd3';

const StreamChart = ({ data }) => {
  const svgRef = useRef(null);
  const simulationRef = useRef(null);

  useEffect(() => {
    const width = 800;
    const height = 600;

    if (!simulationRef.current) {
        // Initialize simulation
        simulationRef.current = d3.forceSimulation()
            .force("link", d3.forceLink().id(d => d.id).distance(100))
            .force("charge", d3.forceManyBody().strength(-300))
            .force("center", d3.forceCenter(width / 2, height / 2));
    }

    const svg = d3.select(svgRef.current);
    svg.selectAll("*").remove(); // Simple clear for demo

    const simulation = simulationRef.current;
    
    // Update nodes and links
    // We need to preserve existing node objects to keep their x, y, vx, vy
    const currentNodes = simulation.nodes();
    const newNodes = data.nodes.map(n => {
        const existing = currentNodes.find(en => en.id === n.id);
        return existing ? existing : { ...n };
    });
    
    simulation.nodes(newNodes);
    simulation.force("link").links(data.links);
    simulation.alpha(1).restart();

    const link = svg.append("g")
        .attr("stroke", "#999")
        .attr("stroke-opacity", 0.6)
        .selectAll("line")
        .data(data.links)
        .join("line")
        .attr("stroke-width", 2);

    const node = svg.append("g")
        .attr("stroke", "#fff")
        .attr("stroke-width", 1.5)
        .selectAll("circle")
        .data(newNodes)
        .join("circle")
        .attr("r", 10)
        .attr("fill", "#69b3a2")
        .call(drag(simulation));
        
    node.append("title")
        .text(d => d.id);

    simulation.on("tick", () => {
        link
            .attr("x1", d => d.source.x)
            .attr("y1", d => d.source.y)
            .attr("x2", d => d.target.x)
            .attr("y2", d => d.target.y);

        node
            .attr("cx", d => d.x)
            .attr("cy", d => d.y);
    });

    function drag(simulation) {
      function dragstarted(event) {
        if (!event.active) simulation.alphaTarget(0.3).restart();
        event.subject.fx = event.subject.x;
        event.subject.fy = event.subject.y;
      }

      function dragged(event) {
        event.subject.fx = event.x;
        event.subject.fy = event.y;
      }

      function dragended(event) {
        if (!event.active) simulation.alphaTarget(0);
        event.subject.fx = null;
        event.subject.fy = null;
      }

      return d3.drag()
          .on("start", dragstarted)
          .on("drag", dragged)
          .on("end", dragended);
    }

    return () => {
       // Cleanup if needed
    };

  }, [data]);

  return (
    <svg ref={svgRef} width="100%" height="100%" viewBox="0 0 800 600"></svg>
  );
};

export default StreamChart;
