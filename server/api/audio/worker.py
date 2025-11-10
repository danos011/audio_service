from multiprocessing import Queue


def audio_handler(input_q: Queue, output_q: Queue):
    while True:
        item = input_q.get()
        if not item:
            continue
        client_id, seq, payload = item
        if client_id is None:
            break

        if isinstance(payload, bytes):
            size = len(payload)
            transcription = f"mock transcription for client {int(client_id)} msg#{seq} (binary {size} bytes)"
        else:

            text = str(payload)
            transcription = f"mock transcription for client {int(client_id)} msg#{seq} (text '{text[:20]}')"

        output_q.put((client_id, {"seq": seq, "transcription": transcription}))
