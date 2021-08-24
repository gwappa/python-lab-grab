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
        self._strobe_mode = _utils.StrobeModes.DISABLED
        self._rate        = FrameRateSettings(available=False, parent=parent)

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
                ## FIXME: warn in case the format is not understood
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

    @property
    def exposure(self):
        return (self.device.exposure_us, self.device.auto_exposure)

    @exposure.setter
    def exposure(self, setting):
        value, auto = setting
        if self.device is not None:
            value = int(round(value))
            m, M = self.device.exposure_range_us
            if m > value:
                value = m # FIXME: warn in some fashion
            elif M < value:
                value = M # FIXME: warn in some fashion
            self.device.exposure_us   = value
            self.device.auto_exposure = bool(auto)
            value = self.device.exposure_us
            auto  = self.device.auto_exposure
        if self._parent is not None:
            self._parent.updatedExposureSettings.emit(value, auto)

    @property
    def exposure_us(self):
        return self.device.exposure_us

    @exposure_us.setter
    def exposure_us(self, val):
        self.exposure = (val, self.device.auto_exposure)

    @property
    def auto_exposure(self):
        return self.device.auto_exposure

    @auto_exposure.setter
    def auto_exposure(self, val):
        self.exposure = (self.device.exposure_us, val)

    @property
    def gain(self):
        return (self.device.gain, self.device.auto_gain)

    @gain.setter
    def gain(self, setting):
        value, auto = setting
        if self.device is not None:
            value = float(value)
            m, M  = self.device.gain_range
            if m > value:
                value = m # FIXME warn in some fashion
            elif M < value:
                value = M # FIXME warn in some fashion
            self.device.gain = value
            self.device.auto_gain = bool(auto)
            value = self.device.gain
            auto  = self.device.auto_gain
        if self._parent is not None:
            self._parent.updatedGainSettings.emit(value, auto)

    @property
    def manual_gain(self):
        return self.device.gain

    @manual_gain.setter
    def manual_gain(self, val):
        self.gain = (val, self.device.auto_gain)

    @property
    def auto_gain(self):
        return self.device.auto_gain

    @auto_gain.setter
    def auto_gain(self, val):
        self.gain = (self.device.gain, val)

    @property
    def strobe_mode(self):
        return self._strobe_mode

    @strobe_mode.setter
    def strobe_mode(self, val):
        val = str(val)
        if val not in _utils.StrobeModes.iterate():
            raise ValueError("unexpected strobe mode: "+val)
        self._strobe_mode = val
        if self._parent is not None:
            self._parent.updatedStrobeMode.emit(self._strobe_mode)

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
    updatedExposureSettings = _QtCore.pyqtSignal(int, bool) # (exposure_us, auto_exposure)
    updatedGainSettings     = _QtCore.pyqtSignal(float, bool) # (gain, auto_gain)
    updatedStrobeMode       = _QtCore.pyqtSignal(str)
    updatedAcquisitionMode  = _QtCore.pyqtSignal(str, str)
    acquisitionReady        = _QtCore.pyqtSignal(object, object, bool) # (framerate, image_descriptor, store_frames)
    acquisitionEnded        = _QtCore.pyqtSignal()
    frameReady              = _QtCore.pyqtSignal(int, object)
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

    def getStrobeMode(self):
        return self._settings.strobe_mode

    def setStrobeMode(self, mode):
        self._settings.strobe_mode = mode
        self.message.emit("info", f"current strobe mode: {self._settings.strobe_mode}")

    def updateExposureSettings(self, value, auto):
        self._settings.exposure = (value, auto)
        value, auto = self._settings.exposure
        if auto == True:
            self.message.emit("info", "enabled auto-exposure")
        else:
            self.message.emit("info", f"current exposure: {value} us")

    def getExposureUs(self):
        return self._settings.exposure_us

    def setExposureUs(self, value):
        self._settings.exposure_us = value

    def getAutoExposure(self):
        return self._settings.auto_exposure

    def setAutoExposure(self, auto):
        self._settings.auto_exposure = auto

    def updateGainSettings(self, value, auto):
        self._settings.gain = (value, auto)
        value, auto = self._settings.gain
        if auto == True:
            self.message.emit("info", "enabled auto-gain")
        else:
            self.message.emit("info", f"current gain: {value:.1f}")

    def getGain(self):
        return self._settings.manual_gain

    def setGain(self, value):
        self._settings.manual_gain = value

    def getAutoGain(self):
        return self._settings.auto_gain

    def setAutoGain(self, auto):
        self._settings.auto_gain = auto

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
        self._settings.device.callbacks.append(self._frameReady)
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
        try:
            self._startAcquisitionMode(mode)
            self._mode = mode # TODO: update the device
            self.updatedAcquisitionMode.emit(oldmode, mode)
            if mode == _utils.AcquisitionModes.IDLE:
                self.message.emit("info", f"finished {oldmode}")
            else:
                self.message.emit("info", f"started {mode}")
        except:
            # FIXME
            raise

    def getAcquisitionMode(self):
        return self._mode

    def _startAcquisitionMode(self, mode):
        device = self._settings.device
        if mode == _utils.AcquisitionModes.IDLE:
            if device.is_setup():
                device.stop()
                device.strobe = self.__prev_strobe_mode
                self.acquisitionEnded.emit()
        elif mode in (_utils.AcquisitionModes.FOCUS, _utils.AcquisitionModes.GRAB):
            # prepare strobe settings
            self.__prev_strobe_mode = device.strobe
            device.strobe = _utils.StrobeModes.requires_strobe(self._settings.strobe_mode,
                                                               mode)

            # prepare the device
            if not device.is_setup():
                device.prepare(preview=False)

            # let the other modules prepare for acquisition
            self.acquisitionReady.emit(self._settings.frame_rate,
                                       device.image_descriptor,
                                       mode == _utils.AcquisitionModes.GRAB)
            device.start(preview=False, update_descriptor=False)
        else:
            raise ValueError(f"unexpected mode: {mode}")

    def _frameReady(self, device, frame_index, frame):
        self.frameReady.emit(frame_index, _utils.image_to_display(frame))
        #_LOGGER.info(f"frame #{frame_index}: {frame.shape}@{str(frame.dtype)}")

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
    strobe_mode   = property(fget=getStrobeMode, fset=setStrobeMode)
    exposure_us   = property(fget=getExposureUs, fset=setExposureUs)
    auto_exposure = property(fget=getAutoExposure, fset=setAutoExposure)
