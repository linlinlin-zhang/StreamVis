import React, { useState } from 'react';
import { X, Mic, MicOff, User, Palette, Volume2, Trash2, Edit2, Check } from 'lucide-react';
import './SpeakerPanel.css';

const COLORS = [
  '#3b82f6', '#06b6d4', '#8b5cf6', '#f59e0b', 
  '#10b981', '#ec4899', '#ef4444', '#84cc16',
  '#6366f1', '#14b8a6', '#f97316', '#d946ef'
];

const SpeakerPanel = ({ 
  speakers, 
  setSpeakers, 
  voicePrints, 
  setVoicePrints,
  onClose, 
  onRegisterVoice 
}) => {
  const [editingId, setEditingId] = useState(null);
  const [editName, setEditName] = useState('');

  const handleEdit = (speakerId) => {
    setEditingId(speakerId);
    setEditName(speakers[speakerId]?.name || speakerId);
  };

  const handleSave = (speakerId) => {
    setSpeakers(prev => ({
      ...prev,
      [speakerId]: { ...prev[speakerId], name: editName }
    }));
    setEditingId(null);
  };

  const handleColorChange = (speakerId, color) => {
    setSpeakers(prev => ({
      ...prev,
      [speakerId]: { ...prev[speakerId], color }
    }));
  };

  const handleDelete = (speakerId) => {
    const newSpeakers = { ...speakers };
    delete newSpeakers[speakerId];
    setSpeakers(newSpeakers);
  };

  // 获取已注册声纹数量
  const registeredCount = Object.keys(voicePrints || {}).length;

  return (
    <div className="side-panel">
      <div className="panel-header">
        <div className="panel-title">
          <Volume2 size={18} />
          <span>说话人管理</span>
        </div>
        <button className="close-btn" onClick={onClose}>
          <X size={18} />
        </button>
      </div>

      <div className="panel-body">
        {/* 统计信息 */}
        <div className="stats-card">
          <div className="stat-item">
            <span className="stat-value">{Object.keys(speakers).length}</span>
            <span className="stat-label">识别说话人</span>
          </div>
          <div className="stat-item">
            <span className="stat-value">{registeredCount}</span>
            <span className="stat-label">已注册声纹</span>
          </div>
        </div>

        {/* 注册声纹按钮 */}
        <button className="register-voice-btn" onClick={onRegisterVoice}>
          <Mic size={18} />
          <span>注册新声纹</span>
        </button>

        {/* 说话人列表 */}
        <div className="section-title">已识别说话人</div>
        <div className="speaker-list">
          {Object.entries(speakers).map(([id, speaker]) => (
            <div key={id} className="speaker-card">
              <div 
                className="speaker-color"
                style={{ background: speaker.color || '#3b82f6' }}
              />
              
              <div className="speaker-info">
                {editingId === id ? (
                  <input
                    type="text"
                    value={editName}
                    onChange={(e) => setEditName(e.target.value)}
                    onBlur={() => handleSave(id)}
                    onKeyDown={(e) => e.key === 'Enter' && handleSave(id)}
                    autoFocus
                    className="edit-input"
                  />
                ) : (
                  <div className="speaker-name">
                    {speaker.name || `发言人${parseInt(id.replace('spk', '')) + 1}`}
                    {voicePrints?.[speaker.name]?.featureId && (
                      <span className="verified-badge">✓</span>
                    )}
                  </div>
                )}
                <div className="speaker-id">{id}</div>
              </div>

              <div className="speaker-actions">
                <button 
                  className="action-icon"
                  onClick={() => handleEdit(id)}
                  title="编辑名称"
                >
                  <Edit2 size={14} />
                </button>
                <button 
                  className="action-icon delete"
                  onClick={() => handleDelete(id)}
                  title="删除"
                >
                  <Trash2 size={14} />
                </button>
              </div>
            </div>
          ))}
        </div>

        {/* 颜色配置 */}
        {Object.keys(speakers).length > 0 && (
          <>
            <div className="section-title">颜色配置</div>
            <div className="color-config">
              {Object.entries(speakers).map(([id, speaker]) => (
                <div key={id} className="color-item">
                  <span className="color-label">
                    {speaker.name || id}
                  </span>
                  <div className="color-options">
                    {COLORS.map(color => (
                      <button
                        key={color}
                        className={`color-dot ${speaker.color === color ? 'active' : ''}`}
                        style={{ background: color }}
                        onClick={() => handleColorChange(id, color)}
                      />
                    ))}
                  </div>
                </div>
              ))}
            </div>
          </>
        )}

        {/* 声纹列表 */}
        {registeredCount > 0 && (
          <>
            <div className="section-title">已注册声纹</div>
            <div className="voiceprint-list">
              {Object.entries(voicePrints || {}).map(([name, vp]) => (
                <div key={name} className="voiceprint-item">
                  <div className="voiceprint-info">
                    <Mic size={14} />
                    <span>{name}</span>
                  </div>
                  <code className="feature-id">{(vp?.featureId || '').slice(0, 8)}...</code>
                </div>
              ))}
            </div>
          </>
        )}

        {/* 提示 */}
        <div className="help-text">
          <p>💡 提示：</p>
          <ul>
            <li>注册声纹可提升说话人分离准确度</li>
            <li>每人录制 10-60 秒语音样本</li>
            <li>建议在安静环境下录制</li>
          </ul>
        </div>
      </div>
    </div>
  );
};

export default SpeakerPanel;
