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
import json as _json
from pyqtgraph.Qt import QtCore as _QtCore, \
                         QtGui as _QtGui, \
                         QtWidgets as _QtWidgets

import tisgrabber as _tisgrabber
from .. import LOGGER as _LOGGER

class DeviceControl(_QtCore.QObject):
    openedDevice  = _QtCore.pyqtSignal(object)
    closedDevice  = _QtCore.pyqtSignal()
    updatedFormat = _QtCore.pyqtSignal(str)
    message       = _QtCore.pyqtSignal(str, str)

    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.message.connect(self._log)
        self._device = None
        self._format = None

    @property
    def settings(self):
        """the grabber settings as a dictionary object."""
        ret = {}
        if self._device is not None:
            ret["device"] = self._device.unique_name
            ret["format"] = self._format
        else:
            ret["device"] = None

    @settings.setter
    def settings(self, cfg):
        device_name = ret.get("device", None)
        if device_name is not None:
            self.openDevice(device_name)

    def getFormat(self):
        return self._format

    def setFormat(self, fmt):
        ## FIXME: warn in case no device is open
        if self._device is not None:
            if fmt in self._device.list_video_formats():
                self._format = fmt
            self.updatedFormat.emit(self._format)
            self.message.emit("info", f"current pixel format is: {self._format}")

    def _log(self, level, message):
        if level == "info":
            _LOGGER.info(message)
        elif level == "warning":
            _LOGGER.warning(message)
        elif level == "error":
            _LOGGER.error(message)
        elif level == "critical":
            _LOGGER.critical(message)
        else:
            _LOGGER.warning(f"<unknown level '{level}'>: {message}")

    def openDevice(self, device_name):
        if self._device is not None:
            self.closeDevice()
        self._device = _tisgrabber.Camera(device_name)
        self.openedDevice.emit(self._device)
        self.message.emit("info", f"opened device: {device_name}")

    def closeDevice(self):
        self._device.close()
        self.closedDevice.emit()
        self.message.emit("info", f"closed the current device.")
        self._device = None

    def currentDevice(self):
        return self._device

    ## TODO: move load/save-Settings() to a higher level (e.g. MainWindow)? 
    def saveSettings(self, path):
        path = _Path(path)
        with open(path, "w") as out:
            _json.dump(self.settings, out, indent=4)
        self.message.emit("info", f"saved settings to: {path.name}")

    def loadSettings(self, path):
        path = _Path(path)
        with open(path, "r") as src:
            self.settings = _json.load(src)
        self.message.emit("info", f"loaded settings from: {path.name}")

    device        = property(fget=currentDevice, fset=openDevice)
    format        = property(fget=getFormat, fset=setFormat)
