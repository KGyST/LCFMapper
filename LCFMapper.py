#!C:\Program Files\Python27amd64\python.exe
# -*- coding: utf-8 -*-
"""
Author: Sam KARLI
Date: 2023-06-19
Description:
"""
# FIXME to provide an UI-filter showing, for example, which parameter exists in which macro
# FIXME to create a config-loader either from .conf file or registry
# FIXME logging
# FIXME {ACVERSION} for the sheets

import os.path
import time
from io import StringIO
import tempfile
import subprocess
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
from Config import *
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
    'Pens':                 PAR_PEN,
    'Fills':                PAR_FILL,
    'Linetypes':            PAR_LINETYPE,
    'Surfaces':             PAR_MATERIAL,
    'Building Materials':   PAR_BMAT,
    'Strings':              PAR_STRING,
    'Booleans':             PAR_BOOL,
    'Integers':             PAR_INT,
}

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
            # GUIAppSingleton().print("WARNING - Missing attribute type: %s" % sheet_name)
            print(_result)
            raise
        # try:
        #     _result = [cell.value for cell in [row for row in self.wb[sheet_name]]]
        # except:
        #     print(_result)
        # return _result


class ParamMapping:
    def __init__(self, p_iType:int, p_row):
        self._type = p_iType
        self._files = str.split(p_row[_E_], ";") if p_row[_E_] else []
        self._paramName = p_row[_F_]
        self._paramDesc = p_row[_G_]
        self._from = p_row[_H_]
        self._to = p_row[_J_]
        _folders = [f for f in p_row[:4] if f]
        self._dirName = os.sep.join(_folders)

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

            _mappingList = []
            for row in _sheet[1:]:
                if row[_J_]:
                    _mappingList.append(ParamMapping(_paramType, row))
            self._mappingList.extend(reversed(_mappingList))

    def _isFileToBeProcessed(self, p_fileName:str, p_dirName:str, p_mapping:'ParamMapping')->bool:
        if not p_mapping._files and p_mapping._dirName in p_dirName or not p_mapping._dirName\
                or p_fileName in p_mapping._files:
            return True
        else:
            return False

    def applyParams(self, p_parSect, p_fileName, p_dirName):
        _appliedParamSet = set()
        for mapping in self._mappingList:
            if self._isFileToBeProcessed(p_fileName, p_dirName, mapping):
                params = p_parSect.getParamsByTypeNameAndValue(mapping._type, mapping._paramName, "", mapping._from)
                for par in params:
                    if par not in _appliedParamSet:
                        par.value = mapping._to
                        _appliedParamSet.add(par)
                    else:
                        GUIAppSingleton().print(f"Tried to apply another conversion to parameter {par.name}: {mapping._from} -> {mapping._to}")


#----------------- gui classes -----------------------------------------------------------------------------------------


