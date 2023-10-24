import asyncio
import threading

def start_loop(loop: asyncio.AbstractEventLoop):
    asyncio.set_event_loop(loop)
    loop.run_forever()

EVENT_LOOP: asyncio.AbstractEventLoop = asyncio.new_event_loop()
EVENT_LOOP_THREAD = threading.Thread(target=start_loop, args=(EVENT_LOOP,), name="EVENT LOOP")
EVENT_LOOP_THREAD.start()


from .cli import BusyBee