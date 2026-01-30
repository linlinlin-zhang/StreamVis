import json
import logging
import asyncio
import uuid
import time
import os

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

from app.core.bailian_images import BailianError, BailianImagesClient
from app.core.config import get_settings
from app.core.context_manager import ContextManager
from app.core.chart_parser import parse_chart_spec
from app.core.context_summary import summarize_system_context
from app.core.file_indexer import index_text
from app.core.intent_decoder import IntentDecoder
from app.core.kimi_client import KimiClient, KimiError
from app.core.kimi_tools import build_streamvis_tools, get_raw_tool_calls, parse_tool_calls_from_chat_response
from app.core.moonshot_files import MoonshotError, MoonshotFilesClient
from app.core.renderer import IncrementalRenderer
from app.core.vector_store import PersistentVectorStore
from app.core.waitk_policy import WaitKPolicy
from app.core.xfyun_rtasr import stream_rtasr
from app.core.xfyun_voiceprint import delete_voiceprint, register_voiceprint, update_voiceprint
from app.models.ws import ChartDeltaEvent, ClientMessage, GraphDeltaEvent, ImageEvent, TextDeltaEvent, TranscriptDeltaEvent

app = FastAPI(title="StreamVis API")

settings = get_settings()
logger = logging.getLogger("streamvis")

_backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
_memory_store: PersistentVectorStore | None = None
if settings.enable_persistent_memory:
    db_path = settings.memory_db_path
    if not os.path.isabs(db_path):
        db_path = os.path.join(_backend_dir, db_path)
    _memory_store = PersistentVectorStore(db_path=db_path)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    return {"message": "StreamVis API is running"}

@app.get("/health")
async def health():
    return {"status": "ok"}


@app.post("/api/kimi/files/extract")
async def kimi_extract_file(file: UploadFile = File(...)):
    if not settings.enable_kimi or not settings.moonshot_api_key:
        raise HTTPException(status_code=400, detail="Kimi 未启用或未配置 MOONSHOT_API_KEY")
    raw = await file.read()
    if not raw:
        raise HTTPException(status_code=400, detail="空文件")
    client = MoonshotFilesClient(api_key=settings.moonshot_api_key, base_url=settings.moonshot_base_url)
    try:
        uploaded = await asyncio.to_thread(client.upload, file_bytes=raw, filename=file.filename or "upload.bin", purpose="file-extract")
        content = await asyncio.to_thread(client.retrieve_content, file_id=uploaded.id)
        await asyncio.to_thread(client.delete, file_id=uploaded.id)
        return {"file_id": uploaded.id, "filename": uploaded.filename, "content": content}
    except MoonshotError as e:
        raise HTTPException(status_code=502, detail=str(e))


@app.post("/api/kimi/files/index")
async def kimi_index_file(file: UploadFile = File(...)):
    if not settings.enable_kimi or not settings.moonshot_api_key:
        raise HTTPException(status_code=400, detail="Kimi 未启用或未配置 MOONSHOT_API_KEY")
    if not _memory_store:
        raise HTTPException(status_code=400, detail="未启用持久化记忆库")
    raw = await file.read()
    if not raw:
        raise HTTPException(status_code=400, detail="空文件")
    client = MoonshotFilesClient(api_key=settings.moonshot_api_key, base_url=settings.moonshot_base_url)
    try:
        uploaded = await asyncio.to_thread(client.upload, file_bytes=raw, filename=file.filename or "upload.bin", purpose="file-extract")
        content = await asyncio.to_thread(client.retrieve_content, file_id=uploaded.id)
        await asyncio.to_thread(client.delete, file_id=uploaded.id)

        count, ids = await asyncio.to_thread(
            index_text,
            store=_memory_store,
            text=content,
            meta={"source": "file", "filename": uploaded.filename, "file_id": uploaded.id, "kind": "file"},
        )

        system_ctx = f"[File:{uploaded.filename}#{uploaded.id}] 已索引 {count} 段，可在提问时按需检索引用。"
        if settings.enable_context_summary and content and len(content) > settings.system_context_max_chars:
            summary = await asyncio.to_thread(
                summarize_system_context,
                None,
                content,
                target_chars=settings.system_context_summary_chars,
            )
            if summary:
                system_ctx = system_ctx + "\n摘要：" + summary

        return {
            "file_id": uploaded.id,
            "filename": uploaded.filename,
            "chunks_indexed": count,
            "chunk_ids": ids[:50],
            "system_context": system_ctx,
        }
    except MoonshotError as e:
        raise HTTPException(status_code=502, detail=str(e))


