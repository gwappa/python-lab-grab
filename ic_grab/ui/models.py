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

import json as _json

from pyqtgraph.Qt import QtCore as _QtCore

class DeviceSetting(_QtCore.QObject):
    message = _QtCore.pyqtSignal(str, str) # level, content

    def __init__(self, device=None, parent=None):
        super().__init__(parent=parent)
        self._device    = device

    def fireDriverError(self, e):
        """emits message() corresponding to the driver error."""
        self.message.emit("error", f"Driver error: {e}")

    def getCurrentDevice(self):
        return self._device

    def updateWithDevice(self, device):
        self._device = device
        self.updateWithDeviceImpl(device)

    def as_dict(self):
        """supposed to return its setting as a dict object."""
        raise NotImplementedError("as_dict")

    def load_dict(self, cfg):
        """supposed to configure this setting object based on the given dict object (non-None)."""
        raise NotImplementedError("load_dict")

    device = property(fget=getCurrentDevice, fset=updateWithDevice)

class ValueModel(DeviceSetting):
    """signal/slot-aware model of a setting.
    interfaces to settings such as auto vs manual, and preferred vs actual.

    the model itself mainly defines the signals:

    - settingsChanged(auto, preferred, actual)
    - rangeChanged(min, max)
    - message(level, content)

    and basic properties:

    - auto (bool)
    - preferred (float)
    - value (float)

    some utility methods:

    - updateWithDevice(device or None) -- fire settingsChanged() when non-None device is specified.
    - fireSettingsChanged() -- fires the event with the current settings (auto/preferred/value).
    - fireRangeChanged() -- fires the rangeChanged event with the current valid range.
    - fireDriverError(RuntimeError) -- emits message() corresponding to the driver error.

    all the basic methods are supposed to be implemented by the subclasses:

    - isAutoImpl(): bool
    - setAutoImpl(bool)
    - getRangeImpl(): int/float, int/float
    - getValueImpl(): int/float
    - setValueImpl(int/float)
    """

    settingsChanged = _QtCore.pyqtSignal(bool, object, object) # auto, manual-preferred, manual-actual
    rangeChanged    = _QtCore.pyqtSignal(object, object) # min, max

    PARAMETER_LABEL      = None
    AUTO_PARAMETER_LABEL = None
    DEFAULT_AUTO         = False
    DEFAULT_VALUE        = None
    DEFAULT_RANGE        = None

    def __init__(self, device=None, preferred=None, parent=None):
        super().__init__(device=device, parent=parent)
        self._preferred = preferred

    # override
    def updateWithDeviceImpl(self, device):
        if device is not None:
            self.fireRangeChanged()
            self.fireSettingsChanged()

    def fireSettingsChanged(self):
        """fires the settingsChanged event with the current settings (auto/preferred/value)."""
        self.settingsChanged.emit(self.auto, self.preferred, self.value)

    def fireRangeChanged(self):
        """fires the rangeChanged event with the current valid range."""
        m, M = self.getRange()
        self.rangeChanged.emit(m, M)

    def isAuto(self):
        if self._device:
            try:
                return self.isAutoImpl()
            except RuntimeError as e:
                self.fireDriverError(e)
        else:
            return self.DEFAULT_AUTO

    def setAuto(self, auto):
        if self._device is None:
            self.message.emit("warning", f"Device not open: attempted to set {self.AUTO_PARAMETER_LABEL} without opening the device.")
            return
        try:
            self.setAutoImpl(bool(auto))
            self.fireSettingsChanged()
        except RuntimeError as e:
            self.fireDriverError(e)

    def getPreferred(self):
        if not self._preferred:
            return self.getValueImpl()
        else:
            return self._preferred

    def setPreferred(self, value):
        """the underlying setPreferredImpl() may or may not update the actual value,
        depending on the mode of the device."""
        self._preferred = value
        if self._device:
            try:
                m, M = self.getRange()
                if m > value:
                    self.message("warning", f"Value {value} is below the minimum acceptable {self.PARAMETER_LABEL}.")
                    value = m
                elif M < value:
                    self.message("warning", f"Value {value} is above the maximum acceptable {self.PARAMETER_LABEL}.")
                    value = M
                self.setValueImpl(value)
            except RuntimeError as e:
                self.fireDriverError(e)
        self.fireSettingsChanged()

    def getValue(self):
        """returns the current (actual, manual) value."""
        if not self._device:
            return self.DEFAULT_VALUE
        else:
            try:
                return self.getValueImpl()
            except RuntimeError as e:
                self.fireDriverError(e)
                return self.DEFAULT_VALUE

    def getRange(self):
        """returns (min, max) for the manual settings."""
        if not self._device:
            return self.DEFAULT_RANGE
        try:
            return self.getRangeImpl()
        except RuntimeError as e:
            self.fireDriverError(e)
            return self.DEFAULT_RANGE

    auto      = property(fget=isAuto, fset=setAuto)
    preferred = property(fget=getPreferred, fset=setPreferred)
    value     = property(fget=getValue)
    range     = property(fget=getRange)

    def isAutoImpl(self):
        """it can be assumed that the device be non-None."""
        raise NotImplementedError("isAutoImpl")

    def setAutoImpl(self, status):
        """it can be assumed that the device be non-None."""
        raise NotImplementedError("setAutoImpl")

    def getRangeImpl(self):
        """it can be assumed that the device be non-None."""
        raise NotImplementedError("getRangeImpl")

    def getValueImpl(self):
        """it can be assumed that the device be non-None."""
        raise NotImplementedError("getValueImpl")

    def setValueImpl(self, value):
        """it can be assumed that the device be non-None, and 'value' be within the range as given by getRangeImpl()."""
        raise NotImplementedError("setValueImpl")

