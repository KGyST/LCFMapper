#!C:\Program Files\Python27amd64\python.exe
# -*- coding: utf-8 -*-
"""
Author: Sam KARLI
Date: 2023-06-19
Description:
"""
# FIXME to provide an UI-filter showing, for example, which parameter exists in which macro
# FIXME to create a config-loader either from .conf file or registry

import os.path
import time
from io import StringIO
import tempfile
from subprocess import check_output
import shutil

import tkinter.filedialog
import asyncio
from configparser import *  #FIXME not *

import pip
import multiprocessing as mp

from Undoable import *
from Async import Loop
from tkinter import scrolledtext

try:
    from lxml import etree
except ImportError:
    pip.main(['install', '--user', 'lxml'])
    from lxml import etree

from GSMXMLLib import *
from SamUITools import singleton, CreateToolTip, InputDirPlusText
from Constants import *
from queue import Empty as QueueEmpty
from concurrent.futures import ProcessPoolExecutor, as_completed

# FIXME Enums
ID = ''
# AC_18   = 28
SCRIPT_NAMES_LIST = ["Script_1D",
                     "Script_2D",
                     "Script_3D",
                     "Script_PR",
                     "Script_UI",
                     "Script_VL",
                     "Script_FWM",
                     "Script_BWM",]

PARAM_TYPES = {
    'Pens':         PAR_PEN,
    'Fills':        PAR_FILL,
    'Linetypes':    PAR_LINETYPE,
    'Surfaces':     PAR_MATERIAL,
    'Strings':      PAR_STRING,
    'Booleans':     PAR_BOOL,
    'Integers':     PAR_INT,
}

# ------------------- data classes -------------------------------------------------------------------------------------

#----------------- mapping classes -------------------------------------------------------------------------------------


class XLSXLoader:
    def __init__(self, table_url:str):
        import openpyxl as opx
        self.wb = opx.load_workbook(table_url)

    def __getitem__(self, sheet_name:str):
        _result = []
        try:
            for row in self.wb[sheet_name]:
                _row = []
                for cell in row:
                    _v = cell.value
                    _row.append(_v)
                _result.append(_row)
            return  _result
        except:
            print(_result)
        # try:
        #     _result = [cell.value for cell in [row for row in self.wb[sheet_name]]]
        # except:
        #     print(_result)
        # return _result


class ParamMapping:
    def __init__(self, p_iType:int, p_row):
        self._type = p_iType
        self._files = str.split(p_row[_A_], ";") if p_row[_A_] else []
        self._paramName = p_row[_B_]
        self._paramDesc = p_row[_C_]
        self._from = p_row[_D_]
        self._to = p_row[_F_]


class ParamMappingContainer:
    def __init__(self, p_sXLSX:str):
        self._mappingList = []
        # FIXME Google Spreadsheet, too
        self.loader = XLSXLoader(p_sXLSX)

        for _sheetName, _paramType in PARAM_TYPES.items():
            try:
                _sheet = self.loader[_sheetName]
            except KeyError:
                continue

            for row in _sheet[1:]:
                self._mappingList.append(ParamMapping(_paramType, row))


    def applyParams(self, p_parSect, p_fileName):
        for mapping in self._mappingList:
            if not mapping._files or p_fileName in mapping._files:
                params = p_parSect.getParamsByTypeNameAndValue(mapping._type, mapping._paramName, mapping._paramDesc, mapping._from)
                for par in params:
                    par.value = mapping._to


#----------------- gui classes -----------------------------------------------------------------------------------------


