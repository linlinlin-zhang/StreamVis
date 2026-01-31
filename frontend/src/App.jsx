import React, { useState, useEffect, useRef, useCallback } from 'react';
import { 
  Mic, MicOff, Users, FileText, Settings, 
  Radio, Activity, Brain, Zap, X, Plus,
  ChevronRight, ChevronLeft, Volume2, VolumeX,
  Share2, Download, RotateCcw, MoreHorizontal,
  MessageSquare, GitGraph, BarChart3, Image as ImageIcon,
  Wifi, WifiOff, Clock, Hash, Sparkles
} from 'lucide-react';
import ChatInterface from './components/ChatInterface';
import StreamChart from './components/StreamChart';
import StreamPlot from './components/StreamPlot';
import VoicePrintModal from './components/VoicePrintModal';
import SpeakerPanel from './components/SpeakerPanel';
import IntentPanel from './components/IntentPanel';
import MemoryPanel from './components/MemoryPanel';
import './App.css';

// 会话模式
const SESSION_MODES = {
  CHAT: 'chat',       // 普通对话
  MEETING: 'meeting', // 会议模式（多人语音）
  BRAINSTORM: 'brainstorm', // 头脑风暴
};

// 可视化模式
const VIZ_MODES = {
  GRAPH: 'graph',   // 知识图谱
  CHART: 'chart',   // 数据图表
  BOTH: 'both',     // 并列
};

