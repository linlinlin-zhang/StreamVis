import React, { useState, useEffect, useRef } from 'react';
import ChatInterface from './components/ChatInterface';
import StreamChart from './components/StreamChart';
import './App.css';

function App() {
  const [messages, setMessages] = useState([]);
  const [graphData, setGraphData] = useState({ nodes: [], links: [] });
  const ws = useRef(null);

  useEffect(() => {
    ws.current = new WebSocket('ws://localhost:8000/ws/chat');

    ws.current.onopen = () => {
      console.log('Connected to WebSocket');
    };

    ws.current.onmessage = (event) => {
      const data = JSON.parse(event.data);
      if (data.type === 'text_delta') {
        // Simple handling for text delta - in real app, append to last message
        setMessages(prev => {
            const last = prev[prev.length - 1];
            if (last && last.role === 'assistant' && last.isStreaming) {
                return [...prev.slice(0, -1), { ...last, content: data.content, isStreaming: false }];
            }
            return [...prev, { role: 'assistant', content: data.content, isStreaming: false }];
        });
      } else if (data.type === 'graph_delta') {
        // Apply graph operations
        setGraphData(prev => {
           const newNodes = [...prev.nodes];
           const newLinks = [...prev.links];
           
           data.content.forEach(op => {
               if (op.op === 'add_node') {
                   if (!newNodes.find(n => n.id === op.id)) {
                       newNodes.push({ id: op.id, ...op });
                   }
               } else if (op.op === 'add_edge') {
                   newLinks.push({ source: op.source, target: op.target });
               }
           });
           
           return { nodes: newNodes, links: newLinks };
        });
      }
    };

    return () => {
      if (ws.current) ws.current.close();
    };
  }, []);

  const sendMessage = (text) => {
    setMessages(prev => [...prev, { role: 'user', content: text }]);
    if (ws.current) {
      ws.current.send(JSON.stringify({ content: text }));
    }
  };

  return (
    <div className="app-container">
      <div className="viz-panel">
        <StreamChart data={graphData} />
      </div>
      <div className="chat-panel">
        <ChatInterface messages={messages} onSendMessage={sendMessage} />
      </div>
    </div>
  );
}

export default App;
