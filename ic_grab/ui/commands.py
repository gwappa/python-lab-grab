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

class CommandBar(_QtWidgets.QWidget):
    def __init__(self, controller=None, parent=None):
        super().__init__(parent=parent)
        self._layout = _QtWidgets.QHBoxLayout()
        self.setLayout(self._layout)
        self._save   = SaveConfigButton(controller=controller)
        self._load   = LoadConfigButton(controller=controller)
        self._focus  = FocusButton(controller=controller)
        self._grab   = GrabButton(controller=controller)
        self._layout.addWidget(self._load)
        self._layout.addWidget(self._save)
        self._layout.addStretch(-1)
        self._layout.addWidget(self._focus)
        self._layout.addWidget(self._grab)

class CommandButton(_QtWidgets.QPushButton):
    def __init__(self, label, controller=None, parent=None):
        super().__init__(label, parent=parent)
        self.setEnabled(False)

class SaveConfigButton(CommandButton):
    def __init__(self, label="Save...", controller=None, parent=None):
        super().__init__(label, controller=controller, parent=parent)

class LoadConfigButton(CommandButton):
    def __init__(self, label="Load...", controller=None, parent=None):
        super().__init__(label, controller=controller, parent=parent)

class FocusButton(CommandButton):
    def __init__(self, label="FOCUS", controller=None, parent=None):
        super().__init__(label, controller=controller, parent=parent)

class GrabButton(CommandButton):
    def __init__(self, label="GRAB", controller=None, parent=None):
        super().__init__(label, controller=controller, parent=parent)