@app.get("/api/memory/search")
async def memory_search(q: str, k: int = 6):
    if not _memory_store:
        raise HTTPException(status_code=400, detail="未启用持久化记忆库")
    kk = max(1, min(20, int(k)))
    hits = await asyncio.to_thread(_memory_store.search, q, kk, None, mmr_lambda=settings.mmr_lambda, candidate_pool=kk * settings.mmr_pool_mult)
    out = []
    for h in hits:
        out.append({"id": h.id, "text": h.text[:220], "meta": h.meta})
    return {"hits": out}


@app.post("/api/xfyun/voiceprint/register")
async def xfyun_voiceprint_register(file: UploadFile = File(...), uid: str = ""):
    if not settings.xfyun_enable:
        raise HTTPException(status_code=400, detail="未启用讯飞 ASR：请设置 STREAMVIS_ENABLE_XFYUN_ASR=1")
    if not (settings.xfyun_app_id and settings.xfyun_access_key_id and settings.xfyun_access_key_secret):
        raise HTTPException(status_code=400, detail="缺少讯飞鉴权配置")
    if not settings.xfyun_voiceprint_register_url:
        raise HTTPException(status_code=400, detail="未配置 XFYUN_VOICEPRINT_REGISTER_URL（从 voice_print 文档复制请求地址）")
    raw = await file.read()
    if not raw:
        raise HTTPException(status_code=400, detail="空音频")
    res = await asyncio.to_thread(
        register_voiceprint,
        register_url=settings.xfyun_voiceprint_register_url,
        app_id=settings.xfyun_app_id,
        access_key_id=settings.xfyun_access_key_id,
        access_key_secret=settings.xfyun_access_key_secret,
        audio_bytes=raw,
        audio_type="raw",
        uid=uid,
    )
    return {"code": res.code, "desc": res.desc, "feature_id": res.feature_id, "raw": res.raw}


@app.post("/api/xfyun/voiceprint/update")
async def xfyun_voiceprint_update(feature_id: str, file: UploadFile = File(...)):
    if not settings.xfyun_enable:
        raise HTTPException(status_code=400, detail="未启用讯飞 ASR：请设置 STREAMVIS_ENABLE_XFYUN_ASR=1")
    if not (settings.xfyun_app_id and settings.xfyun_access_key_id and settings.xfyun_access_key_secret):
        raise HTTPException(status_code=400, detail="缺少讯飞鉴权配置")
    if not settings.xfyun_voiceprint_update_url:
        raise HTTPException(status_code=400, detail="未配置 XFYUN_VOICEPRINT_UPDATE_URL（从 voice_print 文档复制请求地址）")
    raw = await file.read()
    if not raw:
        raise HTTPException(status_code=400, detail="空音频")
    resp = await asyncio.to_thread(
        update_voiceprint,
        update_url=settings.xfyun_voiceprint_update_url,
        app_id=settings.xfyun_app_id,
        access_key_id=settings.xfyun_access_key_id,
        access_key_secret=settings.xfyun_access_key_secret,
        feature_id=feature_id,
        audio_bytes=raw,
        audio_type="raw",
    )
    return resp


@app.post("/api/xfyun/voiceprint/delete")
async def xfyun_voiceprint_delete(feature_ids: str):
    if not settings.xfyun_enable:
        raise HTTPException(status_code=400, detail="未启用讯飞 ASR：请设置 STREAMVIS_ENABLE_XFYUN_ASR=1")
    if not (settings.xfyun_app_id and settings.xfyun_access_key_id and settings.xfyun_access_key_secret):
        raise HTTPException(status_code=400, detail="缺少讯飞鉴权配置")
    if not settings.xfyun_voiceprint_delete_url:
        raise HTTPException(status_code=400, detail="未配置 XFYUN_VOICEPRINT_DELETE_URL（从 voice_print 文档复制请求地址）")
    ids = [s.strip() for s in str(feature_ids).split(",") if s.strip()]
    if not ids:
        raise HTTPException(status_code=400, detail="feature_ids 为空")
    resp = await asyncio.to_thread(
        delete_voiceprint,
        delete_url=settings.xfyun_voiceprint_delete_url,
        app_id=settings.xfyun_app_id,
        access_key_id=settings.xfyun_access_key_id,
        access_key_secret=settings.xfyun_access_key_secret,
        feature_ids=ids,
    )
    return resp

