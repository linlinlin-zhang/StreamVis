import json
import logging
import uuid

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

from app.core.config import get_settings
from app.core.context_manager import ContextManager
from app.core.intent_decoder import IntentDecoder
from app.core.renderer import IncrementalRenderer
from app.models.ws import ClientMessage, GraphDeltaEvent, TextDeltaEvent

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

@app.websocket("/ws/chat")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    session_id = str(uuid.uuid4())[:8]
    context_manager = ContextManager()
    intent_decoder = IntentDecoder()
    renderer = IncrementalRenderer()

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

            user_input = (msg.content or "").strip()
            if not user_input:
                continue

            context_manager.add_user_input(user_input)
            intent = intent_decoder.detect(user_input, context_manager.get_recent_context())
            assistant_message_id = f"a_{session_id}_{uuid.uuid4().hex[:8]}"
            response_text = f"收到：{user_input}"
            context_manager.add_assistant_output(response_text)

            await websocket.send_text(
                TextDeltaEvent(
                    message_id=assistant_message_id,
                    content=response_text,
                    is_final=True,
                    intent=intent,
                ).model_dump_json()
            )

            if float(intent.get("visual_necessity_score", 0.0)) >= settings.visual_threshold:
                ops = renderer.generate_delta(intent, context_manager.get_context_vector())
                await websocket.send_text(GraphDeltaEvent(ops=ops).model_dump_json())

    except WebSocketDisconnect:
        logger.info("ws disconnected session=%s", session_id)

if __name__ == "__main__":
    logging.basicConfig(level=settings.log_level.upper())
    uvicorn.run("app.main:app", host=settings.host, port=settings.port, reload=True)
