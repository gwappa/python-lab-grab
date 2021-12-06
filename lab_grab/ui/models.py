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
from traceback import print_exc as _print_exc

from pyqtgraph.Qt import QtCore as _QtCore
from .. import logger as _logger

_LOGGER = _logger()

def check_error(fun):
    def _call(*args, **kwargs):
        try:
            return fun(*args, **kwargs)
        except:
            _print_exc()
    return _call

NAME_UNKNOWN = "(unknown)"

class DeviceSetting(_QtCore.QObject):
    message = _QtCore.pyqtSignal(str, str) # level, content

    def __init__(self, name=NAME_UNKNOWN, device=None, parent=None):
        super().__init__(parent=parent)
        self._name      = name
        self._device    = device

    def fireDriverError(self, e):
        """emits message() corresponding to the driver error."""
        _LOGGER.debug(f"driver error in '{self.name}': {e}")
        self.message.emit("error", f"Driver error: {e}")

    def getCurrentDevice(self):
        return self._device

    def getSettingName(self):
        return self._name

    def updateWithDevice(self, device):
        self._device = device
        self.updateWithDeviceImpl(device)

    def as_dict(self):
        """supposed to return its setting as a dict object."""
        raise NotImplementedError(f"{self.__class__.__name__}.as_dict")

    def load_dict(self, cfg):
        """supposed to configure this setting object based on the given dict object (non-None)."""
        raise NotImplementedError(f"{self.__class__.__name__}.load_dict")

    device = property(fget=getCurrentDevice, fset=updateWithDevice)
    name   = property(fget=getSettingName)

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

    def __init__(self, name=NAME_UNKNOWN, device=None, preferred=None, parent=None):
        super().__init__(name=name, device=device, parent=parent)
        self._preferred = preferred

    def as_dict(self):
        out = {}
        if self.auto == True:
            out["auto"] = True
            return out
        else:
            out["auto"]      = False
            out["preferred"] = self.preferred
            out["value"]     = self.value
            return out

    def load_dict(self, cfg):
        _LOGGER.debug(f"loading '{self.name}' from config")
        if "auto" in cfg.keys():
            _LOGGER.debug(f"config for '{self.name}': auto-setting found ({cfg['auto']})")
            self.auto = cfg["auto"]
        if "preferred" in cfg.keys():
            _LOGGER.debug(f"config for '{self.name}': preferred value found ({cfg['preferred']})")
            self.preferred = cfg["preferred"]

    # override
    def updateWithDeviceImpl(self, device):
        if device is not None:
            self.fireRangeChanged()
            self.fireSettingsChanged()

    def fireSettingsChanged(self):
        """fires the settingsChanged event with the current settings (auto/preferred/value)."""
        _LOGGER.debug(f"value of '{self.name}' changed to: {self.preferred} (actual: {self.value}, auto: {self.auto})")
        self.settingsChanged.emit(self.auto, self.preferred, self.value)

    def fireRangeChanged(self):
        """fires the rangeChanged event with the current valid range."""
        m, M = self.getRange()
        _LOGGER.debug(f"range of '{self.name}' changed to: ({m}, {M})")
        self.rangeChanged.emit(m, M)

    def isAuto(self):
        try:
            if self.isAutoAvailable() == False:
                return False
            elif self._device is not None:
                try:
                    return self.isAutoImpl()
                except RuntimeError as e:
                    self.fireDriverError(e)
            else:
                return self.DEFAULT_AUTO
        except BaseException as e:
            _LOGGER.info(f"isAuto() failed for '{self.name}': {e}")
            return False

    def setAuto(self, auto):
        if self.isAutoAvailable() == False:
            _LOGGER.debug(f"attempted to set 'auto' for '{self.name}', which does not have the 'auto' property")
        if self._device is None:
            self.message.emit("warning", f"Device not open: attempted to set {self.AUTO_PARAMETER_LABEL} without opening the device.")
            return
        try:
            self.setAutoImpl(bool(auto))
            self.fireSettingsChanged()
        except BaseException as e:
            self.fireDriverError(e)

    def getPreferred(self):
        try:
            if self._preferred is not None:
                return self._preferred
            else:
                return self.getValueImpl()
        except BaseException as e:
            _LOGGER.info(f"getPreferred() failed for '{self.name}': {e}")
            return self.DEFAULT_VALUE

    def setPreferred(self, value):
        """the underlying setValueImpl() may or may not update the actual value,
        depending on the mode of the device and the character of the property of interest."""
        self._preferred = value
        if self._device is not None:
            try:
                m, M = self.getRange()
                if m > value:
                    self.message.emit("warning", f"Value {value} is below the minimum acceptable {self.PARAMETER_LABEL}.")
                    value = m
                elif M < value:
                    self.message.emit("warning", f"Value {value} is above the maximum acceptable {self.PARAMETER_LABEL}.")
                    value = M
                self.setValueImpl(value)
            except BaseException as e:
                self.fireDriverError(e)
        self.fireSettingsChanged()

    def getValue(self):
        """returns the current (actual, manual) value."""
        if self._device is None:
            return self.DEFAULT_VALUE
        else:
            try:
                return self.getValueImpl()
            except BaseException as e:
                self.fireDriverError(e)
                return self.DEFAULT_VALUE

    def getRange(self):
        """returns (min, max) for the manual settings."""
        if self._device is None:
            return self.DEFAULT_RANGE
        try:
            return self.getRangeImpl()
        except BaseException as e:
            self.fireDriverError(e)
            return self.DEFAULT_RANGE

    def isAutoAvailable(self):
        """returns if the device supports auto settings."""
        return True

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

    auto      = property(fget=check_error(isAuto), fset=check_error(setAuto))
    value     = property(fget=check_error(getValue))
    range     = property(fget=check_error(getRange))
    preferred = property(fget=check_error(getPreferred), fset=check_error(setPreferred))

