# StreamVis

基于长文本对话流的实时 AI 图表生成（MVP 原型）。当前版本实现了一个端到端的“流式伴随”骨架：前端通过 WebSocket 与后端持续通信，后端按需输出文本与可视化的增量更新（Graph Delta）。

## 快速开始

### 后端

```bash
cd backend
pip install -r requirements.txt
python -m app.main
```

默认监听 `http://localhost:8000`，健康检查：`GET /health`。

可选配置：复制 [backend/.env.example](file:///e:/Desktop/StreamVis/backend/.env.example) 为 `backend/.env` 并修改参数。

### 前端

```bash
cd frontend
npm install
npm run dev
```

默认地址：`http://localhost:5173`。

## 目录结构

- [backend/app/main.py](file:///e:/Desktop/StreamVis/backend/app/main.py)：FastAPI + WebSocket 入口
- [backend/app/core](file:///e:/Desktop/StreamVis/backend/app/core)：上下文管理 / 意图检测 / 增量渲染骨架
- [backend/app/models/ws.py](file:///e:/Desktop/StreamVis/backend/app/models/ws.py)：WebSocket 消息协议（Pydantic）
- [frontend/src/App.jsx](file:///e:/Desktop/StreamVis/frontend/src/App.jsx)：连接管理与 UI 框架
- [frontend/src/components/StreamChart.jsx](file:///e:/Desktop/StreamVis/frontend/src/components/StreamChart.jsx)：D3 增量图渲染（持久化 simulation）

## 设计系统

设计建议已持久化在 [design-system/streamvis/MASTER.md](file:///e:/Desktop/StreamVis/design-system/streamvis/MASTER.md)。

