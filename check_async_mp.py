import multiprocessing
import asyncio

def process_function(x):
    return x * 2

def server_function(queue, num_tasks):
    pool = multiprocessing.Pool(processes=3)
    results = pool.map(process_function, range(num_tasks))
    pool.close()
    pool.join()

    for result in results:
        print(f"Sent message: {result}")
        queue.put(result)

async def client_function(queue):
    while True:
        message = queue.get()
        if message is None:
            break
        print(f"Received message: {message}")
        await asyncio.sleep(0.1)

if __name__ == "__main__":
    queue = multiprocessing.Queue()
    num_tasks = 10

    # Start the server function in a separate process
    server_process = multiprocessing.Process(target=server_function, args=(queue, num_tasks))
    server_process.start()

    # Start the client function in an asyncio event loop
    loop = asyncio.get_event_loop()
    try:
        client_task = loop.create_task(client_function(queue))
        loop.run_until_complete(client_task)
    except KeyboardInterrupt:
        pass
    finally:
        # Put None in the queue to signal the client to stop
        queue.put(None)
        loop.close()

    # Wait for the server process to finish
    server_process.join()
