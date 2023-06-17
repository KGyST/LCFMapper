import tkinter as tk
import asyncio
from tkinter import scrolledtext
#FIXME transaction recprds
#FIXME variable width input handling


class TestFrame(tk.Frame):
    def __init__(self):
        super().__init__()
        self.top = self.winfo_toplevel()

        self.scrolledText = scrolledtext.ScrolledText()
        self.scrolledText.grid(row=0, column=0, columnspan=3)
        self.label = tk.Label(self.top, text="Initial Text")
        self.label.grid(row=1, column=0)
        self.buttonStart = tk.Button(self.top, text="Start", command=self._update_label_text)
        self.buttonStart.grid(row=1, column=1)
        self.buttonCancel = tk.Button(self.top, text="Cancel", command=self._cancel, state=tk.DISABLED)
        self.buttonCancel.grid(row=1, column=2)
        self.top.bind("<Key>", self._handle_key)

        self.top.protocol("WM_DELETE_WINDOW", self._close)

        self.loop = asyncio.get_event_loop()
        self.loop.create_task(self.asyncio_event_loop())
        self.loop.run_forever()

    # Run the asyncio event loop
    async def asyncio_event_loop(self, interval=0):
        while True:
            self.top.update()
            await asyncio.sleep(interval)

    async def _modify_label_text(self):
        for i in range(100):
            await asyncio.sleep(.1)  # Simulate a long-running task
            self.label.config(text=(text:=f"New Text {i}\n"))
            self.scrolledText.insert("end", text)
            self.scrolledText.see("end")
        self.buttonStart.config(state=tk.NORMAL, text="Modify")
        self.buttonCancel.config(state=tk.DISABLED)

    def _update_label_text(self, event=None):
        self.buttonStart.config(state=tk.DISABLED, text="Processing...")
        self.buttonCancel.config(state=tk.ACTIVE)
        self.scrolledText.delete("1.0", "end")
        self.task = self.loop.create_task(self._modify_label_text())

    def _close(self):
        self.loop.stop()
        self.top.destroy()

    def _cancel(self):
        self.task.cancel()
        self.buttonStart.config(state=tk.NORMAL, text="Modify")
        self.buttonCancel.config(state=tk.DISABLED)

    def _handle_key(self, event):
        hotkey_string = event.keysym
        if event.state:
            print("Hotkey pressed:", hotkey_string)
            self.scrolledText.insert("end", hotkey_string)
            self.scrolledText.see("end")


app = TestFrame()

