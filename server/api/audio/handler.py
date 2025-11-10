# handler.py (упрощённый)
import json
from typing import NewType
from fastapi import APIRouter
from starlette.responses import JSONResponse
from starlette.websockets import WebSocket, WebSocketDisconnect

ClientId = NewType("ClientId", int)
router = APIRouter(prefix="/audio", tags=["Audio"])


@router.get("/health")
async def health():
    return JSONResponse({"status": "ok"})


@router.websocket("/ws")
async def ws_endpoint(websocket: WebSocket):
    await websocket.accept()
    app = websocket.app
    client_id: ClientId = ClientId(id(websocket))
    app.state.clients[client_id] = websocket

    if not hasattr(app.state, "msg_seq"):
        app.state.msg_seq = {}
    app.state.msg_seq.setdefault(client_id, 0)

    try:
        while True:
            msg = await websocket.receive()
            if msg.get("type") == "websocket.disconnect":
                break

            app.state.msg_seq[client_id] += 1
            seq = app.state.msg_seq[client_id]

            data_bytes = msg.get("bytes")
            text = msg.get("text")

            if data_bytes is not None:
                await websocket.send_text(json.dumps({
                    "client_id": int(client_id),
                    "seq": seq,
                    "chunk_size": len(data_bytes),
                }))
                app.state.input_q.put((client_id, seq, data_bytes))

            elif text is not None:
                await websocket.send_text(json.dumps({
                    "client_id": int(client_id),
                    "seq": seq,
                    "text_len": len(text),
                }))
                app.state.input_q.put((client_id, seq, text))
            else:
                await websocket.send_text(json.dumps({"error": "Expected binary audio chunk or text"}))

    except WebSocketDisconnect:
        pass
    finally:
        app.state.clients.pop(client_id, None)
        app.state.msg_seq.pop(client_id, None)
