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
import numpy as _np

import pyqtgraph as _pg
from pyqtgraph.Qt import QtCore as _QtCore, \
                         QtGui as _QtGui, \
                         QtWidgets as _QtWidgets

from . import utils as _utils
from .. import logger as _logger

_LOGGER = _logger()

class FrameView(_QtWidgets.QGraphicsView, _utils.SessionControl):
    INITIAL_DIMS   = (640, 480)
    DEFAULT_COLOR  = (255, 255, 255, 255)
    TARGET_REFRESH = 35 # 30-40 FPS

    def __init__(self, session=None, parent=None):
        super().__init__(parent=parent)
        self.initWithSession(session)
        self._scene   = _QtWidgets.QGraphicsScene()
        self._image   = _pg.ImageItem()
        self._scene.addItem(self._image)
        self._scene.setSceneRect(_QtCore.QRectF(0, 0, *self.INITIAL_DIMS))
        self.setScene(self._scene)
        self._every   = 1
        self._count   = 0

    # override
    def connectWithSession(self, session):
        session.acquisition.format.selectionChanged.connect(self.updateWithFormat)
        session.control.acquisitionReady.connect(self.prepareForAcquisition)
        session.control.frameReady.connect(self.updateWithFrame)
        session.acquisition.framerate.settingsChanged.connect(self.updateWithFrameRateSettings)

    def updateWithFormat(self, format_name):
        if len(format_name) == 0:
            return
        fmt  = _utils.FrameFormat.from_name(format_name)
        dims = fmt.shape
        self._scene.setSceneRect(_QtCore.QRectF(0, 0, *dims))
        self._image.setImage(_np.zeros(dims, dtype=_np.uint8))
        # TODO: set transform to fit the image to the rect

    def prepareForAcquisition(self, desc, rotation, store_frames=None):
        dims = rotation.transform_shape(desc.shape)
        self._scene.setSceneRect(_QtCore.QRectF(0.0, 0.0, float(dims[1]), float(dims[0])))
        img = _np.zeros(dims, dtype=desc.dtype)
        if desc.dtype == _np.uint8:
            self._levels = (0, 255)
        elif desc.dtype == _np.uint16:
            self._levels = (0, 65535)
        else:
            self._levels = None
        self._image.setImage(img, autoLevels=(self._levels is None))
        if self._levels:
            self._image.setLevels(self._levels)
        self._count = 0
        # TODO: set transform to fit the image to the rect

    def updateWithFrameRateSettings(self, auto, preferred, actual):
        if self.TARGET_REFRESH < actual:
            self._every = round(actual / self.TARGET_REFRESH)
        else:
            self._every = 1

    def updateWithFrame(self, frame):
        # `frame` can be assumed to be non-None
        # `frame` must have been already 'rotated'
        self._count += 1
        if self._count == self._every:
            self._image.setImage(frame, autoLevels=(self._levels is None))
            self._count = 0

