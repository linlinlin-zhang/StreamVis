import React, { useState, useRef, useEffect } from 'react';
import { Send, Loader2 } from 'lucide-react';
import './ChatInterface.css';

const ChatInterface = ({ messages, onSendMessage, disabled }) => {
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
    // Auto-focus input when connected
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

  const getMessageIcon = (role) => {
    switch (role) {
      case 'user':
        return (
          <div className="message-avatar user">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2" />
              <circle cx="12" cy="7" r="4" />
            </svg>
          </div>
        );
      case 'assistant':
        return (
          <div className="message-avatar assistant">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M12 3L20 7.5V16.5L12 21L4 16.5V7.5L12 3Z" />
              <path d="M12 12L20 7.5" />
              <path d="M12 12V21" />
              <path d="M12 12L4 7.5" />
            </svg>
          </div>
        );
      case 'system':
        return (
          <div className="message-avatar system">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <circle cx="12" cy="12" r="10" />
              <path d="M12 16v-4" />
              <path d="M12 8h.01" />
            </svg>
          </div>
        );
      default:
        return null;
    }
  };

  return (
    <div className="chat-wrapper">
      {/* 消息列表 */}
      <div className="chat-messages" ref={containerRef}>
        {messages.length === 0 ? (
          <div className="chat-welcome">
            <div className="welcome-icon">
              <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
                <path d="M12 3L20 7.5V16.5L12 21L4 16.5V7.5L12 3Z" />
                <path d="M12 12L20 7.5" />
                <path d="M12 12V21" />
                <path d="M12 12L4 7.5" />
              </svg>
            </div>
            <h2 className="welcome-title">StreamVis</h2>
            <p className="welcome-subtitle">智能数据可视化助手</p>
            <div className="welcome-examples">
              <button 
                className="example-chip" 
                onClick={() => onSendMessage('帮我分析销售数据，创建一个趋势图')}
              >
                📈 分析销售数据趋势
              </button>
              <button 
                className="example-chip" 
                onClick={() => onSendMessage('用图谱展示公司组织架构')}
              >
                🕸️ 展示组织架构
              </button>
              <button 
                className="example-chip" 
                onClick={() => onSendMessage('生成一个项目进度甘特图')}
              >
                📊 生成项目进度图
              </button>
            </div>
          </div>
        ) : (
          <div className="messages-container">
            {messages.map((msg, idx) => (
              <div 
                key={idx} 
                className={`message-group ${msg.role}`}
                style={{ animationDelay: `${idx * 50}ms` }}
              >
                <div className="message-content-wrapper">
                  {getMessageIcon(msg.role)}
                  <div className="message-body">
                    {msg.speaker && (
                      <div className="message-speaker">{msg.speaker}</div>
                    )}
                    <div className="message-bubble">
                      <div className="message-text">{msg.content}</div>
                    </div>
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
                placeholder={disabled ? '正在连接服务器...' : '输入消息，描述您的数据或问题...'}
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
          <div className="input-footer">
            <span className="input-hint">
              按 Enter 发送，Shift + Enter 换行
            </span>
          </div>
        </div>
      </div>
    </div>
  );
};

export default ChatInterface;
