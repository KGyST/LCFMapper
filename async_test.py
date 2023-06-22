import tkinter as tk
import asyncio
from tkinter import scrolledtext
#FIXME variable width input handling
#FIXME tooltip improvements


class StateList:
    """
    Master Class of program's state for Undo/Redo functionality
    """
    def __init__(self, initial_state: 'Transaction'):
        self.lTransactions:list = [initial_state]
        self.iTransaction = 0
        self.currentState = initial_state

    def append(self, transaction: 'Transaction'):
        if self.iTransaction < len(self.lTransactions) - 1:
            self.lTransactions = self.lTransactions[:self.iTransaction]

        transaction.refresh(self.currentState)
        self.lTransactions.append(transaction)
        self.currentState = transaction
        self.iTransaction = len(self.lTransactions) - 1

    def undo(self)-> 'Transaction':
        if self.iTransaction > 0:
            self.iTransaction -= 1
            self.currentState = self.lTransactions[self.iTransaction]
        return self.currentState

    def redo(self)-> 'Transaction':
        if self.iTransaction < len(self.lTransactions) - 1:
            self.iTransaction += 1
            self.currentState = self.lTransactions[self.iTransaction]
        return self.currentState


class Transaction:
    def __init__(self, *args):
        if len(args) and isinstance( args[0], dict):
            self.dict = args[0]
        else:
            self.dict = {VarState(arg).name: VarState(arg) for arg in args}

    def __getitem__(self, item):
        return self.dict[item]

    def __setitem__(self, key, value):
        self.dict[key] = value

    def __delitem__(self, key):
        del self.dict[key]

    def __contains__(self, item):
        return item in self.dict

    def keys(self):
        return self.dict.keys()

    def set(self):
        for vs in self.dict.values():
            vs.set()

    def __sub__(self, other:'Transaction')->'Transaction':
        _result = Transaction()

        for k, v in self.dict.items():
            if k in other:
                if v != other[k]:
                    _result[k] = v
        return _result

    # def __add__(self, other:'Transaction'):
    #     return {**self.dict, **other}

    def refresh(self, other:'Transaction'):
        for k in self.dict:
            if k in other and self.dict[k] == other[k]:
                self.dict[k] = other[k]


# class Undoable:
#     def __init__(self, state_list):
#         self.stateList = state_list
#
#     def __call__(self, func):
#         self.stateList.append()
#         def wrapped_function(*args, **kwargs):
#             return func(*args, **kwargs)
#         return wrapped_function


class VarState:
    def __init__(self, var):
        if isinstance(var, tk.StringVar):
            self.var = var
            self.name = var._name
            self.value = var.get()
        else:
            self.var = var
            self.name = var._name
            self.value = var.get("1.0", "end")

    def set(self):
        if isinstance(self.var, tk.StringVar):
            self.var.set(self.value)
        else:
            self.var.replace("1.0", "end", self.value, )

    def __str__(self):
        pass
        #FIXME

    def __eq__(self, other:'VarState')->bool:
        return self.value == other.value


class TestFrame(tk.Frame):
    def __init__(self):
        super().__init__()
        self.top = self.winfo_toplevel()

        self.sText           = tk.StringVar()
        self.sInt           = tk.StringVar()
        # self.observer = self.sText.trace_variable("w", self._sEntryModified)

        _col = 0
        self.label = tk.Label(self.top, text="Initial Text: ")
        self.label.grid(row=1, column=_col)
        _col += 1
        self.textEntry = tk.Entry(self.top, {"textvariable": self.sText})
        self.textEntry.grid(row=1, column=_col)
        _col += 1
        self.label = tk.Label(self.top, text="Number: ")
        self.label.grid(row=1, column=_col)
        _col += 1
        self.intEntry = tk.Entry(self.top, {"textvariable": self.sInt})
        self.intEntry.grid(row=1, column=_col)
        _col += 1
        self.buttonStart = tk.Button(self.top, text="Start", command=self._start_processing)
        self.buttonStart.grid(row=1, column=_col)
        _col += 1
        self.buttonCancel = tk.Button(self.top, text="Cancel", command=self._cancel_processing, state=tk.DISABLED)
        self.buttonCancel.grid(row=1, column=_col)
        _col += 1

        self.scrolledText = scrolledtext.ScrolledText()
        self.scrolledText.grid(row=0, column=0, columnspan=_col)

        self.top.bind("<Control-z>", self._undo)
        self.top.bind("<Control-y>", self._redo)
        # self.top.bind("<Shift-Control-z>", self._redo)

        self.top.protocol("WM_DELETE_WINDOW", self._close)

        self.trackedFields = self.sText, self.sInt, self.scrolledText
        self.stateList = StateList(self.getState())

        # ------

        self.loop = asyncio.get_event_loop()
        self.loop.create_task(self.asyncio_event_loop())
        self.loop.run_forever()

    # Run the asyncio event loop
    async def asyncio_event_loop(self, interval=0):
        while True:
            self.top.update()
            await asyncio.sleep(interval)

    # ------

    async def _process(self):
        for i in range(int(self.sInt.get())):
            await asyncio.sleep(.1)  # Simulate a long-running task
            self.label.config(text=(text:=f"{self.sText.get()} {i}\n"))
            self.scrolledText.insert("end", text)
            self.scrolledText.see("end")
        self._end_of_processing()

    def _start_processing(self, event=None):
        self.buttonStart.config(state=tk.DISABLED, text="Processing...")
        self.buttonCancel.config(state=tk.ACTIVE)
        self.task = self.loop.create_task(self._process())

    def _cancel_processing(self):
        self.task.cancel()
        self._end_of_processing()

    # ------

    def _end_of_processing(self):
        self.buttonStart.config(state=tk.NORMAL, text="Modify")
        self.buttonCancel.config(state=tk.DISABLED)
        self.stateList.append(self.getState())

    def _undo(self, *_):
        _state = self.stateList.undo()
        self.setState(_state)

    def _redo(self, *_):
        _state = self.stateList.redo()
        self.setState(_state)

    def getState(self)->Transaction:
        return Transaction(*self.trackedFields)

    def setState(self, state:Transaction):
        state.set()
        # self.sText.trace_vdelete("w", self.observer)
        # s.set()
        # self.observer = self.sText.trace_variable("w", self._sEntryModified)

    def _close(self):
        self.loop.stop()
        self.top.destroy()

app = TestFrame()

