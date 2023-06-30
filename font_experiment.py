import tkinter as tk
from tkinter.font import Font

def get_text_width(*_):
    entry.config(width=len(sText.get()))

# Example usage
root = tk.Tk()
font = Font(family="Arial", size=12)
text = "Hello, world!"

sText = tk.StringVar()

entry = tk.Entry(root, font=font, textvariable=sText)
entry.grid(row=0, column=0)

observer = sText.trace_variable("w", get_text_width)

root.mainloop()
