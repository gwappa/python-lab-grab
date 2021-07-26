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

class ViewGroup(_QtWidgets.QGroupBox):
    """a group box view being controlled by a DeviceControl object.

    important note
    --------------
    The first _connectToController() will _not_ be called by ViewGroup.__init__().
    It must be instead called explicitly during initialization of the subclass.
    """
    def __init__(self, title="Group",
                 controller=None,
                 parent=None):
        super().__init__(title, parent=parent)
        self._controller = controller
        self._layout = _QtWidgets.QGridLayout()
        self.setLayout(self._layout)
        self._updating = False # flag to check if it is currently updating to reflect the controller state

    @property
    def controller(self):
        return self._controller

    @controller.setter
    def controller(self, obj):
        if self._controller is not None:
            self._disconnectFromController(self._controller)
        self._controller = obj
        if self._controller is not None:
            self._connectToController(self._controller)

    def _connectToController(self, obj):
        """supposed to be implemented by the subclass.
        `obj` can be assumed to be non-None."""
        pass

    def _disconnectFromController(self, obj):
        """supposed to be implemented by the subclass.
        `obj` can be assumed to be non-None."""
        pass

    def _addFormItem(self, item, row, col):
        self._layout.addWidget(item.label,  row,  col, alignment=_QtCore.Qt.AlignRight)
        self._layout.addWidget(item.widget, row, col+1)