class ExperimentSettings(_utils.ViewGroup):
    requestSubjectUpdate   = _QtCore.pyqtSignal(str)
    requestDomainUpdate    = _QtCore.pyqtSignal(str)
    requestDateUpdate      = _QtCore.pyqtSignal(_QtCore.QDate)
    requestIndexUpdate     = _QtCore.pyqtSignal(int)
    requestAppendageUpdate = _QtCore.pyqtSignal(str)

    def __init__(self, session, title="Experiment", parent=None):
        super().__init__(title=title, parent=parent, session=session)

        self._subject = _utils.FormItem("Subject", _utils.InvalidatableLineEdit(self.subject))
        self._date    = _utils.FormItem("Date", _QtWidgets.QDateEdit(self.date))
        self._today   = _QtWidgets.QPushButton("Today")
        self._index   = _utils.FormItem("Session index", _utils.InvalidatableSpinBox())
        self._type    = _utils.FormItem("Session type", _utils.InvalidatableLineEdit(""))
        self._domain  = _utils.FormItem("Domain", _utils.InvalidatableLineEdit(self.domain))
        self._run     = _utils.FormItem("Run index", _utils.InvalidatableSpinBox())
        self._autoinc = _QtWidgets.QCheckBox("Auto-increment")
        self._append  = _utils.FormItem("Appendage", _utils.InvalidatableLineEdit(self.appendage))
        self._addFormItem(self._subject,   0, 0, widget_colspan=2)
        self._addFormItem(self._date,      1, 0, widget_colspan=1)
        self._layout.addWidget(self._today,1, 2)
        self._addFormItem(self._index,     2, 0)
        self._addFormItem(self._type,      3, 0, widget_colspan=2)
        self._addFormItem(self._domain,    4, 0, widget_colspan=2)
        self._addFormItem(self._run,       5, 0, widget_colspan=1)
        self._layout.addWidget(self._autoinc,5, 2)
        self._addFormItem(self._append,    6, 0, widget_colspan=2)
        self._layout.setColumnStretch(0, 2)
        self._layout.setColumnStretch(1, 1)
        self._layout.setColumnStretch(2, 1)

        self._date.widget.setDisplayFormat(self.qDate_format)
        self._date.widget.setCalendarPopup(True)

        self._index.widget.setMinimum(1)
        self._index.widget.setMaximum(100)
        self._index.widget.setValue(1)

        self._type.setEnabled(False)

        self._run.widget.setMinimum(1)
        self._run.widget.setMaximum(100)
        self._run.widget.setValue(1)
        self._run.setEnabled(False)
        self._autoinc.setChecked(False)
        self._autoinc.setEnabled(False)

        self._subject.widget.textChanged.connect(self._subject.widget.invalidate)
        self._subject.widget.editingFinished.connect(self.dispatchSubjectUpdate)
        self._domain.widget.textChanged.connect(self._domain.widget.invalidate)
        self._domain.widget.editingFinished.connect(self.dispatchDomainUpdate)
        self._date.widget.dateChanged.connect(self.dispatchDateUpdate)
        self._today.clicked.connect(self._updateToToday)
        self._index.widget.valueChanged.connect(self.dispatchIndexUpdate)
        self._append.widget.textChanged.connect(self._append.widget.invalidate)
        self._append.widget.editingFinished.connect(self.dispatchAppendageUpdate)

        self._updating = False

    # override
    def connectWithSession(self, session):
        session.control.updatedAcquisitionMode.connect(self.updateWithAcquisitionMode)

        session.experiment.updatedSubject.connect(self.updateWithSubject)
        session.experiment.updatedDate.connect(self.updateWithDate)
        session.experiment.updatedIndex.connect(self.updateWithIndex)
        session.experiment.updatedDomain.connect(self.updateWithDomain)
        session.experiment.updatedAppendage.connect(self.updateWithAppendage)

        self.requestSubjectUpdate.connect(session.experiment.setSubject)
        self.requestDateUpdate.connect(session.experiment.setQDate)
        self.requestIndexUpdate.connect(session.experiment.setIndex)
        self.requestDomainUpdate.connect(session.experiment.setDomain)
        self.requestAppendageUpdate.connect(session.experiment.setAppendage)

    @property
    def date(self):
        return self.session.experiment.qDate

    @property
    def subject(self):
        return self.session.experiment.subject

    @property
    def domain(self):
        return self.session.experiment.domain

    @property
    def index(self):
        return self.session.experiment.index

    @property
    def appendage(self):
        return self.session.experiment.appendage

    @property
    def qDate_format(self):
        return self.session.experiment.qDate_format

    def setEnabled(self, status):
        for obj in (self._subject,
                    self._date,
                    self._today,
                    self._index,
                    self._domain,
                    self._append):
            obj.setEnabled(status)
        for obj in (self._type, self._run, self._autoinc):
            obj.setEnabled(False)

    def updateWithAcquisitionMode(self, oldmode, newmode):
        self.setEnabled(newmode == _utils.AcquisitionModes.IDLE)

    def dispatchSubjectUpdate(self):
        if not self._updating:
            self.requestSubjectUpdate.emit(self._subject.widget.text())

    def dispatchDomainUpdate(self):
        if not self._updating:
            self.requestDomainUpdate.emit(self._domain.widget.text())

    def dispatchDateUpdate(self, value):
        if not self._updating:
            self.requestDateUpdate.emit(value)

    def dispatchIndexUpdate(self, value):
        if (self._updating == True) or (self._index.widget.editing == True):
            return
        self.requestIndexUpdate.emit(value)

    def dispatchAppendageUpdate(self):
        if self._updating == True:
            return
        self.requestAppendageUpdate.emit(self._append.widget.text())

    def _updateToToday(self):
        if self._updating == True:
            return # just in case
        self.requestDateUpdate.emit(_QtCore.QDate.currentDate())

    def updateWithSubject(self, value):
        self._updating = True
        self._subject.widget.setText(value)
        self._subject.widget.revalidate()
        self._updating = False

    def updateWithDomain(self, value):
        self._updating = True
        self._domain.widget.setText(value)
        self._domain.widget.revalidate()
        self._updating = False

    def updateWithDate(self, year, month, day):
        self._updating = True
        self._date.widget.setDate(_QtCore.QDate(year, month, day))
        self._updating = False

    def updateWithIndex(self, index):
        self._updating = True
        self._index.widget.setValue(index)
        self._updating = False

    def updateWithAppendage(self, append):
        self._updating = True
        self._append.widget.setText(append)
        self._append.widget.revalidate()
        self._updating = False

