import tkinter as tk

class UndoRedo:
    def __init__(self, root, update_label, *text_variables):
        self.history = []
        self.history_index = -1
        self.root = root
        self.text_variables = text_variables
        self.update_label = update_label

        # Bind keyboard shortcuts
        self.root.bind("<Control-z>", self.undo_redo_event)
        self.root.bind("<Control-y>", self.undo_redo_event)
        # self.root.bind("<Control-Shift-Z>", self.undo_redo_event)

    def undo_redo_event(self, event):
        if event.keysym == "z" and event.state == 4:  # Control key + "z" key (Undo)
            value = self.undo()
        elif event.keysym == "Z" and event.state == 12:  # Control key + Shift key + "z" key (Redo)
            value = self.redo()
        else:
            return

        if value is not None:
            for text_variable in self.text_variables:
                text_variable.set(value)
            self.update_label()

    def undo(self):
        if self.history_index > 0:
            self.history_index -= 1
            return self.history[self.history_index]
        return None

    def redo(self):
        if self.history_index < len(self.history) - 1:
            self.history_index += 1
            return self.history[self.history_index]
        return None

    def update_history(self, value):
        self.history = self.history[:self.history_index + 1]
        self.history.append(value)
        self.history_index += 1


class GUI:
    def __init__(self, root):
        self.root = root
        self.text1 = tk.StringVar()
        self.text2 = tk.IntVar()

        self.root.title("Undo/Redo Example")

        # Create GUI elements
        self.input_field1 = tk.Entry(root, textvariable=self.text1)
        self.input_field1.pack()

        self.input_field2 = tk.Entry(root, textvariable=self.text2)
        self.input_field2.pack()

        self.output_label = tk.Label(root, text="")
        self.output_label.pack()

        # Create an instance of UndoRedo class
        self.undo_redo = UndoRedo(root, self.update_label, self.text1, self.text2)

        # Start the main loop
        self.root.mainloop()

    def update_label(self):
        self.output_label.config(text="Text1: {}, Text2: {}".format(self.text1.get(), self.text2.get()))

    def on_text_change(self, event):
        value1 = self.text1.get()
        value2 = self.text2.get()
        self.undo_redo.update_history((value1, value2))
        self.update_label()

# Create the root window
root = tk.Tk()

# Create an instance of the GUI
app = GUI(root)
