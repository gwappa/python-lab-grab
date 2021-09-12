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

import math as _math

from . import models as _models
from . import utils as _utils

class AcquisitionSettings(_models.DeviceSetting):
    def __init__(self, device=None, parent=None):
        super().__init__(device=device, parent=parent)
        self._format    = FrameFormatSetting(device=device, parent=self)
        self._rotation  = FrameRotationSetting(device=device, parent=self)
        self._framerate = FrameRateSetting(device=device, parent=self)
        self._exposure  = ExposureSetting(device=device, parent=self)
        self._gain      = GainSetting(device=device, parent=self)
        self._gamma     = GammaSetting(device=device, parent=self)
        self._strobe    = StrobeSetting(device=device, parent=self)

        # enables this AcquisitionSettings object
        # to 'raise' the message events from its children altogether
        for _, component in self.items():
            component.message.connect(self.handleMessageFromChild)

    def items(self):
        return (
            ("frame-format", self._format),
            ("frame-rotation", self._rotation),
            ("frame-rate",   self._framerate),
            ("exposure",     self._exposure),
            ("gain",         self._gain),
            ("gamma",        self._gamma),
            ("strobe",       self._strobe),
        )

    def handleMessageFromChild(self, level, content):
        self.message.emit(level, content)

    # override
    def updateWithDeviceImpl(self, device):
        for _, obj in self.items():
            obj.updateWithDevice(device)

    # override
    def as_dict(self):
        out = {}
        if self._device is not None:
            out["device"] = self._device.unique_name
        for key, component in self.items():
            out[key] = component.as_dict()
        return out

    # override
    def load_dict(self, cfg):
        device_name = cfg.get("device", None)
        if device_name is not None:
            if self._device is None:
                self.message.emit("warning", "Device not open: Most acquisition settings will not be loaded properly.")
            elif self._device.unique_name != device_name:
                self.message.emit("warning", "Different device: A different device name is specified in the settings. Configuration procedures may not work properly.")
        else:
            self.message.emit("warning", "Device unspecified: the device name is not specified in the settings. Configuration procedures may not work properly.")

        for key, component in self.items():
            if not key in cfg.keys():
                # do not attempt to configure this component
                continue
            component.load_dict(cfg[key])

    @property
    def format(self):
        return self._format

    @property
    def rotation(self):
        return self._rotation

    @property
    def framerate(self):
        return self._framerate

    @property
    def exposure(self):
        return self._exposure

    @property
    def gain(self):
        return self._gain

    @property
    def gamma(self):
        return self._gamma

    @property
    def strobe(self):
        return self._strobe

class FrameRateSetting(_models.ValueModel):
    """'auto' implies _internal_ triggering (not external)"""
    PARAMETER_LABEL      = "frame rate"
    AUTO_PARAMETER_LABEL = "triggering mode"
    DEFAULT_RANGE        = (0.01, 100_000)
    DEFAULT_AUTO         = True # internal triggering
    DEFAULT_VALUE        = 30

    def __init__(self, device=None, preferred=None, parent=None):
        super().__init__(device=device, preferred=preferred, parent=parent)

    # override
    def as_dict(self):
        out = dict(auto=self.auto)
        if self.auto == True:
            out["value"] = self.value
        elif self._preferred is not None:
            out["value"] = self._preferred
        return out

    # override
    def load_dict(self, cfg):
        if "auto" in cfg.keys():
            self.auto = cfg["auto"]
        if "value" in cfg.keys():
            self.preferred = cfg["value"]

    # override
    def isAutoImpl(self):
        return not self._device.triggered

    # override
    def setAutoImpl(self, status):
        try:
            self._device.triggered = not status
            if status:
                self.message.emit("info", "disabled external triggering")
            else:
                self.message.emit("info", "enabled external triggering")
        except AttributeError as e:
            self.message.emit("error", "Not supported: Triggering modes cannot be specified on this device.")

    # override
    def getValueImpl(self):
        return self._device.frame_rate

    # override
    def setValueImpl(self, value):
        self._device.frame_rate = float(value)
        if self.auto == True:
            self.message.emit("info", f"frame rate: {self._device.frame_rate:.1f} Hz")
        else:
            self.message.emit("info", f"frame rate (externally triggered): {self._preferred:.1f} Hz")

    # override
    def getRangeImpl(self):
        return self.DEFAULT_RANGE

class ExposureSetting(_models.ValueModel):
    """exposure in microseconds."""
    PARAMETER_LABEL      = "exposure"
    AUTO_PARAMETER_LABEL = "auto-exposure"
    DEFAULT_RANGE        = (50, 10_000_000)
    DEFAULT_AUTO         = False
    DEFAULT_VALUE        = 33000 # 33 ms, for 30 Hz acquisition

    def __init__(self, device=None, preferred=None, parent=None):
        super().__init__(device=device, preferred=preferred, parent=parent)

    # override
    def isAutoImpl(self):
        return self._device.auto_exposure

    # override
    def setAutoImpl(self, status):
        self._device.auto_exposure = status
        try:
            mode = "enabled" if self._device.auto_exposure else "disabled"
        except RuntimeError:
            mode = "enabled" if status else "disabled"
        self.message.emit("info", mode + " " + self.AUTO_PARAMETER_LABEL)

    # override
    def getRangeImpl(self):
        return self._device.exposure_range_us

    # override
    def getValueImpl(self):
        return self._device.exposure_us

    # override
    def setValueImpl(self, value):
        self._device.exposure_us = int(value)
        self.message.emit("info", f"manual exposure setting: {self._device.exposure_us} us")