class DeviceSelector(_utils.ViewGroup):
    LABEL_OPEN  = "Open"
    LABEL_CLOSE = "Close"
    requestedOpeningDevice = _QtCore.pyqtSignal(str)
    requestedClosingDevice = _QtCore.pyqtSignal()

    def __init__(self,
                 session,
                 title="Device",
                 parent=None):
        super().__init__(session=session, title=title, parent=parent)
        self._box    = _QtWidgets.QComboBox()
        for device in self.session.control.get_device_names():
            self._box.addItem(device)
        self._layout.addWidget(self._box, 0, 0)
        self._action = _QtWidgets.QPushButton(self.LABEL_OPEN)
        self._layout.addWidget(self._action, 0, 1)
        self._layout.setColumnStretch(0, 3)
        self._layout.setColumnStretch(1, 1)
        self._action.clicked.connect(self.dispatchRequest)

    # override
    def connectWithSession(self, session):
        session.control.openedDevice.connect(self.updateWithOpeningDevice)
        session.control.closedDevice.connect(self.updateWithClosingDevice)
        session.control.updatedAcquisitionMode.connect(self.updateWithAcquisitionMode)

        self.requestedOpeningDevice.connect(session.control.openDevice)
        self.requestedClosingDevice.connect(session.control.closeDevice)

    def dispatchRequest(self):
        cmd = self._action.text()
        if cmd == self.LABEL_OPEN:
            self.requestedOpeningDevice.emit(self._box.currentText())
        else:
            self.requestedClosingDevice.emit()

    def updateWithOpeningDevice(self, device):
        self._box.setCurrentText(device.unique_name)
        self._action.setText(self.LABEL_CLOSE)
        self._box.setEnabled(False)

    def updateWithClosingDevice(self):
        self._action.setText(self.LABEL_OPEN)
        self._box.setEnabled(True)

    def updateWithAcquisitionMode(self, oldmode, newmode):
        self._action.setEnabled(newmode == _utils.AcquisitionModes.IDLE)

class FrameFormatSettings(_utils.ViewGroup):
    requestedFormatUpdate   = _QtCore.pyqtSignal(str)
    requestedRotationUpdate = _QtCore.pyqtSignal(str)

    def __init__(self, session, title="Frame", parent=None):
        super().__init__(session=session, title=title, parent=parent)
        self._format   = _utils.FormItem("Format", _QtWidgets.QComboBox())
        self._x        = _utils.FormItem("Offset X", _QtWidgets.QSpinBox())
        self._y        = _utils.FormItem("Offset Y", _QtWidgets.QSpinBox())
        self._center   = _QtWidgets.QCheckBox("Center ROI")
        self._rotation = _utils.FormItem("Rotation clockwise", _QtWidgets.QComboBox())
        for item in self.session.acquisition.rotation.options:
            self._rotation.widget.addItem(item)
        for row, obj in enumerate((self._format,
                                   self._x,
                                   self._y,)):
            self._addFormItem(obj, row, 0)
        self._layout.addWidget(self._center, 3, 1)
        self._addFormItem(self._rotation, 4, 0)

        self.setEnabled(False)
        self._format.widget.currentTextChanged.connect(self.dispatchFormatUpdate)
        self._rotation.widget.currentTextChanged.connect(self.dispatchRotationUpdate)

    # override
    def connectWithSession(self, session):
        session.control.openedDevice.connect(self.updateWithOpeningDevice)
        session.control.closedDevice.connect(self.updateWithClosingDevice)
        session.control.updatedAcquisitionMode.connect(self.updateWithAcquisitionMode)

        session.acquisition.format.selectionChanged.connect(self.updateWithFormat)
        session.acquisition.rotation.selectionChanged.connect(self.updateWithRotation)
        self.requestedFormatUpdate.connect(session.acquisition.format.setValue)
        self.requestedRotationUpdate.connect(session.acquisition.rotation.setValue)

    def setEnabled(self, val):
        for obj in (self._format, self._rotation):
            obj.setEnabled(val)
        for obj in (self._x, self._y, self._center):
            obj.setEnabled(False)

    def dispatchFormatUpdate(self, fmt):
        if self._updating == True:
            return
        self.requestedFormatUpdate.emit(fmt)

    def dispatchRotationUpdate(self, rot):
        if self._updating == True:
            return
        self.requestedRotationUpdate.emit(rot)

    def updateWithOpeningDevice(self, device):
        # re-populate the format selector
        box  = self._format.widget
        for fmt in device.list_video_formats():
            box.addItem(fmt) # will fire dispatchFormatUpdate once
        self.setEnabled(True)

    def updateWithClosingDevice(self):
        self.setEnabled(False)
        self._updating = True
        self._format.widget.clear()
        self._updating = False

    def updateWithFormat(self, fmt):
        self._updating = True
        self._format.widget.setCurrentText(fmt)
        self._updating = False

    def updateWithRotation(self, rot):
        self._updating = True
        self._rotation.widget.setCurrentText(rot)
        self._updating = False

    def updateWithAcquisitionMode(self, oldmode, newmode):
        self.setEnabled(newmode == _utils.AcquisitionModes.IDLE)

