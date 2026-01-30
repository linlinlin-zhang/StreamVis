import React, { useState, useRef, useEffect } from 'react';
import { Send } from 'lucide-react';
import './ChatInterface.css';

const ChatInterface = ({ messages, onSendMessage, disabled }) => {
  const [input, setInput] = useState('');
  const messagesEndRef = useRef(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(scrollToBottom, [messages]);

  const handleSubmit = (e) => {
    e.preventDefault();
    if (disabled) return;
    if (input.trim()) {
      onSendMessage(input);
      setInput('');
    }
  };

  return (
    <div className="chat-container">
      <div className="messages-list">
        {messages.map((msg, idx) => (
          <div key={idx} className={`message ${msg.role}`}>
            {msg.speaker ? <div className="message-speaker">{msg.speaker}</div> : null}
            <div className="message-content">{msg.content}</div>
          </div>
        ))}
        <div ref={messagesEndRef} />
      </div>
      <form onSubmit={handleSubmit} className="input-area">
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder={disabled ? '正在连接后端…' : '描述数据、提出问题，或请求生成图表…'}
          disabled={disabled}
        />
        <button className="send-btn" type="submit" disabled={disabled || !input.trim()}>
          <Send size={20} />
        </button>
      </form>
    </div>
  );
};

export default ChatInterface;
