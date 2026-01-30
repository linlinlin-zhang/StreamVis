# StreamVis 系统说明（实现现状与可升级方向）

本文面向“当前代码仓库”的真实实现，说明 StreamVis 已实现的功能、协议与关键算法策略，并列出可继续升级的方向与落点。

## 1. 项目目标与定位

StreamVis 是一个“对话流驱动的增量可视化（Graph Delta）MVP”。核心体验是：

- 前端持续保持与后端的 WebSocket 会话
- 后端在同一会话中并行推送：
  - 文本流（`text_delta`）：assistant 回复可增量展示
  - 图增量（`graph_delta`）：以小步 ops 更新图结构与布局，尽量保持稳定
  - 图片任务（`image`）：可选的文生图/图像编辑异步任务状态与结果

## 2. 当前已实现的功能清单

### 2.1 前端（React + Vite + D3）

- WebSocket 连接管理（自动重连、状态提示）
- 聊天 UI：user/assistant/system 消息展示
- 文本流式渲染：支持 `text_delta.delta` 增量拼接；也兼容 `text_delta.content` 覆盖式更新
- 图渲染：D3 force simulation 持久化，按 `graph_delta.ops` 增量更新节点与连边
- 图预算兼容：支持 `remove_node/remove_edge`，并自动清理悬挂边
- 文件上传入口：顶栏“上传” → 调后端文件抽取接口 → 将抽取内容注入为 system 上下文（不直接展示全文）
- 图片浮层：展示百炼文生图/图像编辑的状态、错误与结果 URL

