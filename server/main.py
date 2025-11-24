# main.py
import asyncio
import json
import logging
import queue as pyqueue
from contextlib import asynccontextmanager
from multiprocessing import Process, Queue

from fastapi import FastAPI

from api import router
from api.audio.worker import audio_handler

log = logging.getLogger("uvicorn.error")


def get_output_safe(q: "Queue", timeout: float = 0.2):
    try:
        return q.get(timeout=timeout)
    except pyqueue.Empty:
        raise TimeoutError


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.input_q = Queue()
    app.state.output_q = Queue()
    app.state.clients = {}  # client_id -> WebSocket
    app.state.shutdown = False

    app.state.proc = Process(target=audio_handler, args=(app.state.input_q, app.state.output_q))
    app.state.proc.start()
    log.info("Worker process started: pid=%s", app.state.proc.pid)

    async def sender():
        loop = asyncio.get_running_loop()
        while not app.state.shutdown:
            try:
                client_id, result = await loop.run_in_executor(None, get_output_safe, app.state.output_q, 0.2)
            except TimeoutError:
                continue
            except Exception as e:
                # Если что-то пошло не так при чтении — выходим, чтобы не зависать
                log.warning("Sender read error: %s", e)
                break

            ws = app.state.clients.get(client_id)
            if ws:
                try:
                    await ws.send_text(json.dumps(result))
                except Exception as e:
                    log.warning("Send failed to client %s: %s", client_id, e)

    sender_task = asyncio.create_task(sender())
    try:
        yield
    finally:
        # 1) Сигнализируем sender-у остановку и ждём его завершения
        log.info("Stopping sender task...")
        app.state.shutdown = True
        try:
            await asyncio.wait_for(sender_task, timeout=1.0)
        except asyncio.TimeoutError:
            sender_task.cancel()
            try:
                await sender_task
            except asyncio.CancelledError:
                pass

        # 2) Сигнал завершения воркеру
        log.info("Signalling worker to stop...")
        try:
            app.state.input_q.put((None, None, None))
        except TypeError:
            app.state.input_q.put((None, None))

        # 3) Дождаться завершения процесса
        log.info("Joining worker process...")
        app.state.proc.join(timeout=5)
        if app.state.proc.is_alive():
            log.warning("Worker still alive, terminating...")
            app.state.proc.terminate()
            app.state.proc.join(timeout=2)

        # 4) Закрыть очереди, чтобы не оставались семафоры
        for qname in ("input_q", "output_q"):
            q = getattr(app.state, qname)
            try:
                q.close()
            except Exception:
                pass
            try:
                q.join_thread()
            except Exception:
                pass
        log.info("Queues closed.")

        # 5) Закрыть активные WebSocket-соединения
        for ws in list(app.state.clients.values()):
            try:
                await ws.close(code=1001)
            except Exception:
                pass
        app.state.clients.clear()
        log.info("Clients closed.")


app = FastAPI(lifespan=lifespan)
app.include_router(router)
