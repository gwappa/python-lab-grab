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
    openedDevice = _QtCore.pyqtSignal(str)
    closedDevice = _QtCore.pyqtSignal()
    message      = _QtCore.pyqtSignal(str, str)

    def __init__(self, device_selector=None, parent=None):
        super().__init__(parent=parent)
        self.message.connect(self._log)
        if device_selector is None:
            device_selector = DeviceSelector()
        self._selector = device_selector
        self._selector.requestedOpeningDevice.connect(self.openDevice)
        self._selector.requestedClosingDevice.connect(self.closeDevice)
        self.openedDevice.connect(self._selector.updateWithOpeningDevice)
        self.closedDevice.connect(self._selector.updateWithClosingDevice)
        self._device = None

    @property
    def selector(self):
        return self._selector

    @property
    def settings(self):
        """the grabber settings as a dictionary object."""
        ret = {}
        ret["device"] = None if self._device is None else self._device.unique_name

    @settings.setter
    def settings(self, cfg):
        device_name = ret.get("device", None)
        if device_name is not None:
            self.openDevice(device_name)

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
        self._device = _tisgrabber.Camera(device_name)
        self.openedDevice.emit(device_name)
        self.message.emit("info", f"opened device: {device_name}")

    def closeDevice(self):
        self._device.close()
        self.closedDevice.emit()
        self.message.emit("info", f"closed the current device.")
        self._device = None

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

class FormItem:
    """a utility python class for handling a widget
    along with its corresponding label."""
    def __init__(self, label, widget):
        self._label  = _QtWidgets.QLabel(label)
        self._widget = widget

    def setEnabled(self, val):
        for obj in (self._label, self._widget):
            obj.setEnabled(val)

    @property
    def label(self):
        return self._label

    @property
    def widget(self):
        return self._widget

class ViewGroup(_QtWidgets.QGroupBox):
    """a group box view being controlled by a DeviceControl object."""
    def __init__(self, title="Group",
                 controller=None,
                 parent=None):
        super().__init__(title, parent=parent)
        self._controller = None
        self._layout = _QtWidgets.QGridLayout()
        self.setLayout(self._layout)
        if controller is not None:
            self.controller = controller

    @property
    def controller(self):
        return self._controller

    @controller.setter
    def controller(self, obj):
        if self._controller is not None:
            self._disconnectFromController(self._controller)
        self._controller = obj
        self._connectToController(self._controller)

    def _connectToController(self, obj):
        """supposed to be implemented by the subclass."""
        pass

    def _disconnectFromController(self, obj):
        """supposed to be implemented by the subclass."""
        pass

    def _addFormItem(self, item, row, col):
        self._layout.addWidget(item.label,  row,  col, alignment=_QtCore.Qt.AlignRight)
        self._layout.addWidget(item.widget, row, col+1)

class DeviceSelector(_QtWidgets.QGroupBox):
    LABEL_OPEN  = "Open"
    LABEL_CLOSE = "Close"
    requestedOpeningDevice = _QtCore.pyqtSignal(str)
    requestedClosingDevice = _QtCore.pyqtSignal()

    def __init__(self, title="Device", parent=None):
        super().__init__(title, parent=parent)
        self._layout = _QtWidgets.QGridLayout()
        self.setLayout(self._layout)
        self._box    = _QtWidgets.QComboBox()
        for device in _tisgrabber.Camera.get_device_names():
            self._box.addItem(device)
        self._layout.addWidget(self._box, 0, 0)
        self._action = _QtWidgets.QPushButton(self.LABEL_OPEN)
        self._layout.addWidget(self._action, 0, 1)
        self._layout.setColumnStretch(0, 3)
        self._layout.setColumnStretch(1, 1)
        self._action.clicked.connect(self.dispatchRequest)

    def dispatchRequest(self):
        cmd = self._action.text()
        if cmd == self.LABEL_OPEN:
            self.requestedOpeningDevice.emit(self._box.currentText())
        else:
            self.requestedClosingDevice.emit()

    def updateWithOpeningDevice(self, device):
        self._box.setCurrentText(device)
        self._action.setText(self.LABEL_CLOSE)
        self._box.setEnabled(False)

    def updateWithClosingDevice(self):
        self._action.setText(self.LABEL_OPEN)
        self._box.setEnabled(True)

class FrameFormatSelector(ViewGroup):
    def __init__(self, title="Frame",
                 controller=None,
                 parent=None):
        super().__init__(title=title, controller=controller, parent=parent)
        self._format = FormItem("Format", _QtWidgets.QComboBox())
        self._x      = FormItem("Offset X", _QtWidgets.QSpinBox())
        self._y      = FormItem("Offset Y", _QtWidgets.QSpinBox())
        self._w      = FormItem("Width X", _QtWidgets.QSpinBox())
        self._h      = FormItem("Height Y", _QtWidgets.QSpinBox())
        for row, obj in enumerate((self._format,
                                   self._x,
                                   self._y,
                                   self._w,
                                   self._h)):
            self._addFormItem(obj, row, 0)
        # FIXME: add saved ROI feature
        for obj in (self._x, self._y, self._w, self._h):
            obj.setEnabled(False)

    def setEnabled(self, val):
        for obj in (self._format,
                    # self._x,
                    # self._y,
                    # self._w,
                    # self._h,
                    ):
            obj.setEnabled(val)
