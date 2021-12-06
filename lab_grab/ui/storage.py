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
from collections import deque as _deque
from datetime import datetime as _datetime
from traceback import print_exc as _print_exc
import subprocess as _sp

import numpy as _np
from pyqtgraph.Qt import QtCore as _QtCore

from .. import LOGGER as _LOGGER
from . import encoding as _encoding

### the main storage service

BASE_ENCODER_LIST = (
    _encoding.RAW_VIDEO,
    _encoding.MJPEG_CPU,
    _encoding.MJPEG_QSV,
    _encoding.H264_NVENC,
)

class StorageService(_QtCore.QObject):
    EXPERIMENT_ATTRIBUTES = ("subject", "datestr", "indexstr", "domain", "appendagestr")
    TIMESTAMP_FORMAT      = "%H%M%S"
    DEFAULT_NAME_PATTERN  = "{subject}_{date}_{domain}_{time}{appendage}"
    QUALITY_RANGE         = (1, 100)

    DEFAULT_ENCODERS = tuple(enc for enc in BASE_ENCODER_LIST if enc.check_availability())

    _singleton = None

    updatedEncoder       = _QtCore.pyqtSignal(object) # an Encoder object
    updatedQuality       = _QtCore.pyqtSignal(int)
    updatedDirectory     = _QtCore.pyqtSignal(str)
    updatedPattern       = _QtCore.pyqtSignal(str)
    updatedFileName      = _QtCore.pyqtSignal(str)
    interruptAcquisition = _QtCore.pyqtSignal(str) # error msg
    message              = _QtCore.pyqtSignal(str, str)

    # currently the method is defined using the `cls._singleton` object
    # so that every subclass can have its own singleton object.
    # this must be modified to refer to `StorageService._singleton`
    # to achieve the situation where _all_ the subclasses refer to the _same, single_
    # StorageService object
    @classmethod
    def instance(cls):
        if cls._singleton is None:
            cls._singleton = cls()
        return cls._singleton

    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self._encoder    = self.DEFAULT_ENCODERS[0]
        self._quality    = 75
        self._directory  = str(_Path().resolve())
        self._pattern    = self.DEFAULT_NAME_PATTERN

        self._experiment = _Experiment.instance() # must be non-None
        self._experiment.updated.connect(self.updateFileName)

        self._proc       = None # the placeholder for the encoder process
        self._sink       = None # the STDIN of the encoder process
        self._nextindex  = None # the frame index being expected by the encoder (for detection of skips)
        self._empty      = None # the empty frame to be inserted in case of skips
        self._convert    = None # the function to make the frame into the proper structure

    def as_dict(self):
        out = {}
        out["directory"] = self._directory
        out["pattern"]   = self._pattern
        out["encoder"]   = self._encoder.description
        if self.has_quality_setting():
            out["quality"]   = self._quality
        return out

    def load_dict(self, cfg):
        for key in ("directory", "pattern", "encoder", "quality"):
            if key in cfg.keys():
                setattr(self, key, cfg[key])

    def getEncoder(self):
        return self._encoder

    def setEncoder(self, value):
        if isinstance(value, str):
            for encoder in self.list_encoders():
                if encoder.description == value:
                    value = encoder
                    break
            if isinstance(value, str):
                raise ValueError(f"encoder not found: '{value}'")
        self._encoder = value
        self.updatedEncoder.emit(self._encoder)
        self.message.emit("info", f"video encoder: {self._encoder.description}")
        self.updateFileName()

    def getQuality(self):
        return self._quality

    def setQuality(self, value):
        self._quality = int(value)
        self.updatedQuality.emit(self._quality)
        self.message.emit("info", f"encoding quality: {self._quality} (the higher the better)")

    @property
    def quality_range(self):
        return self.QUALITY_RANGE

    def has_quality_setting(self):
        return self._encoder.has_quality_setting()

    def getDirectory(self):
        return self._directory

    def setDirectory(self, value):
        self._directory = str(_Path(value).resolve())
        self.updatedDirectory.emit(self._directory)
        self.message.emit("info", f"save directory: {self._directory}")

    def openDirectory(self):
        """opens the directory on Explorer"""
        proc = _sp.run(["start", self._directory], shell=True)
        if proc.returncode != 0:
            # TODO: generate warning
            _LOGGER.warning("failed to open: " + self._directory)

    def getPattern(self):
        return self._pattern

    def setPattern(self, value):
        self._pattern = str(value)
        self.updatedPattern.emit(self._pattern)
        self.message.emit("info", f"file-name pattern: {self._pattern}")
        self.updateFileName()

    def updateFileName(self):
        pattern = self._pattern
        if "{suffix}" not in pattern:
            pattern = pattern + "{suffix}"
        filename = pattern.format(**(self.format_dict))
        self.updatedFileName.emit(filename)
        return filename

    def as_path(self, filename):
        return _Path(self._directory) / filename

    def list_encoders(self):
        return self.DEFAULT_ENCODERS

    def prepare(self, framerate=30, descriptor=None):
        options    = _encoding.Options(self._encoder,
                                       self.as_path(self.filename),
                                       descriptor=descriptor,
                                       framerate=framerate,
                                       quality=self._quality)
        self._sink = BufferThread(options, parent=self)
        self._nextindex = 0
        self._empty     = _np.zeros(**descriptor.numpy_formatter)
        if self._empty.ndim == 3:
            self._convert = lambda frame: frame.transpose((1,0,2))
        else:
            self._convert = lambda frame: frame.T
        self._sink.start()

    def write(self, index, frame):
        try:
            sink = self._sink
            while index > self._nextindex:
                sink.push(self._empty)
                self._nextindex += 1
            sink.push(self._convert(frame))
            self._nextindex += 1
        except:
            sink = self._sink
            self._sink = None
            sink.signal()
            sink.wait()
            del sink

    def close(self):
        if self._sink is not None:
            sink = self._sink
            self._sink = None
            sink.push(None)
            if sink.wait() == False:
                _LOGGER.error("Storage::close -- BufferThread.wait() returned False")
                sink.terminate()
                sink.wait() # do not check
            del sink

    def is_running(self):
        """returns whether the storage service is currently running the encoder process."""
        return (self._sink is not None)

    @property
    def suffix(self):
        return self._encoder.suffix

    @property
    def format_dict(self):
        opts = dict((attrname, getattr(self._experiment, attrname))\
                    for attrname in self.EXPERIMENT_ATTRIBUTES)
        for name in ("date", "index", "appendage"):
            opts[name] = opts.pop(name + "str")
        opts["time"]   = _datetime.now().strftime(self.TIMESTAMP_FORMAT)
        opts["suffix"] = self.suffix
        return opts

    encoder   = property(fget=getEncoder,   fset=setEncoder)
    quality   = property(fget=getQuality,   fset=setQuality)
    directory = property(fget=getDirectory, fset=setDirectory)
    pattern   = property(fget=getPattern,   fset=setPattern)
    filename  = property(fget=updateFileName)

