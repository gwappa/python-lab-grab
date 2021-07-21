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

            # add device selector
            ## TODO: set controller for the selector, instead of setting selector for the control
            self._layout.addWidget(self._control.selector, 1, 1)
            self.statusBar() # create one
            if show == True:
                self.show()

        def updateWithMessage(self, level, message):
            if level == "info":
                self.statusBar().showMessage(message)
            else:
                _LOGGER.warning(f"MainWindow has not been set up for handling the '{level}' log level.")

    from . import device
    
except ImportError:
    raise RuntimeError("an error occurred while attempting to import 'pyqtgraph'. install it, or fix the installation.")
