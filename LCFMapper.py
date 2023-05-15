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

import openpyxl as opx


class ParamMapping:
    def __init__(self, p_iType, p_row):
        self._type = p_iType
        self._files = str.split(p_row[_A_].value, ";") if p_row[_A_].value else []
        self._paramName = p_row[_B_].value
        self._paramDesc = p_row[_C_].value
        self._from = p_row[_D_].value
        self._to = p_row[_F_].value

PARAM_TYPES = {
    'Pens':         PAR_PEN,
    'Fills':        PAR_FILL,
    'Linetypes':    PAR_LINETYPE,
    'Surfaces':     PAR_MATERIAL,
    'Strings':      PAR_STRING,
    'Booleans':     PAR_BOOL,
    'Integers':     PAR_INT,
}
class ParamMappingContainer:
    def __init__(self, p_sXLSX):
        self._mappingList = []

        wb = opx.load_workbook(p_sXLSX.get())
        for _sheetName, _paramType in PARAM_TYPES.items():
            try:
                _sheet = wb[_sheetName]
            except KeyError:
                continue
            for row in _sheet.iter_rows(min_row=2):
                self._mappingList.append(ParamMapping(_paramType, row))

    def applyParams(self, p_parSect, p_fileName):
        for mapping in self._mappingList:
            if not mapping._files or p_fileName in mapping._files:
                params = p_parSect.getParamsByTypeNameAndValue(mapping._type, mapping._paramName, mapping._paramDesc, mapping._from)
                for par in params:
                    par.value = mapping._to


#----------------- gui classes -----------------------------------------------------------------------------------------

class CreateToolTip:
    def __init__(self, widget, text='widget info'):
        self.waittime = 500
        self.wraplength = 180
        self.widget = widget
        self.text = text

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
        # creates a toplevel window
        self.tw = tk.Toplevel(self.widget)
        # Leaves only the label and removes the app window
        self.tw.wm_overrideredirect(True)
        self.tw.wm_geometry("+%d+%d" % (x, y))
        label = tk.Label(self.tw, text=self.text, justify='left',
                       background="#ffffff", relief='solid', borderwidth=1,
                       wraplength = self.wraplength)
        label.pack(ipadx=1)

    def hidetip(self):
        tw = self.tw
        self.tw = None
        if tw:
            tw.destroy()


class InputDirPlusText:
    def __init__(self, top, text, target, tooltip='', row=0, column=0, func=tkinter.filedialog.askdirectory, title="Select folder"):
        self.target = target
        self.filename = ''
        self._frame = tk.Frame(top)
        self._frame.grid({"row": row, "column": column})

        self._frame.columnconfigure(1, weight=1)

        self.buttonDirName = tk.Button(self._frame, {"text": text, "command": self.getFunc(func, title) })
        self.buttonDirName.grid({"sticky": tk.W + tk.E, "row": 0, "column": 0, })

        self.entryName = tk.Entry(self._frame, {"width": 30, "textvariable": target})
        self.entryName.grid({"row": 0, "column": 1, "sticky": tk.E + tk.W, })

        if tooltip:
            CreateToolTip(self._frame, tooltip)

    def getFunc(self, func, title):
        def inputDirName():
            self.filename = func(initialdir="/", title=title)
            self.target.set(self.filename)
            self.entryName.delete(0, tk.END)
            self.entryName.insert(0, self.filename)
        return inputDirName