class SelectionModel(DeviceSetting):
    PARAMETER_LABEL  = None
    READ_FROM_DEVICE = False
    DEFAULT_OPTIONS  = ("",)
    DEFAULT_VALUE    = ""

    selectionChanged = _QtCore.pyqtSignal(str)
    optionsChanged   = _QtCore.pyqtSignal(tuple)

    def __init__(self, name=NAME_UNKNOWN, device=None, parent=None):
        super().__init__(name=name, device=device, parent=parent)

    def as_dict(self):
        return dict(value=self.value)

    def load_dict(self, cfg):
        _LOGGER.debug(f"loading '{self.name}' from config")
        if "value" in cfg.keys():
            _LOGGER.debug(f"config for '{self.name}': value found ({cfg['value']})")
            self.value = cfg["value"]

    # override
    def updateWithDeviceImpl(self, device):
        if (device is not None) and (self.READ_FROM_DEVICE == True):
            self.fireOptionsChanged()
            self.fireSelectionChanged()

    def fireOptionsChanged(self):
        _LOGGER.debug(f"option '{self.name}' changed its options: {self.options}")
        self.optionsChanged.emit(self.options)

    def fireSelectionChanged(self):
        _LOGGER.debug(f"selection changed for '{self.name}': {self.value}")
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
            self.message.emit("error", f"Unexpected option: Unexpected option for {self.PARAMETER_LABEL}: '{value}'")
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

    options = property(fget=check_error(getOptions))
    value   = property(fget=check_error(getValue), fset=check_error(setValue))

    def getOptionsImpl(self):
        """it can be assumed that the device be non-None."""
        raise NotImplementedError("getOptionsImpl")

    def getValueImpl(self):
        """it can be assumed that the device be non-None."""
        raise NotImplementedError("getValueImpl")

    def setValueImpl(self, value):
        """it can be assumed that the device be non-None, and the value be one of the options given by getOptionsImpl()."""
        raise NotImplementedError("setValueImpl")
