import tkinter as tk


def handle_key(event):
    modifiers = event.state
    keysym = event.keysym

    # Check if only one non-modifier key was pressed
    if not modifiers and len(keysym) == 1 or (modifiers == 8 and len(keysym) == 1):
        hotkey_string = keysym
        print("Hotkey pressed:", hotkey_string)


root = tk.Tk()

# Create a label widget
label = tk.Label(root, text="Press any key combination")

# Place the label widget on the window
label.pack()

# Bind the key event to the label widget
label.bind("<Key>", handle_key)

# Set the focus to the label widget so that it receives the key events
label.focus_set()

# Start the Tkinter event loop
root.mainloop()
