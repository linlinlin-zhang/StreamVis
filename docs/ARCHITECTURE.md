# StreamVis 架构说明（当前实现）

本文描述当前仓库的端到端架构、关键数据流、AI/外部服务接入点与可扩展边界，方便你自行启动调试与二次开发。

## 1. 总览

StreamVis 由两部分组成：
- 前端：React + Vite（交互、实时可视化、麦克风采集、文件上传）
- 后端：FastAPI（WebSocket 会话编排、AI 调用、图表/图谱/图片事件下发、文件抽取/索引、语音转写代理）

核心理念：
- “对话流”是系统主线：用户输入（文本/语音转写）→ 意图判断 → 触发可视化（图表/图谱/图片）
- “增量事件”驱动 UI：后端向前端推送 `*_delta` 事件，前端增量更新图谱/图表与聊天消息

## 2. 运行时组件与端口

### 2.1 前端
- Dev Server：`http://localhost:5173/`
- 入口组件：[App.jsx](file:///e:/Desktop/StreamVis/frontend/src/App.jsx)

### 2.2 后端
- API：`http://localhost:8000/`
- 健康检查：`GET /health`
- Swagger：`/docs`
- WebSocket：
  - 对话：`ws://localhost:8000/ws/chat`
  - 语音转写：`ws://localhost:8000/ws/asr`

后端入口：[main.py](file:///e:/Desktop/StreamVis/backend/app/main.py)

## 3. 核心数据流（文本对话）

### 3.1 事件协议（后端 → 前端）

协议模型定义：[ws.py](file:///e:/Desktop/StreamVis/backend/app/models/ws.py)

主要事件：
- `text_delta`：聊天输出（支持流式 delta、final 标记）
- `chart_delta`：结构化图表数据（折线/柱状 + points）
- `graph_delta`：增量图谱操作（add_node/add_edge/update_node/remove_*）
- `image`：文生图/图像编辑任务状态（queued/running/succeeded/failed）
- `transcript_delta`：语音实时转写（含 speaker + is_final）

### 3.2 文本输入链路（ws/chat）

1) 前端将用户输入通过 `ws://.../ws/chat` 发送给后端  
2) 后端做意图解析与上下文检索  
3) 生成文本回复 + 触发可视化（图谱/图表/图片）  
4) 通过事件推送给前端，前端增量渲染

