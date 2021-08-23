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

from pathlib import Path as _Path
from datetime import datetime as _datetime
from pyqtgraph.Qt import QtCore as _QtCore

class StorageService(_QtCore.QObject):
    EXPERIMENT_ATTRIBUTES = ("subject", "datestr", "indexstr", "domain", "appendagestr")
    TIMESTAMP_FORMAT      = "%H%M%S"
    DEFAULT_NAME_PATTERN  = "{subject}_{date}_{domain}_{time}{appendage}"

    _singleton = None

    updatedCodec     = _QtCore.pyqtSignal(str) # FIXME
    updatedDirectory = _QtCore.pyqtSignal(str)
    updatedPattern   = _QtCore.pyqtSignal(str)
    updatedFileName  = _QtCore.pyqtSignal(str)
    message          = _QtCore.pyqtSignal(str, str)

    # currently the method is defined using the `cls._singleton` object
    # so that every subclass can have its own singleton object.
    # this must be modified to refer to `StorageService._singleton`
    # to achieve the situation where _all_ the subclasses refer to the _same, single_
    # StorageService object
    @classmethod
    def instance(cls):
        if cls._singleton is None:
            cls._singleton = cls()
        return cls._singleton

    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self._codec      = None # FIXME
        self._directory  = str(_Path().resolve())
        self._pattern    = self.DEFAULT_NAME_PATTERN

        self._experiment = _Experiment.instance() # must be non-None
        self._experiment.updated.connect(self.updateFileName)

    def getCodec(self):
        return self._codec

    def setCodec(self, value):
        # FIXME
        self._codec = str(value)
        self.updatedCodec.emit(self._codec)
        self.updateFileName()

    def getDirectory(self):
        return self._directory

    def setDirectory(self, value):
        self._directory = str(_Path(value).resolve())
        self.updatedDirectory.emit(self._directory)
        self.message.emit("info", f"save directory: {self._directory}")

    def getPattern(self):
        return self._pattern

    def setPattern(self, value):
        self._pattern = str(value)
        self.updatedPattern.emit(self._pattern)
        self.message.emit("info", f"file-name pattern: {self._pattern}")
        self.updateFileName()

    def updateFileName(self):
        pattern = self._pattern
        if "{suffix}" not in pattern:
            pattern = pattern + "{suffix}"
        filename = pattern.format(**(self.format_dict))
        self.updatedFileName.emit(filename)
        return filename

    def as_path(self, filename):
        return _Path(self._directory) / filename

    @property
    def suffix(self):
        # FIXME
        return ".avi"

    @property
    def format_dict(self):
        opts = dict((attrname, getattr(self._experiment, attrname))\
                    for attrname in self.EXPERIMENT_ATTRIBUTES)
        for name in ("date", "index", "appendage"):
            opts[name] = opts.pop(name + "str")
        opts["time"]   = _datetime.now().strftime(self.TIMESTAMP_FORMAT)
        opts["suffix"] = self.suffix
        return opts

    codec     = property(fget=getCodec,     fset=setCodec)
    directory = property(fget=getDirectory, fset=setDirectory)
    pattern   = property(fget=getPattern,   fset=setPattern)
    filename  = property(fget=updateFileName)

from .experiment import Experiment as _Experiment
