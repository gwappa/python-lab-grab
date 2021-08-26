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
    def __init__(self, session=None, parent=None):
        super().__init__(parent=parent)
        self._layout = _QtWidgets.QHBoxLayout()
        self.setLayout(self._layout)
        self._save   = SaveConfigButton(session)
        self._load   = LoadConfigButton(session)
        self._focus  = FocusButton(session)
        self._grab   = GrabButton(session)
        self._layout.addWidget(self._load)
        self._layout.addWidget(self._save)
        self._layout.addStretch(-1)
        self._layout.addWidget(self._focus)
        self._layout.addWidget(self._grab)

class CommandButton(_QtWidgets.QPushButton, _utils.SessionControl):
    def __init__(self, label, session, parent=None,
                 connections=dict(from_controller=(), from_interface=())):
        _QtWidgets.QPushButton.__init__(self, label, parent=parent)
        self.setEnabled(False)
        _utils.SessionControl.__init__(self)
        self.initWithSession(session)
        self.clicked.connect(self.dispatchRequest)

    # override
    def connectWithSession(self, session):
        session.control.openedDevice.connect(self.updateWithOpeningDevice)
        session.control.closedDevice.connect(self.updateWithClosingDevice)
        session.control.updatedAcquisitionMode.connect(self.updateWithAcquisitionMode)

    def updateWithOpeningDevice(self, device):
        pass

    def updateWithClosingDevice(self):
        pass

    def updateWithAcquisitionMode(self, oldmode, newmode):
        pass

    def dispatchRequest(self):
        pass

class SaveConfigButton(CommandButton):
    def __init__(self, session, label="Save...", parent=None):
        super().__init__(label, session, parent=parent)

class LoadConfigButton(CommandButton):
    def __init__(self, session, label="Load...", parent=None):
        super().__init__(label, session, parent=parent)

class AcquireButton(CommandButton):
    LABEL_START = _utils.AcquisitionModes.IDLE
    LABEL_STOP  = _utils.AcquisitionModes.IDLE

    requestedAcquisitionMode = _QtCore.pyqtSignal(str)

    def __init__(self, session, label=None, parent=None):
        if label is None:
            label = self.LABEL_START
        super().__init__(label, session, parent=parent)

    # override
    def connectWithSession(self, session):
        super().connectWithSession(session)
        self.requestedAcquisitionMode.connect(session.control.setAcquisitionMode)

    # override
    def updateWithOpeningDevice(self, device):
        self.setEnabled(True)

    # override
    def updateWithClosingDevice(self):
        self.setEnabled(False)

    # override
    def dispatchRequest(self):
        self.requestedAcquisitionMode.emit(self.text())

    # override
    def updateWithAcquisitionMode(self, oldmode, newmode):
        if oldmode == self.LABEL_START:
            # has been in the acquisition started by the command for this button
            self.finishedAcquisition()
            if newmode == _utils.AcquisitionModes.IDLE:
                self.setText(self.LABEL_START)
            else:
                raise RuntimeError(f"unexpected mode transition from {oldmode} to {newmode}")
        elif newmode == self.LABEL_START:
            # started the acquisition handled by this button
            self.startedAcquisition()
            self.setText(self.LABEL_STOP)
        elif oldmode == _utils.AcquisitionModes.IDLE:
            # started the other acquisition mode
            self.setEnabled(False)
        elif newmode == _utils.AcquisitionModes.IDLE:
            # finished the other acquisition mode
            self.setEnabled(True)
        else:
            raise RuntimeError(f"unexpected mode transition from {oldmode} to {newmode}")

    def startedAcquisition(self):
        """a callback which could be implemented by the subclass."""
        pass

    def finishedAcquisition(self):
        """a callback which could be implemented by the subclass."""
        pass

class FocusButton(AcquireButton):
    LABEL_START = _utils.AcquisitionModes.FOCUS

    def __init__(self, session, label=None, parent=None):
        super().__init__(session, label=label, parent=parent)

class GrabButton(AcquireButton):
    LABEL_START = _utils.AcquisitionModes.GRAB

    def __init__(self, session, label=None, parent=None):
        super().__init__(session, label=label, parent=parent)
