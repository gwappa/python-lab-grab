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

from pyqtgraph.Qt import QtCore as _QtCore
import labcamera_tis as _tis

from . import utils as _utils
from .. import LOGGER as _LOGGER

class DeviceControl(_QtCore.QObject):
    """deals with opening/closing of the device, its acquisition modes,
    and broadcasting of incoming frames.

    be aware that this class doe not handle the frame-rate settings
    (refer to AcquisitionSettings if you need to have access to them).
    """

    openedDevice           = _QtCore.pyqtSignal(object)       # device
    closedDevice           = _QtCore.pyqtSignal()
    updatedAcquisitionMode = _QtCore.pyqtSignal(str, str)     # oldmode, newmode
    acquisitionReady       = _QtCore.pyqtSignal(object, object, bool) # FrameTypeDescriptor, rotation, store_frames
    acquisitionEnded       = _QtCore.pyqtSignal()
    frameReady             = _QtCore.pyqtSignal(object)      # frame
    message                = _QtCore.pyqtSignal(str, str)    # level, content

    def __init__(self, device=None, parent=None):
        super().__init__(parent=parent)
        self._device = device
        self._mode   = _utils.AcquisitionModes.IDLE
        self._acq    = None

    def initWithAcquisition(self, acq):
        self._acq = acq
        self._rotation_method = acq.rotation.method

    def fireDriverError(self, e):
        """emits message() corresponding to the driver error."""
        self.message.emit("error", f"Driver error: {e}")

    def get_device_names(self):
        try:
            return _tis.Device.list_names()
        except RuntimeError as e:
            self.fireDriverError(e)
            return ()

    def openDevice(self, device_name):
        try:
            device = _tis.Device(device_name)
            if self._device is not None:
                self.closeDevice()
            self._device = device
            self._device.callbacks.append(self._frameReadyCallback)
            self.openedDevice.emit(device)
            self.message.emit("info", f"opened device: {device_name}")
        except RuntimeError as e:
            self.fireDriverError(e)

    def closeDevice(self):
        if self._device is None:
            return
        try:
            self._device.close()
        except RuntimeError as e:
            pass
        self.closedDevice.emit()
        self.message.emit("info", f"closed the current device.")
        self._device = None

    def setAcquisitionMode(self, mode):
        if self._mode == mode:
            return
        oldmode = self._mode
        try:
            self._startAcquisitionMode(mode)
            self._mode = mode
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
        device = self._device
        if mode == _utils.AcquisitionModes.IDLE:
            if device.is_setup():
                device.stop()
                device.strobe = self.__prev_strobe # restore the previous (default) strobe setting
                # `acquisitionEnded` will be emitted
                # in response to _frameReadyCallback() with the argument being None
        elif mode in (_utils.AcquisitionModes.FOCUS, _utils.AcquisitionModes.GRAB):
            # prepare the device
            if not device.is_setup():
                if mode == _utils.AcquisitionModes.FOCUS:
                    n_buffers = 1
                else: # GRAB
                    n_buffers = int(device.frame_rate)
                device.prepare(buffer_size=n_buffers)

            self._rotation_method = self._acq.rotation.method

            self.__prev_strobe = device.strobe # spare the previous (default) strobe setting
            device.strobe = _utils.StrobeModes.requires_strobe(
                                                    self._acq.strobe.value,
                                                    mode
                                                )

            # let the other modules prepare for acquisition
            # (they have to know which device it is concerning)
            self.acquisitionReady.emit(device.frame_descriptor,
                                       self._acq.rotation,
                                       mode == _utils.AcquisitionModes.GRAB)
            device.start()
        else:
            raise ValueError(f"unexpected mode: {mode}")

    def _frameReadyCallback(self, frame):
        if frame is None:
            _LOGGER.info("None frame detected")
            self.acquisitionEnded.emit()
        else:
            self.frameReady.emit(self._rotation_method(frame))
