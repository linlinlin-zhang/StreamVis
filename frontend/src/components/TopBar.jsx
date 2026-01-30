import React, { useRef } from 'react';
import { Mic, RefreshCw, Trash2, Upload, UserRound } from 'lucide-react';

const TopBar = ({ status, statusText, onReconnect, onClear, onUploadFile, uploadDisabled, onToggleVoice, voiceActive, voiceDisabled, onOpenVoicePrint }) => {
  const dotClass =
    status === 'connected'
      ? 'connected'
      : status === 'connecting'
        ? 'connecting'
        : status === 'error'
          ? 'error'
          : '';

  const fileInputRef = useRef(null);

  return (
    <div className="topbar">
      <div className="topbar-left">
        <div className="brand">
          <div className="brand-title">
            <span>StreamVis</span>
            <span className="status-pill">
              <span className={`status-dot ${dotClass}`} />
              <span>{statusText}</span>
            </span>
          </div>
          <div className="brand-subtitle">基于对话流的增量可视化原型（MVP）</div>
        </div>
      </div>
      <div className="topbar-actions">
        <input
          ref={fileInputRef}
          type="file"
          style={{ display: 'none' }}
          onChange={(e) => {
            const f = e.target.files?.[0];
            if (f) onUploadFile?.(f);
            e.target.value = '';
          }}
        />
        <button className="btn" type="button" onClick={() => fileInputRef.current?.click()} disabled={uploadDisabled}>
          <Upload size={16} />
          上传
        </button>
        <button className={`btn ${voiceActive ? 'primary' : ''}`} type="button" onClick={onToggleVoice} disabled={voiceDisabled}>
          <Mic size={16} />
          语音
        </button>
        <button className="btn" type="button" onClick={onOpenVoicePrint} disabled={voiceDisabled}>
          <UserRound size={16} />
          声纹
        </button>
        <button className="btn" type="button" onClick={onClear}>
          <Trash2 size={16} />
          清空
        </button>
        <button className="btn primary" type="button" onClick={onReconnect}>
          <RefreshCw size={16} />
          重连
        </button>
      </div>
    </div>
  );
};

export default TopBar;
