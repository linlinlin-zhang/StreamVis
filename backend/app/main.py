import json
import logging
import asyncio
import uuid

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

from app.core.bailian_images import BailianError, BailianImagesClient
from app.core.config import get_settings
from app.core.context_manager import ContextManager
from app.core.intent_decoder import IntentDecoder
from app.core.kimi_client import KimiClient, KimiError
from app.core.kimi_tools import build_streamvis_tools, parse_tool_calls_from_chat_response
from app.core.moonshot_files import MoonshotError, MoonshotFilesClient
from app.core.renderer import IncrementalRenderer
from app.models.ws import ClientMessage, GraphDeltaEvent, ImageEvent, TextDeltaEvent

app = FastAPI(title="StreamVis API")

settings = get_settings()
logger = logging.getLogger("streamvis")

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

@app.websocket("/ws/chat")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    session_id = str(uuid.uuid4())[:8]
    context_manager = ContextManager(
        l1_max_turns=settings.l1_max_turns,
        sink_turns=settings.sink_turns,
        retrieval_k=settings.retrieval_k,
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
                context_manager.clear()
                ops = renderer.clear()
                await websocket.send_text(GraphDeltaEvent(ops=ops).model_dump_json())
                continue
            if msg.type == "system":
                context_manager.add_system_context(msg.content or "")
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

                        for c in calls:
                            if c.name == "render_graph_delta":
                                ops = c.arguments.get("ops") or []
                                if isinstance(ops, list) and ops:
                                    graph_emitted = True
                                    await websocket.send_text(GraphDeltaEvent(ops=ops).model_dump_json())

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
                                elif not images_client:
                                    await websocket.send_text(
                                        ImageEvent(
                                            request_id=image_request_id,
                                            status="failed",
                                            message="未配置 DASHSCOPE_API_KEY，无法调用图片模型。",
                                        ).model_dump_json()
                                    )
                                else:
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
                                elif not images_client:
                                    await websocket.send_text(
                                        ImageEvent(
                                            request_id=image_request_id,
                                            status="failed",
                                            message="未配置 DASHSCOPE_API_KEY，无法调用图片模型。",
                                        ).model_dump_json()
                                    )
                                else:
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

                        if graph_emitted or image_emitted:
                            continue
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
                        acc_chars = 0
                        waitk = max(0, int(settings.waitk_chars))

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
                            acc_chars += len(delta)
                            if need_visual and (not graph_emitted):
                                boundary_hit = any(p in delta for p in ("。", "！", "？", ".", "!", "?", "\n"))
                                if acc_chars >= waitk or boundary_hit:
                                    ops = renderer.generate_delta(intent, context_manager.get_context_vector())
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
                if not graph_emitted:
                    ops = renderer.generate_delta(intent, context_manager.get_context_vector())
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

if __name__ == "__main__":
    logging.basicConfig(level=settings.log_level.upper())
    uvicorn.run("app.main:app", host=settings.host, port=settings.port, reload=True)
