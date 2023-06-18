import tkinter as tk


class UndoableEntry(tk.Entry):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.old_text = self.get()

    def insert(self, index, string):
        self.old_text = self.get()
        super().insert(index, string)

    def delete(self, start, end=None):
        self.old_text = self.get()
        super().delete(start, end)


class Transaction:
    def __init__(self, entry_widget, new_text):
        self.entry_widget = entry_widget
        self.old_text = entry_widget.get()
        self.new_text = new_text

    def execute(self):
        self.entry_widget.delete(0, tk.END)
        self.entry_widget.insert(0, self.new_text)

    def undo(self):
        self.entry_widget.delete(0, tk.END)
        self.entry_widget.insert(0, self.old_text)



# Example usage
def perform_transaction():
    transaction = Transaction(entry, "Modified Text")
    transaction.execute()

    print("Transaction executed")
    print("Old text:", transaction.old_text)
    print("New text:", transaction.new_text)
    print("Current text:", entry.get())

    # Undo the transaction
    transaction.undo()
    print("Transaction undone")
    print("Current text after undo:", entry.get())


root = tk.Tk()

entry = UndoableEntry(root)
entry.pack()

button = tk.Button(root, text="Perform Transaction", command=perform_transaction)
button.pack()

root.mainloop()