关键实现：
- WebSocket 会话编排：[main.py](file:///e:/Desktop/StreamVis/backend/app/main.py)
- 意图解码器：[intent_decoder.py](file:///e:/Desktop/StreamVis/backend/app/core/intent_decoder.py)

## 4. 上下文与长期记忆（L1/L2 + 文件索引）

### 4.1 ContextManager：L1/L2 + system 注入

实现：[context_manager.py](file:///e:/Desktop/StreamVis/backend/app/core/context_manager.py)

- L1：最近对话（deque）+ sink（前若干轮固定保留）
- L2：淘汰后的“长期记忆”
  - 分段器：[segmenter.py](file:///e:/Desktop/StreamVis/backend/app/core/segmenter.py)
  - 向量库：[vector_store.py](file:///e:/Desktop/StreamVis/backend/app/core/vector_store.py)
- system：专门存放 system 注入（例如文件摘要、外部上下文），默认最多 8 条

### 4.2 向量检索：HashingEmbedder + MMR 多样性重排

实现：[vector_store.py](file:///e:/Desktop/StreamVis/backend/app/core/vector_store.py)

- Embedding：HashingEmbedder（本地、无外部依赖）
- 检索：余弦相似度召回 + MMR（Maximal Marginal Relevance）重排，降低重复片段，提高覆盖面
- 持久化：`PersistentVectorStore` 使用 SQLite 保存 chunk（默认路径 `backend/data/streamvis_memory.sqlite`）

### 4.3 文件索引：从“注入全文”升级为“入库检索”

后端接口：
- `POST /api/kimi/files/index`：上传文件 → Moonshot 抽取 → 分段入库 → 返回短 `system_context`

关键实现：
- 文件抽取客户端：[moonshot_files.py](file:///e:/Desktop/StreamVis/backend/app/core/moonshot_files.py)
- 分段入库：[file_indexer.py](file:///e:/Desktop/StreamVis/backend/app/core/file_indexer.py)
- 接口编排：[main.py](file:///e:/Desktop/StreamVis/backend/app/main.py)

前端上传流程：上传后只注入短 system_context（避免 prompt 爆炸）  
实现：[App.jsx](file:///e:/Desktop/StreamVis/frontend/src/App.jsx)

## 5. 可视化子系统（图谱 + 图表 + 图片）

### 5.1 图谱（Graph Delta）

渲染端：
- D3 图谱组件：[StreamChart.jsx](file:///e:/Desktop/StreamVis/frontend/src/components/StreamChart.jsx)

生成端：
- 增量渲染器：[renderer.py](file:///e:/Desktop/StreamVis/backend/app/core/renderer.py)
- 语义图谱规划（替代随机图）：[semantic_plan.py](file:///e:/Desktop/StreamVis/backend/app/core/semantic_plan.py)

### 5.2 图表（Chart Delta）

后端解析（从文本抽取序列数据）：[chart_parser.py](file:///e:/Desktop/StreamVis/backend/app/core/chart_parser.py)

前端渲染（折线/柱状）：[StreamPlot.jsx](file:///e:/Desktop/StreamVis/frontend/src/components/StreamPlot.jsx)

### 5.3 文生图/图像编辑（DashScope/百炼）

后端客户端：[bailian_images.py](file:///e:/Desktop/StreamVis/backend/app/core/bailian_images.py)

触发点：当 `visual_necessity_score >= threshold` 且启用图片时，后端异步创建任务并推送 `image` 事件。  
实现：[main.py](file:///e:/Desktop/StreamVis/backend/app/main.py)

## 6. Wait-k 多阶段流式伴随

当走 Kimi 流式输出（SSE）时，系统会“边生成边出图”，而不是只等最终回答：
- 策略机（节流 + 上限）：[waitk_policy.py](file:///e:/Desktop/StreamVis/backend/app/core/waitk_policy.py)
- 触发更新：多次推送 `chart_delta` / `graph_delta`（并在最终阶段再补齐一次）

## 7. Kimi Tool Use（二阶段回填）

当启用 tools 时：
- 第 1 阶段：Kimi 返回 tool_calls（例如 render_graph_delta / generate_image_prompt）
- 系统执行工具并把结果以 `role=tool` 回灌
- 第 2 阶段：Kimi 基于 tool 结果产出最终答复

工具协议：[kimi_tools.py](file:///e:/Desktop/StreamVis/backend/app/core/kimi_tools.py)  
执行编排：[main.py](file:///e:/Desktop/StreamVis/backend/app/main.py)

## 8. 语音对话（麦克风 → 讯飞 RTASR → 分人展示 → 喂给对话链路）

### 8.1 前端：麦克风采集 + 分人展示

- 顶栏入口（语音/声纹）：[TopBar.jsx](file:///e:/Desktop/StreamVis/frontend/src/components/TopBar.jsx)
- 语音采集与转写消息渲染：[App.jsx](file:///e:/Desktop/StreamVis/frontend/src/App.jsx)
- 聊天列表支持 speaker 标签：[ChatInterface.jsx](file:///e:/Desktop/StreamVis/frontend/src/components/ChatInterface.jsx)

工作方式：
- 浏览器获取麦克风 audio stream
- WebAudio 将音频下采样为 16k PCM16，并按 40ms/1280 bytes 的节奏推送给后端 ASR WS
- 收到 `transcript_delta`：
  - 实时显示在聊天区（按 speaker 聚合）
  - 对 `is_final=true` 的片段：自动以“用户输入”的形式发送给 `/ws/chat`，触发图表/图谱/图片逻辑

### 8.2 后端：讯飞 RTASR 代理

- WebSocket 入口：`/ws/asr`（浏览器 → 后端）
- 后端作为客户端连接讯飞 RTASR（后端 → 讯飞），将结果转为 `transcript_delta` 推回前端

实现：
- 签名与 URL： [xfyun_auth.py](file:///e:/Desktop/StreamVis/backend/app/core/xfyun_auth.py)、[xfyun_rtasr.py](file:///e:/Desktop/StreamVis/backend/app/core/xfyun_rtasr.py)
- WebSocket 编排：[main.py](file:///e:/Desktop/StreamVis/backend/app/main.py)

### 8.3 声纹分离（可选增强）

用途：先把 10–60 秒音频注册为 `feature_id`，转写时携带 `feature_ids` 以提升说话人分离稳定性。

实现：
- 前端注册弹窗（录音并上传）：[VoicePrintModal.jsx](file:///e:/Desktop/StreamVis/frontend/src/components/VoicePrintModal.jsx)
- 后端声纹接口封装：[xfyun_voiceprint.py](file:///e:/Desktop/StreamVis/backend/app/core/xfyun_voiceprint.py)
- 后端路由：`/api/xfyun/voiceprint/*`（见 [main.py](file:///e:/Desktop/StreamVis/backend/app/main.py)）

## 9. 配置与开关（.env）

配置加载：[config.py](file:///e:/Desktop/StreamVis/backend/app/core/config.py)

常用开关：
- `STREAMVIS_ENABLE_KIMI`：是否启用 Kimi 作为对话模型
- `STREAMVIS_ENABLE_KIMI_TOOLS`：是否启用 Tool Use（二阶段回填）
- `STREAMVIS_ENABLE_IMAGES`：是否启用 DashScope 图片生成
- `STREAMVIS_ENABLE_XFYUN_ASR`：是否启用讯飞实时转写（/ws/asr）
- `STREAMVIS_ENABLE_PERSISTENT_MEMORY`：是否启用 SQLite 持久化长期记忆

示例配置文件：[backend/.env.example](file:///e:/Desktop/StreamVis/backend/.env.example)

## 10. 自检与诊断

AI 连通性诊断脚本（不会打印密钥）：
- [ai_diagnostics.py](file:///e:/Desktop/StreamVis/backend/scripts/ai_diagnostics.py)

讯飞 RTASR WS 握手诊断（输出 HTTP 状态与错误原因）：
- [xfyun_ws_debug.py](file:///e:/Desktop/StreamVis/backend/scripts/xfyun_ws_debug.py)

