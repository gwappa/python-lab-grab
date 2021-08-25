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
from collections import namedtuple as _namedtuple
import subprocess as _sp
import warnings as _warnings
import sys as _sys

import numpy as _np
from pyqtgraph.Qt import QtCore as _QtCore

from .. import LOGGER as _LOGGER

def find_ffmpeg():
    proc = _sp.run(["where", "ffmpeg"], shell=True,
                   capture_output=True)
    if proc.returncode != 0:
        _warnings.warn(f"failed to find the 'ffmpeg' command: 'where' returned code {proc.returncode}")
        return None

    commands = [item.strip() for item in proc.stdout.decode().split("\n")]
    if len(commands) == 0:
        _warnings.warn(f"the 'ffmpeg' command not found")
        return None
    return commands[0]

FFMPEG_PATH  = find_ffmpeg()
BASE_OPTIONS = [
    "-hide_banner", "-loglevel", "warning", "-stats", # render the command to be (more) quiet
    "-y", # overwrite by default
]
if FFMPEG_PATH is not None:
    _LOGGER.info(f"found 'ffmpeg' at: {FFMPEG_PATH}")

def input_options(width, height, framerate, pixel_format="rgb24"):
    return [
        "-f", "rawvideo",
        "-vcodec", "rawvideo",
        "-s", f"{width}x{height}",
        "-pix_fmt", pixel_format,
        "-r", str(framerate),
        "-i", "-",
        "-an", # do not expect any audio
    ]

class Encoders:
    NONE   = None
    CPU    = "CPU"
    QSV    = "Intel-QSV CPU"
    NVIDIA = "NVIDIA GPU"

class Codec(_namedtuple("_Codec", ("name", "encoder", "suffix", "vcodec", "pix_fmt"))):
    @property
    def description(self):
        return f"{self.label} (*{self.suffix})"

    @property
    def label(self):
        ret = self.name
        if self.encoder is not None:
            ret += ", " + self.encoder + "-encoding"
        return ret

    def as_ffmpeg_command(self, outpath, descriptor, framerate=30):
        """returns a list of options used to encode using the ffmpeg command."""

        ## FIXME: how shall we set e.g. the CRF value / bit rate?
        return [FFMPEG_PATH,] + BASE_OPTIONS \
                + input_options(
                    width=descriptor.width,
                    height=descriptor.height,
                    framerate=framerate,
                    pixel_format=descriptor.pixel_format.ffmpeg_style
                ) \
                + [
                    "-vcodec", self.vcodec,
                    "-pix_fmt", self.pix_fmt,
                    str(outpath)
                ]

    def open_ffmpeg(self, outpath, descriptor, framerate=30):
        """opens and returns a `subprocess.Popen` object
        corresponding to the encoder process."""
        return _sp.Popen(self.as_ffmpeg_command(outpath, descriptor, framerate),
                            stdin=_sp.PIPE)

class StorageService(_QtCore.QObject):
    EXPERIMENT_ATTRIBUTES = ("subject", "datestr", "indexstr", "domain", "appendagestr")
    TIMESTAMP_FORMAT      = "%H%M%S"
    DEFAULT_NAME_PATTERN  = "{subject}_{date}_{domain}_{time}{appendage}"
    DEFAULT_TIMEOUT       = 3.0

    CODECS = (
    # FIXME: better listing up only available ones (i.e. check availability upon initialization)
        Codec("Raw video", Encoders.NONE,   ".avi", "rawvideo", "yuv420p"),
        Codec("MJPEG",     Encoders.CPU,    ".avi", "mjpeg",    "yuvj420p"),
        # Codec("MJPEG",     Encoders.QSV,    ".avi", "mjpeg_qsv", "yuvj420p"),
        Codec("H.264",     Encoders.NVIDIA, ".avi", "h264_nvenc", "yuv420p"),
    )

    _singleton = None

    updatedCodec     = _QtCore.pyqtSignal(object) # a Codec object
    updatedDirectory = _QtCore.pyqtSignal(str)
    updatedPattern   = _QtCore.pyqtSignal(str)
    updatedFileName  = _QtCore.pyqtSignal(str)
    message          = _QtCore.pyqtSignal(str, str)

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
        self._codec      = self.CODECS[0]
        self._directory  = str(_Path().resolve())
        self._pattern    = self.DEFAULT_NAME_PATTERN

        self._experiment = _Experiment.instance() # must be non-None
        self._experiment.updated.connect(self.updateFileName)

        self._encoder    = None # the placeholder for the encoder process
        self._sink       = None # the STDIN of the encoder process
        self._nextindex  = None # the frame index being expected by the encoder (for detection of skips)
        self._empty      = None # the empty frame to be inserted in case of skips
        self._convert    = None # the function to make the frame into the proper structure

    def getCodec(self):
        return self._codec

    def setCodec(self, value):
        if isinstance(value, str):
            for codec in self.list_codecs():
                if codec.description == value:
                    value = codec
                    break
            if isinstance(value, str):
                raise ValueError(f"codec not found: '{value}'")
        self._codec = value
        self.updatedCodec.emit(self._codec)
        self.updateFileName()

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

    def list_codecs(self):
        return self.CODECS

    def prepare(self, framerate=30, descriptor=None):
        self._encoder = self._codec.open_ffmpeg(self.as_path(self.filename),
                                                descriptor=descriptor,
                                                framerate=framerate)
        self._sink      = self._encoder.stdin
        self._nextindex = 0
        self._empty     = _np.zeros(**descriptor.numpy_formatter)
        if self._empty.ndim == 3:
            self._convert = lambda frame: frame.transpose((1,0,2))
        else:
            self._convert = lambda frame: frame.T

    def write(self, index, frame):
        sink = self._sink
        while index > self._nextindex:
            sink.write(self._empty.tobytes())
            self._nextindex += 1
        sink.write(self._convert(frame).tobytes())
        self._nextindex += 1

    def close(self):
        if self._encoder is not None:
            proc = self._encoder
            try:
                stdout, stderr = proc.communicate(timeout=self.DEFAULT_TIMEOUT)
            except TimeoutExpired:
                proc.kill()
                stdout, stderr = proc.communicate()
            if stdout is not None:
                print(stdout.decode('utf-8'), file=_sys.stdout, flush=True)
            if stderr is not None:
                print(stderr.decode('utf-8'), file=_sys.stderr, flush=True)
            self._encoder = None
            del proc

    def is_running(self):
        """returns whether the storage service is currently running the encoder process."""
        return (self._encoder is not None)

    @property
    def suffix(self):
        return self._codec.suffix

    @property
    def format_dict(self):
        opts = dict((attrname, getattr(self._experiment, attrname))\
                    for attrname in self.EXPERIMENT_ATTRIBUTES)
        for name in ("date", "index", "appendage"):
            opts[name] = opts.pop(name + "str")
        opts["time"]   = _datetime.now().strftime(self.TIMESTAMP_FORMAT)
        opts["suffix"] = self.suffix
        return opts

    codec     = property(fget=getCodec,     fset=setCodec)
    directory = property(fget=getDirectory, fset=setDirectory)
    pattern   = property(fget=getPattern,   fset=setPattern)
    filename  = property(fget=updateFileName)

from .experiment import Experiment as _Experiment
