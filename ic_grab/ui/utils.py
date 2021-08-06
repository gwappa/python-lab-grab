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

from .. import LOGGER as _LOGGER

def check_status_notristate(status):
    if status == _QtCore.Qt.Unchecked:
        return False
    elif status == _QtCore.Qt.Checked:
        return True
    else:
        raise ValueError(f"tristate check box is not supported")

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

class ViewGroup(_QtWidgets.QGroupBox, ControllerInterface):
    """a group box view being controlled by a DeviceControl object."""
    def __init__(self, title="Group",
                 controller=None,
                 parent=None,
                 connections=dict(from_controller=(), from_interface=())):
        _QtWidgets.QGroupBox.__init__(self, title, parent=parent)
        self._layout = _QtWidgets.QGridLayout()
        self.setLayout(self._layout)
        ControllerInterface.__init__(self,
                                     controller=controller,
                                     connections=connections)

    def _addFormItem(self, item, row, col):
        self._layout.addWidget(item.label,  row,  col, alignment=_QtCore.Qt.AlignRight)
        self._layout.addWidget(item.widget, row, col+1)