class AcquisitionSettings(_utils.ViewGroup):
    requestedAutoTriggerMode  = _QtCore.pyqtSignal(bool)
    requestedFrameRateUpdate  = _QtCore.pyqtSignal(object) # float
    requestedForcePreferredStatus = _QtCore.pyqtSignal(bool)
    requestedAutoExposureMode = _QtCore.pyqtSignal(bool)
    requestedExposureUpdate   = _QtCore.pyqtSignal(object) # int
    requestedAutoGainMode     = _QtCore.pyqtSignal(bool)
    requestedGainUpdate       = _QtCore.pyqtSignal(object) # float
    requestedGammaUpdate      = _QtCore.pyqtSignal(object) # float

    def __init__(self, session, title="Acquisition", parent=None):
        super().__init__(session=session, title=title, parent=parent)
        self._rate = _utils.FormItem("Frame rate (Hz)", _utils.InvalidatableDoubleSpinBox())
        # set up the spin box
        self._rate.widget.setDecimals(1)
        self._rate.widget.setMaximum(200)
        self._rate.widget.setMinimum(1.0)
        self._rate.widget.setSingleStep(0.1)
        self._rate.widget.setValue(30)
        self._rate.widget.edited.connect(self._rate.widget.invalidate)
        self._rate.widget.valueChanged.connect(self.dispatchFrameRateUpdate)
        self._triggered = _QtWidgets.QCheckBox("Use external trigger")
        self._triggered.stateChanged.connect(self.dispatchTriggerStatusUpdate)
        self._force_preferred = _QtWidgets.QCheckBox("Use 'preferred' frame rate for storage")
        self._force_preferred.stateChanged.connect(self.dispatchForcePreferredUpdate)

        self._strobe   = _utils.FormItem("Strobe output", StrobeModeSelector(session))

        self._exposure = _utils.FormItem("Exposure (us)", _utils.InvalidatableSpinBox())
        # set up the spin box
        self._exposure.widget.setMinimum(1)
        self._exposure.widget.setMaximum(100000)
        self._exposure.widget.setValue(10000)
        self._exposure.widget.edited.connect(self._exposure.widget.invalidate)
        self._exposure.widget.valueChanged.connect(self.dispatchExposureUpdate)
        self._autoexp   = _QtWidgets.QCheckBox("Auto-exposure")
        self._autoexp.stateChanged.connect(self.dispatchAutoExposureUpdate)

        self._gain = _utils.FormItem("Gain", _utils.InvalidatableDoubleSpinBox())
        # set up the gain spin box
        self._gain.widget.setDecimals(1)
        self._gain.widget.setMinimum(0.5)
        self._gain.widget.setMaximum(8.0)
        self._gain.widget.setSingleStep(0.1)
        self._gain.widget.setValue(1.0)
        self._gain.widget.edited.connect(self._gain.widget.invalidate)
        self._gain.widget.valueChanged.connect(self.dispatchGainUpdate)
        self._autogain  = _QtWidgets.QCheckBox("Auto-gain")
        self._autogain.stateChanged.connect(self.dispatchAutoGainUpdate)

        self._gamma = _utils.FormItem("Gamma", _utils.InvalidatableDoubleSpinBox())
        self._gamma.widget.setDecimals(2)
        self._gamma.widget.setMinimum(0.01)
        self._gamma.widget.setMaximum(8.0)
        self._gamma.widget.setSingleStep(0.1)
        self._gamma.widget.setValue(1.0)
        self._gamma.widget.edited.connect(self._gamma.widget.invalidate)
        self._gamma.widget.valueChanged.connect(self.dispatchGammaUpdate)

        self._binning = _utils.FormItem("Binning", _QtWidgets.QComboBox())
        self._binning.widget.addItem("1")
        # TODO: specify actions (probably implement a dedicated class)

        self._addFormItem(self._rate, 0, 0)
        self._layout.addWidget(self._triggered, 0, 2,
                               alignment=_QtCore.Qt.AlignLeft)
        self._layout.addWidget(self._force_preferred, 1, 1, 1, 2,
                               alignment=_QtCore.Qt.AlignLeft)
        self._addFormItem(self._exposure, 2, 0)
        self._layout.addWidget(self._autoexp, 2, 2)
        self._addFormItem(self._gain, 3, 0)
        self._layout.addWidget(self._autogain, 3, 2)
        self._addFormItem(self._gamma, 4, 0)
        self._addFormItem(self._binning, 5, 0)
        self._addFormItem(self._strobe, 6, 0)

        self.setEnabled(False)

    # override
    def connectWithSession(self, session):
        session.control.openedDevice.connect(self.updateWithOpeningDevice)
        session.control.closedDevice.connect(self.updateWithClosingDevice)
        session.control.updatedAcquisitionMode.connect(self.updateWithAcquisitionMode)

        session.acquisition.framerate.rangeChanged.connect(self.updateWithFrameRateRange)
        session.acquisition.framerate.settingsChanged.connect(self.updateWithFrameRateSettings)
        session.acquisition.framerate.forcePreferredStatusChanged.connect(self.updateWithForcePreferredStatus)
        session.acquisition.exposure.rangeChanged.connect(self.updateWithExposureRange)
        session.acquisition.exposure.settingsChanged.connect(self.updateWithExposureSettings)
        session.acquisition.gain.rangeChanged.connect(self.updateWithGainRange)
        session.acquisition.gain.settingsChanged.connect(self.updateWithGainSettings)
        session.acquisition.gamma.rangeChanged.connect(self.updateWithGammaRange)
        session.acquisition.gamma.settingsChanged.connect(self.updateWithGammaSettings)

        session.acquisition.format.selectionChanged.connect(self.reinstateAllSettings)

        self.requestedAutoTriggerMode.connect(session.acquisition.framerate.setAuto)
        self.requestedFrameRateUpdate.connect(session.acquisition.framerate.setPreferred)
        self.requestedForcePreferredStatus.connect(session.acquisition.framerate.setForcePreferred)
        self.requestedAutoExposureMode.connect(session.acquisition.exposure.setAuto)
        self.requestedExposureUpdate.connect(session.acquisition.exposure.setPreferred)
        self.requestedAutoGainMode.connect(session.acquisition.gain.setAuto)
        self.requestedGainUpdate.connect(session.acquisition.gain.setPreferred)
        self.requestedGammaUpdate.connect(session.acquisition.gamma.setPreferred)

    def setEnabled(self, val):
        for obj in (self._rate, self._triggered, self._strobe, self._force_preferred):
            obj.setEnabled(val)
        for obj in (self._exposure, self._autoexp):
            obj.setEnabled(val)
        for obj in (self._gain, self._autogain, self._gamma):
            obj.setEnabled(val)
        self._binning.setEnabled(False)

    def reinstateAllSettings(self, *_):
        """works as a hook to 'reinstate' settings when the frame format has been changed.
        the argument(s) will never be used."""
        self.dispatchTriggerStatusUpdate()
        self.dispatchFrameRateUpdate()
        self.dispatchForcePreferredUpdate()
        self.dispatchAutoExposureUpdate()
        self.dispatchExposureUpdate()
        self.dispatchAutoGainUpdate()
        self.dispatchGainUpdate()
        self.dispatchGammaUpdate()

    def dispatchTriggerStatusUpdate(self, _=None): # the argument will never be used
        if self._updating == True:
            return
        self.requestedAutoTriggerMode.emit(not self._triggered.isChecked())

    def dispatchFrameRateUpdate(self):
        if (self._updating == True) or (self._rate.widget.editing == True):
            return
        self.requestedFrameRateUpdate.emit(self._rate.widget.value())

    def dispatchForcePreferredUpdate(self):
        if self._updating == True:
            return
        self.requestedForcePreferredStatus.emit(self._force_preferred.isChecked())

    def dispatchAutoExposureUpdate(self, _=None): # the argument will never be used
        if self._updating == True:
            return
        self.requestedAutoExposureMode.emit(self._autoexp.isChecked())

    def dispatchExposureUpdate(self):
        if (self._updating == True) or (self._exposure.widget.editing == True):
            return
        self.requestedExposureUpdate.emit(self._exposure.widget.value())

    def dispatchAutoGainUpdate(self, _=None): # the argument will never be used
        if self._updating == True:
            return
        self.requestedAutoGainMode.emit(self._autogain.isChecked())

    def dispatchGainUpdate(self):
        if (self._updating == True) or (self._gain.widget.editing == True):
            return
        self.requestedGainUpdate.emit(self._gain.widget.value())

    def dispatchGammaUpdate(self):
        if (self._updating == True) or (self._gamma.widget.editing == True):
            return
        self.requestedGammaUpdate.emit(self._gamma.widget.value())

    def updateWithOpeningDevice(self, device):
        self._updating = True
        self.setEnabled(True)
        self._rate.widget.setValue(device.frame_rate)
        self._triggered.setEnabled(device.has_trigger)
        self._exposure.widget.setValue(device.exposure_us)
        self._autoexp.setChecked(device.auto_exposure)
        if device.auto_exposure:
            self._exposure.widget.setEnabled(False)
        self._updating = False

    def updateWithClosingDevice(self):
        self.setEnabled(False)

    def updateWithAcquisitionMode(self, oldmode, newmode):
        self.setEnabled(newmode == _utils.AcquisitionModes.IDLE)
        # re-enable those that are updatable even during acquisition
        for obj in (self._exposure, self._autoexp, self._strobe,):
            obj.setEnabled(True)
        for obj in (self._gain, self._autogain, self._gamma):
            obj.setEnabled(True)

    def updateWithFrameRateRange(self, minval, maxval):
        self._updating = True
        self._rate.widget.setMinimum(minval)
        self._rate.widget.setMaximum(maxval)
        self._updating = False

    def updateWithFrameRateSettings(self, auto, preferred, output):
        self._updating = True
        self._triggered.setChecked(not auto)
        if auto and (not self._session.acquisition.framerate.force_preferred):
            self._rate.widget.setValue(output)
        else:
            self._rate.widget.setValue(preferred)
        self._rate.widget.revalidate()
        self._updating = False

    def updateWithForcePreferredStatus(self, status):
        self._updating = True
        self._force_preferred.setChecked(status)
        if (not status) and (self._session.acquisition.framerate.auto):
            self._rate.widget.setValue(self._session.acquisition.framerate.value)
        else:
            self._rate.widget.setValue(self._session.acquisition.framerate.preferred)
        self._updating = False

    def updateWithExposureRange(self, minval, maxval):
        self._updating = True
        self._exposure.widget.setMinimum(minval)
        self._exposure.widget.setMaximum(maxval)
        self._updating = False

    def updateWithExposureSettings(self, auto, preferred, output):
        self._updating = True
        self._exposure.widget.setValue(output)
        self._exposure.widget.revalidate()
        self._autoexp.setChecked(auto)
        self._exposure.widget.setEnabled(not auto)
        self._updating = False

    def updateWithGainRange(self, minval, maxval):
        self._updating = True
        self._gain.widget.setMinimum(minval)
        self._gain.widget.setMaximum(maxval)
        self._updating = False

    def updateWithGainSettings(self, auto, preferred, output):
        self._updating = True
        self._gain.widget.setValue(output)
        self._gain.widget.revalidate()
        self._autogain.setChecked(auto)
        self._gain.widget.setEnabled(not auto)
        self._updating = False

    def updateWithGammaRange(self, minval, maxval):
        self._updating = True
        self._gamma.widget.setMinimum(minval)
        self._gamma.widget.setMaximum(maxval)
        self._updating = False

    def updateWithGammaSettings(self, auto, preferred, output):
        self._updating = True
        self._gamma.widget.setValue(output)
        self._gamma.widget.revalidate()
        self._updating = False

