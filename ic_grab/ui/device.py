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
import math as _math
from pyqtgraph.Qt import QtCore as _QtCore, \
                         QtGui as _QtGui, \
                         QtWidgets as _QtWidgets

import tisgrabber as _tisgrabber
from .. import LOGGER as _LOGGER
from . import utils as _utils

class FrameRateSettings:
    def __init__(self, rate=_math.nan, available=True, parent=None):
        self._parent    = parent
        self.available  = available
        self._value     = rate
        self._triggered = False

    @property
    def value(self):
        return self._value

    @value.setter
    def value(self, value):
        self._value = value
        if self.available and (self._parent is not None):
            self._parent.updatedFrameRate.emit(value)

    @property
    def triggered(self):
        return self._triggered

    @triggered.setter
    def triggered(self, status):
        self._triggered = status
        if self.available and (self._parent is not None):
            self._parent.updatedTriggerStatus.emit(status)

class DeviceSettings:
    def __init__(self, parent=None):
        self._parent = parent
        self.device  = None
        self._format = None
        self._rate   = FrameRateSettings(available=False, parent=parent)

    def as_dict(self):
        raise NotImplementedError() # FIXME

    def load_dict(self, cfg):
        raise NotImplementedError() # FIXME

    @property
    def format(self):
        return self._format

    @format.setter
    def format(self, format_name):
        ## FIXME: warn in case no device is open
        if self.device is not None:
            if format_name in self.device.list_video_formats():
                self.device.video_format = format_name
            if self._parent is not None:
                self._parent.updatedFormat.emit(self._format)
            self.update()

    @property
    def has_trigger(self):
        if self.device is None:
            return False
        else:
            return self.device.has_trigger

    @property
    def triggered(self):
        return self._rate.triggered

    @triggered.setter
    def triggered(self, status):
        if self.device is not None:
            if self.device.has_trigger:
                self.device.triggered = status
        self.update()

    @property
    def frame_rate(self):
        return self._rate.value

    @frame_rate.setter
    def frame_rate(self, value):
        if (self.device is not None) and (not self.device.triggered):
            self.device.frame_rate = value
            self.update()
        else:
            self._rate.value = value

    def update(self):
        self._rate.available = (self.device is not None)
        if self.device is None:
            return

        self._format = self.device.video_format
        if self._parent is not None:
            self._parent.updatedFormat.emit(self._format)

        if not self.device.has_trigger:
            self._rate.triggered = False
            self._rate.value     = self.device.frame_rate
        else:
            self._rate.triggered = self.device.triggered
            if not self.device.triggered:
                self._rate.value = self.device.frame_rate

class DeviceControl(_QtCore.QObject):
    openedDevice            = _QtCore.pyqtSignal(object)
    closedDevice            = _QtCore.pyqtSignal()
    updatedFormat           = _QtCore.pyqtSignal(str)
    updatedTriggerStatus    = _QtCore.pyqtSignal(bool)
    updatedFrameRate        = _QtCore.pyqtSignal(float)
    updatedAcquisitionMode  = _QtCore.pyqtSignal(str, str)
    message                 = _QtCore.pyqtSignal(str, str)

    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.message.connect(self._log)
        self._settings = DeviceSettings(parent=self)
        self._mode     = _utils.AcquisitionModes.IDLE

    @property
    def settings(self):
        """the grabber settings as a dictionary object."""
        return self._settings.as_dict() # FIXME

    @settings.setter
    def settings(self, cfg):
        self._settings.load_dict(cfg) # FIXME

    def getFormat(self):
        return self._settings.format

    def setFormat(self, fmt):
        self._settings.format = fmt
        self.message.emit("info", f"current frame format: {self._settings.format}")

    def isTriggerAvailable(self):
        return self._settings.has_trigger

    def isTriggered(self):
        self._settings.triggered

    def setTriggered(self, val):
        self._settings.triggered = val
        self.message.emit("info", f"trigger status: {self._settings.triggered}")

    def getFrameRate(self):
        return self._settings.frame_rate

    def setFrameRate(self, val):
        self._settings.frame_rate = val
        self.message.emit("info", f"current frame rate: {self._settings.frame_rate:.1f} Hz")

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
        if self._settings.device is not None:
            self.closeDevice()
        self._settings.device = _tisgrabber.Camera(device_name)
        self.openedDevice.emit(self._settings.device)
        self.message.emit("info", f"opened device: {device_name}")

    def closeDevice(self):
        self._settings.device.close()
        self.closedDevice.emit()
        self.message.emit("info", f"closed the current device.")
        self._settings.device = None

    def currentDevice(self):
        return self._settings.device

    def setAcquisitionMode(self, mode):
        if self._mode == mode:
            return
        oldmode = self._mode
        self._mode = mode # TODO: update the device
        self.updatedAcquisitionMode.emit(oldmode, mode)
        if mode == _utils.AcquisitionModes.IDLE:
            self.message.emit("info", f"finished {oldmode} (not implemented)")
        else:
            self.message.emit("info", f"started {mode} (not implemented)")

    def getAcquisitionMode(self):
        return self._mode

    ## TODO: move load/save-Settings() to a higher level (e.g. MainWindow)?
    def saveSettings(self, path):
        raise NotImplementedError() # FIXME
        path = _Path(path)
        with open(path, "w") as out:
            _json.dump(self.settings, out, indent=4)
        self.message.emit("info", f"saved settings to: {path.name}")

    def loadSettings(self, path):
        raise NotImplementedError() # FIXME
        path = _Path(path)
        with open(path, "r") as src:
            self.settings = _json.load(src)
        self.message.emit("info", f"loaded settings from: {path.name}")

    device        = property(fget=currentDevice, fset=openDevice)
    format        = property(fget=getFormat, fset=setFormat)
    triggered     = property(fget=isTriggered, fset=setTriggered)
    has_trigger   = property(fget=isTriggerAvailable)
    frame_rate    = property(fget=getFrameRate, fset=setFrameRate)
    mode          = property(fget=getAcquisitionMode, fset=setAcquisitionMode)