class SelectionModel(DeviceSetting):
    PARAMETER_LABEL  = None
    READ_FROM_DEVICE = False
    DEFAULT_OPTIONS  = ("",)
    DEFAULT_VALUE    = ""

    selectionChanged = _QtCore.pyqtSignal(str)
    optionsChanged   = _QtCore.pyqtSignal(tuple)

    def __init__(self, device=None, parent=None):
        super().__init__(device=device, parent=parent)

    # override
    def updateWithDeviceImpl(self, device):
        if (device is not None) and self.READ_FROM_DEVICE:
            self.fireOptionsChanged()
            self.fireSelectionChanged()

    def fireOptionsChanged(self):
        self.optionsChanged.emit(self.options)

    def fireSelectionChanged(self):
        self.selectionChanged.emit(self.value)

    def getOptions(self):
        if self.READ_FROM_DEVICE:
            if not self._device:
                return self.DEFAULT_OPTIONS
            else:
                try:
                    return self.getOptionsImpl()
                except RuntimeError as e:
                    self.fireDriverError(e)
                    return self.DEFAULT_OPTIONS
        else:
            return self.getOptionsImpl()

    def getValue(self):
        """returns the currently selected option."""
        if self.READ_FROM_DEVICE:
            if not self._device:
                return self.DEFAULT_OPTIONS[0]
            else:
                try:
                    value = self.getValueImpl()
                    if value not in self.options:
                        return self.options[0]
                    else:
                        return value
                except RuntimeError as e:
                    self.fireDriverError(e)
                    return self.options[0]
        else:
            return self.getValueImpl()

    def setValue(self, value):
        if value not in self.options:
            self.message.emit("error", f"Unexpected option: Unexpected option for {self.PARAMETER_LABEL}': {value}'")
            return
        if self.READ_FROM_DEVICE:
            if self._device is None:
                self.message.emit("warning", f"Device not open: attempted to set {self.PARAMETER_LABEL} without opening the device.")
                return
            try:
                self.setValueImpl(value)
                self.fireSelectionChanged()
            except RuntimeError as e:
                self.fireDriverError(e)
        else:
            self.setValueImpl(value)
            self.fireSelectionChanged()

    options = property(fget=getOptions)
    value   = property(fget=getValue, fset=setValue)

    def getOptionsImpl(self):
        """it can be assumed that the device be non-None."""
        raise NotImplementedError("getOptionsImpl")

    def getValueImpl(self):
        """it can be assumed that the device be non-None."""
        raise NotImplementedError("getValueImpl")

    def setValueImpl(self, value):
        """it can be assumed that the device be non-None, and the value be one of the options given by getOptionsImpl()."""
        raise NotImplementedError("setValueImpl")
