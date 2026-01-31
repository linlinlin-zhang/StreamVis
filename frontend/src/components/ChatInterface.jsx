import React, { useState, useRef, useEffect } from 'react';
import { Send, Loader2, Mic, User, Bot, Radio } from 'lucide-react';
import './ChatInterface.css';

const ChatInterface = ({ messages, onSendMessage, speakers, disabled }) => {
  const [input, setInput] = useState('');
  const messagesEndRef = useRef(null);
  const inputRef = useRef(null);
  const containerRef = useRef(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  useEffect(() => {
    if (!disabled && inputRef.current) {
      inputRef.current.focus();
    }
  }, [disabled]);

  const handleSubmit = (e) => {
    e.preventDefault();
    if (disabled || !input.trim()) return;
    onSendMessage(input);
    setInput('');
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit(e);
    }
  };

  // 获取发言人颜色
  const getSpeakerColor = (speakerKey) => {
    if (!speakerKey) return '#3b82f6';
    return speakers[speakerKey]?.color || '#3b82f6';
  };

  // 获取发言人名称
  const getSpeakerName = (speakerKey) => {
    if (!speakerKey) return '未知';
    return speakers[speakerKey]?.name || `发言人${parseInt(speakerKey.replace('spk', '')) + 1}`;
  };

  return (
    <div className="chat-interface">
      {/* 消息列表 */}
      <div className="chat-messages" ref={containerRef}>
        {messages.length === 0 ? (
          <div className="welcome-screen">
            <div className="welcome-logo">
              <div className="logo-glow" />
              <Radio size={48} />
            </div>
            <h2 className="welcome-title">StreamVis Pro</h2>
            <p className="welcome-subtitle">
              实时意图成图 · 多人会议 · 智能可视化
            </p>
            
            <div className="feature-chips">
              <div className="chip">
                <Mic size={14} />
                <span>语音输入自动转录</span>
              </div>
              <div className="chip">
                <User size={14} />
                <span>说话人自动分离</span>
              </div>
              <div className="chip">
                <Bot size={14} />
                <span>AI 智能意图识别</span>
              </div>
            </div>

            <div className="quick-prompts">
              <div className="prompts-title">快速开始</div>
              <button 
                className="prompt-btn" 
                onClick={() => onSendMessage('我们来讨论Q1销售数据：Q1=120万，Q2=135万，Q3=98万，Q4=156万')}
              >
                📊 分析季度销售数据
              </button>
              <button 
                className="prompt-btn" 
                onClick={() => onSendMessage('头脑风暴一下新产品功能，我需要可视化思路')}
              >
                💡 新产品功能头脑风暴
              </button>
              <button 
                className="prompt-btn" 
                onClick={() => onSendMessage('画一个公司组织架构图')}
              >
                🏢 生成组织架构图
              </button>
            </div>
          </div>
        ) : (
          <div className="messages-container">
            {messages.map((msg, idx) => (
              <div 
                key={msg.id || idx} 
                className={`message ${msg.role} ${msg.type || ''}`}
                style={{ animationDelay: `${idx * 30}ms` }}
              >
                <div className="message-avatar">
                  {msg.role === 'user' && msg.type === 'voice' && (
                    <div 
                      className="avatar voice"
                      style={{ 
                        background: `${getSpeakerColor(msg.speakerKey)}20`,
                        borderColor: getSpeakerColor(msg.speakerKey)
                      }}
                    >
                      <Mic size={14} style={{ color: getSpeakerColor(msg.speakerKey) }} />
                    </div>
                  )}
                  {msg.role === 'user' && msg.type !== 'voice' && (
                    <div className="avatar user">
                      <User size={16} />
                    </div>
                  )}
                  {msg.role === 'assistant' && (
                    <div className="avatar assistant">
                      <Bot size={16} />
                    </div>
                  )}
                  {msg.role === 'system' && (
                    <div className="avatar system">⚡</div>
                  )}
                </div>

                <div className="message-content">
                  {msg.speaker && (
                    <div 
                      className="speaker-tag"
                      style={{ color: getSpeakerColor(msg.speakerKey) }}
                    >
                      {msg.speaker}
                    </div>
                  )}
                  <div className="message-bubble">
                    <div className="message-text">{msg.content}</div>
                  </div>
                  <div className="message-meta">
                    {msg.timestamp && (
                      <span className="timestamp">
                        {new Date(msg.timestamp).toLocaleTimeString('zh-CN', { 
                          hour: '2-digit', 
                          minute: '2-digit' 
                        })}
                      </span>
                    )}
                    {!msg.isFinal && (
                      <span className="typing-indicator">
                        <span></span>
                        <span></span>
                        <span></span>
                      </span>
                    )}
                  </div>
                </div>
              </div>
            ))}
            <div ref={messagesEndRef} />
          </div>
        )}
      </div>

      {/* 输入区域 */}
      <div className="chat-input-area">
        <div className="input-container">
          <form onSubmit={handleSubmit} className="input-form">
            <div className="input-wrapper">
              <input
                ref={inputRef}
                type="text"
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={handleKeyDown}
                placeholder={disabled ? '正在连接服务器...' : '输入消息，或描述数据生成图表...'}
                disabled={disabled}
                className="chat-input"
              />
              <button 
                type="submit" 
                className="send-button"
                disabled={disabled || !input.trim()}
              >
                {disabled ? (
                  <Loader2 size={18} className="animate-spin" />
                ) : (
                  <Send size={18} />
                )}
              </button>
            </div>
          </form>
          <div className="input-hint">
            <span>按 Enter 发送 · Shift + Enter 换行</span>
            <span className="hint-shortcuts">
              支持多人讨论 · 语音输入 · 实时成图
            </span>
          </div>
        </div>
      </div>
    </div>
  );
};

export default ChatInterface;
