import React, { useState } from 'react';
import { X, Sparkles, Search, Database, Clock, Hash } from 'lucide-react';
import './MemoryPanel.css';

const MemoryPanel = ({ onClose }) => {
  const [searchQuery, setSearchQuery] = useState('');
  const [searchResults, setSearchResults] = useState([]);
  const [isSearching, setIsSearching] = useState(false);

  // 模拟搜索记忆
  const handleSearch = async () => {
    if (!searchQuery.trim()) return;
    setIsSearching(true);
    
    try {
      const resp = await fetch(`http://localhost:8000/api/memory/search?q=${encodeURIComponent(searchQuery)}&k=6`);
      const data = await resp.json();
      setSearchResults(data.hits || []);
    } catch (e) {
      console.error('搜索失败:', e);
    } finally {
      setIsSearching(false);
    }
  };

  // 模拟记忆统计数据
  const memoryStats = {
    totalChunks: 128,
    totalTokens: 45000,
    lastUpdate: '2分钟前',
    storageSize: '2.4 MB'
  };

  // 模拟最近记忆
  const recentMemories = [
    { id: 'm1', text: 'Q1季度销售额达到120万，同比增长15%', timestamp: '5分钟前', source: '会议记录' },
    { id: 'm2', text: '用户增长趋势图显示3月有显著上升', timestamp: '12分钟前', source: '讨论' },
    { id: 'm3', text: '产品路线图包含AI功能模块规划', timestamp: '1小时前', source: '头脑风暴' },
  ];

  return (
    <div className="side-panel">
      <div className="panel-header">
        <div className="panel-title">
          <Sparkles size={18} />
          <span>记忆检索</span>
        </div>
        <button className="close-btn" onClick={onClose}>
          <X size={18} />
        </button>
      </div>

      <div className="panel-body">
        {/* 统计卡片 */}
        <div className="stats-grid">
          <div className="stat-card">
            <Database size={16} />
            <span className="stat-value">{memoryStats.totalChunks}</span>
            <span className="stat-label">记忆片段</span>
          </div>
          <div className="stat-card">
            <Hash size={16} />
            <span className="stat-value">{(memoryStats.totalTokens / 1000).toFixed(1)}k</span>
            <span className="stat-label">Token数</span>
          </div>
        </div>

        {/* 搜索框 */}
        <div className="search-box">
          <Search size={16} />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && handleSearch()}
            placeholder="搜索历史记忆..."
          />
          <button 
            className="search-btn"
            onClick={handleSearch}
            disabled={isSearching || !searchQuery.trim()}
          >
            {isSearching ? '...' : '搜索'}
          </button>
        </div>

        {/* 搜索结果 */}
        {searchResults.length > 0 && (
          <>
            <div className="section-title">搜索结果 ({searchResults.length})</div>
            <div className="search-results">
              {searchResults.map((hit, index) => (
                <div key={hit.id || index} className="result-item">
                  <div className="result-text">{hit.text}</div>
                  {hit.meta && (
                    <div className="result-meta">
                      {hit.meta.source && <span>来源: {hit.meta.source}</span>}
                    </div>
                  )}
                </div>
              ))}
            </div>
          </>
        )}

        {/* 最近记忆 */}
        <div className="section-title">最近记忆</div>
        <div className="memory-list">
          {recentMemories.map((memory) => (
            <div key={memory.id} className="memory-item">
              <div className="memory-text">{memory.text}</div>
              <div className="memory-meta">
                <span className="memory-source">{memory.source}</span>
                <span className="memory-time">
                  <Clock size={12} />
                  {memory.timestamp}
                </span>
              </div>
            </div>
          ))}
        </div>

        {/* 存储信息 */}
        <div className="storage-info">
          <div className="storage-item">
            <span>存储大小</span>
            <span>{memoryStats.storageSize}</span>
          </div>
          <div className="storage-item">
            <span>最后更新</span>
            <span>{memoryStats.lastUpdate}</span>
          </div>
        </div>

        {/* 说明 */}
        <div className="help-text">
          <p>💡 记忆系统说明：</p>
          <ul>
            <li>自动保存对话历史到向量库</li>
            <li>支持语义检索相似内容</li>
            <li>持久化存储，重启不丢失</li>
            <li>智能上下文增强回答质量</li>
          </ul>
        </div>
      </div>
    </div>
  );
};

export default MemoryPanel;
