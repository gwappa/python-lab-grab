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
import tisgrabber as _tisgrabber

from . import utils as _utils

class DeviceControl(_QtCore.QObject):
    """deals with opening/closing of the device, its acquisition modes,
    and broadcasting of incoming frames.

    be aware that this class doe not handle the frame-rate settings
    (refer to AcquisitionSettings if you need to have access to them).
    """

    openedDevice           = _QtCore.pyqtSignal(object)       # device
    closedDevice           = _QtCore.pyqtSignal()
    updatedAcquisitionMode = _QtCore.pyqtSignal(str, str)     # oldmode, newmode
    acquisitionReady       = _QtCore.pyqtSignal(object, bool) # image_descriptor, store_frames
    acquisitionEnded       = _QtCore.pyqtSignal()
    frameReady             = _QtCore.pyqtSignal(int, object) # frame index, frame
    message                = _QtCore.pyqtSignal(str, str)    # level, content

    def __init__(self, device=None, parent=None):
        super().__init__(parent=parent)
        self._device = device
        self._mode   = _utils.AcquisitionModes.IDLE

    def fireDriverError(self, e):
        """emits message() corresponding to the driver error."""
        self.message.emit("error", f"Driver error: {e}")

    def get_device_names(self):
        try:
            return _tisgrabber.Camera.get_device_names()
        except RuntimeError as e:
            self.fireDriverError(e)
            return ()

    def openDevice(self, device_name):
        try:
            device = _tisgrabber.Camera(device_name)
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
                self.acquisitionEnded.emit()
        elif mode in (_utils.AcquisitionModes.FOCUS, _utils.AcquisitionModes.GRAB):
            # prepare the device
            if not device.is_setup():
                device.prepare(preview=False)

            # let the other modules prepare for acquisition
            # (they have to know which device it is concerning)
            self.acquisitionReady.emit(device.image_descriptor,
                                       mode == _utils.AcquisitionModes.GRAB)
            device.start(preview=False, update_descriptor=False)
        else:
            raise ValueError(f"unexpected mode: {mode}")

    def _frameReadyCallback(self, device, frame_index, frame):
        self.frameReady.emit(frame_index, _utils.image_to_display(frame))
        #_LOGGER.info(f"frame #{frame_index}: {frame.shape}@{str(frame.dtype)}")
