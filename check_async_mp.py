import asyncio
import multiprocessing
import tkinter as tk

class Loop:
    """
    A simple event loop class for tkinter applications.
    """

    def __init__(self, top):
        self.top = top
        self._loop = asyncio.get_event_loop()
        self._loop.create_task(self.asyncio_event_loop())

    async def asyncio_event_loop(self, interval=0):
        while True:
            self.top.update()
            await asyncio.sleep(interval)
            _task = asyncio.current_task()
            if _task:
                if _task.cancelled():
                    raise asyncio.CancelledError()

    def __getattr__(self, item):
        return getattr(self._loop, item)


class Client(tk.Frame):
    def __init__(self, server_queue):
        super().__init__()
        self.loop = Loop(self)

        self.text = tk.Text()
        self.button = tk.Button(text="Send", command=self.on_send)
        self.text.pack()
        self.button.pack()

        self.server_queue = server_queue

    def on_send(self):
        message = self.text.get("1.0", "end-1c")
        print("Sending message:", message)
        self.server_queue.put(message)  # Put the message in the server_queue

    def mainloop(self) -> None:
        self.loop.run_forever()


class Server(multiprocessing.Process):
    def __init__(self):
        super().__init__()
        self._server_queue = multiprocessing.Queue()

    def run(self):
        loop = asyncio.get_event_loop()
        loop.run_until_complete(self._run())

    async def _run(self):
        while True:
            message = self.server_queue.get()  # Get the message from the server_queue
            print("Received message:", message)

    @property
    def server_queue(self):
        return self._server_queue


if __name__ == "__main__":
    server = Server()
    client = Client(server.server_queue)
    server.start()
    client.mainloop()