function App() {
  // ========== 连接状态 ==========
  const [connectionStatus, setConnectionStatus] = useState('connecting');
  const [connectionError, setConnectionError] = useState('');
  
  // ========== 会话状态 ==========
  const [sessionMode, setSessionMode] = useState(SESSION_MODES.CHAT);
  const [messages, setMessages] = useState([]);
  const [graphData, setGraphData] = useState({ nodes: [], links: [] });
  const [chartData, setChartData] = useState(null);
  const [vizMode, setVizMode] = useState(VIZ_MODES.GRAPH);
  
  // ========== 实时语音状态 ==========
  const [asrActive, setAsrActive] = useState(false);
  const [asrStatus, setAsrStatus] = useState('idle');
  const [currentTranscript, setCurrentTranscript] = useState('');
  const [currentSpeaker, setCurrentSpeaker] = useState('');
  
  // ========== 说话人管理 ==========
  const [speakers, setSpeakers] = useState({}); // { spk0: { name: '张三', color: '#3b82f6' } }
  const [voicePrints, setVoicePrints] = useState(() => {
    try {
      const raw = JSON.parse(localStorage.getItem('streamvis_voiceprints') || '{}') || {};
      const out = {};
      for (const [name, val] of Object.entries(raw)) {
        if (typeof val === 'string') out[name] = { featureId: val, enabled: true };
        else if (val && typeof val === 'object') out[name] = { featureId: val.featureId || '', enabled: Boolean(val.enabled ?? true) };
      }
      return out;
    } catch { return {}; }
  });
  
  // ========== 意图可视化 ==========
  const [currentIntent, setCurrentIntent] = useState(null);
  const [intentHistory, setIntentHistory] = useState([]);
  
  // ========== AI 成图 ==========
  const [imageState, setImageState] = useState({ status: 'idle', url: '', message: '' });
  
  // ========== 面板显示状态 ==========
  const [showSpeakerPanel, setShowSpeakerPanel] = useState(false);
  const [showIntentPanel, setShowIntentPanel] = useState(false);
  const [showMemoryPanel, setShowMemoryPanel] = useState(false);
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const [voicePrintOpen, setVoicePrintOpen] = useState(false);
  
  // ========== Refs ==========
  const wsRef = useRef(null);
  const asrWsRef = useRef(null);
  const reconnectTimerRef = useRef(null);
  const shouldReconnectRef = useRef(true);
  const fileInputRef = useRef(null);
  
  // 音频相关 refs
  const micStreamRef = useRef(null);
  const audioCtxRef = useRef(null);
  const processorRef = useRef(null);
  const sourceRef = useRef(null);
  const sendTimerRef = useRef(null);
  const byteChunksRef = useRef([]);

  // ========== 初始化 ==========
  useEffect(() => {
    localStorage.setItem('streamvis_voiceprints', JSON.stringify(voicePrints));
  }, [voicePrints]);

  // ========== WebSocket 连接 ==========
  useEffect(() => {
    const connect = () => {
      setConnectionStatus('connecting');
      const ws = new WebSocket('ws://localhost:8000/ws/chat');
      wsRef.current = ws;

      ws.onopen = () => setConnectionStatus('connected');

      ws.onmessage = (event) => {
        const data = JSON.parse(event.data);
        handleWebSocketMessage(data);
      };

      ws.onerror = () => {
        setConnectionStatus('error');
        setConnectionError('连接失败');
      };

      ws.onclose = () => {
        if (!shouldReconnectRef.current) return;
        setConnectionStatus('closed');
        reconnectTimerRef.current = setTimeout(connect, 2000);
      };
    };

    connect();
    return () => {
      shouldReconnectRef.current = false;
      if (reconnectTimerRef.current) clearTimeout(reconnectTimerRef.current);
      if (wsRef.current) wsRef.current.close();
    };
  }, []);

  // ========== 消息处理 ==========
  const handleWebSocketMessage = useCallback((data) => {
    switch (data.type) {
      case 'text_delta':
        setMessages(prev => {
          const idx = prev.findIndex(m => m.id === data.message_id);
          const content = data.delta != null 
            ? (prev[idx]?.content || '') + data.delta 
            : data.content;
          const msg = { 
            id: data.message_id, 
            role: 'assistant', 
            content,
            isFinal: data.is_final,
            intent: data.intent,
            timestamp: Date.now()
          };
          if (idx >= 0) {
            const updated = [...prev];
            updated[idx] = msg;
            return updated;
          }
          return [...prev, msg];
        });
        
        // 更新意图
        if (data.intent) {
          setCurrentIntent(data.intent);
          if (data.is_final) {
            setIntentHistory(prev => [...prev.slice(-19), { ...data.intent, timestamp: Date.now() }]);
          }
        }
        break;

      case 'graph_delta':
        setGraphData(prev => {
          const nodeMap = new Map(prev.nodes.map(n => [n.id, n]));
          const links = [...prev.links];
          const ops = data.ops || [];

          for (const op of ops) {
            switch (op.op) {
              case 'add_node':
                if (!nodeMap.has(op.id)) nodeMap.set(op.id, { ...op });
                break;
              case 'update_node':
                const existing = nodeMap.get(op.id);
                if (existing) nodeMap.set(op.id, { ...existing, ...op });
                break;
              case 'remove_node':
                nodeMap.delete(op.id);
                for (let i = links.length - 1; i >= 0; i--) {
                  if (links[i].source === op.id || links[i].target === op.id) links.splice(i, 1);
                }
                break;
              case 'add_edge':
                links.push({ source: op.source, target: op.target, id: `${op.source}__${op.target}` });
                break;
              case 'remove_edge':
                for (let i = links.length - 1; i >= 0; i--) {
                  if (links[i].source === op.source && links[i].target === op.target) links.splice(i, 1);
                }
                break;
              case 'clear':
                nodeMap.clear();
                links.length = 0;
                break;
            }
          }

          const nodeIds = new Set([...nodeMap.keys()]);
          return { 
            nodes: [...nodeMap.values()], 
            links: links.filter(l => nodeIds.has(l.source) && nodeIds.has(l.target)) 
          };
        });
        break;

      case 'chart_delta':
        setChartData({
          chart_type: data.chart_type || 'line',
          title: data.title || '',
          x_label: data.x_label || '',
          y_label: data.y_label || '',
          series_name: data.series_name || '',
          points: data.points || [],
        });
        if (vizMode === VIZ_MODES.GRAPH) setVizMode(VIZ_MODES.BOTH);
        break;

      case 'image':
        setImageState({
          status: data.status,
          url: data.url || '',
          message: data.message || '',
          prompt: data.prompt || '',
        });
        break;

      case 'transcript_delta':
        // 实时语音转写
        const speakerKey = data.speaker || 'spk0';
        const speakerName = speakers[speakerKey]?.name || `发言人${parseInt(speakerKey.replace('spk', '')) + 1}`;
        
        setCurrentTranscript(data.text);
        setCurrentSpeaker(speakerKey);
        
        if (data.is_final) {
          setMessages(prev => [...prev, {
            id: `asr_${data.segment_id}_${Date.now()}`,
            role: 'user',
            content: data.text,
            speaker: speakerName,
            speakerKey,
            isFinal: true,
            timestamp: Date.now(),
            type: 'voice'
          }]);
          setCurrentTranscript('');
          
          // 自动发送到 AI 分析
          if (wsRef.current?.readyState === WebSocket.OPEN) {
            wsRef.current.send(JSON.stringify({ 
              type: 'user', 
              content: `【${speakerName}】${data.text}` 
            }));
          }
        }
        break;
    }
  }, [speakers, vizMode]);

  // ========== 发送消息 ==========
  const sendMessage = useCallback((text) => {
    if (!text.trim()) return;
    setMessages(prev => [...prev, {
      id: `user_${Date.now()}`,
      role: 'user',
      content: text,
      timestamp: Date.now()
    }]);
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ type: 'user', content: text }));
    }
  }, []);

  // ========== 清空会话 ==========
  const handleClear = useCallback(() => {
    setMessages([]);
    setGraphData({ nodes: [], links: [] });
    setChartData(null);
    setImageState({ status: 'idle', url: '', message: '' });
    setCurrentIntent(null);
    setIntentHistory([]);
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ type: 'clear' }));
    }
  }, []);

  // ========== 文件上传 ==========
  const handleFileUpload = useCallback(async (file) => {
    if (!file) return;
    setMessages(prev => [...prev, {
      id: `sys_${Date.now()}`,
      role: 'system',
      content: `正在解析文件：${file.name}`,
      timestamp: Date.now()
    }]);
    
    try {
      const form = new FormData();
      form.append('file', file);
      const resp = await fetch('http://localhost:8000/api/kimi/files/index', { 
        method: 'POST', 
        body: form 
      });
      const data = await resp.json();
      if (!resp.ok) throw new Error(data?.detail || '解析失败');
      
      if (data.system_context) {
        wsRef.current?.send(JSON.stringify({ type: 'system', content: data.system_context }));
      }
      
      setMessages(prev => [...prev, {
        id: `sys_${Date.now()}`,
        role: 'system',
        content: `✓ 已索引文件「${data.filename}」(${data.chunks_indexed} 段)`,
        timestamp: Date.now()
      }]);
    } catch (e) {
      setMessages(prev => [...prev, {
        id: `sys_${Date.now()}`,
        role: 'system',
        content: `✗ 文件解析失败：${e.message}`,
        timestamp: Date.now()
      }]);
    }
  }, []);

  // ========== 实时语音控制 ==========
  const toggleASR = useCallback(async () => {
    if (asrActive) {
      // 停止录音
      setAsrActive(false);
      setAsrStatus('stopping');
      
      if (sendTimerRef.current) clearInterval(sendTimerRef.current);
      processorRef.current?.disconnect();
      sourceRef.current?.disconnect();
      await audioCtxRef.current?.close();
      micStreamRef.current?.getTracks()?.forEach(t => t.stop());
      
      asrWsRef.current?.send(JSON.stringify({ type: 'stop' }));
      asrWsRef.current?.close();
      setAsrStatus('idle');
    } else {
      // 开始录音
      setAsrActive(true);
      setAsrStatus('connecting');
      
      const ws = new WebSocket('ws://localhost:8000/ws/asr');
      ws.binaryType = 'arraybuffer';
      asrWsRef.current = ws;

      ws.onopen = async () => {
        setAsrStatus('recording');
        const featureIds = Object.values(voicePrints)
          .filter((v) => v && v.enabled && v.featureId)
          .map((v) => v.featureId)
          .join(',');
        ws.send(JSON.stringify({ 
          type: 'start', 
          feature_ids: featureIds,
          eng_spk_match: featureIds ? 1 : 0
        }));

        try {
          const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
          micStreamRef.current = stream;
          
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

          // 定时发送音频帧
          const frameBytes = 1280;
          sendTimerRef.current = setInterval(() => {
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
              for (const p of parts) { out.set(p, off); off += p.length; }
              sock.send(out);
            }
          }, 40);
        } catch (e) {
          setAsrStatus('error');
          setAsrActive(false);
        }
      };

      ws.onmessage = (event) => {
        const data = JSON.parse(event.data);
        handleWebSocketMessage(data);
      };

      ws.onerror = () => setAsrStatus('error');
      ws.onclose = () => setAsrActive(false);
    }
  }, [asrActive, voicePrints, handleWebSocketMessage]);

  // ========== 音频处理辅助函数 ==========
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

  // ========== 渲染 ==========
  return (
    <div className="app">
      {/* 左侧边栏 */}
      <aside className={`sidebar ${sidebarCollapsed ? 'collapsed' : ''}`}>
        <div className="sidebar-header">
          <div className="logo">
            <div className="logo-icon">
              <Activity size={20} />
            </div>
            {!sidebarCollapsed && (
              <div className="logo-text">
                <span className="logo-title">StreamVis</span>
                <span className="logo-badge">PRO</span>
              </div>
            )}
          </div>
          <button 
            className="sidebar-toggle" 
            onClick={() => setSidebarCollapsed(!sidebarCollapsed)}
          >
            {sidebarCollapsed ? <ChevronRight size={16} /> : <ChevronLeft size={16} />}
          </button>
        </div>

        {!sidebarCollapsed && (
          <>
            {/* 模式切换 */}
            <div className="mode-selector">
              <div className="section-title">会话模式</div>
              <div className="mode-buttons">
                <button 
                  className={`mode-btn ${sessionMode === SESSION_MODES.CHAT ? 'active' : ''}`}
                  onClick={() => setSessionMode(SESSION_MODES.CHAT)}
                >
                  <MessageSquare size={16} />
                  <span>对话</span>
                </button>
                <button 
                  className={`mode-btn ${sessionMode === SESSION_MODES.MEETING ? 'active' : ''}`}
                  onClick={() => setSessionMode(SESSION_MODES.MEETING)}
                >
                  <Users size={16} />
                  <span>会议</span>
                </button>
                <button 
                  className={`mode-btn ${sessionMode === SESSION_MODES.BRAINSTORM ? 'active' : ''}`}
                  onClick={() => setSessionMode(SESSION_MODES.BRAINSTORM)}
                >
                  <Zap size={16} />
                  <span>头脑风暴</span>
                </button>
              </div>
            </div>

            {/* 快捷操作 */}
            <div className="quick-actions">
              <div className="section-title">快捷操作</div>
              <button className="action-btn" onClick={handleClear}>
                <Plus size={16} />
                <span>新建会话</span>
              </button>
              <button 
                className="action-btn" 
                onClick={() => fileInputRef.current?.click()}
              >
                <FileText size={16} />
                <span>上传文档</span>
              </button>
              <button 
                className={`action-btn ${asrActive ? 'active recording' : ''}`}
                onClick={toggleASR}
              >
                {asrActive ? <Mic size={16} /> : <MicOff size={16} />}
                <span>{asrActive ? '停止录音' : '语音输入'}</span>
                {asrActive && <span className="recording-dot" />}
              </button>
              <button 
                className="action-btn" 
                onClick={() => setShowSpeakerPanel(true)}
              >
                <Users size={16} />
                <span>说话人管理</span>
              </button>
            </div>

            {/* 数据面板 */}
            <div className="data-panels">
              <div className="section-title">数据面板</div>
              <button 
                className={`panel-btn ${showIntentPanel ? 'active' : ''}`}
                onClick={() => setShowIntentPanel(!showIntentPanel)}
              >
                <Brain size={16} />
                <span>意图分析</span>
                {intentHistory.length > 0 && (
                  <span className="panel-badge">{intentHistory.length}</span>
                )}
              </button>
              <button 
                className={`panel-btn ${showMemoryPanel ? 'active' : ''}`}
                onClick={() => setShowMemoryPanel(!showMemoryPanel)}
              >
                <Sparkles size={16} />
                <span>记忆检索</span>
              </button>
            </div>

            {/* 连接状态 */}
            <div className="connection-info">
              <div className={`status-indicator ${connectionStatus}`}>
                {connectionStatus === 'connected' ? <Wifi size={14} /> : <WifiOff size={14} />}
                <span>
                  {connectionStatus === 'connected' ? '已连接' : 
                   connectionStatus === 'connecting' ? '连接中...' : '断开'}
                </span>
              </div>
              <div className="session-stats">
                <div className="stat">
                  <Hash size={12} />
                  <span>{messages.length} 条消息</span>
                </div>
                <div className="stat">
                  <GitGraph size={12} />
                  <span>{graphData.nodes.length} 节点</span>
                </div>
              </div>
            </div>
          </>
        )}
      </aside>

      {/* 主内容区 */}
      <main className="main-content">
        {/* 顶部栏 */}
        <header className="top-bar">
          <div className="top-bar-left">
            <h1 className="page-title">
              {sessionMode === SESSION_MODES.CHAT && '智能对话'}
              {sessionMode === SESSION_MODES.MEETING && '实时会议'}
              {sessionMode === SESSION_MODES.BRAINSTORM && '头脑风暴'}
            </h1>
            {currentTranscript && (
              <div className="live-transcript">
                <span className="live-indicator">●</span>
                <span className="speaker-label">{currentSpeaker}</span>
                <span className="transcript-text">{currentTranscript}</span>
              </div>
            )}
          </div>
          
          <div className="top-bar-right">
            {/* 可视化模式切换 */}
            <div className="viz-toggle">
              <button 
                className={vizMode === VIZ_MODES.GRAPH ? 'active' : ''}
                onClick={() => setVizMode(VIZ_MODES.GRAPH)}
              >
                <GitGraph size={16} />
                <span>图谱</span>
              </button>
              <button 
                className={vizMode === VIZ_MODES.CHART ? 'active' : ''}
                onClick={() => setVizMode(VIZ_MODES.CHART)}
                disabled={!chartData}
              >
                <BarChart3 size={16} />
                <span>图表</span>
              </button>
              <button 
                className={vizMode === VIZ_MODES.BOTH ? 'active' : ''}
                onClick={() => setVizMode(VIZ_MODES.BOTH)}
              >
                <span>并列</span>
              </button>
            </div>

            <button className="icon-btn" title="导出">
              <Download size={18} />
            </button>
            <button className="icon-btn" title="分享">
              <Share2 size={18} />
            </button>
            <button className="icon-btn" title="设置">
              <Settings size={18} />
            </button>
          </div>
        </header>

        {/* 内容网格 */}
        <div className={`content-grid ${vizMode === VIZ_MODES.BOTH ? 'split' : ''}`}>
          {/* 可视化区域 */}
          <div className="viz-section">
            {(vizMode === VIZ_MODES.GRAPH || vizMode === VIZ_MODES.BOTH) && (
              <div className="viz-panel graph-panel">
                <div className="panel-header">
                  <GitGraph size={16} />
                  <span>知识图谱</span>
                  <span className="node-count">{graphData.nodes.length} 节点</span>
                </div>
                <div className="panel-content">
                  <StreamChart data={graphData} />
                  {graphData.nodes.length === 0 && (
                    <div className="empty-viz">
                      <div className="empty-icon">
                        <GitGraph size={48} />
                      </div>
                      <p>开始对话后，知识图谱将在这里实时生成</p>
                    </div>
                  )}
                </div>
              </div>
            )}

            {(vizMode === VIZ_MODES.CHART || vizMode === VIZ_MODES.BOTH) && (
              <div className="viz-panel chart-panel">
                <div className="panel-header">
                  <BarChart3 size={16} />
                  <span>数据图表</span>
                </div>
                <div className="panel-content">
                  <StreamPlot data={chartData} />
                </div>
              </div>
            )}

            {/* AI 成图浮层 */}
            {imageState.status !== 'idle' && (
              <div className="image-overlay">
                <div className="image-card">
                  <div className="image-header">
                    <ImageIcon size={16} />
                    <span>AI 生成图像</span>
                    <button 
                      className="close-btn"
                      onClick={() => setImageState({ status: 'idle', url: '', message: '' })}
                    >
                      <X size={14} />
                    </button>
                  </div>
                  <div className="image-body">
                    {(imageState.status === 'queued' || imageState.status === 'running') && (
                      <div className="image-loading">
                        <div className="loading-spinner" />
                        <span>{imageState.status === 'queued' ? '排队中...' : '生成中...'}</span>
                      </div>
                    )}
                    {imageState.status === 'failed' && (
                      <div className="image-error">{imageState.message}</div>
                    )}
                    {imageState.status === 'succeeded' && imageState.url && (
                      <img src={imageState.url} alt="AI generated" />
                    )}
                  </div>
                </div>
              </div>
            )}
          </div>

          {/* 对话区域 */}
          <div className="chat-section">
            <ChatInterface 
              messages={messages}
              onSendMessage={sendMessage}
              speakers={speakers}
              disabled={connectionStatus !== 'connected'}
            />
          </div>
        </div>
      </main>

      {/* 右侧边栏面板 */}
      {showSpeakerPanel && (
        <SpeakerPanel 
          speakers={speakers}
          setSpeakers={setSpeakers}
          voicePrints={voicePrints}
          setVoicePrints={setVoicePrints}
          onClose={() => setShowSpeakerPanel(false)}
          onRegisterVoice={() => setVoicePrintOpen(true)}
        />
      )}

      {showIntentPanel && (
        <IntentPanel 
          currentIntent={currentIntent}
          intentHistory={intentHistory}
          onClose={() => setShowIntentPanel(false)}
        />
      )}

      {showMemoryPanel && (
        <MemoryPanel onClose={() => setShowMemoryPanel(false)} />
      )}

      {/* 模态框 */}
      <VoicePrintModal
        open={voicePrintOpen}
        onClose={() => setVoicePrintOpen(false)}
        voicePrints={voicePrints}
        onUpdateVoicePrints={setVoicePrints}
        onRegistered={({ speakerName, featureId }) => {
          setVoicePrints(prev => ({ ...prev, [speakerName]: { featureId, enabled: true } }));
          setSpeakers(prev => ({ 
            ...prev, 
            [`spk${Object.keys(prev).length}`]: { name: speakerName, color: getSpeakerColor(Object.keys(prev).length) }
          }));
        }}
      />

      {/* 隐藏的文件输入 */}
      <input
        ref={fileInputRef}
        type="file"
        style={{ display: 'none' }}
        onChange={(e) => {
          const f = e.target.files?.[0];
          if (f) handleFileUpload(f);
          e.target.value = '';
        }}
      />
    </div>
  );
}

// 获取发言人颜色
function getSpeakerColor(index) {
  const colors = [
    '#3b82f6', '#06b6d4', '#8b5cf6', '#f59e0b', 
    '#10b981', '#ec4899', '#ef4444', '#84cc16'
  ];
  return colors[index % colors.length];
}

export default App;
