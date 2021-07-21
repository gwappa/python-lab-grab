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
        DEFAULT_GEOMETRY = (100, 100, 800, 640) # X, Y, W, H

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

            # create device control
            self._control = device.DeviceControl()
            self._control.message.connect(self.updateWithMessage)
            self._deviceselect = views.DeviceSelector(controller=self._control)
            self._frameformat  = views.FrameFormatSettings(controller=self._control)
            self._acquisition  = views.AcquisitionSettings(controller=self._control)

            # add device selector
            ## TODO: set controller for the selector, instead of setting selector for the control
            self._layout.addWidget(self._deviceselect, 1, 1)
            self._layout.addWidget(self._frameformat, 2, 1)
            self._layout.addWidget(self._acquisition, 3, 1)
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

except ImportError:
    raise RuntimeError("an error occurred while attempting to import 'pyqtgraph'. install it, or fix the installation.")
