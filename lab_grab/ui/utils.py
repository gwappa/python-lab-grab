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

import re as _re
from collections import namedtuple as _namedtuple

from pyqtgraph.Qt import QtCore as _QtCore, \
                         QtGui as _QtGui, \
                         QtWidgets as _QtWidgets

from .. import logger as _logger

_LOGGER = _logger()

def image_to_display(img):
    if img.ndim == 3:
        return img.transpose((1,0,2))[:,::-1]
    else:
        return img.T[:,::-1]

def check_status_notristate(status):
    if status == _QtCore.Qt.Unchecked:
        return False
    elif status == _QtCore.Qt.Checked:
        return True
    else:
        raise ValueError(f"tristate check box is not supported")

def set_dirty(widget):
    widget.setStyleSheet("color: red")

def clear_dirty(widget):
    widget.setStyleSheet("")

class StrobeModes:
    DISABLED       = "Disabled"
    GRAB_ONLY      = "Grab only"
    FOCUS_AND_GRAB = "Focus and Grab"

    @staticmethod
    def iterate():
        return (StrobeModes.DISABLED,
                StrobeModes.GRAB_ONLY,
                StrobeModes.FOCUS_AND_GRAB)

    @staticmethod
    def requires_strobe(strobemode, acqmode):
        if acqmode == AcquisitionModes.FOCUS:
            return strobemode == StrobeModes.FOCUS_AND_GRAB
        elif acqmode == AcquisitionModes.GRAB:
            return strobemode in (StrobeModes.FOCUS_AND_GRAB, StrobeModes.GRAB_ONLY)
        else:
            return False

class AcquisitionModes:
    FOCUS   = "FOCUS" # start FOCUS mode
    GRAB    = "GRAB"  # start GRAB mode
    IDLE    = "ABORT" # stop the current acquisition

def transpose_image(img):
    if img.ndim == 3:
        return img.transpose((1,0,2))
    else:
        return img.T

class FrameRotation:
    """a set of functions intended for _clockwise_ rotation of acquired frames."""

    @staticmethod
    def R270(img):
        """as it is read from the IS camera."""
        return img

    @staticmethod
    def R0(img):
        """+90 from the original image (from the IS camera)."""
        return transpose_image(img)[:,::-1]

    @staticmethod
    def R90(img):
        """+180 from the original image (from the IS camera)."""
        return img[::-1,::-1]

    @staticmethod
    def R180(img):
        """-90 from the original image (from the IS camera)."""
        return transpose_image(img)[::-1,:]

    OPTIONS = None

    @classmethod
    def _init(cls):
        if cls.OPTIONS is None:
            cls.OPTIONS = {
                "0":   cls.R0,
                "90":  cls.R90,
                "180": cls.R180,
                "270": cls.R270,
            }

    @staticmethod
    def iterate():
        FrameRotation._init()
        return tuple(key for key in FrameRotation.OPTIONS.keys())

    @staticmethod
    def get(key):
        FrameRotation._init()
        return FrameRotation.OPTIONS[key]

class FrameFormat(_namedtuple("_FrameFormat", ("pixel", "width", "height"))):
    FORMAT_PATTERN = _re.compile(r"([a-zA-Z0-9-]+) \((\d+)x(\d+)\)")

    @classmethod
    def from_name(cls, format_name):
        matched = cls.FORMAT_PATTERN.match(format_name)
        if not matched:
            raise RuntimeError(f"unexpected format name: {format_name}")
        pixel, width, height = [matched.group(i) for i in (1, 2, 3)]
        return cls(pixel, int(width), int(height))

    @property
    def shape(self):
        return (self.width, self.height)

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

class ControllerConnections:
    def __init__(self, parent, from_controller=(), from_interface=()):
        self._parent          = parent
        self._from_controller = from_controller
        self._from_interface  = from_interface

    def iterate(self, controller):
        for src, dst in self._from_controller:
            yield (getattr(controller, src), getattr(self._parent, dst))
        for src, dst in self._from_interface:
            yield (getattr(self._parent, src), getattr(controller, dst))

