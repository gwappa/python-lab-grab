# MIT License
#
# Copyright (c) 2021 Keisuke Sehara
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

from datetime import datetime as _datetime
from pyqtgraph.Qt import QtCore as _QtCore

class Experiment(_QtCore.QObject):
    DEFAULT_SUBJECT  = "unspecified"
    DEFAULT_DOMAIN   = "camera"

    updatedSubject   = _QtCore.pyqtSignal(str)
    updatedDate      = _QtCore.pyqtSignal(int, int, int)
    updatedDomain    = _QtCore.pyqtSignal(str)
    updatedIndex     = _QtCore.pyqtSignal(int)
    updatedAppendage = _QtCore.pyqtSignal(str)
    message          = _QtCore.pyqtSignal(str, str)

    _singleton = None

    # currently the method is defined using the `cls._singleton` object
    # so that every subclass can have its own singleton object.
    # this must be modified to refer to `Experiment._singleton`
    # to achieve the situation where _all_ the subclasses refer to the _same, single_
    # Experiment object
    @classmethod
    def instance(cls):
        if cls._singleton is None:
            cls._singleton = cls()
        return cls._singleton

    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self._subject = self.DEFAULT_SUBJECT
        self._date    = _datetime.now()
        self._index   = 1
        self._domain  = self.DEFAULT_DOMAIN
        self._append  = ""

    def getSubject(self):
        return self._subject

    def setSubject(self, value):
        self._subject = value
        self.updatedSubject.emit(value)
        self.message.emit("info", f"experiment subject: {value}")

    def getDate(self):
        return self._date

    def setDate(self, value):
        ## FIXME: only accepts datetime for the time being
        self._date = value
        self.updatedDate.emit(value.year, value.month, value.day)
        self.message.emit("info", f"experiment date: {value.strftime(self.date_format)}")

    def getQDate(self):
        return _QtCore.QDate(self._date.year, self._date.month, self._date.day)

    def setQDate(self, value):
        self.setDate(_datetime(value.year(), value.month(), value.day()))

    def getIndex(self):
        return self._index

    def setIndex(self, value):
        self._index = int(value)
        self.updatedIndex.emit(self._index)
        self.message.emit("info", f"session index: {self._index:03d}")

    def getIndexStr(self):
        return str(self._index).zfill(3)

    def setIndexStr(self, value):
        self.setIndex(value)

    def getDomain(self):
        return self._domain

    def setDomain(self, value):
        self._domain = value
        self.updatedDomain.emit(value)
        self.message.emit("info", f"experiment data domain: {value}")

    def getAppendage(self):
        return self._append

    def setAppendage(self, value):
        self._append = str(value).strip()
        self.updatedAppendage.emit(self._append)
        self.message.emit("info", f"file appendage: {self._append}")

    @property
    def date_format(self):
        return "%Y-%m-%d"

    @property
    def qDate_format(self):
        return "yyyy-MM-dd"

    @property
    def appendagestr(self):
        if len(self._append) == 0:
            return ""
        else:
            return "_" + self._append

    subject   = property(fget=getSubject,  fset=setSubject)
    date      = property(fget=getDate,     fset=setDate)
    qDate     = property(fget=getQDate,    fset=setQDate)
    index     = property(fget=getIndex,    fset=setIndex)
    indexstr  = property(fget=getIndexStr, fset=setIndexStr)
    domain    = property(fget=getDomain,   fset=setDomain)
    appendage = property(fget=getAppendage,fset=setAppendage)
