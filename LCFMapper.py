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
from os import listdir
import tempfile
from subprocess import check_output
import subprocess
import shutil

import tkinter as tk
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

# FIXME Enums
ID = ''
LISTBOX_SEPARATOR = '--------'
AC_18   = 28
SCRIPT_NAMES_LIST = ["Script_1D",
                     "Script_2D",
                     "Script_3D",
                     "Script_PR",
                     "Script_UI",
                     "Script_VL",
                     "Script_FWM",
                     "Script_BWM",]

PAR_UNKNOWN     = 0
PAR_LENGTH      = 1
PAR_ANGLE       = 2
PAR_REAL        = 3
PAR_INT         = 4
PAR_BOOL        = 5
PAR_STRING      = 6
PAR_MATERIAL    = 7
PAR_LINETYPE    = 8
PAR_FILL        = 9
PAR_PEN         = 10
PAR_SEPARATOR   = 11
PAR_TITLE       = 12
PAR_BMAT        = 13
PAR_PROF        = 14
PAR_COMMENT     = 15
# FIXME to handle unknown parameter types as string representations

PARAM_TYPES = {
    'Pens':         PAR_PEN,
    'Fills':        PAR_FILL,
    'Linetypes':    PAR_LINETYPE,
    'Surfaces':     PAR_MATERIAL,
    'Strings':      PAR_STRING,
    'Booleans':     PAR_BOOL,
    'Integers':     PAR_INT,
}

PARFLG_CHILD    = 1
PARFLG_BOLDNAME = 2
PARFLG_UNIQUE   = 3
PARFLG_HIDDEN   = 4

# ------------------- GUI ------------------------------
# ------------------- GUI ------------------------------
# ------------------- GUI ------------------------------

# ------------------- data classes -------------------------------------------------------------------------------------

#----------------- mapping classes -------------------------------------------------------------------------------------

_A_ =  0;   _B_ =  1;   _C_ =  2;   _D_ =  3;   _E_ =  4
_F_ =  5;   _G_ =  6;   _H_ =  7;   _I_ =  8;   _J_ =  9
_K_ = 10;   _L_ = 11;   _M_ = 12;   _N_ = 13;   _O_ = 14
_P_ = 15;   _Q_ = 16;   _R_ = 17;   _S_ = 18;   _T_ = 19
_U_ = 20;   _V_ = 21;   _W_ = 22;   _X_ = 23;   _Y_ = 24
_Z_ = 25


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
        self._files = str.split(p_row[_E_], ";") if p_row[_E_] else []
        self._paramName = p_row[_F_]
        self._paramDesc = p_row[_G_]
        self._from = p_row[_H_]
        self._to = p_row[_J_]


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
                if row[_J_]:
                    self._mappingList.append(ParamMapping(_paramType, row))

    def applyParams(self, p_parSect, p_fileName):
        for mapping in self._mappingList:
            if not mapping._files or p_fileName in mapping._files:
                params = p_parSect.getParamsByTypeNameAndValue(mapping._type, mapping._paramName, "", mapping._from)
                for par in params:
                    par.value = mapping._to


#----------------- config classes -----------------------------------------------------------------------------------------

@singleton
class Config:
    """
    app_name:str="application" - application's own name
    default_section:str=None
    """
    def __init__(self, app_name:str="application", default_section:str=None):
        self._appName = app_name
        self._currentConfig = ConfigParser()
        self._defaultConfig = ConfigParser()

        self.getConfigFromFile()
        self.setCurrentSection(default_section)

    def getConfigFromFile(self):
        self.appDataDir = os.getenv('APPDATA')
        if os.path.isfile(_fileName := (self._appName + ".ini")):
            self._currentConfig.read(os.path.join(self.appDataDir, _fileName), encoding="UTF-8")
        self._defaultConfig.read(_fileName, encoding="UTF-8")

    def __getitem__(self, item):
        if isinstance(item, tuple) or isinstance(item, list):
            _sec = item[0]
        else:
            _sec = self._currentSection
        try:
            return self._currentConfig[_sec][item]
        except:
            return self._defaultConfig[_sec][item]
        #         except NoOptionError:
        #             print("NoOptionError")
        #             continue
        #         except NoSectionError:
        #             print("NoSectionError")
        #             continue
        #         except ValueError:
        #             print("ValueError")
        #             continue

    def __setitem__(self, key, value:str):
        self._currentConfig[self._currentSection][key] = value

    def setCurrentSection(self, section:str):
        self._currentSection = section

    def writeConfigBack(self, ):
        with open(os.path.join(self.appDataDir, self._appName + ".ini"), 'w', encoding="UTF-8") as configFile:
            try:
                self._currentConfig.write(configFile)
            except UnicodeEncodeError:
                #FIXME
                pass


#-----------------/config classes -----------------------------------------------------------------------------------------

#----------------- gui classes -----------------------------------------------------------------------------------------