class StrobeModeSelector(_QtWidgets.QComboBox, _utils.SessionControl):
    requestStrobeModeUpdate = _QtCore.pyqtSignal(str)

    def __init__(self, session, parent=None):
        super().__init__(parent=parent)
        self.initWithSession(session)
        self.currentTextChanged.connect(self.dispatchStrobeModeUpdate)

    # override
    def connectWithSession(self, session):
        session.acquisition.strobe.selectionChanged.connect(self.updateWithStrobeMode)
        self.requestStrobeModeUpdate.connect(session.acquisition.strobe.setValue)
        for mode in session.acquisition.strobe.options:
            self.addItem(mode)
        self.setCurrentText(session.acquisition.strobe.value)

    def dispatchStrobeModeUpdate(self, mode):
        if self._updating == True:
            return
        self.requestStrobeModeUpdate.emit(mode)

    def updateWithStrobeMode(self, mode):
        self._updating = True
        self.setCurrentText(mode)
        self._updating = False


class StorageSettings(_utils.ViewGroup):
    FILE_DESC_NOGRAB = "Sample file name: "
    FILE_DESC_GRAB   = "File name: "

    requestedEncoderUpdate   = _QtCore.pyqtSignal(str)
    requestedDirectoryUpdate = _QtCore.pyqtSignal(str)
    requestedPatternUpdate   = _QtCore.pyqtSignal(str)

    def __init__(self, session, title="Storage", parent=None):
        super().__init__(session=session, title=title, parent=parent)

        self._directory = _utils.FormItem("Directory", DirectorySelector(self.session.storage.directory))
        self._directory.widget.directorySelected.connect(self.dispatchDirectoryUpdate)
        self._directory.widget.requestedOpeningDirectory.connect(self.session.storage.openDirectory)
        self._pattern = _utils.FormItem("File name pattern", _utils.InvalidatableLineEdit(self.session.storage.pattern))
        self._pattern.widget.edited.connect(self._pattern.widget.invalidate)
        self._pattern.widget.editingFinished.connect(self.dispatchPatternUpdate)
        self._file    = _utils.FormItem(self.FILE_DESC_NOGRAB, _QtWidgets.QLabel(self.session.storage.filename))
        self._encoder = _utils.FormItem("Video format", _QtWidgets.QComboBox())
        self._quality = _utils.FormItem("Quality", EncodingQualitySelector())
        self._quality.widget.setRange(self.session.storage.quality_range)
        self._quality.widget.setSteps(1, 10)
        self._quality.widget.setValue(self.session.storage.quality)
        self.session.storage.updatedQuality.connect(self._quality.widget.setValue)
        self._quality.widget.valueChanged.connect(self.session.storage.setQuality)
        self._quality.setEnabled(self.session.storage.has_quality_setting())
        for encoder in self.session.storage.list_encoders():
            self._encoder.widget.addItem(encoder.description)
        self._encoder.widget.setCurrentText(self.session.storage.encoder.description)
        self._encoder.widget.currentTextChanged.connect(self.dispatchEncoderUpdate)
        self._addFormItem(self._encoder,   0, 0)
        self._addFormItem(self._quality,   1, 0)
        self._addFormItem(self._directory, 2, 0)
        self._addFormItem(self._pattern,   3, 0)
        self._addFormItem(self._file,      4, 0)

        self.setEnabled(True)

    # override
    def connectWithSession(self, session):
        session.control.updatedAcquisitionMode.connect(self.updateWithAcquisitionMode)

        session.storage.updatedDirectory.connect(self.updateWithDirectory)
        session.storage.updatedPattern.connect(self.updateWithPattern)
        session.storage.updatedFileName.connect(self.updateWithFileName)
        session.storage.updatedEncoder.connect(self.updateWithEncoder)

        self.requestedEncoderUpdate.connect(session.storage.setEncoder)
        self.requestedDirectoryUpdate.connect(session.storage.setDirectory)
        self.requestedPatternUpdate.connect(session.storage.setPattern)

    def setEnabled(self, state):
        for obj in (self._directory, self._pattern, self._encoder, self._quality, ):
            obj.setEnabled(state)

    def dispatchEncoderUpdate(self, value):
        if self._updating == True:
            return
        self.requestedEncoderUpdate.emit(value)

    def dispatchDirectoryUpdate(self, value):
        if self._updating == True:
            return
        self.requestedDirectoryUpdate.emit(value)

    def dispatchPatternUpdate(self):
        if self._updating == True:
            return
        self.requestedPatternUpdate.emit(self._pattern.widget.text())

    def updateWithEncoder(self, codec):
        self._updating = True
        self._encoder.widget.setCurrentText(codec.description)
        self._quality.setEnabled(self.session.storage.has_quality_setting())
        self._updating = False

    def updateWithDirectory(self, value):
        self._updating = True
        self._directory.widget.value = value
        self._updating = False

    def updateWithPattern(self, value):
        self._updating = True
        self._pattern.widget.setText(value)
        self._pattern.widget.revalidate()
        self._updating = False

    def updateWithFileName(self, value):
        if not hasattr(self, "_file"):
            return # during initialization
        self._updating = True
        self._file.widget.setText(value)
        self._updating = False

    def updateWithAcquisitionMode(self, oldmode, newmode):
        self.setEnabled(newmode == _utils.AcquisitionModes.IDLE)
        self._file.setEnabled(newmode != _utils.AcquisitionModes.FOCUS)
        if newmode == _utils.AcquisitionModes.GRAB:
            self._file.label.setText(self.FILE_DESC_GRAB)
        else:
            self._file.label.setText(self.FILE_DESC_NOGRAB)