class GainSetting(_models.ValueModel):
    PARAMETER_LABEL      = "gain"
    AUTO_PARAMETER_LABEL = "auto-gain"
    DEFAULT_RANGE        = (0, 10)
    DEFAULT_AUTO         = False
    DEFAULT_VALUE        = 1

    def __init__(self, device=None, preferred=None, parent=None):
        super().__init__(device=device, preferred=preferred, parent=parent)

    # override
    def isAutoImpl(self):
        return self._device.auto_gain

    # override
    def setAutoImpl(self, status):
        self._device.auto_gain = status
        try:
            mode = "enabled" if self._device.auto_exposure else "disabled"
        except RuntimeError:
            mode = "enabled" if status else "disabled"
        self.message.emit("info", mode + " " + self.AUTO_PARAMETER_LABEL)

    # override
    def getRangeImpl(self):
        m, M = self._device.gain_range
        return _math.ceil(m), _math.floor(M)

    # override
    def getValueImpl(self):
        return self._device.gain

    # override
    def setValueImpl(self, value):
        self._device.gain = float(value)
        self.message.emit("info", f"manual gain setting: {self._device.gain:.1f}")

class GammaSetting(_models.ValueModel):
    PARAMETER_LABEL      = "gamma"
    AUTO_PARAMETER_LABEL = "auto-gamma"
    DEFAULT_RANGE        = (0, 5)
    DEFAULT_AUTO         = False
    DEFAULT_VALUE        = 1

    def __init__(self, device=None, preferred=None, parent=None):
        super().__init__(device=device, preferred=preferred, parent=parent)

    # override
    def as_dict(self):
        return dict(value=self.value)

    # override
    def isAutoImpl(self):
        return self.DEFAULT_AUTO

    # override
    def isAutoAvailable(self):
        return False

    # override
    def setAutoImpl(self, status):
        self.message.emit("warning", "auto-gamma is not supported")

    # override
    def getRangeImpl(self):
        m, M = self._device.gamma_range
        return m, M

    # override
    def getValueImpl(self):
        return self._device.gamma

    # override
    def setValueImpl(self, value):
        self._device.gamma = float(value)
        self.message.emit("info", f"gamma setting: {self._device.gamma:.1f}")

class StrobeSetting(_models.SelectionModel):
    PARAMETER_LABEL  = "strobe setting"
    READ_FROM_DEVICE = False
    DEFAULT_OPTIONS  = _utils.StrobeModes.iterate()
    DEFAULT_VALUE    = _utils.StrobeModes.DISABLED

    def __init__(self, device=None, parent=None):
        super().__init__(device=device, parent=parent)
        self._value = self.DEFAULT_VALUE

    # override
    def getOptionsImpl(self):
        return self.DEFAULT_OPTIONS

    # override
    def getValueImpl(self):
        return self._value

    # override
    def setValueImpl(self, value):
        self._value = value
        self.message.emit("info", "strobe mode: " + str(value))

class FrameFormatSetting(_models.SelectionModel):
    PARAMETER_LABEL  = "frame format"
    READ_FROM_DEVICE = True

    def __init__(self, device=None, parent=None):
        super().__init__(device=device, parent=parent)
        self._value = None

    # override
    def getOptionsImpl(self):
        return tuple(item for item in self._device.list_video_formats())

    # override
    def getValueImpl(self):
        if self._value is None:
            return self.options[0]
        else:
            return self._value

    # override
    def setValueImpl(self, value):
        value = str(value)
        self._device.video_format = value
        self._value = value
        self.message.emit("info", "frame format: " + value)

class FrameRotationSetting(_models.SelectionModel):
    PARAMETER_LABEL  = "frame rotation"
    READ_FROM_DEVICE = False
    DEFAULT_OPTIONS  = _utils.FrameRotation.iterate()
    DEFAULT_VALUE    = "0"

    def __init__(self, device=None, parent=None):
        super().__init__(device=device, parent=parent)
        self._value = self.DEFAULT_VALUE

    # override
    def getOptionsImpl(self):
        return self.DEFAULT_OPTIONS

    # override
    def getValueImpl(self):
        return self._value

    # override
    def setValueImpl(self, value):
        value = str(value)
        self._value = value
        self.message.emit("info", f"frame rotation (clockwise): {str(value)} deg")

    @property
    def method(self):
        return _utils.FrameRotation.get(self._value)
