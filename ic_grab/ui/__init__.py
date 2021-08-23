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

try:
    from pyqtgraph.Qt import QtCore as _QtCore, \
                             QtGui as _QtGui, \
                             QtWidgets as _QtWidgets
    from .. import LOGGER as _LOGGER

    APP = _QtGui.QApplication([])

    def run():
        APP.exec()

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

    from . import device
    from . import views
    from . import commands
    from . import experiment
    from . import storage

except ImportError:
    raise RuntimeError("an error occurred while attempting to import 'pyqtgraph'. install it, or fix the installation.")
