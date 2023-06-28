import asyncio
import tkinter as tk

class Loop(asyncio.ProactorEventLoop):
    def __init__(self, top):
        super().__init__()
        self.top = top
        self._task = None

    async def asyncio_event_loop(self, interval=0):
        try:
            while True:
                self.top.update()
                await asyncio.sleep(interval)
        except asyncio.CancelledError:
            pass

    def start(self, interval=0):
        self._task = self.create_task(self.asyncio_event_loop(interval))

    def stop(self):
        if self._task:
            self._task.cancel()
        super().stop()

class TestFrame(tk.Frame):
    def __init__(self):
        super().__init__()
        self.top = self.winfo_toplevel()
        self.top.protocol("WM_DELETE_WINDOW", self._close)

        self.loop = Loop(self.top)
        self.loop.start()
        self.loop.run_forever()

    def _close(self):
        self.loop.stop()
        self.top.destroy()

app = TestFrame()
