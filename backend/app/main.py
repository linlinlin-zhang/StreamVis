from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import json
import asyncio
from app.core.context_manager import ContextManager
from app.core.intent_decoder import IntentDecoder
from app.core.renderer import IncrementalRenderer

app = FastAPI(title="StreamVis API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

context_manager = ContextManager()
intent_decoder = IntentDecoder()
renderer = IncrementalRenderer()

@app.get("/")
async def root():
    return {"message": "StreamVis API is running"}

@app.websocket("/ws/chat")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            data = await websocket.receive_text()
            message = json.loads(data)
            user_input = message.get("content")
            
            # 1. Update Context
            context_manager.add_user_input(user_input)
            
            # 2. Detect Intent
            intent = intent_decoder.detect(user_input, context_manager.get_recent_context())
            
            # 3. Stream Response (Text + Visualization)
            # Simulate streaming response
            response_text = f"Processed: {user_input}"
            await websocket.send_text(json.dumps({
                "type": "text_delta",
                "content": response_text,
                "intent": intent
            }))

            if intent['visual_necessity_score'] > 0.5:
                # 4. Generate Graph Delta
                graph_delta = renderer.generate_delta(intent, context_manager.get_context_vector())
                await websocket.send_text(json.dumps({
                    "type": "graph_delta",
                    "content": graph_delta
                }))
            
    except WebSocketDisconnect:
        print("Client disconnected")

if __name__ == "__main__":
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
