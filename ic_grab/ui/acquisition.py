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
        self._framerate = FrameRateSetting(device=device, parent=self)
        self._exposure  = ExposureSetting(device=device, parent=self)
        self._gain      = GainSetting(device=device, parent=self)
        self._strobe    = StrobeSetting(device=device, parent=self)

    def items(self):
        return (
            ("frame-format", self._format),
            ("frame-rate",   self._framerate),
            ("exposure",     self._exposure),
            ("gain",         self._gain),
            ("strobe",       self._strobe),
        )

    # override
    def updateWithDeviceImpl(self, device):
        for obj in (self._format, self._framerate, self._exposure, self._gain, self._strobe):
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
            if self._device.unique_name != device_name:
                self.message.emit("warning", "Different device: A different device name is specified in the config. Configuration procedures may not work as being specified.")
        else:
            self.message.emit("warning", "Generic configuration: the device name is not specified in the config. Configuration procedures may not work as being specified.")

        for key, component in self.items():
            if not key in cfg.keys():
                # do not attempt to configure this component
                continue
            component.load_dict(cfg[key])

    @property
    def format(self):
        return self._format

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
    def isAutoImpl(self):
        return not self._device.triggered

    # override
    def setAutoImpl(self, status):
        try:
            self._device.triggered = not status
        except AttributeError as e:
            self.message.emit("error", "Not supported: Triggering modes cannot be specified on this device.")

    # override
    def getValueImpl(self):
        return self._device.frame_rate

    # override
    def setValueImpl(self, value):
        self._device.frame_rate = float(value)

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

    def __init__(self, device=None, preferred=preferred, parent=None):
        super().__init__(device=device, preferred=preferred, parent=parent)

    # override
    def isAutoImpl(self):
        return self._device.auto_exposure

    # override
    def setAutoImpl(self, status):
        self._device.auto_exposure = status

    # override
    def getRangeImpl(self):
        return self._device.exposure_range_us

    # override
    def getValueImpl(self):
        return self.exposure_us

    # override
    def setValueImpl(self, value):
        self._device.exposure_us = int(value)

class GainSetting(_models.ValueModel):
    PARAMETER_LABEL      = "gain"
    AUTO_PARAMETER_LABEL = "auto-gain"
    DEFAULT_RANGE        = (0, 10)
    DEFAULT_AUTO         = False
    DEFAULT_VALUE        = 1

    def __init__(self, device=None, preferred=preferred, parent=None):
        super().__init__(device=device, preferred=preferred, parent=parent)

    # override
    def isAutoImpl(self):
        return self._device.auto_gain

    # override
    def setAutoImpl(self, status):
        self._device.auto_gain = status

    # override
    def getRangeImpl(self):
        m, M = self._device.gain_range
        return _math.ceil(m), _math.floor(M)

    # override
    def getValueImpl(self):
        return self.gain

    # override
    def setValueImpl(self, value):
        self._device.gain = float(value)

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