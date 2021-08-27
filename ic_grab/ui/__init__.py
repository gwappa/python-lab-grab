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
from datetime import datetime as _datetime
import json as _json

from .. import LOGGER as _LOGGER

try:
    from pyqtgraph.Qt import QtCore as _QtCore, \
                             QtGui as _QtGui, \
                             QtWidgets as _QtWidgets

    APP = _QtGui.QApplication([])

    def run():
        APP.exec()

    class SessionManager(_QtCore.QObject):
        """manages the non-graphical state of the app."""
        message = _QtCore.pyqtSignal(str, str)

        def __init__(self, parent=None):
            super().__init__(parent=parent)
            self._experiment  = experiment.Experiment.instance()
            self._control     = control.DeviceControl()
            self._acquisition = acquisition.AcquisitionSettings()
            self._storage     = storage.StorageService.instance()

            for _, component in self.items():
                component.message.connect(self.handleMessageFromChild)
            self.message.connect(self.log)

            self._control.openedDevice.connect(self._updateWithOpeningDevice)
            self._control.closedDevice.connect(self._updateWithClosingDevice)
            self._control.acquisitionReady.connect(self._initializeAcquisition)
            self._control.acquisitionEnded.connect(self._finalizeAcquisition)

            self._storage.interruptAcquisition.connect(self._dealWithEncodingError)

        def items(self):
            return (
                ("experiment",  self._experiment),
                (None,          self._control),
                ("acquisition", self._acquisition),
                ("storage",     self._storage),
            )

        def log(self, level, content):
            getattr(_LOGGER, level)(content)

        def handleMessageFromChild(self, level, content):
            self.message.emit(level, content)

        def as_dict(self):
            out = dict(timestamp=str(_datetime.now()))
            for key, component in self.items():
                if key is None:
                    # not saved
                    continue
                out[key] = component.as_dict()
            return out

        def load_dict(self, cfg):
            if ("acquisition" in cfg.keys()) and ("device" in cfg["acquisition"].keys()):
                self.control.openDevice(cfg["acquisition"]["device"])

            for key, component in self.items():
                if (not key) or (key not in cfg.keys()):
                    continue
                try:
                    component.load_dict(cfg[key])
                except:
                    pass

        def save(self, path):
            path = _Path(path)
            with open(path, "w") as out:
                _json.dump(self.as_dict(), out, indent=4)
            self.message.emit("info", f"saved settings to: {path.name}")

        def load(self, path):
            path = _Path(path)
            with open(path, "r") as src:
                self.load_dict(_json.load(src))
            self.message.emit("info", f"loaded settings from: {path.name}")

        @property
        def experiment(self):
            return self._experiment

        @property
        def control(self):
            return self._control

        @property
        def acquisition(self):
            return self._acquisition

        @property
        def storage(self):
            return self._storage

        def _updateWithOpeningDevice(self, device):
            self._acquisition.updateWithDevice(device)

        def _updateWithClosingDevice(self):
            self._acquisition.updateWithDevice(None)

        def _initializeAcquisition(self, descriptor, store_frames):
            if store_frames == True:
                if self._acquisition.framerate.auto == True:
                    rate = self._acquisition.framerate.value
                else:
                    rate = self._acquisition.framerate.preferred
                self._storage.prepare(framerate=rate, descriptor=descriptor)
                self._control.frameReady.connect(self._storage.write)

        def _dealWithEncodingError(self, msg):
            self._control.setAcquisitionMode(utils.AcquisitionModes.IDLE)
            self.message.emit("error", "Encoding failed unexpectedly: Please refer to the console for more details")

        def _finalizeAcquisition(self):
            if self._storage.is_running():
                self._storage.close()
            # in any case
            try:
                self._control.frameReady.disconnect(self._storage.write)
            except TypeError: # it has not been connected
                pass

    class MainWindow(_QtWidgets.QMainWindow):
        DEFAULT_TITLE    = "IC-GRAB"
        DEFAULT_GEOMETRY = (100, 100, 1200, 720) # X, Y, W, H

        def __init__(self, title=None, parent=None, show=True):
            super().__init__(parent=parent)
            if title is None:
                title = self.DEFAULT_TITLE
            self.setWindowTitle(title)
            self.setGeometry(*self.DEFAULT_GEOMETRY)
            self._widget = _QtWidgets.QWidget()
            self._layout = _QtWidgets.QGridLayout()
            self.setCentralWidget(self._widget)
            self._widget.setLayout(self._layout)

            # create control objects
            self._session    = SessionManager()
            self._session.message.connect(self.updateWithMessage)

            self._exp_edit     = views.ExperimentSettings(self._session)
            self._deviceselect = views.DeviceSelector(self._session)
            self._frameformat  = views.FrameFormatSettings(self._session)
            self._acquisition  = views.AcquisitionSettings(self._session)
            self._storage_edit = views.StorageSettings(self._session)
            self._frame        = views.FrameView(self._session)

            # add commands bar
            self._commands     = commands.CommandBar(self._session)

            # add child components to the main widget
            self._layout.addWidget(self._frame, 0, 0, 5, 1)
            self._layout.addWidget(self._exp_edit, 0, 1)
            self._layout.addWidget(self._deviceselect, 1, 1)
            self._layout.addWidget(self._frameformat, 2, 1)
            self._layout.addWidget(self._acquisition, 3, 1)
            self._layout.addWidget(self._storage_edit, 4, 1)
            self._layout.addWidget(self._commands, 5, 0, 1, 2)
            self._layout.setColumnStretch(0, 2)
            self._layout.setColumnStretch(1, 1)
            self._layout.setRowStretch(0, 6)
            self._layout.setRowStretch(1, 2)
            self._layout.setRowStretch(2, 4)
            self._layout.setRowStretch(3, 6)
            self._layout.setRowStretch(4, 5)
            self._layout.setRowStretch(5, 1)
            self.statusBar() # create one
            if show == True:
                self.show()

        def updateWithMessage(self, level, message):
            if level == "info":
                self.statusBar().showMessage(message)
            elif level == "debug":
                pass # ignore
            elif level in ("warning", "error"):
                elems = message.split(":")
                if len(elems) > 1:
                    title = elems[0]
                else:
                    title = ""
                if level == "error":
                    _QtWidgets.QMessageBox.critical(self, title, message)
                else: # warning
                    _QtWidgets.QMessageBox.warning(self, title, message)
            else:
                _LOGGER.warning(f"MainWindow has not been set up for handling the '{level}' log level.")

    from . import control
    from . import experiment
    from . import acquisition
    from . import storage
    from . import views
    from . import commands
    from . import utils

except ImportError:
    raise RuntimeError("an error occurred while attempting to import 'pyqtgraph'. install it, or fix the installation.")
