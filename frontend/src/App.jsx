import React, { useState, useEffect, useRef } from 'react';
import ChatInterface from './components/ChatInterface';
import StreamChart from './components/StreamChart';
import TopBar from './components/TopBar';
import './App.css';

function App() {
  const [messages, setMessages] = useState([]);
  const [graphData, setGraphData] = useState({ nodes: [], links: [] });
  const [connectionStatus, setConnectionStatus] = useState('connecting');
  const [connectionError, setConnectionError] = useState('');
  const wsRef = useRef(null);
  const reconnectTimerRef = useRef(null);
  const shouldReconnectRef = useRef(true);

  useEffect(() => {
    const connect = () => {
      setConnectionStatus('connecting');
      setConnectionError('');
      const ws = new WebSocket('ws://localhost:8000/ws/chat');
      wsRef.current = ws;

      ws.onopen = () => {
        setConnectionStatus('connected');
      };

      ws.onmessage = (event) => {
        const data = JSON.parse(event.data);

        if (data.type === 'text_delta') {
          setMessages((prev) => {
            const messageId = data.message_id || 'assistant';
            const existingIndex = prev.findIndex((m) => m.id === messageId);
            const nextMessage = {
              id: messageId,
              role: 'assistant',
              content: data.content ?? data.delta ?? '',
              isFinal: Boolean(data.is_final ?? true),
            };

            if (existingIndex >= 0) {
              const updated = [...prev];
              updated[existingIndex] = nextMessage;
              return updated;
            }

            return [...prev, nextMessage];
          });
          return;
        }

        if (data.type === 'graph_delta') {
          setGraphData((prev) => {
            const nodeMap = new Map(prev.nodes.map((n) => [n.id, n]));
            const links = [...prev.links];
            const ops = Array.isArray(data.content) ? data.content : Array.isArray(data.ops) ? data.ops : [];

            for (const op of ops) {
              if (op.op === 'add_node') {
                if (!nodeMap.has(op.id)) nodeMap.set(op.id, { ...op });
              } else if (op.op === 'update_node') {
                const existing = nodeMap.get(op.id);
                if (existing) nodeMap.set(op.id, { ...existing, ...op });
              } else if (op.op === 'remove_node') {
                nodeMap.delete(op.id);
              } else if (op.op === 'add_edge') {
                links.push({ source: op.source, target: op.target, id: `${op.source}__${op.target}` });
              } else if (op.op === 'clear') {
                nodeMap.clear();
                links.length = 0;
              }
            }

            return { nodes: [...nodeMap.values()], links };
          });
        }
      };
      ws.onerror = () => {
        setConnectionStatus('error');
        setConnectionError('WebSocket 连接失败');
      };

      ws.onclose = () => {
        if (!shouldReconnectRef.current) return;
        setConnectionStatus('closed');
        reconnectTimerRef.current = window.setTimeout(connect, 1500);
      };
    };

    connect();

    return () => {
      shouldReconnectRef.current = false;
      if (reconnectTimerRef.current) window.clearTimeout(reconnectTimerRef.current);
      if (wsRef.current) wsRef.current.close();
    };
  }, []);

  const sendMessage = (text) => {
    const trimmed = text.trim();
    if (!trimmed) return;
    setMessages((prev) => [...prev, { id: `user_${Date.now()}`, role: 'user', content: trimmed }]);
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ content: trimmed }));
    }
  };

  const handleReconnect = () => {
    shouldReconnectRef.current = true;
    if (reconnectTimerRef.current) window.clearTimeout(reconnectTimerRef.current);
    if (wsRef.current) wsRef.current.close();
    setConnectionStatus('connecting');
    setConnectionError('');
    reconnectTimerRef.current = window.setTimeout(() => {
      shouldReconnectRef.current = true;
      const ws = new WebSocket('ws://localhost:8000/ws/chat');
      wsRef.current = ws;
      ws.onopen = () => setConnectionStatus('connected');
      ws.onerror = () => {
        setConnectionStatus('error');
        setConnectionError('WebSocket 连接失败');
      };
      ws.onclose = () => {
        if (!shouldReconnectRef.current) return;
        setConnectionStatus('closed');
      };
      ws.onmessage = (event) => {
        const data = JSON.parse(event.data);
        if (data.type === 'text_delta') {
          setMessages((prev) => {
            const messageId = data.message_id || 'assistant';
            const existingIndex = prev.findIndex((m) => m.id === messageId);
            const nextMessage = {
              id: messageId,
              role: 'assistant',
              content: data.content ?? data.delta ?? '',
              isFinal: Boolean(data.is_final ?? true),
            };
            if (existingIndex >= 0) {
              const updated = [...prev];
              updated[existingIndex] = nextMessage;
              return updated;
            }
            return [...prev, nextMessage];
          });
        } else if (data.type === 'graph_delta') {
          setGraphData((prev) => {
            const nodeMap = new Map(prev.nodes.map((n) => [n.id, n]));
            const links = [...prev.links];
            const ops = Array.isArray(data.content) ? data.content : Array.isArray(data.ops) ? data.ops : [];
            for (const op of ops) {
              if (op.op === 'add_node') {
                if (!nodeMap.has(op.id)) nodeMap.set(op.id, { ...op });
              } else if (op.op === 'add_edge') {
                links.push({ source: op.source, target: op.target, id: `${op.source}__${op.target}` });
              } else if (op.op === 'clear') {
                nodeMap.clear();
                links.length = 0;
              }
            }
            return { nodes: [...nodeMap.values()], links };
          });
        }
      };
    }, 100);
  };

  const handleClear = () => {
    setMessages([]);
    setGraphData({ nodes: [], links: [] });
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ type: 'clear' }));
    }
  };

  const statusText =
    connectionStatus === 'connected'
      ? '已连接'
      : connectionStatus === 'connecting'
        ? '连接中'
        : connectionStatus === 'error'
          ? connectionError || '错误'
          : '已断开';

  return (
    <div className="app-shell">
      <TopBar
        status={connectionStatus}
        statusText={statusText}
        onReconnect={handleReconnect}
        onClear={handleClear}
      />
      <div className="main">
        <div className="panel viz-panel">
          <StreamChart data={graphData} />
          {graphData.nodes.length === 0 ? (
            <div className="viz-empty">
              <div className="viz-empty-card">
                <h3 className="viz-empty-title">增量可视化</h3>
                <p className="viz-empty-desc">
                  在右侧输入对数据的描述或问题；当系统判断需要可视化时，会以增量方式更新图结构，尽量保持布局稳定。
                </p>
              </div>
            </div>
          ) : null}
        </div>
        <div className="panel chat-panel">
          <ChatInterface
            messages={messages}
            onSendMessage={sendMessage}
            disabled={connectionStatus !== 'connected'}
          />
        </div>
      </div>
    </div>
  );
}

export default App;
