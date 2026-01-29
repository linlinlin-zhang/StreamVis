import React from 'react';
import { RefreshCw, Trash2 } from 'lucide-react';

const TopBar = ({ status, statusText, onReconnect, onClear }) => {
  const dotClass =
    status === 'connected'
      ? 'connected'
      : status === 'connecting'
        ? 'connecting'
        : status === 'error'
          ? 'error'
          : '';

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

