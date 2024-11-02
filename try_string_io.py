import multiprocessing
import os
import time
import asyncio
import random
from concurrent.futures import ProcessPoolExecutor
from queue import Empty as QueueEmpty
from io import StringIO
from multiprocessing import Lock

N_PROCESSES = 1
N_ITER = 20
N_SEC = 1

class NonBlockingLockableStringIO(StringIO):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._lock = Lock()

    def write(self, s):
        with self._lock:
            super().write(s)

def worker_main(p_item, string_io):
    print(f"{p_item[0]} - {os.getpid()}")
    time.sleep(p_item[1])
    with string_io._lock:
        string_io.write(f"{p_item[0]} - {os.getpid()}: {p_item[1]} sec\n")

async_queue = asyncio.Queue()

async def run(mp_queue):
    asyncio.create_task(mp_queue_to_async_queue(mp_queue))
    await print_out_async()

async def mp_queue_to_async_queue(mp_queue):
    while True:
        try:
            message = mp_queue.get_nowait()
        except QueueEmpty:
            await asyncio.sleep(0)
            continue
        except BrokenPipeError:
            break
        print(f"-> {message}")
        await async_queue.put(message)

async def print_out_async():
    processes_finished = 0
    while True:
        b = await async_queue.get()
        print(f"<- {b}")
        processes_finished += 1
        if b is None:
            break

def worker_pool(mp_queue):
    pool_map = [(i, N_SEC * random.random()) for i in range(N_ITER)]
    with ProcessPoolExecutor(max_workers=N_PROCESSES) as executor:
        string_io = NonBlockingLockableStringIO()
        for p_item in pool_map:
            executor.submit(worker_main, p_item, string_io)

        executor.shutdown(wait=True)
        mp_queue.put(None)

async def main():
    try:
        with multiprocessing.Manager() as manager:
            mp_queue = manager.Queue()
            loop = asyncio.get_event_loop()
            _task = loop.create_task(run(mp_queue))
            loop.run_in_executor(None, worker_pool, mp_queue)
            await _task
    except Exception:
        print(1)
if __name__ == '__main__':
    asyncio.run(main())