@app.websocket("/ws/chat")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    session_id = str(uuid.uuid4())[:8]
    context_manager = ContextManager(
        l1_max_turns=settings.l1_max_turns,
        sink_turns=settings.sink_turns,
        retrieval_k=settings.retrieval_k,
        mmr_lambda=settings.mmr_lambda,
        mmr_pool_mult=settings.mmr_pool_mult,
        store=_memory_store,
    )
    intent_decoder = IntentDecoder()
    renderer = IncrementalRenderer(max_nodes=settings.graph_max_nodes, max_edges=settings.graph_max_edges)
    send_lock = asyncio.Lock()
    bg_tasks: set[asyncio.Task] = set()

    images_client: BailianImagesClient | None = None
    if settings.enable_images and settings.dashscope_api_key:
        images_client = BailianImagesClient(
            api_key=settings.dashscope_api_key,
            base_url=settings.dashscope_base_url,
            workspace=settings.dashscope_workspace or None,
        )
    kimi_client: KimiClient | None = None
    if settings.enable_kimi and settings.moonshot_api_key:
        kimi_client = KimiClient(
            api_key=settings.moonshot_api_key,
            base_url=settings.moonshot_base_url,
            model=settings.moonshot_model,
            timeout_s=70.0,
        )

    try:
        while True:
            raw = await websocket.receive_text()
            try:
                payload = json.loads(raw)
            except json.JSONDecodeError:
                evt = TextDeltaEvent(
                    message_id=f"sys_{session_id}",
                    content="消息格式错误：需要 JSON。",
                    is_final=True,
                )
                await websocket.send_text(evt.model_dump_json())
                continue

            try:
                msg = ClientMessage.model_validate(payload)
            except Exception:
                evt = TextDeltaEvent(
                    message_id=f"sys_{session_id}",
                    content="消息字段不合法。",
                    is_final=True,
                )
                await websocket.send_text(evt.model_dump_json())
                continue

            if msg.type == "clear":
                context_manager.clear(preserve_long_term=bool(_memory_store))
                ops = renderer.clear()
                await websocket.send_text(GraphDeltaEvent(ops=ops).model_dump_json())
                continue
            if msg.type == "system":
                raw_ctx = msg.content or ""
                if settings.enable_context_summary and raw_ctx and len(raw_ctx) > settings.system_context_max_chars:
                    summary = await asyncio.to_thread(
                        summarize_system_context,
                        kimi_client,
                        raw_ctx,
                        target_chars=settings.system_context_summary_chars,
                    )
                    context_manager.add_system_context(summary)
                else:
                    context_manager.add_system_context(raw_ctx)
                continue

            user_input = (msg.content or "").strip()
            if not user_input:
                continue

            context_manager.add_user_input(user_input)
            augmented_context = context_manager.get_augmented_context(user_input, max_prompt_tokens=settings.kimi_max_prompt_tokens)
            intent = intent_decoder.detect(user_input, augmented_context)
            intent["memory_hits"] = len(context_manager.retrieve(user_input, k=settings.retrieval_k))
            assistant_message_id = f"a_{session_id}_{uuid.uuid4().hex[:8]}"
            assistant_text = ""
            graph_emitted = False
            image_emitted = False
            tool_mode_used = False
            if not kimi_client:
                assistant_text = f"收到：{user_input}"
                context_manager.add_assistant_output(assistant_text)
                await websocket.send_text(
                    TextDeltaEvent(
                        message_id=assistant_message_id,
                        content=assistant_text,
                        is_final=True,
                        intent=intent,
                    ).model_dump_json()
                )
                if float(intent.get("visual_necessity_score", 0.0)) >= settings.visual_threshold:
                    spec = parse_chart_spec(user_input)
                    if not spec or not spec.points:
                        hint_id = f"a_{session_id}_{uuid.uuid4().hex[:8]}"
                        hint = "为了生成趋势图，请补充可解析的数据序列，例如：Q1 X=120，Q2 X=130，Q3 X=90；或 1月 100，2月 120，3月 90。"
                        context_manager.add_assistant_output(hint)
                        await websocket.send_text(
                            TextDeltaEvent(
                                message_id=hint_id,
                                content=hint,
                                is_final=True,
                            ).model_dump_json()
                        )
            else:
                system_msg = {
                    "role": "system",
                    "content": "你是 StreamVis 助手：输出要简洁、结构清晰；当用户需要可视化时，解释你将如何展示（但不要编造数据）。",
                }
                messages = [system_msg]
                for m in augmented_context:
                    role = m.get("role")
                    content = m.get("content")
                    if role in {"user", "assistant", "system"} and isinstance(content, str) and content.strip():
                        messages.append({"role": role, "content": content})

                try:
                    if settings.enable_kimi_tools:
                        tool_mode_used = True
                        resp = await asyncio.to_thread(
                            kimi_client.chat,
                            messages=messages,
                            temperature=0.3,
                            tools=build_streamvis_tools(),
                            tool_choice="auto",
                            stream=False,
                        )
                        assistant_text, calls = parse_tool_calls_from_chat_response(resp)
                        if not assistant_text:
                            assistant_text = "（Kimi 未返回文本内容）"
                        async with send_lock:
                            await websocket.send_text(
                                TextDeltaEvent(
                                    message_id=assistant_message_id,
                                    content=assistant_text,
                                    is_final=False,
                                    intent=intent,
                                ).model_dump_json()
                            )

                        tool_results = {}
                        for c in calls:
                            if c.name == "render_graph_delta":
                                ops = c.arguments.get("ops") or []
                                if isinstance(ops, list) and ops:
                                    graph_emitted = True
                                    await websocket.send_text(GraphDeltaEvent(ops=ops).model_dump_json())
                                    tool_results[c.id] = {"ok": True, "type": "graph_delta", "ops_count": len(ops)}

                            if c.name == "generate_image_prompt":
                                if not isinstance(c.arguments, dict):
                                    continue
                                prompt = str(c.arguments.get("prompt") or "").strip()
                                negative_prompt = str(c.arguments.get("negative_prompt") or "").strip()
                                if not prompt:
                                    continue
                                image_emitted = True
                                image_request_id = f"img_{session_id}_{uuid.uuid4().hex[:8]}"
                                if not settings.enable_images:
                                    await websocket.send_text(
                                        ImageEvent(request_id=image_request_id, status="disabled", message="图片服务未启用").model_dump_json()
                                    )
                                    tool_results[c.id] = {"ok": False, "type": "image", "status": "disabled"}
                                elif not images_client:
                                    await websocket.send_text(
                                        ImageEvent(
                                            request_id=image_request_id,
                                            status="failed",
                                            message="未配置 DASHSCOPE_API_KEY，无法调用图片模型。",
                                        ).model_dump_json()
                                    )
                                    tool_results[c.id] = {"ok": False, "type": "image", "status": "failed"}
                                else:
                                    tool_results[c.id] = {"ok": True, "type": "image", "status": "queued", "request_id": image_request_id}
                                    async def _run_image_job() -> None:
                                        async with send_lock:
                                            await websocket.send_text(
                                                ImageEvent(request_id=image_request_id, status="queued", prompt=prompt).model_dump_json()
                                            )
                                        try:
                                            async with send_lock:
                                                await websocket.send_text(
                                                    ImageEvent(request_id=image_request_id, status="running", prompt=prompt).model_dump_json()
                                                )
                                            task_id = await asyncio.to_thread(
                                                images_client.create_text_to_image_task,
                                                model=settings.t2i_model,
                                                prompt=prompt,
                                                negative_prompt=negative_prompt or "文字、水印、模糊、低分辨率、扭曲",
                                                size=settings.t2i_size,
                                                n=1,
                                                style="<auto>",
                                            )
                                            result = await images_client.wait_task(task_id, timeout_s=90.0)
                                            url = result.urls[0]
                                            async with send_lock:
                                                await websocket.send_text(
                                                    ImageEvent(
                                                        request_id=image_request_id,
                                                        status="succeeded",
                                                        prompt=prompt,
                                                        task_id=task_id,
                                                        url=url,
                                                    ).model_dump_json()
                                                )
                                        except BailianError as e:
                                            async with send_lock:
                                                await websocket.send_text(
                                                    ImageEvent(
                                                        request_id=image_request_id,
                                                        status="failed",
                                                        prompt=prompt,
                                                        message=str(e),
                                                    ).model_dump_json()
                                                )
                                        except Exception:
                                            async with send_lock:
                                                await websocket.send_text(
                                                    ImageEvent(
                                                        request_id=image_request_id,
                                                        status="failed",
                                                        prompt=prompt,
                                                        message="图片生成失败（未知错误）。",
                                                    ).model_dump_json()
                                                )

                                    task = asyncio.create_task(_run_image_job())
                                    bg_tasks.add(task)
                                    task.add_done_callback(lambda t: bg_tasks.discard(t))

                            if c.name == "request_image_edit":
                                if not isinstance(c.arguments, dict):
                                    continue
                                function = str(c.arguments.get("function") or "").strip()
                                prompt = str(c.arguments.get("prompt") or "").strip()
                                base_image_url = str(c.arguments.get("base_image_url") or "").strip()
                                n = int(c.arguments.get("n") or 1)
                                if not function or not prompt or not base_image_url:
                                    continue
                                image_emitted = True
                                image_request_id = f"img_{session_id}_{uuid.uuid4().hex[:8]}"
                                if not settings.enable_images:
                                    await websocket.send_text(
                                        ImageEvent(request_id=image_request_id, status="disabled", message="图片服务未启用").model_dump_json()
                                    )
                                    tool_results[c.id] = {"ok": False, "type": "image_edit", "status": "disabled"}
                                elif not images_client:
                                    await websocket.send_text(
                                        ImageEvent(
                                            request_id=image_request_id,
                                            status="failed",
                                            message="未配置 DASHSCOPE_API_KEY，无法调用图片模型。",
                                        ).model_dump_json()
                                    )
                                    tool_results[c.id] = {"ok": False, "type": "image_edit", "status": "failed"}
                                else:
                                    tool_results[c.id] = {"ok": True, "type": "image_edit", "status": "queued", "request_id": image_request_id}
                                    async def _run_edit_job() -> None:
                                        async with send_lock:
                                            await websocket.send_text(
                                                ImageEvent(request_id=image_request_id, status="queued", prompt=prompt).model_dump_json()
                                            )
                                        try:
                                            async with send_lock:
                                                await websocket.send_text(
                                                    ImageEvent(request_id=image_request_id, status="running", prompt=prompt).model_dump_json()
                                                )
                                            task_id = await asyncio.to_thread(
                                                images_client.create_image_edit_task,
                                                model=settings.imageedit_model,
                                                function=function,
                                                prompt=prompt,
                                                base_image_url=base_image_url,
                                                n=n,
                                            )
                                            result = await images_client.wait_task(task_id, timeout_s=90.0)
                                            url = result.urls[0]
                                            async with send_lock:
                                                await websocket.send_text(
                                                    ImageEvent(
                                                        request_id=image_request_id,
                                                        status="succeeded",
                                                        prompt=prompt,
                                                        task_id=task_id,
                                                        url=url,
                                                    ).model_dump_json()
                                                )
                                        except BailianError as e:
                                            async with send_lock:
                                                await websocket.send_text(
                                                    ImageEvent(
                                                        request_id=image_request_id,
                                                        status="failed",
                                                        prompt=prompt,
                                                        message=str(e),
                                                    ).model_dump_json()
                                                )
                                        except Exception:
                                            async with send_lock:
                                                await websocket.send_text(
                                                    ImageEvent(
                                                        request_id=image_request_id,
                                                        status="failed",
                                                        prompt=prompt,
                                                        message="图片编辑失败（未知错误）。",
                                                    ).model_dump_json()
                                                )

                                    task = asyncio.create_task(_run_edit_job())
                                    bg_tasks.add(task)
                                    task.add_done_callback(lambda t: bg_tasks.discard(t))

                        raw_tool_calls = get_raw_tool_calls(resp)
                        if raw_tool_calls and tool_results:
                            followup_messages = list(messages)
                            followup_messages.append({"role": "assistant", "content": assistant_text, "tool_calls": raw_tool_calls})
                            for tc in raw_tool_calls:
                                tc_id = str(tc.get("id") or "")
                                if not tc_id:
                                    continue
                                result = tool_results.get(tc_id) or {"ok": True}
                                followup_messages.append(
                                    {
                                        "role": "tool",
                                        "tool_call_id": tc_id,
                                        "content": json.dumps(result, ensure_ascii=False),
                                    }
                                )
                            resp2 = await asyncio.to_thread(
                                kimi_client.chat,
                                messages=followup_messages,
                                temperature=0.3,
                                stream=False,
                            )
                            choices2 = resp2.get("choices") or []
                            msg2 = (choices2[0] or {}).get("message") if choices2 else {}
                            final_text = (msg2 or {}).get("content") or ""
                            if not str(final_text).strip():
                                final_text = assistant_text
                            context_manager.add_assistant_output(final_text)
                            async with send_lock:
                                await websocket.send_text(
                                    TextDeltaEvent(
                                        message_id=assistant_message_id,
                                        content=final_text,
                                        is_final=True,
                                        intent=intent,
                                    ).model_dump_json()
                                )
                            if graph_emitted or image_emitted:
                                continue
                        else:
                            context_manager.add_assistant_output(assistant_text)
                            async with send_lock:
                                await websocket.send_text(
                                    TextDeltaEvent(
                                        message_id=assistant_message_id,
                                        content=assistant_text,
                                        is_final=True,
                                        intent=intent,
                                    ).model_dump_json()
                                )
                    if not settings.enable_kimi_tools:
                        async with send_lock:
                            await websocket.send_text(
                                TextDeltaEvent(
                                    message_id=assistant_message_id,
                                    content="",
                                    delta=None,
                                    is_final=False,
                                    intent=intent,
                                ).model_dump_json()
                            )

                        q: asyncio.Queue = asyncio.Queue()
                        done = object()
                        loop = asyncio.get_running_loop()

                        import threading

                        def _worker() -> None:
                            try:
                                for ch in kimi_client.stream_chat(messages=messages):
                                    asyncio.run_coroutine_threadsafe(q.put(ch), loop)
                            finally:
                                asyncio.run_coroutine_threadsafe(q.put(done), loop)

                        threading.Thread(target=_worker, daemon=True).start()

                        need_visual = float(intent.get("visual_necessity_score", 0.0)) >= settings.visual_threshold
                        policy = WaitKPolicy(
                            step_chars=int(settings.waitk_chars),
                            min_interval_ms=int(settings.waitk_min_interval_ms),
                            max_updates=int(settings.waitk_max_updates),
                        )
                        last_chart_sig = None

                        while True:
                            item = await q.get()
                            if item is done:
                                break
                            chunk = item
                            if getattr(chunk, "is_done", False):
                                break
                            delta = getattr(chunk, "delta", "")
                            if not delta:
                                continue
                            assistant_text += delta
                            if need_visual:
                                now_ms = int(time.monotonic() * 1000)
                                if policy.observe(delta=delta, now_ms=now_ms):
                                    combined = f"{user_input}\n{assistant_text}"
                                    spec = parse_chart_spec(combined)
                                    if spec and spec.points:
                                        sig = (spec.chart_type, spec.title, spec.x_label, spec.y_label, spec.series_name, tuple((p.x, p.y) for p in spec.points))
                                        if sig != last_chart_sig:
                                            last_chart_sig = sig
                                            async with send_lock:
                                                await websocket.send_text(
                                                    ChartDeltaEvent(
                                                        chart_type=spec.chart_type,
                                                        title=spec.title,
                                                        x_label=spec.x_label,
                                                        y_label=spec.y_label,
                                                        series_name=spec.series_name,
                                                        points=[{"x": p.x, "y": p.y} for p in spec.points],
                                                    ).model_dump_json()
                                                )

                                    ops = renderer.generate_delta(
                                        intent,
                                        context_manager.get_context_vector(),
                                        user_input=combined,
                                    )
                                    async with send_lock:
                                        await websocket.send_text(GraphDeltaEvent(ops=ops).model_dump_json())
                                    graph_emitted = True
                            async with send_lock:
                                await websocket.send_text(
                                    TextDeltaEvent(
                                        message_id=assistant_message_id,
                                        content=assistant_text,
                                        delta=delta,
                                        is_final=False,
                                    ).model_dump_json()
                                )

                        context_manager.add_assistant_output(assistant_text)
                        async with send_lock:
                            await websocket.send_text(
                                TextDeltaEvent(
                                    message_id=assistant_message_id,
                                    content=assistant_text,
                                    is_final=True,
                                    intent=intent,
                                ).model_dump_json()
                            )
                except KimiError as e:
                    assistant_text = f"（Kimi 调用失败）{str(e)}"
                    context_manager.add_assistant_output(assistant_text)
                    async with send_lock:
                        await websocket.send_text(
                            TextDeltaEvent(
                                message_id=assistant_message_id,
                                content=assistant_text,
                                is_final=True,
                                intent=intent,
                            ).model_dump_json()
                        )

            if float(intent.get("visual_necessity_score", 0.0)) >= settings.visual_threshold:
                if tool_mode_used and (graph_emitted or image_emitted):
                    continue
                combined_final = f"{user_input}\n{assistant_text}"
                spec = parse_chart_spec(combined_final)
                if spec and spec.points:
                    await websocket.send_text(
                        ChartDeltaEvent(
                            chart_type=spec.chart_type,
                            title=spec.title,
                            x_label=spec.x_label,
                            y_label=spec.y_label,
                            series_name=spec.series_name,
                            points=[{"x": p.x, "y": p.y} for p in spec.points],
                        ).model_dump_json()
                    )
                if not graph_emitted:
                    ops = renderer.generate_delta(
                        intent,
                        context_manager.get_context_vector(),
                        user_input=combined_final,
                    )
                    await websocket.send_text(GraphDeltaEvent(ops=ops).model_dump_json())

                image_request_id = f"img_{session_id}_{uuid.uuid4().hex[:8]}"
                if not settings.enable_images:
                    await websocket.send_text(
                        ImageEvent(request_id=image_request_id, status="disabled", message="图片服务未启用").model_dump_json()
                    )
                    continue
                if not images_client:
                    await websocket.send_text(
                        ImageEvent(
                            request_id=image_request_id,
                            status="failed",
                            message="未配置 DASHSCOPE_API_KEY，无法调用图片模型。",
                        ).model_dump_json()
                    )
                    continue
                if image_emitted:
                    continue

                prompt = (
                    "生成一张深色科技风的数据可视化信息图（chart-like），内容与用户描述一致，"
                    "尽量避免出现难以辨认的文字；整体简洁，重点突出。\n用户描述："
                    + user_input
                )

                async def _run_image_job() -> None:
                    async with send_lock:
                        await websocket.send_text(
                            ImageEvent(request_id=image_request_id, status="queued", prompt=prompt).model_dump_json()
                        )
                    try:
                        async with send_lock:
                            await websocket.send_text(
                                ImageEvent(request_id=image_request_id, status="running", prompt=prompt).model_dump_json()
                            )
                        task_id = await asyncio.to_thread(
                            images_client.create_text_to_image_task,
                            model=settings.t2i_model,
                            prompt=prompt,
                            negative_prompt="文字、水印、模糊、低分辨率、过度锐化、扭曲",
                            size=settings.t2i_size,
                            n=1,
                            style="<auto>",
                        )
                        result = await images_client.wait_task(task_id, timeout_s=90.0)
                        url = result.urls[0]
                        async with send_lock:
                            await websocket.send_text(
                                ImageEvent(
                                    request_id=image_request_id,
                                    status="succeeded",
                                    prompt=prompt,
                                    task_id=task_id,
                                    url=url,
                                ).model_dump_json()
                            )
                    except BailianError as e:
                        async with send_lock:
                            await websocket.send_text(
                                ImageEvent(
                                    request_id=image_request_id,
                                    status="failed",
                                    prompt=prompt,
                                    message=str(e),
                                ).model_dump_json()
                            )
                    except Exception:
                        async with send_lock:
                            await websocket.send_text(
                                ImageEvent(
                                    request_id=image_request_id,
                                    status="failed",
                                    prompt=prompt,
                                    message="图片生成失败（未知错误）。",
                                ).model_dump_json()
                            )

                task = asyncio.create_task(_run_image_job())
                bg_tasks.add(task)
                task.add_done_callback(lambda t: bg_tasks.discard(t))

    except WebSocketDisconnect:
        logger.info("ws disconnected session=%s", session_id)
        for t in list(bg_tasks):
            t.cancel()