@singleton
class GUIAppSingleton(tk.Frame):
    def __init__(self):
        super().__init__()
        self.top = self.winfo_toplevel()

        self.currentConfig = ConfigParser()
        self.appDataDir  = os.getenv('APPDATA')
        if os.path.isfile(self.appDataDir  + r"\LCFMapper.ini"):
            self.currentConfig.read(self.appDataDir  + r"\LCFMapper.ini", encoding="UTF-8")
        else:
            self.currentConfig.read("LCFMapper.ini", encoding="UTF-8")    #TODO into a different class or stg

        self.SourceXMLDirName = tk.StringVar()
        self.SourceXLSXPath = tk.StringVar()
        self.TargetLCFPath = tk.StringVar()
        self.SourceImageDirName = tk.StringVar()
        self.ACLocation = tk.StringVar()
        self.bDebug             = tk.BooleanVar()
        self.bCleanup           = tk.BooleanVar()

        self._iCurrent = 0
        self._iTotal = 0
        self._sOutput = StringIO()
        self._tick = time.perf_counter()
        self._iCurrentLock = mp.Lock()
        self._iTotalLock = mp.Lock()
        self._lock = mp.Lock()

        self.cpuCount = max(mp.cpu_count() - 1, 1)

        try:
            for cName, cValue in self.currentConfig.items('ArchiCAD'):
                try:
                    if   cName == 'bdebug':             self.bDebug.set(cValue)
                    elif cName == 'bcleanup':           self.bCleanup.set(cValue)
                    elif cName == 'allkeywords':
                        XMLFile.all_keywords |= set(v.strip() for v in cValue.split(',') if v !='')
                    elif cName == 'aclocation':         self.ACLocation.set(cValue)
                    elif cName == 'inputimagesource':   self.SourceImageDirName.set(cValue)
                    elif cName == 'sourcedirname':      self.SourceXMLDirName.set(cValue)
                    elif cName == 'sourcexlsxpath':     self.SourceXLSXPath.set(cValue)
                    elif cName == 'targetlcfpath':      self.TargetLCFPath.set(cValue)
                except NoOptionError:
                    print("NoOptionError")
                    continue
                except NoSectionError:
                    print("NoSectionError")
                    continue
                except ValueError:
                    print("ValueError")
                    continue
        except NoSectionError:
            print("NoSectionError")

        # GUI itself----------------------------------------------------------------------------------------------------

        iR = 0

        InputDirPlusText(self.top, "XLSX name", self.SourceXLSXPath, row=iR, func=tkinter.filedialog.askopenfilename, title="Select file", tooltip="Path of the .xlsx file that describes the conversion")

        iR += 1

        self.textEntry = InputDirPlusText(self.top, "XML Source folder", self.SourceXMLDirName, row=iR, tooltip='Path of the folder where extracted .lcf file structure is')

        iR += 1

        InputDirPlusText(self.top, "Images' source folder", self.SourceImageDirName, row=iR, tooltip="Path of image folder that is the result of extractontainer 's -img switch, for encoded images")

        iR += 1

        # InputDirPlusText(self.top, "LCF Source path", self.TargetLCFPath, "LCF Source path", row=iR, func=tkinter.filedialog.askopenfilename, title="Select file")

        # iR += 1

        InputDirPlusText(self.top, "LCF Destination path", self.TargetLCFPath, "LCF Destination path", row=iR, func=tkinter.filedialog.asksaveasfilename, title="Select file")

        iR += 1

        InputDirPlusText(self.top, "ArchiCAD location",  self.ACLocation, "ArchiCAD location", row=iR)

        iR += 1

        self.bottomFrame        = tk.Frame(self.top, )
        self.bottomFrame.grid({"row":iR, "sticky":  tk.S + tk.N, })

        # Bottom row----------------------------------------------------------------------------------------------------

        iC = 0

        self.buttonStart        = tk.Button(self.bottomFrame, {"text": "Start", "command": self.start})
        self.buttonStart.grid({"row": 0, "column": iC, "sticky": tk.E})

        iC += 1

        CreateToolTip(self.buttonStart, "Start conversion")

        self.debugCheckButton   = tk.Checkbutton(self.bottomFrame, {"text": "Debug", "variable": self.bDebug})
        self.debugCheckButton.grid({"row": 0, "column": iC})

        iC += 1

        CreateToolTip(self.debugCheckButton, "Print out debug info")

        self.cleanupCheckButton   = tk.Checkbutton(self.bottomFrame, {"text": "Cleanup", "variable": self.bCleanup})
        self.cleanupCheckButton.grid({"row": 0, "column": iC})

        iC += 1

        CreateToolTip(self.cleanupCheckButton, "Delete temporary files after conversion")

        iR += 1

        #/Bottom row----------------------------------------------------------------------------------------------------

        self.scrolledText = scrolledtext.ScrolledText()
        self.scrolledText.grid(row=0, column=1, rowspan=iR, sticky=tk.SE + tk.NW)

        #           ----------------------------------------------------------------------------------------------------

        self.progressInfo = tk.Label(self.top, text=f"{self.iCurrent} / {self.iTotal}")
        self.progressInfo.grid({"row": iR, "column": 0, "sticky": tk.W}); iC += 1

        self.top.protocol("WM_DELETE_WINDOW", self.writeConfigBack)

        Observer(self.SourceXMLDirName, self._sourceXMLDirModified)
        self.task = None

        self.loop = Loop(self.top)
        self.message_queue = mp.Manager().Queue()
        self.async_queue = asyncio.Queue()

        self.loop.create_task(self.mp_queue_to_async_queue())
        self.loop.create_task(self.print_out_async())

        # await self.process_messages()

    def mainloop(self) -> None:
        self.loop.run_forever()

    def _sourceXMLDirModified(self, *_):
        if self.SourceXMLDirName.get():
            _ = self.tick
            self.textEntry.config(width=len(self.SourceXMLDirName.get()))
            # self.update()
            self._start_source_xml_processing()

    def _start_source_xml_processing(self):
        self._cancel_source_xml_processing()
        self.buttonStart.config(state=tk.DISABLED, text="Processing...")
        self.textEntry.config(state=tk.DISABLED)
        self.task = self.loop.create_task(self._process())
        self.task.add_done_callback(self._end_of_xml_dir_processing)

    def _cancel_source_xml_processing(self):
        if self.task:
            self.task.cancel()
        self.task=None
        self._iCurrent = 0
        self._iTotal = 0

    def _end_of_xml_dir_processing(self, task):
        self.buttonStart.config(state=tk.NORMAL, text="Start")
        self.textEntry.config(state=tk.NORMAL)
        # self._refresh_outputs()
        self.progressInfo.config(text=f"{self.iCurrent} / {self.iTotal} Scanning dirs took {self.tick:.2f} seconds")

    def _end_of_conversion(self, task):
        self.buttonStart.config(state=tk.NORMAL, text="Start")
        self.textEntry.config(state=tk.NORMAL)
        # self._refresh_outputs()
        self.progressInfo.config(text=f"{self.iCurrent} / {self.iTotal} Conversion took {self.tick:.2f} seconds")

    @property
    def iTotal(self):
        with self._iTotalLock:
            return self._iTotal

    @iTotal.setter
    def iTotal(self, value):
        with self._iTotalLock:
            self._iTotal = value
            self.progressInfo.config(text=f"{self.iCurrent} / {self._iTotal}")

    @property
    def iCurrent(self):
        with self._iCurrentLock:
            return self._iCurrent

    @iCurrent.setter
    def iCurrent(self, value):
        with self._iCurrentLock:
            self._iCurrent = value
            self.progressInfo.config(text=f"{self._iCurrent} / {self.iTotal}")

    @property
    def tick(self):
        _t = self._tick
        self._tick = time.perf_counter()
        return self._tick - _t

    @staticmethod
    def clear_data():
        DestXML.dest_dict.clear()
        DestXML.dest_sourcenames.clear()
        DestXML.id_dict.clear()
        DestResource.pict_dict.clear()

    def print(self, text:str):
        with self._lock:
            self._sOutput.write(f"{text}\n")
            self.scrolledText.replace("1.0", "end", self._sOutput.getvalue())
        self.scrolledText.see(tk.END)
        print(text)

    def start(self):
        # self.buttonStart.setvar("state", "disabled")
        self.buttonStart.config(state=tk.DISABLED, text="Processing...")
        _ = self.tick
        self.task = self.loop.create_task(self._start())
        # self.loop.run_until_complete(self._start())
        self.task.add_done_callback(self._end_of_conversion)

        self.print("Starting conversion")

    async def _process(self):
        SourceXML.sSourceXMLDir = self.SourceXMLDirName.get()
        SourceResource.sSourceResourceDir = self.SourceImageDirName.get()
        await self.scanDirFactory(self.SourceXMLDirName.get(), current_folder='')

    async def mp_queue_to_async_queue(self):
        """
        Puts messages from multiple processes to the async loop of UI to be printed out
        """
        while True:
            try:
                message = self.message_queue.get_nowait()
            except QueueEmpty:
                await asyncio.sleep(0)
                continue
            except BrokenPipeError:
                break
            await self.async_queue.put(message)

    async def print_out_async(self):
        while True:
            async_message = await self.async_queue.get()
            if async_message is None:
                break
            self.print(async_message)

    def worker_pool(self, tempXMLDir):
        pool_map = [{"dest": DestXML.dest_dict[k],
                     "tempXMLDir": tempXMLDir,
                     } for k in list(DestXML.dest_dict.keys()) if
                    isinstance(DestXML.dest_dict[k], DestXML)]
        with ProcessPoolExecutor(max_workers=self.cpuCount) as executor:
            for p_item in pool_map:
                executor.submit(processOneXML, p_item, self.message_queue)

            executor.shutdown(wait=True)

        self.message_queue.put(None)

    async def _start(self):
        """
        :return:
        """
        self.clear_data()

        SourceXML.sSourceXMLDir = self.SourceXMLDirName.get()
        SourceResource.sSourceResourceDir = self.SourceImageDirName.get()

        tempXMLDir = tempfile.mkdtemp()
        tempGDLDir = tempfile.mkdtemp()
        tempPicDir = tempfile.mkdtemp()  # For every image file, collected

        self.print("tempXMLDir: %s" % tempXMLDir)
        self.print("tempGDLDir: %s" % tempGDLDir)
        self.print("tempPicDir: %s" % tempPicDir)

        for sourceXML in SourceXML.replacement_dict.values():
            DestXML(sourceXML, DestXML.sDestXMLDir)

        for sourceResource in SourceResource.source_pict_dict.values():
            DestResource(sourceResource, tempPicDir if sourceResource.isEncodedImage else tempGDLDir)

        await  self.loop.run_in_executor(None, self.worker_pool, tempXMLDir)

        for f in list(DestResource.pict_dict.keys()):
            if DestResource.pict_dict[f].sourceFile.isEncodedImage:
                try:
                    shutil.copyfile(os.path.join(self.SourceImageDirName.get(),
                                                 DestResource.pict_dict[f].sourceFile.relPath),
                                    os.path.join(tempPicDir, DestResource.pict_dict[f].relPath))
                except IOError:
                    os.makedirs(os.path.join(tempPicDir, DestResource.pict_dict[f].dirName))
                    shutil.copyfile(os.path.join(self.SourceImageDirName.get(),
                                                 DestResource.pict_dict[f].sourceFile.relPath),
                                    os.path.join(tempPicDir, DestResource.pict_dict[f].relPath))
            else:
                try:
                    shutil.copyfile(DestResource.pict_dict[f].sourceFile.fullPath,
                                    os.path.join(tempGDLDir, DestResource.pict_dict[f].relPath))
                except IOError:
                    os.makedirs(os.path.join(tempGDLDir, DestResource.pict_dict[f].dirName))
                    shutil.copyfile(DestResource.pict_dict[f].sourceFile.fullPath,
                                    os.path.join(tempGDLDir, DestResource.pict_dict[f].relPath))

        x2lCommand = '"%s" x2l -img "%s" "%s" "%s"' % (os.path.join(self.ACLocation.get(), 'LP_XMLConverter.exe'), self.SourceImageDirName.get(), tempXMLDir, tempGDLDir)

        if self.bDebug.get():
            # FIXME to JSON
            self.print("x2l Command being executed...")
            self.print(x2lCommand)
            if not self.bCleanup.get():
                with open(tempXMLDir + "\dict.txt", "w") as d:
                    for k in list(DestXML.dest_dict.keys()):
                        d.write(
                            k + " " + DestXML.dest_dict[k].sourceFile.name + "->" + DestXML.dest_dict[
                                k].name + " " + DestXML.dest_dict[k].sourceFile.guid + " -> " +
                            DestXML.dest_dict[k].guid + "\n")

                with open(tempXMLDir + "\pict_dict.txt", "w") as d:
                    for k in list(DestResource.pict_dict.keys()):
                        d.write(DestResource.pict_dict[k].sourceFile.fullPath + "->" + DestResource.pict_dict[
                            k].relPath + "\n")

                with open(tempXMLDir + "\id_dict.txt", "w") as d:
                    for k in list(DestXML.id_dict.keys()):
                        d.write(DestXML.id_dict[k] + "\n")

        check_output(x2lCommand, shell=True)

        containerCommand = '"%s" createcontainer "%s" "%s"' % (
        os.path.join(self.ACLocation.get(), 'LP_XMLConverter.exe'), self.TargetLCFPath.get(),
        tempGDLDir)

        if self.bDebug.get():
            self.print("containerCommand Command being executed...")
            self.print(containerCommand)

        check_output(containerCommand, shell=True)

        # cleanup ops
        if self.bCleanup.get():
            shutil.rmtree(tempXMLDir)
            shutil.rmtree(tempPicDir)
        else:
            self.print("tempXMLDir: %s" % tempXMLDir)
            self.print("tempPicDir: %s" % tempPicDir)

        self.print("*****FINISHED SUCCESFULLY******")

        self.buttonStart.setvar("state", "active")

    async def scanDirFactory(self, root_folder, current_folder='', accepted_formats=(".XML",)):
        """
        only scanning input dir recursively to set up xml and image files' list
        :param root_folder:
        :param current_folder:
        :param accepted_formats:
        :return:
        """
        try:
            for f in os.listdir(os.path.join(root_folder, current_folder)):
                try:
                    sRelPath = os.path.join(current_folder, f)
                    if not os.path.isdir(os.path.join(root_folder, sRelPath)):
                    # if it IS NOT a folder
                        self.iTotal += 1
                        if os.path.splitext(os.path.basename(f))[1].upper() in accepted_formats:
                            SourceXML(sRelPath)
                        else:
                            if os.path.splitext(os.path.basename(f))[0].upper() not in SourceResource.source_pict_dict:
                                sR = SourceResource(sRelPath, base_path=root_folder)
                                if SourceResource.sSourceResourceDir in sR.fullPath and SourceResource.sSourceResourceDir:
                                    sR.isEncodedImage = True
                        await asyncio.sleep(0)
                    else:
                    # if it IS a folder
                        await self.scanDirFactory(root_folder, sRelPath)
                except KeyError:
                    self.print("KeyError %s" % f)
                    continue
                except etree.XMLSyntaxError:
                    self.print("XMLSyntaxError %s" % f)
                    continue
        except WindowsError:
            pass

    def writeConfigBack(self, ):
        # FIXME encrypting of sensitive data
        # TODO bdebug handling
        if not self.bDebug.get():
            currentConfig = RawConfigParser()
            currentConfig.add_section("ArchiCAD")
            currentConfig.set("ArchiCAD", "sourcexlsxpath",     self.SourceXLSXPath.get())
            currentConfig.set("ArchiCAD", "sourcedirname",      self.SourceXMLDirName.get())
            currentConfig.set("ArchiCAD", "inputimagesource",   self.SourceImageDirName.get())
            currentConfig.set("ArchiCAD", "targetlcfpath",      self.TargetLCFPath.get())
            currentConfig.set("ArchiCAD", "aclocation",         self.ACLocation.get())
            currentConfig.set("ArchiCAD", "bcleanup",           str(self.bCleanup.get()))
            currentConfig.set("ArchiCAD", "bdebug",             str(self.bDebug.get()))
            currentConfig.set("ArchiCAD", "allkeywords",        ', '.join(sorted(list(XMLFile.all_keywords))))

            # if self.googleSpreadsheet:
            #     currentConfig.add_section("GoogleSpreadsheetAPI")
            #     currentConfig.set("GoogleSpreadsheetAPI", "access_token",   self.googleSpreadsheet.googleCreds.token)
            #     currentConfig.set("GoogleSpreadsheetAPI", "refresh_token",  self.googleSpreadsheet.googleCreds.refresh_token)
            #     currentConfig.set("GoogleSpreadsheetAPI", "id_token",       self.googleSpreadsheet.googleCreds.id_token)
            #     currentConfig.set("GoogleSpreadsheetAPI", "token_uri",      self.googleSpreadsheet.googleCreds.token_uri)
            #     currentConfig.set("GoogleSpreadsheetAPI", "client_id",      self.googleSpreadsheet.googleCreds.client_id)
            #     currentConfig.set("GoogleSpreadsheetAPI", "client_secret",  self.googleSpreadsheet.googleCreds.client_secret)

            with open(os.path.join(self.appDataDir, "LCFMapper.ini"), 'w', encoding="UTF-8") as configFile:
                #FIXME proper config place
                try:
                    currentConfig.write(configFile)
                except UnicodeEncodeError:
                    #FIXME
                    pass
        self.loop.stop()
        self.top.destroy()


