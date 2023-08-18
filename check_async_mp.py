import multiprocessing
import os
import time
import asyncio
import random
from concurrent.futures import ProcessPoolExecutor
from queue import Empty as QueueEmpty

N_PROCESSES = 8
N_ITER = 20
N_SEC = 1

async_queue = asyncio.Queue()

def worker_main(p_item):
    print(f"{p_item[0]} - {os.getpid()}")
    time.sleep(p_item[1])
    mp_queue.put(f"{p_item[0]} - {os.getpid()}: {p_item[1]} sec")

def init_worker(queue):
    global mp_queue
    mp_queue = queue
    print(os.getpid(), "working")

async def run(mp_queue):
    asyncio.create_task(mp_queue_to_async_queue(mp_queue))  # Pass mp_queue as an argument
    await print_out_async()


async def mp_queue_to_async_queue(mp_queue):  # Receive mp_queue as an argument
    processes_finished = 0
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
        if message is None:
            processes_finished += 1
        if processes_finished == N_PROCESSES:
            break

async def print_out_async():
    processes_finished = 0
    while True:
        b = await async_queue.get()
        print(f"<- {b}")
        processes_finished += 1
        if processes_finished == N_ITER:
            break

def worker_pool(mp_queue):  # Pass mp_queue as an argument
    pool_map = [(i, N_SEC * random.random()) for i in range(N_ITER)]
    with ProcessPoolExecutor(max_workers=N_PROCESSES, initializer=init_worker, initargs=(mp_queue,)) as executor:
        executor.map(worker_main, pool_map)

async def main():
    loop = asyncio.get_event_loop()

    with multiprocessing.Manager() as manager:
        mp_queue = manager.Queue()
        _task = loop.create_task(run(mp_queue))
        loop.run_in_executor(None, worker_pool, mp_queue)  # Pass mp_queue as an argument

        await _task

if __name__ == '__main__':
    asyncio.run(main())