# https://stackoverflow.com/questions/12305142/issue-with-singleton-python-call-two-times-init
def singleton(cls):
    instances = {}
    def getinstance():
        if cls not in instances:
            instances[cls] = cls()
        return instances[cls]
    return getinstance

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


        self.SourceGDLDirName   = tk.StringVar()
        self.TargetXMLDirName   = tk.StringVar()

        self.TargetImageDirName = tk.StringVar()
        self.AdditionalImageDir = tk.StringVar()

        self.ImgStringFrom      = tk.StringVar()
        self.ImgStringTo        = tk.StringVar()

        self.StringFrom         = tk.StringVar()
        self.StringTo           = tk.StringVar()

        self.fileName           = tk.StringVar()
        self.proDatURL          = tk.StringVar()
        self.DestItem           = None

        self.bCheckParams       = tk.BooleanVar()
        self.bDebug             = tk.BooleanVar()
        self.bCleanup           = tk.BooleanVar()
        self.bOverWrite         = tk.BooleanVar()
        self.bAddStr            = tk.BooleanVar()
        self.doBOUpdate         = tk.BooleanVar()

        self.bXML               = tk.BooleanVar()
        self.bGDL               = tk.BooleanVar()
        self.isSourceGDL        = tk.BooleanVar()

        self.observer  = None
        self.observer2 = None

        self.warnings = []

        self.bo                 = None
        self.googleSpreadsheet  = None
        self.bWriteToSelf       = False             # Whether to write back to the file itself

        __tooltipIDPT1 = "Something like E:/_GDL_SVN/_TEMPLATE_/AC18_Opening/library"
        __tooltipIDPT2 = "Images' dir that are NOT to be renamed per project and compiled into final gdls (prev pics, for example), something like E:\_GDL_SVN\_TEMPLATE_\AC18_Opening\library_images"
        __tooltipIDPT3 = "Something like E:/_GDL_SVN/_TARGET_PROJECT_NAME_/library"
        __tooltipIDPT4 = "Final GDL output dir"
        __tooltipIDPT5 = "If set, copy project specific pictures here, too, for endcoded images. Something like E:/_GDL_SVN/_TARGET_PROJECT_NAME_/library_images"
        __tooltipIDPT6 = "Additional images' dir, for all other images, which can be used by any projects, something like E:/_GDL_SVN/_IMAGES_GENERIC_"
        __tooltipIDPT7 = "Source GDL folder name"

        try:
            for cName, cValue in self.currentConfig.items('ArchiCAD'):
                try:
                    if   cName == 'bgdl':               self.bGDL.set(cValue)
                    elif cName == 'xmltargetdirname':   self.TargetXMLDirName.set(cValue)

                    elif cName == 'bxml':               self.bXML.set(cValue)
                    elif cName == 'bdebug':             self.bDebug.set(cValue)
                    elif cName == 'additionalimagedir': self.AdditionalImageDir.set(cValue)
                    elif cName == 'stringto':           self.StringTo.set(cValue)
                    elif cName == 'stringfrom':         self.StringFrom.set(cValue)
                    elif cName == 'inputimagetarget':   self.TargetImageDirName.set(cValue)
                    elif cName == 'imgstringfrom':      self.ImgStringFrom.set(cValue)
                    elif cName == 'imgstringto':        self.ImgStringTo.set(cValue)

                    elif cName == 'baddstr':            self.bAddStr.set(cValue)
                    elif cName == 'boverwrite':         self.bOverWrite.set(cValue)
                    elif cName == 'allkeywords':
                        XMLFile.all_keywords |= set(v.strip() for v in cValue.split(',') if v !='')

                    elif cName == 'aclocation':         self.ACLocation.set(cValue)
                    elif cName == 'inputimagesource':   self.SourceImageDirName.set(cValue)
                    elif cName == 'sourcedirname':      self.SourceXMLDirName.set(cValue)
                    elif cName == 'sourcexlsxpath':      self.SourceXLSXPath.set(cValue)
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

        InputDirPlusText(self.top, "XLSX name", self.SourceXLSXPath, row=iF, func=tkinter.filedialog.askopenfilename, title="Select file")

        iF += 1

        InputDirPlusText(self.top, "XML Source folder", self.SourceXMLDirName, row=iF)

        iF += 1

        InputDirPlusText(self.top, "Images' source folder", self.SourceImageDirName, "Images' source folder", row=iF)

        iF += 1

        # InputDirPlusText(self.top, "LCF Source path", self.TargetLCFPath, "LCF Source path", row=iF, func=tkinter.filedialog.askopenfilename, title="Select file")

        # iF += 1

        InputDirPlusText(self.top, "LCF Destination path", self.TargetLCFPath, "LCF Destination path", row=iF, func=tkinter.filedialog.asksaveasfilename, title="Select file")

        iF += 1

        InputDirPlusText(self.top, "ArchiCAD location",  self.ACLocation, "ArchiCAD location", row=iF)

        iF += 1

        self.bottomFrame        = tk.Frame(self.top, )
        self.bottomFrame.grid({"row":iF, "column": 0, "columnspan": 7, "sticky":  tk.S + tk.N, })

        iF += 1

        self.startButton        = tk.Button(self.bottomFrame, {"text": "Start", "command": self.start})
        self.startButton.grid({"row": 0, "column": 0, "sticky": tk.E})

    def createDestItems(self, inList):
        firstRow = inList[0]

        for row in inList[1:]:
            if firstRow[1] == "":
                #empty header => row[1] is for destItem
                destItem = self.addFileRecursively(row[0], row[1])

            else:
                #no destitem so write to itself
                destItem = DestXML(row[0], targetFileName=row[0])
                DestXML.dest_dict[destItem.name.upper()] = destItem
                DestXML.dest_sourcenames.add(destItem.sourceFile.name)
            if len(row) > 2 and next((c for c in row[2:] if c != ""), ""):
                for parName, col in zip(firstRow[2:], row[2:]):
                    destItem.parameters.createParamfromCSV(parName, col)

    def paramWrite(self):
        """
        This method should write params directly into selected .GSMs/.XLSs
        (source and destination is the same)
        :return:
        """
        self.bWriteToSelf = True
        self.XMLDir.config(state=tk.DISABLED)
        self.LCFPath.config(state=tk.DISABLED)
        self.showGoogleSpreadsheetEntry(inFunc=self.getListFromGoogleSpreadsheet)

    def getFromCSV(self):
        """
        Source-dest file conversation based on csv
        :return:
        """
        SRC_NAME    = 0
        TARG_NAME   = 1
        PRODATURL   = 2
        VALUES      = 3
        csvFileName = tkinter.filedialog.askopenfilename(initialdir="/", title="Select folder", filetypes=(("CSV files", "*.csv"), ("all files","*.*")))
        if csvFileName:
            with open(csvFileName, "r") as csvFile:
                firstRow = next(csv.reader(csvFile))
                for row in csv.reader(csvFile):
                    destItem = self.addFileRecursively(row[SRC_NAME], row[TARG_NAME])
                    if row[PRODATURL]:
                        destItem.parameters.BO_update(row[PRODATURL])
                    if len(row) > 3 and next((c for c in row[PRODATURL:] if c != ""), ""):
                        for parName, col in zip(firstRow[VALUES:], row[VALUES:]):
                            if "-y" in parName or "-array" in parName:
                                arrayValues = []
                                with open(col, "r") as arrayCSV:
                                    for arrayRow in csv.reader(arrayCSV):
                                        if arrayRow[TARG_NAME].strip() == row[TARG_NAME].strip:
                                            arrayValues = [[arrayRow[2:]]]
                                        if arrayValues \
                                                and len(arrayRow) > 2 \
                                                and not arrayRow[TARG_NAME] \
                                                and arrayRow[2] != "":
                                            arrayValues += [arrayRow[2:]]
                                        else:
                                            break
                                destItem.parameters.createParamfromCSV(parName, col, arrayValues)
                            else:
                                destItem.parameters.createParamfromCSV(parName, col)

    def convertFilesGoogleSpreadsheet(self):
        """
        Source-dest file conversation based on Google Spreadsheet
        :return:
        """
        self.showGoogleSpreadsheetEntry()

    def setACLoc(self):
        ACLoc = tkinter.filedialog.askdirectory(initialdir="/", title="Select ArchiCAD folder")
        self.ACLocation.set(ACLoc)

    def setAdditionalImageDir(self):
        AIDLoc = tkinter.filedialog.askdirectory(initialdir="/", title="Select additional images' folder")
        self.AdditionalImageDir.set(AIDLoc)

    def processGDLDir(self, *_):
        '''
        When self.SourceGDLDirName is modified, convert files to xml and set ui accordingly
        :return:
        '''
        # global SourceXMLDirName, SourceImageDirName
        if not self.SourceGDLDirName.get():
            return
        self.tempXMLDir = tempfile.mkdtemp()
        self.tempImgDir = tempfile.mkdtemp()
        print("tempXMLDir: %s" % self.tempXMLDir)
        print("tempImgDir: %s" % self.tempImgDir)
        print("SourceGDLDirName %s" % self.SourceGDLDirName.get())
        l2xCommand = '"%s" l2x -img "%s" "%s" "%s"' % (os.path.join(self.ACLocation.get(), 'LP_XMLConverter.exe'), self.tempImgDir, self.SourceGDLDirName.get(), self.tempXMLDir)
        print("l2xCommand: %s" % l2xCommand)
        check_output(l2xCommand, shell=True)
        # self.inputXMLDir.idpt.entryDirName.config(cnf={'state': tk.NORMAL})
        self.sourceImageDir.entryName.config(cnf={'state': tk.NORMAL})
        self.sourceImageDir.buttonDirName.config(cnf={'state': tk.NORMAL})
        self.SourceXMLDirName.set(self.tempXMLDir)
        self.SourceImageDirName.set(self.tempImgDir)
        # self.inputXMLDir.idpt.entryDirName.config(cnf={'state': tk.DISABLED})
        self.sourceImageDir.entryName.config(cnf={'state': tk.DISABLED})
        self.sourceImageDir.buttonDirName.config(cnf={'state': tk.DISABLED})

    def targetGDLModified(self, *_):
        if not self.bGDL.get():
            self.bXML.set(True)

    def targetXMLModified(self, *_):
        if not self.bXML.get():
            self.bGDL.set(True)

    def sourceGDLModified(self, *_):
        if not self.bGDL.get():
            self.bXML.set(True)
            self.LCFPath.idpt.entryName.config(state=tk.DISABLED)
        else:   self.LCFPath.idpt.entryName.config(state=tk.NORMAL)

    def sourceXMLModified(self, *_):
        if not self.bXML.get():
            self.bGDL.set(True)
            self.XMLDir.idpt.entryName.config(state=tk.DISABLED)
        else:   self.XMLDir.idpt.entryName.config(state=tk.NORMAL)

    def start(self):
        """
        :return:
        """
        print ("Starting conversion")
        SourceXML.sSourceXMLDir = self.SourceXMLDirName.get()
        DestXML.sTargetXMLDir = self.TargetXMLDirName.get()
        DestXML.bOverWrite =  False     #self.bOverWrite.get()
        SourceImage.sSourceImageDir = self.SourceImageDirName.get()

        self.scanDirs(self.SourceXMLDirName.get())

        for sourceFileName in SourceXML.replacement_dict.keys():
            destItem = DestXML(SourceXML.replacement_dict[sourceFileName.upper()],
                               targetFileName=sourceFileName)
            DestXML.dest_dict[destItem.name.upper()] = destItem
            DestXML.dest_sourcenames.add(destItem.sourceFile.name)

        tempdir = tempfile.mkdtemp()

        targGDLDir = tempfile.mkdtemp()

        targPicDir = self.TargetImageDirName.get()  # For target library's encoded images
        tempPicDir = tempfile.mkdtemp()  # For every image file, collected

        print("tempdir: %s" % tempdir)
        print("tempPicDir: %s" % tempPicDir)

        pool_map = [{"dest": DestXML.dest_dict[k],
                     "tempdir": tempdir,
                     "bOverWrite": self.bOverWrite.get(),
                     "StringTo": self.StringTo.get(),
                     "pict_dict": DestImage.pict_dict,
                     "dest_dict": DestXML.dest_dict,
                     } for k in list(DestXML.dest_dict.keys()) if
                    isinstance(DestXML.dest_dict[k], DestXML)]
        cpuCount = max(mp.cpu_count() - 1, 1)

        p = mp.Pool(processes=cpuCount)
        p.map(processOneXML, pool_map)

        _picdir = self.AdditionalImageDir.get()  # Like IMAGES_GENERIC

        if _picdir:
            for f in listdir(_picdir):
                shutil.copytree(os.path.join(_picdir, f), os.path.join(tempPicDir, f))

        for f in list(DestImage.pict_dict.keys()):
            if DestImage.pict_dict[f].sourceFile.isEncodedImage:
                try:
                    shutil.copyfile(os.path.join(self.SourceImageDirName.get(),
                                                 DestImage.pict_dict[f].sourceFile.relPath),
                                    os.path.join(tempPicDir, DestImage.pict_dict[f].relPath))
                except IOError:
                    os.makedirs(os.path.join(tempPicDir, DestImage.pict_dict[f].dirName))
                    shutil.copyfile(os.path.join(self.SourceImageDirName.get(),
                                                 DestImage.pict_dict[f].sourceFile.relPath),
                                    os.path.join(tempPicDir, DestImage.pict_dict[f].relPath))

                if targPicDir:
                    try:
                        shutil.copyfile(os.path.join(self.SourceImageDirName.get(),
                                                     DestImage.pict_dict[f].sourceFile.relPath),
                                        os.path.join(targPicDir, DestImage.pict_dict[f].relPath))
                    except IOError:
                        os.makedirs(os.path.join(targPicDir, DestImage.pict_dict[f].dirName))
                        shutil.copyfile(os.path.join(self.SourceImageDirName.get(),
                                                     DestImage.pict_dict[f].sourceFile.relPath),
                                        os.path.join(targPicDir, DestImage.pict_dict[f].relPath))
            else:
                if targGDLDir:
                    try:
                        shutil.copyfile(DestImage.pict_dict[f].sourceFile.fullPath,
                                        os.path.join(targGDLDir, DestImage.pict_dict[f].relPath))
                    except IOError:
                        os.makedirs(os.path.join(targGDLDir, DestImage.pict_dict[f].dirName))
                        shutil.copyfile(DestImage.pict_dict[f].sourceFile.fullPath,
                                        os.path.join(targGDLDir, DestImage.pict_dict[f].relPath))

                if self.TargetXMLDirName.get():
                    try:
                        shutil.copyfile(DestImage.pict_dict[f].sourceFile.fullPath,
                                        os.path.join(self.TargetXMLDirName.get(),
                                                     DestImage.pict_dict[f].relPath))
                    except IOError:
                        os.makedirs(os.path.join(self.TargetXMLDirName.get(),
                                                 DestImage.pict_dict[f].dirName))
                        shutil.copyfile(DestImage.pict_dict[f].sourceFile.fullPath,
                                        os.path.join(self.TargetXMLDirName.get(),
                                                     DestImage.pict_dict[f].relPath))

        x2lCommand = '"%s" x2l -img "%s" "%s" "%s"' % (
        os.path.join(self.ACLocation.get(), 'LP_XMLConverter.exe'),
        self.SourceImageDirName.get(), tempdir, targGDLDir)
        print("x2l Command being executed...")
        print(x2lCommand)

        if self.bWriteToSelf:
            tempGDLArchiveDir = tempfile.mkdtemp()
            print("GDL's archive dir: %s" % tempGDLArchiveDir)
            for k in list(DestXML.dest_dict.keys()):
                os.rename(k.sourceFile.fullPath, os.path.join(tempGDLArchiveDir, k.sourceFile.relPath))
                os.rename(os.path.join(targGDLDir, k.sourceFile.relPath), k.sourceFile.fullPath)

        if self.bDebug.get():
            print("ac command:")
            print(x2lCommand)
            with open(tempdir + "\dict.txt", "w") as d:
                for k in list(DestXML.dest_dict.keys()):
                    d.write(
                        k + " " + DestXML.dest_dict[k].sourceFile.name + "->" + DestXML.dest_dict[
                            k].name + " " + DestXML.dest_dict[k].sourceFile.guid + " -> " +
                        DestXML.dest_dict[k].guid + "\n")

            with open(tempdir + "\pict_dict.txt", "w") as d:
                for k in list(DestImage.pict_dict.keys()):
                    d.write(DestImage.pict_dict[k].sourceFile.fullPath + "->" + DestImage.pict_dict[
                        k].relPath + "\n")

            with open(tempdir + "\id_dict.txt", "w") as d:
                for k in list(DestXML.id_dict.keys()):
                    d.write(DestXML.id_dict[k] + "\n")

        check_output(x2lCommand, shell=True)

        containerCommand = '"%s" createcontainer "%s" "%s"' % (
        os.path.join(self.ACLocation.get(), 'LP_XMLConverter.exe'), self.TargetLCFPath.get(),
        targGDLDir)
        print("containerCommand Command being executed...")
        print(containerCommand)

        check_output(containerCommand, shell=True)

        # cleanup ops
        if not self.bCleanup.get():
            shutil.rmtree(tempPicDir)
            if not self.bXML:
                shutil.rmtree(tempdir)
        else:
            print("tempdir: %s" % tempdir)
            print("tempPicDir: %s" % tempPicDir)

        print("*****FINISHED SUCCESFULLY******")

    def addFile(self, sourceFileName='', targetFileName=''):
        if not sourceFileName:
            sourceFileName = self.listBox.get(tk.ACTIVE)
        if sourceFileName.startswith(LISTBOX_SEPARATOR):
            self.listBox.select_clear(tk.ACTIVE)
            return
        if sourceFileName.upper() in SourceXML.replacement_dict:
            if targetFileName:
                destItem = DestXML(SourceXML.replacement_dict[sourceFileName.upper()], targetFileName=targetFileName)
            else:
                destItem = DestXML(SourceXML.replacement_dict[sourceFileName.upper()], self.StringFrom.get(), self.StringTo.get())
            DestXML.dest_dict[destItem.name.upper()] = destItem
            DestXML.dest_sourcenames.add(destItem.sourceFile.name)
        else:
            #File should be in library_additional, possibly worth of checking it or add a warning
            return
        self.refreshDestItem()
        return destItem

    def addMoreFiles(self):
        for sourceFileIndex in self.listBox.curselection():
            self.addFile(sourceFileName=self.listBox.get(sourceFileIndex))

    def addImageFile(self, fileName=''):
        if not fileName:
            fileName = self.listBox2.get(tk.ACTIVE)
        if not fileName.upper() in DestImage.pict_dict and not fileName.startswith(LISTBOX_SEPARATOR):
            destItem = DestImage(SourceImage.source_pict_dict[fileName.upper()])
            DestImage.pict_dict[destItem.fileNameWithExt.upper()] = destItem
        self.refreshDestItem()

    def addAllFiles(self):
        for filename in self.listBox.get(0, tk.END):
            self.addFile(filename)

        for imageFileName in self.listBox2.get(0, tk.END):
            self.addImageFile(imageFileName)

        self.addAllButton.config({"state": tk.DISABLED})

    def addFileRecursively(self, sourceFileName='', targetFileName=''):
        if not sourceFileName:
            sourceFileName = self.listBox.get(tk.ACTIVE)

        destItem = self.addFile(sourceFileName, targetFileName)

        if sourceFileName.upper() not in SourceXML.replacement_dict:
            #should be in library_additional
            return

        x = SourceXML.replacement_dict[sourceFileName.upper()]

        for k, v in x.calledMacros.items():
            if v not in DestXML.dest_sourcenames:
                self.addFileRecursively(v)

        for parentGUID in x.parentSubTypes:
            if parentGUID not in DestXML.id_dict:
                if parentGUID in SourceXML.source_guids:
                    self.addFileRecursively(SourceXML.source_guids[parentGUID])

        for pict in list(SourceImage.source_pict_dict.values()):
            for script in list(x.scripts.values()):
                if pict.fileNameWithExt.upper() in script or pict.fileNameWithOutExt.upper() in script.upper():
                    self.addImageFile(pict.fileNameWithExt)
            if pict.fileNameWithExt.upper() in x.gdlPicts:
                self.addImageFile(pict.fileNameWithExt)

        if x.prevPict:
            bN = os.path.basename(x.prevPict)
            self.addImageFile(bN)

        self.refreshDestItem()
        return destItem

    def addMoreFilesRecursively(self):
        for sourceFileIndex in self.listBox.curselection():
            self.addFileRecursively(sourceFileName=self.listBox.get(sourceFileIndex))

    def delFile(self, fileName = ''):
        if not fileName:
            fileName = self.listBox3.get(tk.ACTIVE)
        if fileName.startswith(LISTBOX_SEPARATOR):
            self.listBox3.select_clear(tk.ACTIVE)
            return

        fN = self.__unmarkFileName(fileName).upper()
        del DestXML.dest_sourcenames [ DestXML.dest_dict[fN].sourceFile.name ]
        del DestXML.dest_dict[fN]
        self.listBox3.refresh()
        if not DestXML.dest_dict and not DestImage.pict_dict:
            self.addAllButton.config({"state": tk.NORMAL})
        self.fileName.set('')

    def resetAll(self):
        self.XMLDir.config(state=tk.NORMAL)
        self.LCFPath.config(state=tk.NORMAL)

        DestXML.dest_dict.clear()
        DestXML.dest_sourcenames.clear()
        SourceXML.replacement_dict.clear()
        DestXML.id_dict.clear()
        SourceXML.source_guids.clear()
        DestImage.pict_dict.clear()
        SourceImage.source_pict_dict.clear()

        self.listBox.refresh()
        self.listBox2.refresh()
        self.listBox3.refresh()
        self.listBox4.refresh()

        for w in self.warnings:
            w.destroy()

        self.addAllButton.config({"state": tk.NORMAL})
        self.sourceImageDir.entryName.config(cnf={'state': tk.NORMAL})
        self.sourceImageDir.buttonDirName.config(cnf={'state': tk.NORMAL})

    def listboxselect(self, event, ):
        if not event.widget.get(0):
            return
        if event.widget.get(event.widget.curselection()[0]).startswith(LISTBOX_SEPARATOR):
            return

        currentSelection = event.widget.get(int(event.widget.curselection()[0])).upper()
        if currentSelection[:2] == "* ":
            currentSelection = currentSelection[2:]
        self.destItem = DestXML.dest_dict[currentSelection]
        self.selectedName = currentSelection

        if self.observer:
            self.fileName.trace_vdelete("w", self.observer)
        if self.observer2:
            self.proDatURL.trace_vdelete("w", self.observer2)

        self.fileName.set(self.destItem.name)
        self.observer = self.fileName.trace_variable("w", self.modifyDestItem)

        for w in self.warnings:
            w.destroy()
        self.warnings = [tk.Label(self.warningFrame, {"text": w}) for w in self.destItem.warnings]
        for w, n in zip(self.warnings, list(range(len(self.warnings)))):
            w.grid({"row": n, "sticky": tk.W})
            #FIXME wrong

    def listboxImageSelect(self, event):
        self.destItem = DestImage.pict_dict[event.widget.get(int(event.widget.curselection()[0])).upper()]
        self.selectedName = event.widget.get(int(event.widget.curselection()[0])).upper()

        if self.observer:
            self.fileName.trace_vdelete("w", self.observer)
        self.fileName.set(self.destItem.fileNameWithExt)
        self.observer = self.fileName.trace_variable("w", self.modifyDestImageItem)

    def modifyDestImageItem(self, *_):
        self.destItem.fileNameWithExt = self.fileName.get()
        self.destItem.name = self.destItem.fileNameWithExt
        DestImage.pict_dict[self.destItem.fileNameWithExt.upper()] = self.destItem

        del DestImage.pict_dict[self.selectedName.upper()]
        self.selectedName = self.destItem.fileNameWithExt

        self.destItem.refreshFileNames()
        self.refreshDestItem()

    def modifyDestItem(self, *_):
        fN = self.fileName.get().upper()
        if fN and fN not in DestXML.dest_dict:
            self.destItem.name = self.fileName.get()
            DestXML.dest_dict[fN] = self.destItem
            del DestXML.dest_dict[self.selectedName.upper()]
            self.selectedName = self.destItem.name

            self.destItem.refreshFileNames()
            self.refreshDestItem()

    def refreshDestItem(self):
        self.listBox3.refresh()
        self.listBox4.refresh()

    def writeConfigBack(self):
        currentConfig = RawConfigParser()
        currentConfig.add_section("ArchiCAD")
        currentConfig.set("ArchiCAD", "sourcexlsxpath", self.SourceXLSXPath.get())
        currentConfig.set("ArchiCAD", "sourcedirname", self.SourceXMLDirName.get())
        currentConfig.set("ArchiCAD", "inputimagesource",   self.SourceImageDirName.get())
        currentConfig.set("ArchiCAD", "targetlcfpath",   self.TargetLCFPath.get())
        currentConfig.set("ArchiCAD", "aclocation",         self.ACLocation.get())
        currentConfig.set("ArchiCAD", "bdebug",             self.bDebug.get())

        with open(os.path.join(self.appDataDir, "LCFMapper.ini"), 'w') as configFile:
            #FIXME proper config place
            try:
                currentConfig.write(configFile)
            except UnicodeEncodeError:
                #FIXME
                pass
        self.top.destroy()

    def reconnect(self):
        #FIXME
        '''Meaningful when overwriting XMLs:
        '''
        pass

    @staticmethod
    def __unmarkFileName(inFileName):
        '''removes remarks form on the GUI displayed filenames, like * at the beginning'''
        if inFileName.upper() in GUIAppSingleton().dest_dict:
            return inFileName
        elif inFileName[:2] == '* ':
            if inFileName[2:].upper() in GUIAppSingleton().dest_dict:
                return inFileName [2:]

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
                            if os.path.splitext(os.path.basename(f))[
                                0].upper() not in SourceImage.source_pict_dict:
                                sI = SourceImage(os.path.join(p_sCurrentFolder, f))
                                SIDN = self.SourceImageDirName.get()
                                if SIDN in sI.fullDirName and SIDN:
                                    sI.isEncodedImage = True
                                # SourceImage.source_pict_dict[sI.fileNameWithExt.upper()] = sI
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