class EncodingQualitySelector(_QtWidgets.QWidget):
    valueChanged = _QtCore.pyqtSignal(int)

    def __init__(self, parent=None):
        super().__init__()
        self._slider = _QtWidgets.QSlider(_QtCore.Qt.Horizontal)
        self._editor = _utils.InvalidatableSpinBox()
        self._layout = _QtGui.QHBoxLayout()

        self.setLayout(self._layout)
        self._layout.addWidget(self._slider)
        self._layout.addWidget(self._editor)
        self._updating = False
        self._slidermoving = False

        self._slider.sliderPressed.connect(self.updateWithSliderStart)
        self._slider.sliderReleased.connect(self.updateWithSliderStop)
        self._slider.valueChanged.connect(self.requestFromSlider)
        self._editor.valueChanged.connect(self.requestFromEditor)
        self._editor.edited.connect(self._editor.invalidate)

    def setRange(self, rng):
        self._updating = True
        m, M = min(rng), max(rng)
        for obj in (self._slider, self._editor):
            obj.setMinimum(m)
            obj.setMaximum(M)
        self._updating = False

    def setValue(self, value):
        self._updating = True
        for obj in (self._slider, self._editor):
            obj.setValue(value)
        self._editor.revalidate()
        self._slidermoving = False
        self._updating = False

    def setSteps(self, single, page):
        for obj in (self._slider, self._editor):
            obj.setSingleStep(single)
        self._slider.setPageStep(page)
        self._slider.setTickPosition(_QtWidgets.QSlider.TicksBelow)
        self._slider.setTickInterval(page)

    def requestFromSlider(self, value):
        if self._updating == True:
            return
        elif self._slidermoving == True:
            self._editor.edit(value)
            return
        self.valueChanged.emit(value)

    def requestFromEditor(self, value):
        if (self._updating == True) or (self._editor.editing == True):
            return
        self.valueChanged.emit(value)

    def updateWithSliderStart(self):
        self._slidermoving = True

    def updateWithSliderStop(self):
        self._slidermoving = False
        self.requestFromSlider(self._slider.value())