class BufferThread(_QtCore.QThread):
    """the intermediatary buffer between StorageService and encoding.WriterThread.

    The basic principles here are:
    1. To avoid sharing a single mutex object between the callback and the encoder contexts.
    2. To avoid dynamic memory allocation related to buffering of frames.

    """
    def __init__(self,
                 options,
                 num_buffer=200,
                 parent=None):
        super().__init__(parent=parent)
        self._writer  = _encoding.WriterThread(options,
                                               buffer=self,
                                               parent=self)
        self._queue   = _deque()
        self._count   = 0
        self._mutex   = _QtCore.QMutex()
        self._signal  = _QtCore.QWaitCondition()
        self._toquit  = False

        ## frame buffer
        self._buffer  = _deque()
        self._in_buf  = 0
        self._use_buf = _QtCore.QMutex()
        for _ in range(num_buffer):
            self._buffer.append(_np.empty(**options.descriptor.numpy_formatter))
            self._in_buf += 1

        self._writer.start()

    def push(self, frame):
        """pushes the copy of the frame into the internal FIFO queue.
        pushing `None` will signal the thread to finish encoding."""
        if frame is not None:
            ## load one buffer frame
            img = None
            self._use_buf.lock()
            try:
                if self._in_buf == 0:
                    _LOGGER.error("***FATAL*** ran out of buffer!")
                else:
                    img = self._buffer.pop()
                    self._in_buf -= 1
            finally:
                self._use_buf.unlock()

            ## copy the content of frame into the buffer frame
            if img is None:
                img = frame.copy()
            else:
                img[:] = frame
        else:
            img = None

        ## push the buffer frame into the queue
        self._mutex.lock()
        try:
            self._queue.appendleft(img)
            self._count += 1
            self._signal.wakeAll()
        finally:
            self._mutex.unlock()

    def recycle(self, frame):
        """returns the used buffered frame back to the frame buffer.
        normally, this method is called from within the encoder thread."""
        self._use_buf.lock()
        try:
            self._buffer.append(frame)
            self._in_buf += 1
        finally:
            self._use_buf.unlock()

    # override
    def run(self):
        """runs the storage thread.

        1. waits for the event (either a frame / None is pushed, or signal() is called)
        2. processes the event:
            - a frame: passes it to the writer thread.
            - None: finishes its intermediatary job.
            - signal(): aborts encoding without passing any more frames in the FIFO.
        """
        try:
            while True:
                self._mutex.lock()
                try:
                    if self._count == 0:
                        self._signal.wait(self._mutex)
                except:
                    _print_exc()
                    self._mutex.unlock()
                    self._writer.push(None)
                    break # no more while loop

                if self._toquit == True:
                    self._mutex.unlock()
                    self._writer.push(None)
                    break # no more while loop

                # now there should be a frame in the FIFO
                try:
                    img = self._queue.pop()
                    self._count -= 1
                finally:
                    self._mutex.unlock()

                # just pass the acquired frame to the writer
                self._writer.push(img)
                if img is None:
                    break # no more while loop (i.e. end of the thread)
        finally:
            writer = self._writer
            if writer.wait() == False:
                _LOGGER.error("BufferThread::run -- EncodingThread.wait() returned False")
                writer.terminate()
                writer.wait() # do not check

    def signal(self):
        """tell the thread to abort waiting for any more frames.
        the frames remaining in the FIFO will not be saved."""
        self._mutex.lock()
        try:
            self._toquit = True
            self._signal.wakeAll()
        finally:
            self._mutex.unlock()

from .experiment import Experiment as _Experiment
