import tkinter as tk
from tkinter.font import Font

def get_text_width(text, font):
    # Create a temporary Tkinter window to measure the text width
    root = tk.Tk()
    entry = tk.Entry(root, font=font)
    entry.insert(0, text)
    entry.pack()
    # Update the window to calculate the size of the entry
    root.update()
    # Get the width of the entry in pixels
    width = entry.winfo_width()
    # Destroy the temporary window
    root.destroy()
    return width

# Example usage
root = tk.Tk()

# Define the font
font = Font(family="Arial", size=12)
text = "Hello, wo                                      rld!"
width = font.measure(text)

# Define the text

# Get the width of the text using the font

# Reset the width of an Entry field based on the text width
entry = tk.Entry(root, font=font)
entry.insert(0, text)
# entry.config(width=width)
# entry.pack()
entry.place(width=width)

root.mainloop()
