import asyncio
from tkinter import scrolledtext
#FIXME tooltip improvements
from GSMXMLLib import *
from lxml import etree
from SamUITools import InputDirPlusText
from Undoable import *
from Async import Loop


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

        self.top.protocol("WM_DELETE_WINDOW", self._close)
        self.testResultList = []

        self.trackedFieldS = self.sText, self.testResultList
        Observer(self.sText, self._textEntryModified)
        self.stateList = StateList(self.top, self._refresh_outputs, self.trackedFieldS)
        self.task = None

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
            self.stateList.append(self.stateList.getState())
        else:
            self.stateList.setState(self.stateList.currentState)
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

