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

from pyqtgraph.Qt import QtCore as _QtCore, \
                         QtGui as _QtGui, \
                         QtWidgets as _QtWidgets

import tisgrabber as _tisgrabber

from . import utils as _utils
from .. import LOGGER as _LOGGER

class DeviceSelector(_utils.ViewGroup):
    LABEL_OPEN  = "Open"
    LABEL_CLOSE = "Close"
    requestedOpeningDevice = _QtCore.pyqtSignal(str)
    requestedClosingDevice = _QtCore.pyqtSignal()

    def __init__(self,
                 title="Device",
                 controller=None,
                 parent=None):
        super().__init__(title=title, controller=controller, parent=parent)
        self._box    = _QtWidgets.QComboBox()
        for device in _tisgrabber.Camera.get_device_names():
            self._box.addItem(device)
        self._layout.addWidget(self._box, 0, 0)
        self._action = _QtWidgets.QPushButton(self.LABEL_OPEN)
        self._layout.addWidget(self._action, 0, 1)
        self._layout.setColumnStretch(0, 3)
        self._layout.setColumnStretch(1, 1)
        self._action.clicked.connect(self.dispatchRequest)
        self._connectToController(self.controller)

    def dispatchRequest(self):
        cmd = self._action.text()
        if cmd == self.LABEL_OPEN:
            self.requestedOpeningDevice.emit(self._box.currentText())
        else:
            self.requestedClosingDevice.emit()

    def updateWithOpeningDevice(self, device):
        self._box.setCurrentText(device.unique_name)
        self._action.setText(self.LABEL_CLOSE)
        self._box.setEnabled(False)

    def updateWithClosingDevice(self):
        self._action.setText(self.LABEL_OPEN)
        self._box.setEnabled(True)

    def _connectToController(self, obj):
        self.requestedOpeningDevice.connect(obj.openDevice)
        self.requestedClosingDevice.connect(obj.closeDevice)
        obj.openedDevice.connect(self.updateWithOpeningDevice)
        obj.closedDevice.connect(self.updateWithClosingDevice)

    def _disconnectFromController(self, obj):
        self.requestedOpeningDevice.disconnect(obj.openDevice)
        self.requestedClosingDevice.disconnect(obj.closeDevice)
        obj.openedDevice.disconnect(self.updateWithOpeningDevice)
        obj.closedDevice.disconnect(self.updateWithClosingDevice)

class FrameFormatSettings(_utils.ViewGroup):
    requestedFormatUpdate = _QtCore.pyqtSignal(str)

    def __init__(self, title="Frame",
                 controller=None,
                 parent=None):
        super().__init__(title=title, controller=controller, parent=parent)
        self._format = _utils.FormItem("Format", _QtWidgets.QComboBox())
        self._x      = _utils.FormItem("Offset X", _QtWidgets.QSpinBox())
        self._y      = _utils.FormItem("Offset Y", _QtWidgets.QSpinBox())
        self._w      = _utils.FormItem("Width X", _QtWidgets.QSpinBox())
        self._h      = _utils.FormItem("Height Y", _QtWidgets.QSpinBox())
        for row, obj in enumerate((self._format,
                                   self._x,
                                   self._y,
                                   self._w,
                                   self._h)):
            self._addFormItem(obj, row, 0)
        # FIXME: add saved ROI feature
        for obj in (self._x, self._y, self._w, self._h):
            obj.setEnabled(False)

        self.setEnabled(False)
        self._connectToController(self.controller)
        self._format.widget.currentTextChanged.connect(self.dispatchFormatUpdate)

    def _connectToController(self, obj):
        self.requestedFormatUpdate.connect(obj.setFormat)
        obj.openedDevice.connect(self.updateWithOpeningDevice)
        obj.closedDevice.connect(self.updateWithClosingDevice)
        obj.updatedFormat.connect(self.updateWithFormat)

    def _disconnectFromController(self, obj):
        self.requestedFormatUpdate.disconnect(obj.setFormat)
        obj.openedDevice.disconnect(self.updateWithOpeningDevice)
        obj.closedDevice.disconnect(self.updateWithClosingDevice)
        obj.updatedFormat.disconnect(self.updateWithFormat)

    def setEnabled(self, val):
        for obj in (self._format,
                    # self._x,
                    # self._y,
                    # self._w,
                    # self._h,
                    ):
            obj.setEnabled(val)

    def dispatchFormatUpdate(self, fmt):
        if self._updating == False:
            self.requestedFormatUpdate.emit(fmt)
        else:
            _LOGGER.debug(f"updating with controller: suppressed to emit requestedFormatUpdate({repr(fmt)})")

    def updateWithOpeningDevice(self, device):
        # re-populate the format selector
        box  = self._format.widget
        for fmt in device.list_video_formats():
            box.addItem(fmt) # will fire dispatchFormatUpdate once
        self.setEnabled(True)

    def updateWithClosingDevice(self):
        self.setEnabled(False)
        self._updating = True
        self._format.widget.clear()
        self._updating = False

    def updateWithFormat(self, fmt):
        self._updating = True
        self._format.widget.setCurrentText(fmt)
        self._updating = False

