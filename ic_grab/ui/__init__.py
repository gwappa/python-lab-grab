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

            # TODO: connect components with each other

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
                if not key:
                    # not saved
                    continue
                out[key] = component.as_dict()
            return out

        def load_dict(self, cfg):
            for key, component in self.items():
                if (not key) or (key not in cfg.keys()):
                    continue
                component.load_dict(cfg[key])

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
            self._control    = device.DeviceControl()
            self._experiment = experiment.Experiment.instance()
            self._storage    = storage.StorageService.instance()
            self._control.message.connect(self.updateWithMessage)
            self._experiment.message.connect(self.updateWithMessage)
            self._storage.message.connect(self.updateWithMessage)

            self._deviceselect = views.DeviceSelector(controller=self._control)
            self._frameformat  = views.FrameFormatSettings(controller=self._control)
            self._acquisition  = views.AcquisitionSettings(controller=self._control)
            self._exp_edit     = views.ExperimentSettings(controller=self._control,
                                                          experiment=self._experiment)
            self._storage_edit = views.StorageSettings(controller=self._control,
                                                       storage_service=self._storage)
            self._frame        = views.FrameView(controller=self._control)

            # add commands bar
            self._commands     = commands.CommandBar(controller=self._control)

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
            else:
                _LOGGER.warning(f"MainWindow has not been set up for handling the '{level}' log level.")

    from . import control
    from . import experiment
    from . import acquisition
    from . import storage
    from . import views
    from . import commands

except ImportError:
    raise RuntimeError("an error occurred while attempting to import 'pyqtgraph'. install it, or fix the installation.")