关键实现：
- WebSocket 消息处理：[App.jsx](file:///e:/Desktop/StreamVis/frontend/src/App.jsx)
- 图增量渲染：[StreamChart.jsx](file:///e:/Desktop/StreamVis/frontend/src/components/StreamChart.jsx)
- 顶栏上传入口：[TopBar.jsx](file:///e:/Desktop/StreamVis/frontend/src/components/TopBar.jsx)

### 2.2 后端（FastAPI + WebSocket）

- WebSocket `/ws/chat`：接收客户端 `user/system/clear`，持续推送事件流
- 健康检查 `/health`
- Kimi（Moonshot）对话：
  - 可选开启：将 Kimi SSE chunk 转成 `text_delta(delta)` 推送
  - 可选开启 Tool Use：一次非流式调用中允许模型输出 tool_calls，下发图/成图/编辑任务
- 百炼（DashScope）成图：
  - 文生图（text-to-image）
  - 图像编辑（image edit）
  - 以后台任务异步等待，推送 `image` 状态：queued/running/succeeded/failed
- Kimi Files（Moonshot 文件抽取）：
  - `POST /api/kimi/files/extract`：上传文件→抽取内容→返回抽取结果（并删除远端文件）
  - 抽取结果由前端通过 WS 发送 `type=system` 注入上下文
- 讯飞实时语音转写（RTASR LLM，可选）：
  - `ws://localhost:8000/ws/asr`：前端上传麦克风 PCM 流，后端代理连接讯飞 RTASR，实时推送 `transcript_delta`（含说话人分离）
  - 声纹分离（可选增强）：提供 `/api/xfyun/voiceprint/*` 注册/更新/删除接口，用注册得到的 `feature_id` 提升分离稳定性

关键实现：
- WebSocket 入口与事件编排：[main.py](file:///e:/Desktop/StreamVis/backend/app/main.py)
- WebSocket 协议模型：[ws.py](file:///e:/Desktop/StreamVis/backend/app/models/ws.py)
- Kimi API 客户端（OpenAI 兼容 Chat Completions）：[kimi_client.py](file:///e:/Desktop/StreamVis/backend/app/core/kimi_client.py)
- Tool Use 定义与解析：[kimi_tools.py](file:///e:/Desktop/StreamVis/backend/app/core/kimi_tools.py)
- Moonshot Files 上传/抽取/删除：[moonshot_files.py](file:///e:/Desktop/StreamVis/backend/app/core/moonshot_files.py)
- 百炼文生图/编辑：[bailian_images.py](file:///e:/Desktop/StreamVis/backend/app/core/bailian_images.py)

## 3. WebSocket 协议（核心数据面）

### 3.1 客户端 → 服务端（ClientMessage）

定义见：[ws.py](file:///e:/Desktop/StreamVis/backend/app/models/ws.py)

- `{"type":"user","content":"..."}`：用户输入
- `{"type":"system","content":"..."}`：system 上下文注入（例如文件抽取内容）
- `{"type":"clear"}`：清空会话（并触发图 clear）

### 3.2 服务端 → 客户端

- `text_delta`
  - `message_id`：一条 assistant 消息的稳定 id
  - `delta`：增量内容（流式时使用）
  - `content`：当前累计内容（兼容覆盖式更新）
  - `is_final`：是否最终
  - `intent`：意图检测结果（含 `visual_necessity_score`）

- `graph_delta`
  - `ops`：图增量操作序列（支持 add/update/remove/clear）

- `image`
  - `status`：disabled/queued/running/succeeded/failed
  - `url`：成功结果
  - `message`：失败原因

## 4. 核心算法/策略（当前实现）

> 本节只描述仓库里“已经落地运行”的策略，并说明其意图与局限。

### 4.1 意图检测（IntentDecoder：规则+打分）

实现：[intent_decoder.py](file:///e:/Desktop/StreamVis/backend/app/core/intent_decoder.py)

- 目标：估计“是否需要可视化”
- 方法：关键词触发 + 数字存在性加分
  - 强触发词：画图/折线图/柱状图/趋势图/plot/graph 等，加 0.7
  - 弱触发词：趋势/对比/波动/compare 等，加 0.25
  - 输入包含数字，加 0.08
- 结果：`visual_necessity_score ∈ [0,1]`，超过阈值则进入可视化链路
- 阈值：`STREAMVIS_VISUAL_THRESHOLD`（默认 0.55）

### 4.2 上下文管理（L1/L2 记忆 + 文件 system）

实现：[context_manager.py](file:///e:/Desktop/StreamVis/backend/app/core/context_manager.py)

- L1：最近对话（deque）+ sink（固定保留头部若干轮）
- L2：淘汰到长期记忆（分段后写入向量库；默认使用 SQLite 持久化）
- system：专门存放 system 注入（文件抽取内容等），最多保留 8 条

向量库与检索策略：
- 向量库：HashingEmbedder + SQLite（可关闭持久化回退为内存）
- 检索：相似度召回 + MMR 多样性重排（降低重复片段、提升覆盖面）
- 文件索引：支持把文件抽取文本分段入库，后续通过检索按需引用

### 4.3 Prompt 预算（token 估算 + 动态裁剪/检索）

实现：[token_budget.py](file:///e:/Desktop/StreamVis/backend/app/core/token_budget.py)，调用在 `ContextManager.get_augmented_context(..., max_prompt_tokens=...)`

- 目的：避免 prompt 过长导致模型超窗/拒绝
- 做法：
  - 近似 token 估算（ASCII 与非 ASCII 分别按比例估算）
  - 单条消息过长截断
  - 在总预算内尽量保留尾部最近 N 条，并从旧到新回填历史消息
  - 动态调整 retrieval_k：根据预算 headroom 估算最多可放入多少条 memory 片段

配置项：
- `STREAMVIS_KIMI_MAX_PROMPT_TOKENS`（默认 5200）

### 4.4 增量可视化触发（两条链路）

#### 链路 A：启发式触发（默认）

逻辑在：[main.py](file:///e:/Desktop/StreamVis/backend/app/main.py)

- 当 `visual_necessity_score >= threshold`：
  - 生成图 ops：`renderer.generate_delta(...)` → 推 `graph_delta`
  -（可选）生成图片任务：推 `image` 事件

#### 链路 B：Tool Use 触发（可选）

启用 `STREAMVIS_ENABLE_KIMI_TOOLS=1` 时：

- Kimi 一次调用可输出 tool_calls
- 后端解析并执行：
  - `render_graph_delta(ops)`：直接推 `graph_delta`
  - `generate_image_prompt(prompt)`：触发百炼文生图
  - `request_image_edit(...)`：触发百炼图像编辑

### 4.5 Wait-k（流式策略驱动“提前出图”）

当使用 Kimi 且关闭 tools（走 SSE 文本流）时：

- 进入文本流循环后，通过 Wait-k 策略机持续观察增量 `delta`
- 满足“累计输出达到 step_chars 或句末/换行边界”且满足最小间隔后，触发一次可视化更新（多阶段）
- 每条消息最多触发 N 次（节流上限），避免过度刷屏与前端抖动
- 触发时会尝试基于 `user_input + assistant_text` 的合并文本更新：
  - `chart_delta`（若可解析出更多数据点/更完整 spec）
  - `graph_delta`（语义图谱可随生成过程逐步补齐）

配置项：
- `STREAMVIS_WAITK_CHARS`（默认 120）
- `STREAMVIS_WAITK_MIN_INTERVAL_MS`（默认 700）
- `STREAMVIS_WAITK_MAX_UPDATES`（默认 4）

### 4.6 图状态预算与淘汰（Graph Budget）

实现：[renderer.py](file:///e:/Desktop/StreamVis/backend/app/core/renderer.py)

- 目标：防止长会话图无限增大导致性能/布局崩坏
- 做法：
  - `max_nodes/max_edges` 约束
  - 超限时按“最早加入节点”淘汰：
    - 下发 `remove_edge`（先移除相关边）
    - 下发 `remove_node`
    - 同步清理内部 graph、pos、edges 列表

配置项：
- `STREAMVIS_GRAPH_MAX_NODES`（默认 60）
- `STREAMVIS_GRAPH_MAX_EDGES`（默认 120）

## 5. 运行与配置

### 5.1 后端

```bash
cd backend
pip install -r requirements.txt
python -m app.main
```

### 5.2 前端

```bash
cd frontend
npm install
npm run dev
```

### 5.3 可选能力开关

见：[backend/.env.example](file:///e:/Desktop/StreamVis/backend/.env.example)

- Kimi（Moonshot）
  - `STREAMVIS_ENABLE_KIMI=1`
  - `MOONSHOT_API_KEY=...`
  - `MOONSHOT_BASE_URL=https://api.moonshot.cn/v1`
  - `STREAMVIS_KIMI_MODEL=moonshot-v1-8k`
- Tool Use
  - `STREAMVIS_ENABLE_KIMI_TOOLS=1`
- 百炼成图/编辑
  - `STREAMVIS_ENABLE_IMAGES=1`
  - `DASHSCOPE_API_KEY=...`

## 6. 验证与脚本

- WebSocket 冒烟（需要后端已在 8000 启动）：[ws_smoke.py](file:///e:/Desktop/StreamVis/backend/scripts/ws_smoke.py)
- 算法冒烟（预算/淘汰/上下文）：[algo_smoke.py](file:///e:/Desktop/StreamVis/backend/scripts/algo_smoke.py)

## 7. 后续可升级改进点（建议路线）

### 7.1 意图与结构化任务图（从“词表打分”升级）

- 用 LLM 输出结构化 JSON（图类型、字段映射、度量/维度、置信度、是否需要用户确认）
- 引入“二阶段确认”：当置信度低时先问 1 个澄清问题再出图
- 落点：
  - 升级 [intent_decoder.py](file:///e:/Desktop/StreamVis/backend/app/core/intent_decoder.py)
  - 或在 [main.py](file:///e:/Desktop/StreamVis/backend/app/main.py) 中做 LLM→回退规则的双通道

### 7.2 图语义（从随机图到数据驱动图）

目前 renderer 是“占位随机图”。下一步可改为：

- 识别实体（指标/维度/时间/类别）→ 构建图 schema
- 节点：字段、指标、派生指标、过滤条件、图层（axes/legend）
- 边：依赖/映射/聚合关系
- 图布局：分层布局（schema 图）+ 数据点渲染（chart 图）

落点：重写 [renderer.py](file:///e:/Desktop/StreamVis/backend/app/core/renderer.py) 的 `generate_delta` 为“plan→ops”。

### 7.3 Wait-k 策略升级（从“一次提前触发”到多阶段流式伴随）

- 增加“冷却窗口/最小间隔”与“分段边界识别”（段落/列表/表格块）
- 允许在流式文本中多次 graph_delta（但要保证前端 simulation 稳定）
- 增加“撤销/修正”op（当模型后续修正理解时回滚局部结构）

落点：[main.py](file:///e:/Desktop/StreamVis/backend/app/main.py) 的流式循环。

### 7.4 Prompt/记忆预算升级

- 用真实 tokenizer 计数（替换近似估算）
- 对 system 注入做“摘要压缩/分块引用”，而不是整段塞入
- 对长期记忆做“相关性 + 新鲜度 + 多样性”重排序

落点：[token_budget.py](file:///e:/Desktop/StreamVis/backend/app/core/token_budget.py)、[context_manager.py](file:///e:/Desktop/StreamVis/backend/app/core/context_manager.py)

### 7.5 Tool Use 完整闭环

目前工具主要负责“graph_delta / prompt / edit 参数”。进一步可以：

- 增加 `parse_table`/`infer_schema`/`suggest_chart_spec` 等工具
- 让模型输出 Vega-Lite/ECharts spec，由前端渲染（从图结构图走向真正 chart）
- 工具执行结果回灌为 tool message，形成多轮工具链

落点：[kimi_tools.py](file:///e:/Desktop/StreamVis/backend/app/core/kimi_tools.py)、[main.py](file:///e:/Desktop/StreamVis/backend/app/main.py)
