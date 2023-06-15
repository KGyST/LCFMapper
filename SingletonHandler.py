import tkinter as tk
import asyncio

async def modify_label_text():
    await asyncio.sleep(1)  # Simulate a long-running task
    label.config(text="New Text")
    button.config(state=tk.NORMAL, text="Modify")

# Run the asyncio event loop
async def asyncio_event_loop():
    while True:
        window.update()
        await asyncio.sleep(0)

def update_label_text():
    button.config(state=tk.DISABLED, text="Processing...")
    loop.create_task(modify_label_text())

window = tk.Tk()
label = tk.Label(window, text="Initial Text")
label.pack()
button = tk.Button(window, text="Modify", command=update_label_text)
button.pack()

loop = asyncio.get_event_loop()
loop.create_task(asyncio_event_loop())
loop.run_forever()

