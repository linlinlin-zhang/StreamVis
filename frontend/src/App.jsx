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
  const [imageState, setImageState] = useState({ status: 'idle', url: '', message: '' });
  const [uploadBusy, setUploadBusy] = useState(false);
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
            const delta = data.delta ?? null;
            const baseContent = existingIndex >= 0 ? prev[existingIndex].content : '';
            const content = delta !== null ? `${baseContent}${delta}` : data.content ?? '';
            const nextMessage = {
              id: messageId,
              role: 'assistant',
              content,
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
                for (let i = links.length - 1; i >= 0; i--) {
                  if (links[i].source === op.id || links[i].target === op.id) links.splice(i, 1);
                }
              } else if (op.op === 'add_edge') {
                links.push({ source: op.source, target: op.target, id: `${op.source}__${op.target}` });
              } else if (op.op === 'remove_edge') {
                for (let i = links.length - 1; i >= 0; i--) {
                  if (links[i].source === op.source && links[i].target === op.target) links.splice(i, 1);
                  if (links[i].source === op.target && links[i].target === op.source) links.splice(i, 1);
                }
              } else if (op.op === 'clear') {
                nodeMap.clear();
                links.length = 0;
              }
            }

            const nodeIds = new Set([...nodeMap.keys()]);
            const filteredLinks = links.filter((l) => nodeIds.has(l.source) && nodeIds.has(l.target));
            return { nodes: [...nodeMap.values()], links: filteredLinks };
          });
        }

        if (data.type === 'image') {
          setImageState({
            status: data.status || 'unknown',
            url: data.url || '',
            message: data.message || '',
            prompt: data.prompt || '',
            requestId: data.request_id || '',
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
      wsRef.current.send(JSON.stringify({ type: 'user', content: trimmed }));
    }
  };

  const sendSystemContext = (content) => {
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ type: 'system', content }));
    }
  };

  const handleUploadFile = async (file) => {
    if (!file) return;
    setUploadBusy(true);
    setMessages((prev) => [...prev, { id: `sys_${Date.now()}`, role: 'system', content: `正在解析文件：${file.name}` }]);
    try {
      const form = new FormData();
      form.append('file', file);
      const resp = await fetch('http://localhost:8000/api/kimi/files/extract', { method: 'POST', body: form });
      const data = await resp.json();
      if (!resp.ok) {
        throw new Error(data?.detail || '文件解析失败');
      }
      const content = data?.content || '';
      sendSystemContext(content);
      setMessages((prev) => [...prev, { id: `sys_${Date.now()}`, role: 'system', content: `已加载文件：${data?.filename || file.name}` }]);
    } catch (e) {
      setMessages((prev) => [...prev, { id: `sys_${Date.now()}`, role: 'system', content: `文件解析失败：${e?.message || '未知错误'}` }]);
    } finally {
      setUploadBusy(false);
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
            const delta = data.delta ?? null;
            const baseContent = existingIndex >= 0 ? prev[existingIndex].content : '';
            const content = delta !== null ? `${baseContent}${delta}` : data.content ?? '';
            const nextMessage = {
              id: messageId,
              role: 'assistant',
              content,
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
              } else if (op.op === 'update_node') {
                const existing = nodeMap.get(op.id);
                if (existing) nodeMap.set(op.id, { ...existing, ...op });
              } else if (op.op === 'remove_node') {
                nodeMap.delete(op.id);
                for (let i = links.length - 1; i >= 0; i--) {
                  if (links[i].source === op.id || links[i].target === op.id) links.splice(i, 1);
                }
              } else if (op.op === 'add_edge') {
                links.push({ source: op.source, target: op.target, id: `${op.source}__${op.target}` });
              } else if (op.op === 'remove_edge') {
                for (let i = links.length - 1; i >= 0; i--) {
                  if (links[i].source === op.source && links[i].target === op.target) links.splice(i, 1);
                  if (links[i].source === op.target && links[i].target === op.source) links.splice(i, 1);
                }
              } else if (op.op === 'clear') {
                nodeMap.clear();
                links.length = 0;
              }
            }
            const nodeIds = new Set([...nodeMap.keys()]);
            const filteredLinks = links.filter((l) => nodeIds.has(l.source) && nodeIds.has(l.target));
            return { nodes: [...nodeMap.values()], links: filteredLinks };
          });
        } else if (data.type === 'image') {
          setImageState({
            status: data.status || 'unknown',
            url: data.url || '',
            message: data.message || '',
            prompt: data.prompt || '',
            requestId: data.request_id || '',
          });
        }
      };
    }, 100);
  };

  const handleClear = () => {
    setMessages([]);
    setGraphData({ nodes: [], links: [] });
    setImageState({ status: 'idle', url: '', message: '' });
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
        onUploadFile={handleUploadFile}
        uploadDisabled={connectionStatus !== 'connected' || uploadBusy}
      />
      <div className="main">
        <div className="panel viz-panel">
          <StreamChart data={graphData} />
          {imageState.status && imageState.status !== 'idle' ? (
            <div className="image-overlay">
              <div className="image-overlay-card">
                <div className="image-overlay-top">
                  <div className="image-overlay-title">AI 成图</div>
                  <button className="image-overlay-close" type="button" onClick={() => setImageState({ status: 'idle', url: '', message: '' })}>
                    关闭
                  </button>
                </div>
                {imageState.status === 'queued' || imageState.status === 'running' ? (
                  <div className="image-overlay-status">
                    {imageState.status === 'queued' ? '排队中…' : '生成中…'}
                  </div>
                ) : null}
                {imageState.status === 'failed' ? (
                  <div className="image-overlay-error">{imageState.message || '生成失败'}</div>
                ) : null}
                {imageState.status === 'disabled' ? (
                  <div className="image-overlay-error">{imageState.message || '图片服务未启用'}</div>
                ) : null}
                {imageState.status === 'succeeded' && imageState.url ? (
                  <img className="image-overlay-img" src={imageState.url} alt="AI generated" />
                ) : null}
              </div>
            </div>
          ) : null}
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