class ControllerInterface:
    """the mix-in class to manage connections with the device controller."""
    def __init__(self, controller=None,
                 connections=dict(from_controller=(), from_interface=())):
        self._controller = None
        self._updating = False # flag to check if it is currently updating to reflect the controller state
        self._conns    = ControllerConnections(self, **connections)
        self.controller = controller

    @property
    def controller(self):
        return self._controller

    @controller.setter
    def controller(self, obj):
        if self._controller is not None:
            for src, dst in self._conns.iterate(self._controller):
                src.disconnect(dst)
            self._disconnectFromController(self._controller)
        self._controller = obj
        if self._controller is not None:
            for src, dst in self._conns.iterate(self._controller):
                src.connect(dst)
            self._connectToController(self._controller)

    def _connectToController(self, obj):
        """may be implemented by the subclass, in case connections were
        not supplied as the `connections` argument upon initialization.

        `obj` can be assumed to be non-None.
        """
        pass

    def _disconnectFromController(self, obj):
        """may be implemented by the subclass, in case connections were
        not supplied as the `connections` argument upon initialization.

        `obj` can be assumed to be non-None.
        """
        pass

class SessionControl:
    def initWithSession(self, session):
        self._session  = session
        self._updating = True
        self.connectWithSession(session)
        self._updating = False

    def connectWithSession(self, session):
        pass # to be overridden by the subclasses

    @property
    def session(self):
        return self._session

class ViewGroup(_QtWidgets.QGroupBox, SessionControl):
    """a group box view being controlled by a DeviceControl object."""
    def __init__(self, title="Group", session=None, parent=None):
        _QtWidgets.QGroupBox.__init__(self, title, parent=parent)
        self.initWithSession(session)
        self._layout  = _QtWidgets.QGridLayout()
        self.setLayout(self._layout)

    def _addFormItem(self, item, row, col, widget_colspan=1):
        self._layout.addWidget(item.label,  row,  col, alignment=_QtCore.Qt.AlignRight)
        self._layout.addWidget(item.widget, row, col+1, 1, widget_colspan)

    def _addWidget(self, widget, row, col, rowspan=1, colspan=1, alignment=_QtCore.Qt.AlignLeft):
        self._layout.addWidget(widget, row, col, rowspan, colspan, alignment=alignment)

class InvalidatableLineEdit(_QtWidgets.QLineEdit):
    edited = _QtCore.pyqtSignal()

    def __init__(self, text="", parent=None):
        super().__init__(text, parent=parent)
        self.textChanged.connect(self.dispatchEdited)
        self._editing  = False

    @property
    def editing(self):
        return self._editing

    def dispatchEdited(self):
        self._editing = True
        self.edited.emit()

    def invalidate(self):
        set_dirty(self)

    def revalidate(self):
        self._editing = False
        clear_dirty(self)

class InvalidatableSpinBox(_QtWidgets.QSpinBox):
    """invalidatable version of QSpinBox."""
    edited = _QtCore.pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.editingFinished.connect(self.dispatchValueChange)
        self._editing  = False
        self._pressing = False

    @property
    def editing(self):
        return self._editing

    # override
    def stepBy(self, steps):
        self._pressing = True
        self._editing  = False
        super().stepBy(steps)
        self._pressing = False

    # override
    def valueFromText(self, text):
        if self._pressing == False:
            self._editing = True
            self.edited.emit()
        return super().valueFromText(text)

    def dispatchValueChange(self):
        self._editing = False
        self.valueChanged.emit(self.value())

    def invalidate(self):
        set_dirty(self)

    def revalidate(self):
        self._editing = False
        clear_dirty(self)

    def edit(self, value):
        self._editing = True
        self.edited.emit()
        self.setValue(value)

class InvalidatableDoubleSpinBox(_QtWidgets.QDoubleSpinBox):
    """invalidatable version of QDoubleSpinBox."""
    edited = _QtCore.pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.editingFinished.connect(self.dispatchValueChange)
        self._editing  = False
        self._pressing = False

    @property
    def editing(self):
        return self._editing

    # override
    def stepBy(self, steps):
        self._pressing = True
        self._editing  = False
        super().stepBy(steps)
        self._pressing = False

    # override
    def valueFromText(self, text):
        if self._pressing == False:
            self._editing = True
            self.edited.emit()
        return super().valueFromText(text)

    def dispatchValueChange(self):
        self._editing = False
        self.valueChanged.emit(self.value())

    def invalidate(self):
        set_dirty(self)

    def revalidate(self):
        self._editing = False
        clear_dirty(self)
