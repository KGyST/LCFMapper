import multiprocessing
import os
import time
import asyncio
import random

N_PROCESSES = 2
N_ITER = 10
N_SEC = 1

async_queue = asyncio.Queue()

def worker_main(p_queue):
    print (_pid:=os.getpid(),"working")
    for i in range(N_ITER):
        some_random_time = N_SEC * random.random()
        p_queue.put(f"{i} - {_pid}: {some_random_time} sec")
        time.sleep(some_random_time)
    p_queue.put(None)

async def run():
    await mp_queue_to_async_queue()
    await print_out_async()

async def mp_queue_to_async_queue():
    processes_finished = 0
    while True:
        message = mp_queue.get()
        print(f"-> {message}")
        await async_queue.put(message)
        if message == None:
            processes_finished += 1
        if processes_finished == N_PROCESSES:
            break

async def print_out_async():
    processes_finished = 0
    while True:
        b = await async_queue.get()
        print(f"<- {b}")
        if b == None:
            processes_finished += 1
        if processes_finished == N_PROCESSES:
            break

if __name__ == '__main__':
    mp_queue = multiprocessing.Queue()
    pool = multiprocessing.Pool(processes=N_PROCESSES, initializer=worker_main, initargs=(mp_queue,))

    loop = asyncio.get_event_loop()
    loop.run_until_complete(run())

    pool.terminate()

