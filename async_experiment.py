import tkinter as tk
import asyncio
from tkinter import scrolledtext
import copy
#FIXME variable width input handling
#FIXME tooltip improvements


class StateList:
    """
    Master Class of program's state for Undo/Redo functionality
    """
    def __init__(self, initial_state: 'Transaction'):
        self.lTransactionS:list = [initial_state]
        self.iTransaction = 0
        self.currentState = initial_state

    def append(self, transaction: 'Transaction'):
        if self.iTransaction < len(self.lTransactionS) - 1:
            self.lTransactionS = self.lTransactionS[:self.iTransaction]

        transaction.refresh(self.currentState)
        self.lTransactionS.append(transaction)
        self.currentState = transaction
        self.iTransaction = len(self.lTransactionS) - 1

    def undo(self)-> 'Transaction':
        if self.iTransaction > 0:
            self.iTransaction -= 1
            self.currentState = self.lTransactionS[self.iTransaction]
        return self.currentState

    def redo(self)-> 'Transaction':
        if self.iTransaction < len(self.lTransactionS) - 1:
            self.iTransaction += 1
            self.currentState = self.lTransactionS[self.iTransaction]
        return self.currentState


class Transaction:
    def __init__(self, *args):
        self.dict = {VarState(arg).name if VarState(arg).name else VarState(arg).id: VarState(arg) for arg in args}

    def __getitem__(self, item):
        return self.dict[item]

    def __setitem__(self, key, value):
        self.dict[key] = value

    def __delitem__(self, key):
        del self.dict[key]

    def __contains__(self, item):
        return item in self.dict

    def set(self):
        for vs in self.dict.values():
            vs.set()

    def refresh(self, other:'Transaction'):
        for k in self.dict:
            if k in other and self.dict[k] == other[k]:
                self.dict[k] = other[k]


class VarState:
    def __init__(self, var):
        self.var = var
        self.id = id(var)

        if isinstance(var, tk.StringVar):
            self.name = var._name
            self.value = var.get()
        elif isinstance(var, scrolledtext.ScrolledText):
            self.name = var._name
            self.value = var.get("1.0", "end")
        elif isinstance(var, list):
            self.name = None
            self.value = copy.deepcopy(var)

    def set(self):
        if isinstance(self.var, tk.StringVar):
            self.var.set(self.value)
        elif isinstance(self.var, scrolledtext.ScrolledText):
            self.var.replace("1.0", "end", self.value, )
        elif isinstance(self.var, list):
            self.var.clear()
            self.var.extend(self.value)

    def __str__(self):
        #FIXME
        pass

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
        # FIXME multiple modifier handling:
        # self.top.bind("<Shift-Control-z>", self._redo)

        self.top.protocol("WM_DELETE_WINDOW", self._close)
        self.testResultList = []

        self.trackedFields = self.sText, self.sInt, self.testResultList
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

    def _refresh_scrolledText(self):
        self.scrolledText.replace("1.0", "end", "\n".join(self.testResultList))

    async def _process(self):
        for i in range(int(self.sInt.get())):
            await asyncio.sleep(.1)  # Simulate a long-running task
            self.testResultList.append(f"{self.sText.get()} {i}")
            self._refresh_scrolledText()
        self._end_of_processing()

    def _start_processing(self):
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
        self._refresh_scrolledText()
        # self.sText.trace_vdelete("w", self.observer)
        # s.set()
        # self.observer = self.sText.trace_variable("w", self._sEntryModified)

    def _close(self):
        self.loop.stop()
        self.top.destroy()


app = TestFrame()

