import React from 'react';
import { X, Brain, Target, TrendingUp, BarChart2, Activity } from 'lucide-react';
import './IntentPanel.css';

const IntentPanel = ({ currentIntent, intentHistory, onClose }) => {
  // 计算可视化必要性分数的颜色
  const getScoreColor = (score) => {
    if (score >= 0.7) return '#10b981'; // 绿色 - 高
    if (score >= 0.4) return '#f59e0b'; // 橙色 - 中
    return '#ef4444'; // 红色 - 低
  };

  // 计算意图类型标签
  const getIntentLabel = (type) => {
    switch (type) {
      case 'request-create': return { text: '创建图表', color: '#3b82f6' };
      case 'request-update': return { text: '更新图表', color: '#8b5cf6' };
      case 'inform': return { text: '信息交流', color: '#64748b' };
      default: return { text: '未知', color: '#64748b' };
    }
  };

  return (
    <div className="side-panel">
      <div className="panel-header">
        <div className="panel-title">
          <Brain size={18} />
          <span>意图分析</span>
        </div>
        <button className="close-btn" onClick={onClose}>
          <X size={18} />
        </button>
      </div>

      <div className="panel-body">
        {/* 当前意图 */}
        {currentIntent && (
          <div className="current-intent">
            <div className="section-title">当前意图</div>
            <div className="intent-card">
              <div className="intent-type">
                <span 
                  className="intent-badge"
                  style={{ 
                    background: `${getIntentLabel(currentIntent.type).color}20`,
                    color: getIntentLabel(currentIntent.type).color 
                  }}
                >
                  {getIntentLabel(currentIntent.type).text}
                </span>
              </div>
              
              <div className="intent-score">
                <div className="score-label">
                  <Target size={14} />
                  <span>可视化必要性</span>
                </div>
                <div className="score-bar-container">
                  <div 
                    className="score-bar"
                    style={{ 
                      width: `${(currentIntent.visual_necessity_score || 0) * 100}%`,
                      background: getScoreColor(currentIntent.visual_necessity_score || 0)
                    }}
                  />
                </div>
                <div className="score-value">
                  {((currentIntent.visual_necessity_score || 0) * 100).toFixed(0)}%
                </div>
              </div>

              {currentIntent.entities && currentIntent.entities.length > 0 && (
                <div className="intent-entities">
                  <div className="entities-label">识别实体</div>
                  <div className="entities-list">
                    {currentIntent.entities.map((entity, i) => (
                      <span key={i} className="entity-tag">{entity}</span>
                    ))}
                  </div>
                </div>
              )}
            </div>
          </div>
        )}

        {/* 意图历史 */}
        {intentHistory.length > 0 && (
          <>
            <div className="section-title">意图历史 ({intentHistory.length})</div>
            <div className="intent-history">
              {intentHistory.slice().reverse().map((intent, index) => (
                <div key={index} className="history-item">
                  <div className="history-dot" 
                    style={{ background: getScoreColor(intent.visual_necessity_score) }}
                  />
                  <div className="history-info">
                    <div className="history-type">
                      {getIntentLabel(intent.type).text}
                    </div>
                    <div className="history-score">
                      {(intent.visual_necessity_score * 100).toFixed(0)}% 
                      <span className="history-time">
                        {new Date(intent.timestamp).toLocaleTimeString('zh-CN', { 
                          hour: '2-digit', 
                          minute: '2-digit' 
                        })}
                      </span>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </>
        )}

        {/* 统计图表 */}
        {intentHistory.length >= 3 && (
          <>
            <div className="section-title">可视化趋势</div>
            <div className="intent-chart">
              <div className="sparkline">
                {intentHistory.slice(-10).map((intent, i) => (
                  <div 
                    key={i}
                    className="spark-bar"
                    style={{ 
                      height: `${intent.visual_necessity_score * 100}%`,
                      background: getScoreColor(intent.visual_necessity_score)
                    }}
                    title={`${(intent.visual_necessity_score * 100).toFixed(0)}%`}
                  />
                ))}
              </div>
            </div>
          </>
        )}

        {/* 说明 */}
        <div className="help-text">
          <p>📊 意图检测说明：</p>
          <ul>
            <li>系统自动分析对话内容</li>
            <li>检测是否需要生成可视化</li>
            <li>分数 ≥ 55% 时触发图谱生成</li>
            <li>支持图表、图谱、图像三种形式</li>
          </ul>
        </div>
      </div>
    </div>
  );
};

export default IntentPanel;
