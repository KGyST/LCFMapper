import tkinter as tk
import asyncio
import typing
from tkinter import scrolledtext
#FIXME variable width input handling
#FIXME tooltip improvements


from GSMXMLLib import *
from lxml import etree
from SamUITools import InputDirPlusText


class StateList:
    """
    Master Class of program's state/transaction for Undo/Redo functionality
    """
    def __init__(self, initial_state: 'ProgramState'):
        self.lTransactionS:list = [initial_state]
        self.iTransaction = 0
        self.currentState = initial_state

    def append(self, transaction: 'ProgramState'):
        if self.iTransaction < len(self.lTransactionS) - 1:
            self.lTransactionS = self.lTransactionS[:self.iTransaction]

        transaction.refresh(self.currentState)
        self.lTransactionS.append(transaction)
        self.currentState = transaction
        self.iTransaction = len(self.lTransactionS) - 1

    def undo(self)-> 'ProgramState':
        if self.iTransaction > 0:
            self.iTransaction -= 1
            self.currentState = self.lTransactionS[self.iTransaction]
        return self.currentState

    def redo(self)-> 'ProgramState':
        if self.iTransaction < len(self.lTransactionS) - 1:
            self.iTransaction += 1
            self.currentState = self.lTransactionS[self.iTransaction]
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

    def __getattr__(self, item):
        return getattr(self._loop, item)


class TestFrame(tk.Frame):
    """
    Program GUI window class with async working and undo/redo functionality
    """
    def __init__(self):
        super().__init__()
        self.top = self.winfo_toplevel()

        self.sText    = tk.StringVar()
        self.sInt     = tk.StringVar()
        self.observer = self.sText.trace_variable("w", self._sEntryModified)

        _col = 0
        self.label = tk.Label(self.top, text="Initial Text: ")
        self.label.grid(row=1, column=_col)
        _col += 1
        self.textEntry = InputDirPlusText(self.top, "XML Source folder", self.sText, row=1, column=_col)
        _col += 1
        # self.textEntry = tk.Entry(self.top, {"textvariable": self.sText, "width": 1})
        # self.textEntry.grid(row=1, column=_col)
        # _col += 1
        self.label = tk.Label(self.top, text="Number: ")
        self.label.grid(row=1, column=_col)
        _col += 1
        # self.intEntry = tk.Entry(self.top, {"textvariable": self.sInt})
        # self.intEntry.grid(row=1, column=_col)
        # _col += 1
        self.buttonStart = tk.Button(self.top, text="Start", command=self._start_processing)
        self.buttonStart.grid(row=1, column=_col)
        _col += 1
        self.buttonCancel = tk.Button(self.top, text="Cancel", command=self._cancel_processing, state=tk.DISABLED)
        self.buttonCancel.grid(row=1, column=_col)

        self.scrolledText = scrolledtext.ScrolledText()
        self.scrolledText.grid(row=0, column=0, columnspan=_col, sticky=tk.SE + tk.NW)
        # self.scrolledText.grid({"row":0, "column":0, "columnspan":_col, "sticky":tk.SE + tk.NW} )

        self.top.bind("<Control-z>", self._undo)
        self.top.bind("<Control-y>", self._redo)
        # FIXME multiple modifier handling:
        # self.top.bind("<Shift-Control-z>", self._redo)

        self.top.protocol("WM_DELETE_WINDOW", self._close)
        self.testResultList = []

        self.trackedFields = self.sText, self.sInt, self.testResultList
        self.stateList = StateList(self.getState())

        # ------

        self.loop = Loop(self.top)
        self.loop.run_forever()

    def _refresh_scrolledText(self):
        self.scrolledText.replace("1.0", "end", "\n".join(self.testResultList))
        self.scrolledText.see(tk.END)

    async def _process(self):
        await self.scanDirFactory(self.sText.get(), p_sCurrentFolder='')

        # for i in range(int(self.sInt.get())):
        #     await asyncio.sleep(.1)  # Simulate a long-running task
        #     self.testResultList.append(f"{self.sText.get()} {i}")
        #     self._refresh_scrolledText()
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

    def getState(self)->ProgramState:
        return ProgramState(*self.trackedFields)

    def setState(self, state:ProgramState):
        state.set()
        self._refresh_scrolledText()

    def _close(self):
        self.loop.stop()
        self.top.destroy()

    # ------

    def _sEntryModified(self, *_):
        self.textEntry.config(width=len(self.sText.get()))
        self.update()

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
                    #     GUIAppSingleton().iTotal += 1
                        if os.path.splitext(os.path.basename(f))[1].upper() in p_acceptedFormatS:
                            self.testResultList.append(f"{self.sText.get()} {f}")
                            self._refresh_scrolledText()
                            await asyncio.sleep(0)
                            # SourceXML(os.path.join(p_sCurrentFolder, f))
                        else:
                            self.testResultList.append(f"{self.sText.get()} {f}")
                            self._refresh_scrolledText()
                            await asyncio.sleep(0)
                    # set up replacement dict for other files
                            # if os.path.splitext(os.path.basename(f))[0].upper() not in SourceResource.source_pict_dict:
                            #     sI = SourceResource(os.path.join(p_sCurrentFolder, f), p_sBasePath=p_sRootFolder)
                            #     if SourceResource.sSourceResourceDir in sI.fullPath and SourceResource.sSourceResourceDir:
                            #         sI.isEncodedImage = True
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