@singleton
class GUIAppSingleton(tk.Frame):
    def __init__(self):
        super().__init__()
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

        # self.trackedFieldS = self.sText, self.testResultList
        Observer(self.SourceXMLDirName, self._sourceXMLDirModified)
        # self.stateList = StateList(self.top, self._refresh_outputs, self.trackedFieldS)
        self.task = None

        self.loop = Loop(self.top)

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

    # def _refresh_outputs(self):
    #     self.scrolledText.replace("1.0", "end", self._sOutput.getvalue())
    #     self.scrolledText.see(tk.END)
    #     # self.progressInfo.config(text=f"{self.iCurrent} / {self.iTotal}")

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
        self.task.add_done_callback(self._end_of_conversion)

        self.print("Starting conversion")

    async def _process(self):
        SourceXML.sSourceXMLDir = self.SourceXMLDirName.get()
        SourceResource.sSourceResourceDir = self.SourceImageDirName.get()

        await self.scanDirFactory(self.SourceXMLDirName.get(), current_folder='')

    async def _start(self):
        """
        :return:
        """
        self.clear_data()
        message_queue = asyncio.Queue()
        process_queue = asyncio.Queue()

        SourceXML.sSourceXMLDir = self.SourceXMLDirName.get()
        SourceResource.sSourceResourceDir = self.SourceImageDirName.get()

        tempXMLDir = tempfile.mkdtemp()
        tempGDLDir = tempfile.mkdtemp()
        tempPicDir = tempfile.mkdtemp()  # For every image file, collected
        DestXML.sDestXMLDir = tempXMLDir

        GUIAppSingleton().print("tempXMLDir: %s" % tempXMLDir)
        GUIAppSingleton().print("tempGDLDir: %s" % tempGDLDir)
        GUIAppSingleton().print("tempPicDir: %s" % tempPicDir)

        for sourceXML in SourceXML.replacement_dict.values():
            DestXML(sourceXML)

        for sourceResource in SourceResource.source_pict_dict.values():
            DestResource(sourceResource, tempPicDir if sourceResource.isEncodedImage else tempGDLDir)

        pool_map = [{"dest": DestXML.dest_dict[k],
                     "tempXMLDir": tempXMLDir,
                     "message_queue": message_queue,
                     "process_queue": process_queue,
                     } for k in list(DestXML.dest_dict.keys()) if
                    isinstance(DestXML.dest_dict[k], DestXML)]
        cpuCount = max(mp.cpu_count() - 1, 1)

        p = mp.Pool(processes=cpuCount)
        p.map(processOneXML, pool_map)
        p.close()
        p.join()

        async def process_messages():
            while not message_queue.empty():
                message = await message_queue.get()
                self.print(message)
        await process_messages()

        async def process_icurrent():
            while not process_queue.empty():
                message = await process_queue.get()
                self.iCurrent += message
        await process_icurrent()

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

        # if self.bDebug.get():
        #     # FIXME to JSON
        #     if not self.bCleanup.get():
        #         with open(tempXMLDir + "\dict.txt", "w") as d:
        #             for k in list(DestXML.dest_dict.keys()):
        #                 d.write(
        #                     k + " " + DestXML.dest_dict[k].sourceFile.name + "->" + DestXML.dest_dict[
        #                         k].name + " " + DestXML.dest_dict[k].sourceFile.guid + " -> " +
        #                     DestXML.dest_dict[k].guid + "\n")
        #
        #         with open(tempXMLDir + "\pict_dict.txt", "w") as d:
        #             for k in list(DestResource.pict_dict.keys()):
        #                 d.write(DestResource.pict_dict[k].sourceFile.fullPath + "->" + DestResource.pict_dict[
        #                     k].relPath + "\n")
        #
        #         with open(tempXMLDir + "\id_dict.txt", "w") as d:
        #             for k in list(DestXML.id_dict.keys()):
        #                 d.write(DestXML.id_dict[k] + "\n")

        # check_output(x2lCommand, shell=True)

        result = subprocess.run([os.path.join(self.ACLocation.get(), 'LP_XMLConverter.exe'), "x2l", "-img", self.SourceImageDirName.get(), tempXMLDir, tempGDLDir], capture_output=True, text=True, timeout=100)

        output = result.stdout
        print(output)

        # containerCommand = '"%s" createcontainer "%s" "%s"' % (
        # os.path.join(self.ACLocation.get(), 'LP_XMLConverter.exe'), self.TargetLCFPath.get(),
        # tempGDLDir)

        # if self.bDebug.get():
        # GUIAppSingleton().print("containerCommand Command being executed...")
        # GUIAppSingleton().print(containerCommand)

        # check_output(containerCommand, shell=True)

        result = subprocess.run([os.path.join(self.ACLocation.get(), 'LP_XMLConverter.exe'), "createcontainer",  self.TargetLCFPath.get(), tempGDLDir], capture_output=True, text=True, timeout=1000)
        output = result.stdout
        print(output)

        # cleanup ops
        if self.bCleanup.get():
            shutil.rmtree(tempXMLDir)
            shutil.rmtree(tempPicDir)
        else:
            GUIAppSingleton().print("tempXMLDir: %s" % tempXMLDir)
            GUIAppSingleton().print("tempPicDir: %s" % tempPicDir)

        GUIAppSingleton().print("*****FINISHED SUCCESFULLY******")

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
                    GUIAppSingleton().print("KeyError %s" % f)
                    continue
                except etree.XMLSyntaxError:
                    GUIAppSingleton().print("XMLSyntaxError %s" % f)
                    continue
        except WindowsError:
            pass

    def getConfig(self):
        pass

    def writeConfigBack(self, ):
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


def processOneXML(data):
    dest = data['dest']
    tempDir = data["tempXMLDir"]
    message_queue = data["message_queue"]
    process_queue = data["process_queue"]

    mapping = ParamMappingContainer(GUIAppSingleton().SourceXLSXPath.get())

    src = dest.sourceFile
    srcPath = src.fullPath
    destPath = os.path.join(tempDir, dest.relPath)
    destDir = os.path.dirname(destPath)

    # message_queue.put("%s -> %s" % (srcPath, destPath,))
    async def update_message():
        await message_queue.put("%s -> %s" % (srcPath, destPath,))
    asyncio.run(update_message())

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
    # asyncio.run(process_queue.put(1))
    async def update_iCurrent():
        await process_queue.put(1)
    asyncio.run(update_iCurrent())


if __name__ == "__main__":
    app = GUIAppSingleton()
    # app.top.protocol("WM_DELETE_WINDOW", app.writeConfigBack)
    app.mainloop()