@app.websocket("/ws/asr")
async def websocket_asr(websocket: WebSocket):
    await websocket.accept()
    if not settings.xfyun_enable:
        await websocket.send_text(
            TextDeltaEvent(message_id="sys_asr", content="ASR 未启用：请设置 STREAMVIS_ENABLE_XFYUN_ASR=1", is_final=True).model_dump_json()
        )
        await websocket.close()
        return
    if not (settings.xfyun_app_id and settings.xfyun_access_key_id and settings.xfyun_access_key_secret):
        await websocket.send_text(
            TextDeltaEvent(
                message_id="sys_asr",
                content="ASR 配置缺失：请配置 XFYUN_APP_ID / XFYUN_ACCESS_KEY_ID / XFYUN_ACCESS_KEY_SECRET",
                is_final=True,
            ).model_dump_json()
        )
        await websocket.close()
        return

    audio_q: asyncio.Queue[bytes | None] = asyncio.Queue()
    started = False

    async def _audio_iter():
        while True:
            item = await audio_q.get()
            if item is None:
                break
            yield item

    async def _run_asr(feature_ids: str, eng_spk_match: int) -> None:
        async for evt in stream_rtasr(
            base_url=settings.xfyun_rtasr_base_url,
            app_id=settings.xfyun_app_id,
            access_key_id=settings.xfyun_access_key_id,
            access_key_secret=settings.xfyun_access_key_secret,
            audio_iter=_audio_iter(),
            lang=settings.xfyun_lang,
            audio_encode=settings.xfyun_audio_encode,
            samplerate=settings.xfyun_samplerate,
            role_type=settings.xfyun_role_type,
            feature_ids=feature_ids,
            eng_spk_match=eng_spk_match,
        ):
            await websocket.send_text(
                TranscriptDeltaEvent(
                    segment_id=evt.segment_id,
                    speaker=evt.speaker,
                    text=evt.text,
                    is_final=evt.is_final,
                ).model_dump_json()
            )

    asr_task: asyncio.Task | None = None
    try:
        while True:
            msg = await websocket.receive()
            if "text" in msg and msg["text"] is not None:
                try:
                    payload = json.loads(msg["text"])
                except Exception:
                    continue
                action = str(payload.get("type") or payload.get("action") or "")
                if action == "start" and not started:
                    started = True
                    feature_ids = str(payload.get("feature_ids") or settings.xfyun_feature_ids or "").strip()
                    eng_spk_match = int(payload.get("eng_spk_match") or settings.xfyun_eng_spk_match or 0)
                    asr_task = asyncio.create_task(_run_asr(feature_ids, eng_spk_match))
                    await websocket.send_text(
                        TextDeltaEvent(message_id="sys_asr", content="ASR 已开始（说话人分离已开启）", is_final=True).model_dump_json()
                    )
                if action == "stop":
                    break
            if "bytes" in msg and msg["bytes"] is not None:
                if not started:
                    continue
                await audio_q.put(msg["bytes"])
    except WebSocketDisconnect:
        pass
    finally:
        await audio_q.put(None)
        if asr_task:
            try:
                await asyncio.wait_for(asr_task, timeout=3.0)
            except Exception:
                asr_task.cancel()
        try:
            await websocket.close()
        except Exception:
            pass

if __name__ == "__main__":
    logging.basicConfig(level=settings.log_level.upper())
    logging.basicConfig(level=settings.log_level.upper())
    uvicorn.run("app.main:app", host=settings.host, port=settings.port, reload=True)