class AcquisitionSettings(_utils.ViewGroup):
    requestedTriggerStatusUpdate = _QtCore.pyqtSignal(bool)
    requestedFrameRateUpdate     = _QtCore.pyqtSignal(float)

    def __init__(self, title="Acquisition",
                 controller=None,
                 parent=None):
        super().__init__(title=title, controller=controller, parent=parent)
        self._rate = _utils.FormItem("Frame rate (Hz)", _QtWidgets.QDoubleSpinBox())
        # set up the spin box
        # TODO: configure upon opening a device?
        self._rate.widget.setDecimals(1)
        self._rate.widget.setMaximum(200)
        self._rate.widget.setMinimum(1.0)
        self._rate.widget.setSingleStep(0.1)
        self._rate.widget.setValue(30)
        self._rate.widget.valueChanged.connect(self.dispatchFrameRateUpdate)

        self._exposure = _utils.FormItem("Exposure (us)", _QtWidgets.QSpinBox())
        # set up the spin box
        # TODO: configure upon opening a device
        self._exposure.widget.setMinimum(1)
        self._exposure.widget.setMaximum(100000)
        self._exposure.widget.setValue(10000)

        self._gain = _utils.FormItem("Gain", _QtWidgets.QSpinBox())
        # TODO: deal with gain settings

        self._triggered = _QtWidgets.QCheckBox("Use external trigger")
        self._triggered.stateChanged.connect(self.dispatchTriggerStatusUpdate)
        self._autoexp   = _QtWidgets.QCheckBox("Auto-exposure")
        self._autogain  = _QtWidgets.QCheckBox("Auto-gain")
        self._addFormItem(self._rate, 0, 0)
        self._layout.addWidget(self._triggered, 0, 2,
                               alignment=_QtCore.Qt.AlignLeft)
        self._addFormItem(self._exposure, 1, 0)
        self._layout.addWidget(self._autoexp, 1, 2)
        self._addFormItem(self._gain, 2, 0)
        self._layout.addWidget(self._autogain, 2, 2)

        self.setEnabled(False)
        self._connectToController(self.controller)

    def setEnabled(self, val):
        for obj in (self._rate, self._triggered):
            obj.setEnabled(val)
        for obj in (self._exposure, self._autoexp):
            obj.setEnabled(False)
        for obj in (self._gain, self._autogain):
            obj.setEnabled(False)

    def dispatchTriggerStatusUpdate(self, status):
        if self._updating == True:
            return
        self.requestedTriggerStatusUpdate.emit(_utils.check_status_notristate(status))

    def dispatchFrameRateUpdate(self, val):
        if self._updating == True:
            return
        self.requestedFrameRateUpdate.emit(val)

    def updateWithOpeningDevice(self, device):
        self.setEnabled(True)
        self._updating = True
        self._rate.widget.setValue(device.frame_rate)
        if device.has_trigger:
            self._triggered.setEnabled(True)
            self._triggered.setChecked(device.triggered)
        else:
            self._triggered.setEnabled(False)
            self._triggered.setChecked(False)
        self._updating = False

    def updateWithClosingDevice(self):
        self.setEnabled(False)

    def updateWithTriggerStatus(self, val):
        self._updating = True
        self._triggered.setChecked(val)
        self._updating = False

    def updateWithFrameRate(self, val):
        self._updating = True
        self._rate.widget.setValue(val)
        self._updating = False

    def _connectToController(self, obj):
        obj.openedDevice.connect(self.updateWithOpeningDevice)
        obj.closedDevice.connect(self.updateWithClosingDevice)
        obj.updatedTriggerStatus.connect(self.updateWithTriggerStatus)
        obj.updatedFrameRate.connect(self.updateWithFrameRate)
        self.requestedTriggerStatusUpdate.connect(obj.setTriggered)
        self.requestedFrameRateUpdate.connect(obj.setFrameRate)

    def _disconnectFromController(self, obj):
        obj.openedDevice.disconnect(self.updateWithOpeningDevice)
        obj.closedDevice.disconnect(self.updateWithClosingDevice)
        obj.updatedTriggerStatus.disconnect(self.updateWithTriggerStatus)
        obj.updatedFrameRate.disconnect(self.updateWithFrameRate)
        self.requestedTriggerStatusUpdate.disconnect(obj.setTriggered)
        self.requestedFrameRateUpdate.disconnect(obj.setFrameRate)
