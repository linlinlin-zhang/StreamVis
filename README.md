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

## 可选能力：Kimi 与百炼成图

将 [backend/.env.example](file:///e:/Desktop/StreamVis/backend/.env.example) 复制为 `backend/.env` 后配置：

### Kimi（Moonshot）

- `STREAMVIS_ENABLE_KIMI=1`
- `MOONSHOT_API_KEY=...`
- `MOONSHOT_BASE_URL=https://api.moonshot.cn/v1`
- `STREAMVIS_KIMI_MODEL=moonshot-v1-8k`

启用后，后端会把 Kimi 的流式输出转成 `text_delta(delta)` 推送到前端。
也可以在前端顶栏点击“上传”，将文件通过 Kimi Files 抽取为结构化内容并注入为 system 上下文（不直接展示全文）。

### 百炼（DashScope）文生图

- `STREAMVIS_ENABLE_IMAGES=1`
- `DASHSCOPE_API_KEY=...`
- `DASHSCOPE_BASE_URL=https://dashscope.aliyuncs.com`
- `STREAMVIS_T2I_MODEL=wanx-v1`（可改为你开通的模型）

当意图触发可视化时，后端会额外推送 `image` 事件，成功后携带图片 URL。

### Kimi Tool Use（可选）

- `STREAMVIS_ENABLE_KIMI_TOOLS=1`

启用后，后端会在一次 Kimi 调用中允许模型通过 tool_calls 直接下发：图结构增量（Graph Delta）、文生图 prompt 或图像编辑任务参数；后端执行并回推 `graph_delta` / `image` 事件。

## 目录结构

- [backend/app/main.py](file:///e:/Desktop/StreamVis/backend/app/main.py)：FastAPI + WebSocket 入口
- [backend/app/core](file:///e:/Desktop/StreamVis/backend/app/core)：上下文管理 / 意图检测 / 增量渲染骨架
- [backend/app/models/ws.py](file:///e:/Desktop/StreamVis/backend/app/models/ws.py)：WebSocket 消息协议（Pydantic）
- [frontend/src/App.jsx](file:///e:/Desktop/StreamVis/frontend/src/App.jsx)：连接管理与 UI 框架
- [frontend/src/components/StreamChart.jsx](file:///e:/Desktop/StreamVis/frontend/src/components/StreamChart.jsx)：D3 增量图渲染（持久化 simulation）

## 设计系统

设计建议已持久化在 [design-system/streamvis/MASTER.md](file:///e:/Desktop/StreamVis/design-system/streamvis/MASTER.md)。

## 系统说明

更详细的“功能清单 / 协议 / 算法策略 / 可升级方向”见：[docs/SYSTEM_OVERVIEW.md](file:///e:/Desktop/StreamVis/docs/SYSTEM_OVERVIEW.md)。
