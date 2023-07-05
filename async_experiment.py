import dataclasses
import tkinter as tk
import asyncio
from tkinter import scrolledtext
#FIXME variable width input handling
#FIXME tooltip improvements
from typing import Callable

from GSMXMLLib import *
from lxml import etree
from SamUITools import InputDirPlusText


class StateList:
    """
    Master Class of program's state/transaction for Undo/Redo functionality
    """
    def __init__(self, initial_state: 'ProgramState'):
        self.transactionS:list = [initial_state]
        self.iTransaction = 0
        self.currentState = initial_state

    def append(self, transaction: 'ProgramState'):
        if self.iTransaction < len(self.transactionS) - 1:
            self.transactionS = self.transactionS[:self.iTransaction+1]

        transaction.refresh(self.currentState)
        self.transactionS.append(transaction)
        self.currentState = transaction
        self.iTransaction = len(self.transactionS) - 1

    def undo(self)-> 'ProgramState':
        if self.iTransaction > 0:
            self.iTransaction -= 1
            self.currentState = self.transactionS[self.iTransaction]
            return self.currentState

    def redo(self)-> 'ProgramState':
        if self.iTransaction < len(self.transactionS) - 1:
            self.iTransaction += 1
            self.currentState = self.transactionS[self.iTransaction]
            return self.currentState


class ProgramState:
    """
    Describes a new program state
    """
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

    def refresh(self, other: 'ProgramState'):
        for k in self.dict:
            if k in other and self.dict[k] == other[k]:
                self.dict[k] = other[k]


class VarState:
    """
    Describes a variable that is saved between transactions
    """
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

    def __eq__(self, other:'VarState')->bool:
        return self.value == other.value

    def __repr__(self):
        return ": ".join((self.name if self.name else str(self.id), self.value.__repr__(),))


class Loop:
    """

    """
    def __init__(self, top):
        self.top = top
        self._loop = asyncio.get_event_loop()
        self._loop.create_task(self.asyncio_event_loop())

    async def asyncio_event_loop(self, interval=0):
        while True:
            self.top.update()
            await asyncio.sleep(interval)
            _task = asyncio.current_task()
            if _task:
                if _task.cancelled():
                    raise asyncio.CancelledError()

    def __getattr__(self, item):
        return getattr(self._loop, item)


class Observer:
    observerS = []

    def __init__(self, variable, callback: Callable, mode:str= "w"):
        self.callback = callback
        self.variable = variable
        self.mode = mode
        self.observerS.append(self)
        self.register()

    def register(self):
        self.observer = self.variable.trace(self.mode, self.callback)

    def unregister(self):
        self.variable.trace_vdelete(self.mode, self.observer)