def processOneXML(p_data, p_messageQueue):
    dest = p_data['dest']
    tempDir = p_data["tempXMLDir"]

    mapping = ParamMappingContainer(GUIAppSingleton().SourceXLSXPath.get())

    src = dest.sourceFile
    srcPath = src.fullPath
    destPath = os.path.join(tempDir, dest.relPath)
    destDir = os.path.dirname(destPath)

    p_messageQueue.put("%s -> %s" % (srcPath, destPath,))
    # print("%s -> %s" % (srcPath, destPath,))

    mdp = etree.parse(srcPath, etree.XMLParser(strip_cdata=False))

    if dest.bPlaceable:
        parRoot = mdp.find("./ParamSection")
        parPar = parRoot.getparent()
        parPar.remove(parRoot)

        mapping.applyParams(dest.parameters, dest.name)

        destPar = dest.parameters.toEtree()
        parPar.append(destPar)
    try:
        os.makedirs(destDir)
    except WindowsError:
        pass
    with open(destPath, "wb") as file_handle:
        mdp.write(file_handle, pretty_print=True, encoding="UTF-8", xml_declaration=True, )

if __name__ == "__main__":
    app = GUIAppSingleton()
    # app.top.protocol("WM_DELETE_WINDOW", app.writeConfigBack)
    app.mainloop()

