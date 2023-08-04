import asyncio
from tkinter import scrolledtext
#FIXME tooltip improvements
from GSMXMLLib import *
from lxml import etree
from SamUITools import InputDirPlusText
from Undoable import *
from Async import Loop


import tkinter as tk
import webbrowser

import tkinter as tk
import webbrowser
import re


class CreateToolTip:
    def __init__(self, widget, text='widget info', url=None):
        self.waittime = 500
        self.wraplength = 180
        self.widget = widget
        self.text = text
        self.url = url

        self.widget.bind("<Enter>", self.enter)
        self.widget.bind("<Leave>", self.leave)
        self.widget.bind("<ButtonPress>", self.leave)
        self.id = None
        self.tw = None

    def enter(self, event=None):
        self.schedule()

    def leave(self, event=None):
        self.unschedule()
        self.hidetip()

    def schedule(self):
        self.unschedule()
        self.id = self.widget.after(self.waittime, self.showtip)

    def unschedule(self):
        idx = self.id
        self.id = None
        if idx:
            self.widget.after_cancel(idx)

    def showtip(self, event=None):
        x, y, cx, cy = self.widget.bbox("insert")
        x += self.widget.winfo_rootx() + 25
        y += self.widget.winfo_rooty() + 20

        self.tw = tk.Toplevel(self.widget)
        self.tw.wm_overrideredirect(True)
        self.tw.wm_geometry("+%d+%d" % (x, y))

        if self.url:
            label = tk.Label(self.tw, text=self.text, justify='left',
                             background="#ffffff", relief='solid', borderwidth=1,
                             wraplength=self.wraplength, cursor="hand2", fg="blue")
            label.pack(ipadx=1)
            label.bind("<Button-1>", lambda e: webbrowser.open(self.url))
        else:
            label = tk.Label(self.tw, justify='left',
                             background="#ffffff", relief='solid', borderwidth=1,
                             wraplength=self.wraplength)
            label.pack(ipadx=1)

            self.parse_and_display(label)

    def parse_and_display(self, label):
        # Bold text
        self.text = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', self.text)

        # Italic text
        self.text = re.sub(r'\*(.*?)\*', r'<i>\1</i>', self.text)

        # Underlined text
        self.text = re.sub(r'_(.*?)_', r'<u>\1</u>', self.text)

        # Bullet lists
        self.text = re.sub(r'^\s*\*\s+(.*)$', r'<li>\1</li>', self.text, flags=re.MULTILINE)
        self.text = f'<ul>{self.text}</ul>'

        label.config(text=self.text)

    def hidetip(self):
        tw = self.tw
        self.tw = None
        if tw:
            tw.destroy()


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
        self.textEntry = InputDirPlusText(self.top, "XML Source folder", self.sText, row=1, column=_col, tooltip="teszt")
        _col += 1
        self.label = tk.Label(self.top, text=f"{self.iInt}")
        self.label.grid(row=1, column=_col)
        _col += 1
        self.buttonStart = tk.Button(self.top, text="Start", command=self._start_processing)
        self.buttonStart.grid(row=1, column=_col)

        tooltip_text = '''
        This is a tooltip with reST markup:

        - **Bold text**
        - *Italic text*
        - _Underlined text_

        Bullet list:
        * Item 1
        * Item 2
        '''

        CreateToolTip(self.buttonStart, text=tooltip_text)

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