class TestFrame(tk.Frame):
    """
    Program GUI window class with async working and undo/redo functionality
    """
    def __init__(self):
        super().__init__()
        self.top = self.winfo_toplevel()

        self.sText    = tk.StringVar()
        self.iInt     = 0

        _col = 0
        self.textEntry = InputDirPlusText(self.top, "XML Source folder", self.sText, row=1, column=_col)
        _col += 1
        self.label = tk.Label(self.top, text=f"{self.iInt}")
        self.label.grid(row=1, column=_col)
        _col += 1
        self.buttonStart = tk.Button(self.top, text="Start", command=self._start_processing)
        self.buttonStart.grid(row=1, column=_col)
        _col += 1
        self.buttonCancel = tk.Button(self.top, text="Cancel", command=self._cancel_processing, state=tk.DISABLED)
        self.buttonCancel.grid(row=1, column=_col)

        self.scrolledText = scrolledtext.ScrolledText()
        self.scrolledText.grid(row=0, column=0, columnspan=_col, sticky=tk.SE + tk.NW)
        # FIXME self.scrolledText.grid({"row":0, "column":0, "columnspan":_col, "sticky":tk.SE + tk.NW} )

        self.top.bind("<Control-z>", self._undo)
        self.top.bind("<Control-y>", self._redo)
        # FIXME multiple modifier handling:
        # self.top.bind("<Shift-Control-z>", self._redo)

        self.top.protocol("WM_DELETE_WINDOW", self._close)
        self.testResultList = []

        self.trackedFieldS = self.sText, self.testResultList
        Observer(self.sText, self._textEntryModified)
        self.stateList = StateList(self.getState())
        self.task = None

        # ------

        self.loop = Loop(self.top)
        self.loop.run_forever()

    def _refresh_outputs(self):
        self.scrolledText.replace("1.0", "end", "\n".join(self.testResultList))
        self.scrolledText.see(tk.END)
        self.label.config(text=f"{self.iInt}, {len(self.stateList.transactionS)}, {self.stateList.iTransaction+1}")

    async def _process(self):
        await self.scanDirFactory(self.sText.get(), p_sCurrentFolder='')

    def _start_processing(self):
        self._cancel_processing()
        self.buttonStart.config(state=tk.DISABLED, text="Processing...")
        self.buttonCancel.config(state=tk.ACTIVE)
        self.textEntry.config(state=tk.DISABLED)
        self.task = self.loop.create_task(self._process())
        self.task.add_done_callback(self._end_of_processing)

    def _cancel_processing(self):
        if self.task:
            self.task.cancel()
        self.task=None
        self.testResultList.clear()
        self.iInt = 0

    # ------

    def _end_of_processing(self, task):
        self.buttonStart.config(state=tk.NORMAL, text="Modify")
        self.buttonCancel.config(state=tk.DISABLED)
        self.textEntry.config(state=tk.NORMAL)
        if task._state != 'CANCELLED':
            self.stateList.append(self.getState())
        else:
            self.setState(self.stateList.currentState)
        self._refresh_outputs()

    def _undo(self, *_):
        self._cancel_processing()
        _state = self.stateList.undo()
        if _state:
            self.setState(_state)

    def _redo(self, *_):
        self._cancel_processing()
        _state = self.stateList.redo()
        if _state:
            self.setState(_state)

    def getState(self)->ProgramState:
        return ProgramState(*self.trackedFieldS)

    def setState(self, state:ProgramState):
        for o in Observer.observerS:
            o.unregister()
        state.set()

        for o in Observer.observerS:
            o.register()
        self._refresh_outputs()

    def _close(self):
        self.loop.stop()
        self.top.destroy()

    # ------

    def _textEntryModified(self, *_):
        if self.sText.get():
            self.textEntry.config(width=len(self.sText.get()))
            self.update()
            self._start_processing()

    # ------

    async def scanDirFactory(self, p_sRootFolder, p_sCurrentFolder='', p_acceptedFormatS=(".XML",)):
        """
        only scanning input dir recursively to set up xml and image files' list
        :param p_sRootFolder:
        :param p_sCurrentFolder:
        :param p_acceptedFormatS:
        :return:
        """
        try:
            path_join = os.path.join(p_sRootFolder, p_sCurrentFolder)
            for f in os.listdir(path_join):
                try:
                    src = os.path.join(p_sRootFolder, p_sCurrentFolder, f)
                    if not os.path.isdir(src):
                    # if it IS NOT a folder
                        self.iInt += 1
                        if os.path.splitext(os.path.basename(f))[1].upper() in p_acceptedFormatS:
                            self.testResultList.append(f"{self.sText.get()} {f}")
                            self._refresh_outputs()
                            await asyncio.sleep(0)
                            # SourceXML(os.path.join(p_sCurrentFolder, f))
                        else:
                            self.testResultList.append(f"{self.sText.get()} {f}")
                            self._refresh_outputs()
                            await asyncio.sleep(0)
                    else:
                    # if it IS a folder
                        await self.scanDirFactory(p_sRootFolder, os.path.join(p_sCurrentFolder, f))
                except KeyError:
                    print("KeyError %s" % f)
                    continue
                except etree.XMLSyntaxError:
                    print("XMLSyntaxError %s" % f)
                    continue
        except WindowsError:
            pass

app = TestFrame()

