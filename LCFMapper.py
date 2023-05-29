#!C:\Program Files\Python27amd64\python.exe
# -*- coding: utf-8 -*-
#HOTFIXREQ if image dest folder is retained, remove common images from it
#HOTFIXREQ ImportError: No module named googleapiclient.discovery
#HOTFIXREQ unicode error when running ac command in path with native characters
#HOTFIXREQ SOURCE_IMAGE_DIR_NAME images are not renamed at all
#FIXME renaming errors and param csv parameter overwriting
#FIXME append param to the end when no argument for position
#FIXME library_images copy always as temporary folder; instead junction
#FIXME param editor should offer auto param inserting from Listing Parameters Google Spreadsheet
#FIXME automatic checking and warning of (collected) old project's names
#FIXME UI process messages
#FIXME MigrationTable progressing
#FIXME GDLPict progressing

import os.path
from os import listdir
import tempfile
from subprocess import check_output
import shutil

import tkinter as tk
import tkinter.filedialog

from configparser import *  #FIXME not *
import csv

import pip
import multiprocessing as mp

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
        tk.Frame.__init__(self)
        self.top = self.winfo_toplevel()

        self.warnings = []

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

        self.warnings = []

        self.bo                 = None
        self.googleSpreadsheet  = None
        self.bWriteToSelf       = False             # Whether to write back to the file itself

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

        self.warnings = []

        # GUI itself----------------------------------------------------------------------------------------------------

        iF = 0

        InputDirPlusText(self.top, "XLSX name", self.SourceXLSXPath, row=iF, func=tkinter.filedialog.askopenfilename, title="Select file", tooltip="Path of the .xlsx file that describes the conversion")

        iF += 1

        InputDirPlusText(self.top, "XML Source folder", self.SourceXMLDirName, row=iF, tooltip='Path of the folder where extracted .lcf file structure is')

        iF += 1

        InputDirPlusText(self.top, "Images' source folder", self.SourceImageDirName, row=iF, tooltip="Path of image folder that is the result of extractontainer 's -img switch, for encoded images")

        iF += 1

        # InputDirPlusText(self.top, "LCF Source path", self.TargetLCFPath, "LCF Source path", row=iF, func=tkinter.filedialog.askopenfilename, title="Select file")

        # iF += 1

        InputDirPlusText(self.top, "LCF Destination path", self.TargetLCFPath, "LCF Destination path", row=iF, func=tkinter.filedialog.asksaveasfilename, title="Select file")

        iF += 1

        InputDirPlusText(self.top, "ArchiCAD location",  self.ACLocation, "ArchiCAD location", row=iF)

        iF += 1

        self.bottomFrame        = tk.Frame(self.top, )
        self.bottomFrame.grid({"row":iF, "column": 0, "columnspan": 7, "sticky":  tk.S + tk.N, })

        iC = 0

        self.startButton        = tk.Button(self.bottomFrame, {"text": "Start", "command": self.start})
        self.startButton.grid({"row": 0, "column": iC, "sticky": tk.E}); iC += 1
        CreateToolTip(self.startButton, "Start conversion")

        self.debugCheckButton   = tk.Checkbutton(self.bottomFrame, {"text": "Debug", "variable": self.bDebug})
        self.debugCheckButton.grid({"row": 0, "column": iC}); iC += 1
        CreateToolTip(self.debugCheckButton, "Print out debug info")

        self.cleanupCheckButton   = tk.Checkbutton(self.bottomFrame, {"text": "Cleanup", "variable": self.bCleanup})
        self.cleanupCheckButton.grid({"row": 0, "column": iC}); iC += 1
        CreateToolTip(self.cleanupCheckButton, "Delete temporary files after conversion")

    @staticmethod
    def clear_data():
        DestXML.dest_dict.clear()
        DestXML.dest_sourcenames.clear()
        SourceXML.replacement_dict.clear()
        DestXML.id_dict.clear()
        DestResource.pict_dict.clear()

    def start(self):
        """
        :return:
        """
        self.clear_data()

        print ("Starting conversion")
        SourceXML.sSourceXMLDir = self.SourceXMLDirName.get()
        SourceResource.sSourceResourceDir = self.SourceImageDirName.get()

        self.scanDirs(SourceXML.sSourceXMLDir)
        self.scanDirs(SourceResource.sSourceResourceDir)

        tempDir = tempfile.mkdtemp()
        tempGDLDir = tempfile.mkdtemp()
        tempPicDir = tempfile.mkdtemp()  # For every image file, collected

        print("tempDir: %s" % tempDir)
        print("tempGDLDir: %s" % tempGDLDir)
        print("tempPicDir: %s" % tempPicDir)

        for sourceXML in SourceXML.replacement_dict.values():
            DestXML(sourceXML, DestXML.sDestXMLDir)

        for sourceResource in SourceResource.source_pict_dict.values():
            DestResource(sourceResource, tempPicDir if sourceResource.isEncodedImage else tempGDLDir)

        pool_map = [{"dest": DestXML.dest_dict[k],
                     "tempDir": tempDir,
                     } for k in list(DestXML.dest_dict.keys()) if
                    isinstance(DestXML.dest_dict[k], DestXML)]
        cpuCount = max(mp.cpu_count() - 1, 1)

        p = mp.Pool(processes=cpuCount)
        p.map(processOneXML, pool_map)

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

        x2lCommand = '"%s" x2l -img "%s" "%s" "%s"' % (os.path.join(self.ACLocation.get(), 'LP_XMLConverter.exe'), self.SourceImageDirName.get(), tempDir, tempGDLDir)

        if self.bDebug.get():
            # FIXME to JSON
            print("x2l Command being executed...")
            print(x2lCommand)
            if not self.bCleanup.get():
                with open(tempDir + "\dict.txt", "w") as d:
                    for k in list(DestXML.dest_dict.keys()):
                        d.write(
                            k + " " + DestXML.dest_dict[k].sourceFile.name + "->" + DestXML.dest_dict[
                                k].name + " " + DestXML.dest_dict[k].sourceFile.guid + " -> " +
                            DestXML.dest_dict[k].guid + "\n")

                with open(tempDir + "\pict_dict.txt", "w") as d:
                    for k in list(DestResource.pict_dict.keys()):
                        d.write(DestResource.pict_dict[k].sourceFile.fullPath + "->" + DestResource.pict_dict[
                            k].relPath + "\n")

                with open(tempDir + "\id_dict.txt", "w") as d:
                    for k in list(DestXML.id_dict.keys()):
                        d.write(DestXML.id_dict[k] + "\n")

        check_output(x2lCommand, shell=True)

        containerCommand = '"%s" createcontainer "%s" "%s"' % (
        os.path.join(self.ACLocation.get(), 'LP_XMLConverter.exe'), self.TargetLCFPath.get(),
        tempGDLDir)

        if self.bDebug.get():
            print("containerCommand Command being executed...")
            print(containerCommand)

        check_output(containerCommand, shell=True)

        # cleanup ops
        if not self.bCleanup.get():
            shutil.rmtree(tempDir)
            shutil.rmtree(tempPicDir)
        else:
            print("tempDir: %s" % tempDir)
            print("tempPicDir: %s" % tempPicDir)

        print("*****FINISHED SUCCESFULLY******")

    def scanDirs(self, p_sRootFolder, p_sCurrentFolder='', p_acceptedFormatS=(".XML",)):
        """
        only scanning input dir recursively to set up xml and image files' list
        :param p_sRootFolder:
        :param p_sCurrentFolder:
        :param p_acceptedFormatS:
        :return:
        """
        try:
            path_join = os.path.join(p_sRootFolder, p_sCurrentFolder)
            for f in listdir(path_join):
                try:
                    src = os.path.join(p_sRootFolder, p_sCurrentFolder, f)
                    if not os.path.isdir(src):
                    # if it IS NOT a folder
                        if os.path.splitext(os.path.basename(f))[1].upper() in p_acceptedFormatS:
                            SourceXML(os.path.join(p_sCurrentFolder, f))
                        else:
                            # set up replacement dict for other files
                            if os.path.splitext(os.path.basename(f))[0].upper() not in SourceResource.source_pict_dict:
                                sI = SourceResource(os.path.join(p_sCurrentFolder, f), p_sBasePath=p_sRootFolder)
                                if SourceResource.sSourceResourceDir in sI.fullPath and SourceResource.sSourceResourceDir:
                                    sI.isEncodedImage = True
                    else:
                    # if it IS a folder
                        self.scanDirs(p_sRootFolder, os.path.join(p_sCurrentFolder, f))
                except KeyError:
                    print("KeyError %s" % f)
                    continue
                except etree.XMLSyntaxError:
                    print("XMLSyntaxError %s" % f)
                    continue
        except WindowsError:
            pass

    def writeConfigBack(self, ):
        # FIXME encrypting of sensitive data

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
        self.top.destroy()


def processOneXML(p_Data):
    dest = p_Data['dest']
    tempDir = p_Data["tempDir"]
    mapping = ParamMappingContainer(GUIAppSingleton().SourceXLSXPath.get())

    src = dest.sourceFile
    srcPath = src.fullPath
    destPath = os.path.join(tempDir, dest.relPath)
    destDir = os.path.dirname(destPath)

    print("%s -> %s" % (srcPath, destPath,))

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


def main():
    app = GUIAppSingleton()
    app.top.protocol("WM_DELETE_WINDOW", app.writeConfigBack)
    app.top.mainloop()

if __name__ == "__main__":
    main()

