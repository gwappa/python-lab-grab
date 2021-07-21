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

class FrameFormatSelector(_utils.ViewGroup):
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
        self._updating = False # flag to check if it is currently updating to reflect the controller state

    def _connectToController(self, obj):
        self.requestedFormatUpdate.connect(obj.setFormat)
        obj.openedDevice.connect(self.updateWithOpeningDevice)
        obj.closedDevice.connect(self.updateWithClosingDevice)
        obj.updatedFormat.connect(self.updateWithFormat)

    def _disconnectFromController(self, obj):
        obj.openedDevice.disconnect(self.updateWithOpeningDevice)
        obj.closedDevice.disconnect(self.updateWithClosingDevice)

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