# -------------------/GUI------------------------------
# -------------------/GUI------------------------------
# -------------------/GUI------------------------------


def processOneXML(inData):
    dest = inData['dest']
    tempdir = inData["tempdir"]
    dest_dict = inData["dest_dict"]
    pict_dict = inData["pict_dict"]
    bOverWrite = inData["bOverWrite"]
    StringTo = inData["StringTo"]
    mapping = ParamMappingContainer(GUIAppSingleton().SourceXLSXPath)

    src = dest.sourceFile
    srcPath = src.fullPath
    destPath = os.path.join(tempdir, dest.relPath)
    destDir = os.path.dirname(destPath)

    print("%s -> %s" % (srcPath, destPath,))

    # FIXME multithreading, map-reduce
    mdp = etree.parse(srcPath, etree.XMLParser(strip_cdata=False))
    mdp.getroot().attrib[dest.sourceFile.ID] = dest.guid
    # FIXME what if calledmacros are not overwritten?
    if bOverWrite and dest.bRetainCalledMacros:
        cmRoot = mdp.find("./CalledMacros")
        for m in mdp.findall("./CalledMacros/Macro"):
            cmRoot.remove(m)

        for key, cM in dest.retainedCalledMacros.items():
            macro = etree.Element("Macro")

            mName = etree.Element("MName")
            mName.text = etree.CDATA('"' + cM + '"')
            macro.append(mName)

            guid = etree.Element(dest.sourceFile.ID)
            guid.text = key
            macro.append(guid)

            cmRoot.append(macro)
    else:
        for m in mdp.findall("./CalledMacros/Macro"):
            for dI in list(dest_dict.keys()):
                d = dest_dict[dI]
                if m.find("MName").text.strip("'" + '"') == d.sourceFile.name:
                    m.find("MName").text = etree.CDATA('"' + d.name + '"')
                    m.find(dest.sourceFile.ID).text = d.guid

    for sect in ["./Script_2D", "./Script_3D", "./Script_1D", "./Script_PR", "./Script_UI", "./Script_VL",
                 "./Script_FWM", "./Script_BWM", ]:
        section = mdp.find(sect)
        if section is not None:
            t = section.text

            for dI in list(dest_dict.keys()):
                t = re.sub(r'(?<=[,"\'`\s])' + dest_dict[dI].sourceFile.name + r'(?=[,"\'`\s])', dest_dict[dI].name, t, flags=re.IGNORECASE)

            for pr in sorted(list(pict_dict.keys()), key=lambda x: -len(x)):
                # Replacing images
                t = re.sub(r'(?<=[,"\'`\s])' + pict_dict[pr].sourceFile.fileNameWithOutExt + '(?!' + StringTo + ')',
                           pict_dict[pr].fileNameWithOutExt, t, flags=re.IGNORECASE)

            section.text = etree.CDATA(t)
    # ---------------------Prevpict-------------------------------------------------------
    #TODO
    if dest.bPlaceable:
        section = mdp.find('Picture')
        if isinstance(section, etree._Element) and 'path' in section.attrib:
            path = os.path.basename(section.attrib['path']).upper()
            if path:
                n = next((pict_dict[p].relPath for p in list(pict_dict.keys()) if
                          os.path.basename(pict_dict[p].sourceFile.relPath).upper() == path), None)
                if n:
                    section.attrib['path'] = os.path.dirname(n) + "/" + os.path.basename(n)  # Not os.path.join!

    parRoot = mdp.find("./ParamSection")
    parPar = parRoot.getparent()
    parPar.remove(parRoot)

    mapping.applyParams(dest.parameters, dest.name)

    destPar = dest.parameters.toEtree()
    parPar.append(destPar)

    # ---------------------Ancestries--------------------
    # FIXME not clear, check, writes an extra empty mainunid field
    # FIXME ancestries to be used in param checking
    # FIXME this is unclear what id does
    for m in mdp.findall("./Ancestry/" + dest.sourceFile.ID):
        guid = m.text
        # FIXME DestXML.id_dict maybe empty in a separate process
        if guid.upper() in DestXML.id_dict:
            print("ANCESTRY: %s" % guid)
            par = m.getparent()
            par.remove(m)

            element = etree.Element(dest.sourceFile.ID)
            element.text = DestXML.id_dict[guid]
            element.tail = '\n'
            par.append(element)
    try:
        os.makedirs(destDir)
    except WindowsError:
        pass
    with open(destPath, "wb") as file_handle:
        mdp.write(file_handle, pretty_print=True, encoding="UTF-8", )


def main():
    global app

    app = GUIAppSingleton()
    # app.top.protocol("WM_DELETE_WINDOW", app.writeConfigBack)
    app.top.mainloop()

if __name__ == "__main__":
    main()