@singleton
class GUIAppSingleton(tk.Frame):
    def __init__(self):
        super().__init__()
        self.top = self.winfo_toplevel()
        self.top = self.winfo_toplevel()

        self._currentConfig = Config("LCFMapper", "ArchiCAD")

        self.SourceXLSXPath = tk.StringVar(self.top, self._currentConfig["sourcexlsxpath"])
        self.SourceXMLDirName = tk.StringVar(self.top, self._currentConfig["sourcedirname"])
        self.SourceImageDirName = tk.StringVar(self.top, self._currentConfig["inputimagesource"])
        self.TargetLCFPath = tk.StringVar(self.top, self._currentConfig["targetlcfpath"])
        self.ACLocation = tk.StringVar(self.top, self._currentConfig["aclocation"])
        self.bDebug             = tk.BooleanVar(self.top, self._currentConfig["bdebug"] != "False")
        self.bCleanup           = tk.BooleanVar(self.top, self._currentConfig["bcleanup"] != "False")

        self._iCurrent = 0
        self._iTotal = 0
        self._sOutput = StringIO()
        self._tick = time.perf_counter()
        self._iCurrentLock = mp.Lock()
        self._iTotalLock = mp.Lock()
        self._lock = mp.Lock()
        self._log=""

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
        Observer(self.SourceXLSXPath, self._sourceXLSXPathModified)
        self.task = None

        self.loop = Loop(self.top)
        self.message_queue = mp.Manager().Queue()
        self.async_queue = asyncio.Queue()

        self.loop.create_task(self.mp_queue_to_async_queue())
        self.loop.create_task(self.print_out_async())

        self._startup()


    def mainloop(self) -> None:
        self.loop.run_forever()

    def _startup(self):
        self._sourceXMLDirModified()
        self._sourceXLSXPathModified()

    def _sourceXMLDirModified(self, *_):
        if self.SourceXMLDirName.get():
            _ = self.tick
            self.textEntry.config(width=len(self.SourceXMLDirName.get()))
            # self.update()
            self._start_source_xml_processing()

    def _sourceXLSXPathModified(self, *_):
        _path = self.SourceXLSXPath.get()
        if _path and os.path.isfile(_path):
            self.paramMapping = ParamMappingContainer(_path)

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
            self._log += text + "\n"
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
                     "mapping": self.paramMapping,
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
        tempGDLDir = os.path.join(tempGDLDir, "Archicad Library 26")
        os.makedirs(tempGDLDir)

        tempPicDir = tempfile.mkdtemp()  # For every image file, collected
        DestXML.sDestXMLDir = tempXMLDir

        self.print("tempXMLDir: %s" % tempXMLDir)
        self.print("tempGDLDir: %s" % tempGDLDir)
        self.print("tempPicDir: %s" % tempPicDir)

        for sourceXML in SourceXML.replacement_dict.values():
            DestXML(sourceXML)

        for sourceResource in SourceResource.source_pict_dict.values():
            DestResource(sourceResource, tempPicDir if sourceResource.isEncodedImage else tempGDLDir)

        await  self.loop.run_in_executor(None, self.worker_pool, tempXMLDir)

        for f in list(DestResource.pict_dict.keys()):
            if DestResource.pict_dict[f].sourceFile.isEncodedImage:
                #Now probably unused:
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
                    if self.bDebug.get():
                        shutil.copyfile(DestResource.pict_dict[f].sourceFile.fullPath,
                                        os.path.join(tempXMLDir, DestResource.pict_dict[f].relPath))
                except IOError:
                    os.makedirs(os.path.join(tempGDLDir, DestResource.pict_dict[f].dirName))
                    shutil.copyfile(DestResource.pict_dict[f].sourceFile.fullPath,
                                    os.path.join(tempGDLDir, DestResource.pict_dict[f].relPath))
                    if self.bDebug.get():
                        os.makedirs(os.path.join(tempXMLDir, DestResource.pict_dict[f].dirName))
                        shutil.copyfile(DestResource.pict_dict[f].sourceFile.fullPath,
                                        os.path.join(tempXMLDir, DestResource.pict_dict[f].relPath))

        x2lCommand = '"%s" x2l -img "%s" "%s" "%s"' % (os.path.join(self.ACLocation.get(), 'LP_XMLConverter.exe'), self.SourceImageDirName.get(), tempXMLDir, tempGDLDir)

        GUIAppSingleton().print("x2l Command being executed...")
        GUIAppSingleton().print(x2lCommand)

        result = subprocess.run(
            [os.path.join(self.ACLocation.get(), 'LP_XMLConverter.exe'), "x2l", "-img", self.SourceImageDirName.get(),
             tempXMLDir, tempGDLDir], capture_output=True, text=True, timeout=100)

        output = result.stdout
        GUIAppSingleton().print(output)

        result = subprocess.run(
            [os.path.join(self.ACLocation.get(), 'LP_XMLConverter.exe'), "createcontainer", self.TargetLCFPath.get(),
             tempGDLDir], capture_output=True, text=True, timeout=1000)
        output = result.stdout
        GUIAppSingleton().print(output)

        # cleanup ops
        if self.bCleanup.get():
            shutil.rmtree(tempXMLDir)
            shutil.rmtree(tempPicDir)
        else:
            GUIAppSingleton().print("tempXMLDir: %s" % tempXMLDir)
            GUIAppSingleton().print("tempPicDir: %s" % tempPicDir)
            GUIAppSingleton().print("tempGDLDir: %s" % tempGDLDir)
            with open(os.path.join(tempGDLDir, "log.txt"), "w") as _file:
                _file.write(self._log)

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

    def getConfig(self):
        pass

    def writeConfigBack(self, ):
        # FIXME encrypting of sensitive data
        # TODO bdebug handling
        currentConfig = RawConfigParser()
        currentConfig.add_section("ArchiCAD")
        currentConfig.set("ArchiCAD", "bdebug", str(self.bDebug.get()))

        if not self.bDebug.get():
            currentConfig.set("ArchiCAD", "sourcexlsxpath",     self.SourceXLSXPath.get())
            currentConfig.set("ArchiCAD", "sourcedirname",      self.SourceXMLDirName.get())
            currentConfig.set("ArchiCAD", "inputimagesource",   self.SourceImageDirName.get())
            currentConfig.set("ArchiCAD", "targetlcfpath",      self.TargetLCFPath.get())
            currentConfig.set("ArchiCAD", "aclocation",         self.ACLocation.get())
            currentConfig.set("ArchiCAD", "bcleanup",           str(self.bCleanup.get()))
            currentConfig.set("ArchiCAD", "allkeywords",        ', '.join(sorted(list(XMLFile.all_keywords))))

        # if self.googleSpreadsheet:
        #     currentConfig.add_section("GoogleSpreadsheetAPI")
        #     currentConfig.set("GoogleSpreadsheetAPI", "access_token",   self.googleSpreadsheet.googleCreds.token)
        #     currentConfig.set("GoogleSpreadsheetAPI", "refresh_token",  self.googleSpreadsheet.googleCreds.refresh_token)
        #     currentConfig.set("GoogleSpreadsheetAPI", "id_token",       self.googleSpreadsheet.googleCreds.id_token)
        #     currentConfig.set("GoogleSpreadsheetAPI", "token_uri",      self.googleSpreadsheet.googleCreds.token_uri)
        #     currentConfig.set("GoogleSpreadsheetAPI", "client_id",      self.googleSpreadsheet.googleCreds.client_id)
        #     currentConfig.set("GoogleSpreadsheetAPI", "client_secret",  self.googleSpreadsheet.googleCreds.client_secret)

        with open(os.path.join(os.getenv('APPDATA'), "LCFMapper.ini"), 'w', encoding="UTF-8") as configFile:
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
    mapping = p_data['mapping']
    tempDir = p_data["tempXMLDir"]

    # FIXME ParamMappingContainer is the same for all so move to the singleton:
    # mapping = ParamMappingContainer(GUIAppSingleton().SourceXLSXPath.get())

    src = dest.sourceFile
    srcPath = src.fullPath
    destPath = os.path.join(tempDir, dest.relPath)
    destDir = os.path.dirname(destPath)

    p_messageQueue.put("%s -> %s" % (srcPath, destPath,))

    mdp = etree.parse(srcPath, etree.XMLParser(strip_cdata=False))

    parRoot = mdp.find("./ParamSection")
    mapping.applyParams(dest.parameters, dest.name, dest.dirName)
    destPar = dest.parameters.toEtree()	
    parRoot.getparent().replace(parRoot, destPar)

    try:
        os.makedirs(destDir)
    except WindowsError:
        pass

    with open(destPath, "w", encoding="utf-8-sig", newline="\n") as file_handle:
        xml_declaration = '<?xml version="1.0" encoding="UTF-8"?>\n'
        mdp_tostring = etree.tostring(mdp, pretty_print=True, encoding="UTF-8").decode("UTF-8")
        sXML = xml_declaration + mdp_tostring
        file_handle.write(sXML)

    p_messageQueue.put ("%s -> %s" % (srcPath, destPath,))


if __name__ == "__main__":
    app = GUIAppSingleton()
    # app.top.protocol("WM_DELETE_WINDOW", app.writeConfigBack)
    app.mainloop()