class DirectorySelector(_QtWidgets.QWidget):
    directorySelected = _QtCore.pyqtSignal(str)
    requestedOpeningDirectory = _QtCore.pyqtSignal()

    def __init__(self, path="", parent=None):
        path = str(_Path(path).resolve())

        super().__init__(parent=parent)
        self._chooser = _QtWidgets.QFileDialog(self, _QtCore.Qt.Dialog)
        self._chooser.setAcceptMode(_QtWidgets.QFileDialog.AcceptOpen)
        self._chooser.setFileMode(_QtWidgets.QFileDialog.Directory)
        self._chooser.setOptions(_QtWidgets.QFileDialog.ReadOnly)
        self._chooser.setModal(True)
        self._chooser.setWindowTitle("Directory to save videos")
        self._chooser.accepted.connect(self.updateFromChooser)
        self._disp   = _QtWidgets.QLabel(path)
        self._open   = _QtWidgets.QPushButton("Open")
        self._open.clicked.connect(self.showDirectoryOnExplorer)
        self._search = _QtWidgets.QPushButton("Select...")
        self._search.clicked.connect(self.startEditing)

        self._layout = _QtWidgets.QGridLayout()
        self.setLayout(self._layout)
        self._layout.addWidget(self._disp, 0, 0)
        self._layout.addWidget(self._open, 0, 1)
        self._layout.addWidget(self._search, 0, 2)
        self._layout.setColumnStretch(0, 5)
        self._layout.setColumnStretch(1, 1)
        self._layout.setColumnStretch(2, 1)

        self._from_chooser = False # updating from the file dialog

    @property
    def value(self):
        return self._disp.text()

    @value.setter
    def value(self, val):
        path = _Path(str(val)).resolve()
        self._disp.setText(str(path))
        self._chooser.setDirectory(str(path.parent))
        if self._from_chooser == True:
            self.directorySelected.emit(str(path))

    def startEditing(self):
        # somehow _chooser.exec() (or any other static methods to show a modal dialog)
        # does not work. So I chose to explicitly show() a modal dialog here
        path = _Path(self._disp.text())
        # FIXME: cannot pre-specify the selected directory!
        self._chooser.show()

    def showDirectoryOnExplorer(self):
        self.requestedOpeningDirectory.emit()

    def updateFromChooser(self):
        self._from_chooser = True
        self.value = self._chooser.selectedFiles()[0]
        self._from_chooser = False
