import React, { useState, useEffect, useRef } from 'react';
import ChatInterface from './components/ChatInterface';
import StreamChart from './components/StreamChart';
import StreamPlot from './components/StreamPlot';
import TopBar from './components/TopBar';
import VoicePrintModal from './components/VoicePrintModal';
import './App.css';

function App() {
  const [messages, setMessages] = useState([]);
  const [graphData, setGraphData] = useState({ nodes: [], links: [] });
  const [connectionStatus, setConnectionStatus] = useState('connecting');
  const [connectionError, setConnectionError] = useState('');
  const [imageState, setImageState] = useState({ status: 'idle', url: '', message: '' });
  const [chartData, setChartData] = useState(null);
  const [vizMode, setVizMode] = useState('graph');
  const [uploadBusy, setUploadBusy] = useState(false);
  const [asrActive, setAsrActive] = useState(false);
  const [asrStatus, setAsrStatus] = useState('idle');
  const [voicePrintOpen, setVoicePrintOpen] = useState(false);
  const [voicePrints, setVoicePrints] = useState(() => {
    try {
      return JSON.parse(localStorage.getItem('streamvis_voiceprints') || '{}');
    } catch {
      return {};
    }
  });
  const wsRef = useRef(null);
  const reconnectTimerRef = useRef(null);
  const shouldReconnectRef = useRef(true);

  const asrWsRef = useRef(null);
  const micStreamRef = useRef(null);
  const audioCtxRef = useRef(null);
  const sourceRef = useRef(null);
  const processorRef = useRef(null);
  const sendTimerRef = useRef(null);
  const byteChunksRef = useRef([]);
  const mediaRecorderRef = useRef(null);
  const recordChunksRef = useRef([]);

  useEffect(() => {
    localStorage.setItem('streamvis_voiceprints', JSON.stringify(voicePrints || {}));
  }, [voicePrints]);

  const speakerLabel = (spk) => {
    const s = String(spk || 'spk0');
    const m = s.match(/^spk(\d+)$/);
    if (m) return `发言人${Number(m[1]) + 1}`;
    return s;
  };

  const downsampleTo16k = (buffer, inputSampleRate) => {
    const outputSampleRate = 16000;
    if (inputSampleRate === outputSampleRate) {
      const out = new Int16Array(buffer.length);
      for (let i = 0; i < buffer.length; i++) out[i] = Math.max(-1, Math.min(1, buffer[i])) * 0x7fff;
      return out;
    }
    const ratio = inputSampleRate / outputSampleRate;
    const newLength = Math.round(buffer.length / ratio);
    const out = new Int16Array(newLength);
    let offsetResult = 0;
    let offsetBuffer = 0;
    while (offsetResult < out.length) {
      const nextOffsetBuffer = Math.round((offsetResult + 1) * ratio);
      let accum = 0;
      let count = 0;
      for (let i = offsetBuffer; i < nextOffsetBuffer && i < buffer.length; i++) {
        accum += buffer[i];
        count++;
      }
      const sample = count ? accum / count : 0;
      out[offsetResult] = Math.max(-1, Math.min(1, sample)) * 0x7fff;
      offsetResult++;
      offsetBuffer = nextOffsetBuffer;
    }
    return out;
  };

  const int16ToU8 = (pcm16) => {
    const out = new Uint8Array(pcm16.length * 2);
    for (let i = 0; i < pcm16.length; i++) {
      const v = pcm16[i];
      out[i * 2] = v & 0xff;
      out[i * 2 + 1] = (v >> 8) & 0xff;
    }
    return out;
  };

  const feedChatBackend = (text, spk) => {
    const trimmed = String(text || '').trim();
    if (!trimmed) return;
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ type: 'user', content: `【${speakerLabel(spk)}】${trimmed}` }));
    }
  };

  const upsertTranscriptMessage = (segmentId, spk, text, isFinal) => {
    const msgId = `asr_${segmentId}`;
    setMessages((prev) => {
      const idx = prev.findIndex((m) => m.id === msgId);
      const next = { id: msgId, role: 'user', speaker: speakerLabel(spk), content: text, isFinal: Boolean(isFinal) };
      if (idx >= 0) {
        const updated = [...prev];
        updated[idx] = { ...updated[idx], ...next };
        return updated;
      }
      return [...prev, next];
    });
  };

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

        if (data.type === 'chart_delta') {
          setChartData({
            chart_type: data.chart_type || 'line',
            title: data.title || '',
            x_label: data.x_label || '',
            y_label: data.y_label || '',
            series_name: data.series_name || '',
            points: Array.isArray(data.points) ? data.points : [],
          });
          setVizMode('chart');
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
      const resp = await fetch('http://localhost:8000/api/kimi/files/index', { method: 'POST', body: form });
      const data = await resp.json();
      if (!resp.ok) {
        throw new Error(data?.detail || '文件解析失败');
      }
      const systemContext = data?.system_context || '';
      if (systemContext) sendSystemContext(systemContext);
      const chunks = data?.chunks_indexed ?? null;
      setMessages((prev) => [
        ...prev,
        { id: `sys_${Date.now()}`, role: 'system', content: `已索引文件：${data?.filename || file.name}${chunks !== null ? `（${chunks} 段）` : ''}` },
      ]);
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
    setChartData(null);
    setVizMode('graph');
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ type: 'clear' }));
    }
  };

  const stopAsr = async () => {
    setAsrActive(false);
    setAsrStatus('stopping');
    try {
      if (sendTimerRef.current) window.clearInterval(sendTimerRef.current);
      sendTimerRef.current = null;
      processorRef.current?.disconnect();
      sourceRef.current?.disconnect();
      await audioCtxRef.current?.close();
      micStreamRef.current?.getTracks()?.forEach((t) => t.stop());
    } catch {
    } finally {
      processorRef.current = null;
      sourceRef.current = null;
      audioCtxRef.current = null;
      micStreamRef.current = null;
      byteChunksRef.current = [];
    }

    try {
      if (mediaRecorderRef.current && mediaRecorderRef.current.state !== 'inactive') mediaRecorderRef.current.stop();
    } catch {
    }

    try {
      if (asrWsRef.current && asrWsRef.current.readyState === WebSocket.OPEN) {
        asrWsRef.current.send(JSON.stringify({ type: 'stop' }));
      }
      asrWsRef.current?.close();
    } catch {
    } finally {
      asrWsRef.current = null;
    }
    setAsrStatus('idle');
  };

  const startAsr = async () => {
    setAsrStatus('connecting');
    setAsrActive(true);
    const ws = new WebSocket('ws://localhost:8000/ws/asr');
    ws.binaryType = 'arraybuffer';
    asrWsRef.current = ws;

    ws.onmessage = (event) => {
      let data = null;
      try {
        data = JSON.parse(event.data);
      } catch {
        return;
      }
      if (data.type === 'transcript_delta') {
        upsertTranscriptMessage(data.segment_id, data.speaker, data.text || '', data.is_final);
        if (data.is_final) {
          feedChatBackend(data.text || '', data.speaker);
        }
        return;
      }
      if (data.type === 'text_delta' && (data.message_id || '').startsWith('sys_asr')) {
        setMessages((prev) => [...prev, { id: data.message_id, role: 'system', content: data.content || '' }]);
      }
    };
    ws.onerror = () => setAsrStatus('error');
    ws.onclose = () => {
      if (asrActive) setAsrStatus('idle');
    };

    ws.onopen = async () => {
      setAsrStatus('running');
      const featureIds = Object.values(voicePrints || {}).join(',');
      ws.send(JSON.stringify({ type: 'start', feature_ids: featureIds, eng_spk_match: featureIds ? 1 : 0 }));

      try {
        const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
        micStreamRef.current = stream;

        try {
          const rec = new MediaRecorder(stream);
          recordChunksRef.current = [];
          rec.ondataavailable = (e) => {
            if (e.data && e.data.size) recordChunksRef.current.push(e.data);
          };
          rec.onstop = () => {
            if (!recordChunksRef.current.length) return;
            const blob = new Blob(recordChunksRef.current, { type: 'audio/webm' });
            const url = URL.createObjectURL(blob);
            setMessages((prev) => [...prev, { id: `rec_${Date.now()}`, role: 'system', content: `录音已保存（本地）：${url}` }]);
          };
          mediaRecorderRef.current = rec;
          rec.start(1000);
        } catch {
        }

        const audioCtx = new (window.AudioContext || window.webkitAudioContext)();
        audioCtxRef.current = audioCtx;
        const source = audioCtx.createMediaStreamSource(stream);
        sourceRef.current = source;
        const processor = audioCtx.createScriptProcessor(4096, 1, 1);
        processorRef.current = processor;
        processor.onaudioprocess = (e) => {
          if (!asrWsRef.current || asrWsRef.current.readyState !== WebSocket.OPEN) return;
          const data = e.inputBuffer.getChannelData(0);
          const pcm16 = downsampleTo16k(data, audioCtx.sampleRate);
          const u8 = int16ToU8(pcm16);
          byteChunksRef.current.push(u8);
        };
        source.connect(processor);
        processor.connect(audioCtx.destination);

        const frameBytes = 1280;
        sendTimerRef.current = window.setInterval(() => {
          const sock = asrWsRef.current;
          if (!sock || sock.readyState !== WebSocket.OPEN) return;
          let need = frameBytes;
          const parts = [];
          while (need > 0 && byteChunksRef.current.length) {
            const head = byteChunksRef.current[0];
            if (head.length <= need) {
              parts.push(head);
              byteChunksRef.current.shift();
              need -= head.length;
            } else {
              parts.push(head.slice(0, need));
              byteChunksRef.current[0] = head.slice(need);
              need = 0;
            }
          }
          if (parts.length && need === 0) {
            const out = new Uint8Array(frameBytes);
            let off = 0;
            for (const p of parts) {
              out.set(p, off);
              off += p.length;
            }
            sock.send(out);
          }
        }, 40);
      } catch (e) {
        setAsrStatus('error');
        setMessages((prev) => [...prev, { id: `asr_err_${Date.now()}`, role: 'system', content: `麦克风启动失败：${e?.message || '未知错误'}` }]);
        stopAsr();
      }
    };
  };

  const toggleAsr = () => {
    if (asrActive) stopAsr();
    else startAsr();
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
        onToggleVoice={toggleAsr}
        voiceActive={asrActive}
        voiceDisabled={connectionStatus !== 'connected'}
        onOpenVoicePrint={() => setVoicePrintOpen(true)}
      />
      <div className="main">
        <div className="panel viz-panel">
          <div className="viz-toolbar">
            <button className={`viz-tab ${vizMode === 'chart' ? 'active' : ''}`} type="button" onClick={() => setVizMode('chart')} disabled={!chartData}>
              图表
            </button>
            <button className={`viz-tab ${vizMode === 'graph' ? 'active' : ''}`} type="button" onClick={() => setVizMode('graph')}>
              图谱
            </button>
          </div>
          {vizMode === 'chart' ? <StreamPlot data={chartData} /> : <StreamChart data={graphData} />}
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
      <VoicePrintModal
        open={voicePrintOpen}
        onClose={() => setVoicePrintOpen(false)}
        onRegistered={({ speakerName, featureId }) => {
          setVoicePrints((prev) => ({ ...(prev || {}), [speakerName]: featureId }));
        }}
      />
    </div>
  );
}

export default App;
