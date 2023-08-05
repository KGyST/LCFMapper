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
        self.top = self.winfo_toplevel()
        self.loop = Loop(self.top)

        self.text = tk.Text()
        self.text.pack()

        self.server_queue = server_queue  # Change the type of the server_queue attribute

    def mainloop(self):
        # server.start()  # Start the server process before starting the client process
        self.loop.create_task(self._get_message())   # Get the message from the queue
        self.loop.run_forever()

    async def _get_message(self):
        while True:
            message = await self.server_queue.get()  # Get the message from the server_queue
            self.text.insert("end", f"{message}\n")  # Display the message in the client's text widget


class Server(multiprocessing.Process):
    def __init__(self):
        super().__init__()
        self._server_queue = asyncio.Queue()
        self.messages = ["Hello, world!", "This is a message from the server.", "Have a nice day!"]

    def run(self):
        loop = asyncio.get_event_loop()
        loop.create_task(self._run())

    async def _run(self):
        while True:
            for message in self.messages:
                await self._server_queue.put(message)  # Put the message in the server_queue
                await asyncio.sleep(1)  # Wait 1 second before sending the next message

    @property
    def server_queue(self):
        return self._server_queue


if __name__ == "__main__":
    server = Server()
    client = Client(server.server_queue)
    server.run()
    client.mainloop()
