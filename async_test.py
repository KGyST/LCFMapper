import tkinter as tk
import asyncio
from tkinter import scrolledtext
from functools import reduce
#FIXME transaction recprds
#FIXME variable width input handling
#FIXME tooltip improvements


class TransactionRecord:
    def __init__(self):
        self.transactions = []

    def add_transaction(self, transaction):
        self.transactions.append(transaction)

    def undo_last_transaction(self):
        if self.transactions:
            transaction = self.transactions.pop()
            transaction.undo()


class UndoableEntry(tk.Entry):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.transaction_record = TransactionRecord()
        self.bind("<Key>", self.on_key_press)

    def on_key_press(self, event):
        # Skip modifier keys
        STATE_CTRL = 4
        # STATE_LEFT_ALT = 8
        STATE_RIGHT_ALT = 64

        if  event.keysym in ["Shift_L", "Shift_R", "Control_L", "Control_R", "Alt_L", "Alt_R"] \
        or  event.state & STATE_CTRL\
        or  event.state & STATE_RIGHT_ALT:
            # or  event.state & STATE_LEFT_ALT\
            return

        current_text = self.get()
        new_text = current_text + event.char
        transaction = Transaction(self, current_text, new_text)
        self.transaction_record.add_transaction(transaction)

    def undo_last_transaction(self):
        self.transaction_record.undo_last_transaction()


# class ProgramState:
#     def __init__(self, widget_stsates:dict):
#         self.dState = widget_stsates


class Transaction:
    def __init__(self, entry_widget, old_text, new_text, *args):
        # self.target = target
        # self.action = action
        # self.args = args
        self.entry_widget = entry_widget
        self.old_text = old_text
        self.new_text = new_text

    def execute(self):
        # if self.action == 'set':
        #     self.target = self.args
        self.entry_widget.delete(0, tk.END)
        self.entry_widget.insert(0, self.new_text)

    def undo(self):
        # if self.action == 'set':
        #     self.target = self.args
        self.entry_widget.delete(0, tk.END)
        self.entry_widget.insert(0, self.old_text)



class TestFrame(tk.Frame):
    def __init__(self):
        super().__init__()
        self.top = self.winfo_toplevel()

        self.transactionS = []
        self.sEntry           = tk.StringVar()
        # self.observer = self.sEntry.trace_variable("w", self._sEntryModified)
        self.transaction_record = TransactionRecord()

        self.scrolledText = scrolledtext.ScrolledText()
        self.scrolledText.grid(row=0, column=0, columnspan=4)
        self.entry = UndoableEntry(self.top, {"textvariable": self.sEntry})
        self.entry.grid(row=1, column=0)
        self.label = tk.Label(self.top, text="Initial Text")
        self.label.grid(row=1, column=1)
        self.buttonStart = tk.Button(self.top, text="Start", command=self._update_label_text)
        self.buttonStart.grid(row=1, column=2)
        self.buttonCancel = tk.Button(self.top, text="Cancel", command=self._cancel, state=tk.DISABLED)
        self.buttonCancel.grid(row=1, column=3)
        self.top.bind("<Key>", self._handle_key)
        self.top.bind("<Control-z>", self._undo)

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
        # hotkey_string = event.keysym
        if event.widget.widgetName == 'entry':
            pass
        # if event.state:
        #     print("Hotkey pressed:", hotkey_string)
        #     self.scrolledText.insert("end", hotkey_string)
        #     self.scrolledText.see("end")

    def _sEntryModified(self, *_):
        # self._do(Transaction(self.sEntry, 'set'))
        pass

    def _do(self, transaction):
        self.transactionS.append(transaction)

    def _undo(self, *_):
        # _transaction = self.transactionS.pop()
        # if _transaction.action == 'set':
        #     _transaction.target.set(*_transaction.args)
        self.entry.undo_last_transaction()

    def _redo(self):
        pass

    def _states_to_string(self):
        return " ".join(self.transactionS)

    def getState(self):
        return {self.sEntry: self.sEntry.get()}


app = TestFrame()

