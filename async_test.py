import tkinter as tk
import asyncio

def absorbTclError(func):
    def resultFunc(*args, **kwargs):
        try:
            return  func(*args, **kwargs)
        except tk.TclError:
            print("TclError absorbed")
    return resultFunc


class AsyncFrame(tk.Frame):
    def __init__(self):
        super().__init__()

        self.top = self.winfo_toplevel()

        self.label = tk.Label(self.top, text="Initial Text")
        self.label.pack()
        self.button = tk.Button(self.top, text="Modify", command=self.update_label_text)
        self.button.pack()

        self.top.protocol("WM_DELETE_WINDOW", self._close)

        self.loop = asyncio.get_event_loop()
        self.loop.create_task(self.asyncio_event_loop())
        self.loop.run_forever()

    @absorbTclError
    async def modify_label_text(self):
        for i in range(10):
            await asyncio.sleep(.5)  # Simulate a long-running task
            self.label.config(text=f"New Text {i}")
        self.button.config(state=tk.NORMAL, text="Modify")

    # Run the asyncio event loop
    @absorbTclError
    async def asyncio_event_loop(self, interval=0):
        while True:
            self.winfo_toplevel().update()
            await asyncio.sleep(interval)

    def update_label_text(self):
        self.button.config(state=tk.DISABLED, text="Processing...")
        self.loop.create_task(self.modify_label_text())

    def _close(self):
        self.loop.stop()
        self.top.destroy()

app = AsyncFrame()

