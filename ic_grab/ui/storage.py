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
import re as _re

import numpy as _np
from pyqtgraph.Qt import QtCore as _QtCore

from .. import LOGGER as _LOGGER

def find_command(cmd):
    proc = _sp.run(["where", cmd], shell=True,
                   capture_output=True)
    if proc.returncode != 0:
        _warnings.warn(f"failed to find the '{cmd}' command: 'where' returned code {proc.returncode}")
        return None

    commands = [item.strip() for item in proc.stdout.decode().split("\n")]
    if len(commands) == 0:
        _warnings.warn(f"the '{cmd}' command not found")
        return None
    return commands[0]

### ffmpeg-related ###

FFMPEG_PATH  = find_command('ffmpeg')
BASE_OPTIONS = [
    "-hide_banner", "-loglevel", "warning", "-stats", # render the command to be (more) quiet
    "-y", # overwrite by default
]
if FFMPEG_PATH is not None:
    _LOGGER.debug(f"found 'ffmpeg' at: {FFMPEG_PATH}")

def ffmpeg_input_options(width, height, framerate, pixel_format="rgb24"):
    return [
        "-f", "rawvideo",
        "-vcodec", "rawvideo",
        "-s", f"{width}x{height}",
        "-pix_fmt", pixel_format,
        "-r", str(framerate),
        "-i", "-",
        "-an", # do not expect any audio
    ]

### encoder-related

def number_of_nvidia_gpus():
    nvidia_smi = find_command('nvidia-smi')
    if nvidia_smi is None:
        return 0  # cannot detect NVIDA driver

    # check the version of the driver
    proc = _sp.run([nvidia_smi], shell=True, capture_output=True)
    if proc.returncode != 0:
        _warnings.warn(f"failed to run 'nvidia-smi': code {proc.returncode}")
        return 0
    out = [line.strip() for line in proc.stdout.decode().split("\n") if len(line.strip()) > 0]
    pattern = _re.compile(r"Driver Version: (\d+(\.\d+)?)") # trying to capture only 'xx.yy', instead of 'xx.yy.zz'
    version = None
    for line in out:
        matched = pattern.search(line)
        if matched:
            version = matched.group(1)
            break
    if version is None:
        _LOGGER.warning("failed to parse the driver version from 'nvidia-smi'")
        return 0
    major, minor = [int(digits) for digits in version.split(".")]
    _LOGGER.debug(f"NVIDIA driver version: {version} (major={major}, minor={minor})")
    if major < 450:
        _LOGGER.warning("NVIDIA driver must be newer than 450.xx: please update via https://www.nvidia.com/Download/driverResults.aspx/176854/en-us")
        return 0

    # check the number of GPUs abailable
    proc = _sp.run([nvidia_smi, "-L"], shell=True,
                   capture_output=True)
    if proc.returncode != 0:
        err = proc.stderr.decode().strip()
        _warnings.warn(f"failed to list up available GPUs: 'nvidia-smi' returned code {proc.returncode} ({err})")
        return 0

    GPUs = [item.strip() for item in proc.stdout.decode().split("\n") if len(item.strip()) > 0]
    _LOGGER.info(f"number of NVIDIA GPUs available: {len(GPUs)}")
    ## FIXME
    _LOGGER.warn("note that having a GPU does not ascertain the availability of NVEnc functionality: check the list of supported GPUs at: https://developer.nvidia.com/video-encode-and-decode-gpu-support-matrix-new")
    return len(GPUs)

class EncodingDevices:
    NONE   = "None"
    CPU    = "CPU"
    QSV    = "Intel-QSV CPU"
    NVIDIA = "NVIDIA GPU"

    _availability = dict()

    @classmethod
    def available(cls, device):
        device = str(device)
        if device not in cls._availability.keys():
            cls._availability[device] = cls.check_availability(device)
        return cls._availability[device]

    @classmethod
    def check_availability(cls, device):
        """explicitly check the availability of the device."""
        device = str(device)
        if device == cls.NONE:
            return True
        elif device == cls.CPU:
            return True
        elif device == cls.QSV:
            # FIXME
            _LOGGER.warning("the current version of the program cannot detect the availability of Intel QSV. the option is disabled.")
            return False
        elif device == cls.NVIDIA:
            return (number_of_nvidia_gpus() > 0)
        else:
            _LOGGER.warning("unknown encoder device name: " + device)
            return False

class Encoder(_namedtuple("_Encoder", ("name", "device", "suffix", "vcodec", "pix_fmt"))):
    @property
    def description(self):
        return f"{self.label} (*{self.suffix})"

    @property
    def label(self):
        ret = self.name
        if self.device != EncodingDevices.NONE:
            ret += ", " + self.device + "-encoding"
        return ret

    def as_ffmpeg_command(self, outpath, descriptor, framerate=30):
        """returns a list of options used to encode using the ffmpeg command."""

        ## FIXME: how shall we set e.g. the CRF value / bit rate?
        return [FFMPEG_PATH,] + BASE_OPTIONS \
                + ffmpeg_input_options(
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

BASE_ENCODER_LIST = (
    Encoder("Raw video", EncodingDevices.NONE,   ".avi", "rawvideo", "yuv420p"),
    Encoder("MJPEG",     EncodingDevices.CPU,    ".avi", "mjpeg",    "yuvj420p"),
    Encoder("MJPEG",     EncodingDevices.QSV,    ".avi", "mjpeg_qsv", "yuvj420p"),
    Encoder("H.264",     EncodingDevices.NVIDIA, ".avi", "h264_nvenc", "yuv420p"),
)

### the main storage service

class StorageService(_QtCore.QObject):
    EXPERIMENT_ATTRIBUTES = ("subject", "datestr", "indexstr", "domain", "appendagestr")
    TIMESTAMP_FORMAT      = "%H%M%S"
    DEFAULT_NAME_PATTERN  = "{subject}_{date}_{domain}_{time}{appendage}"
    DEFAULT_TIMEOUT       = 3.0

    DEFAULT_ENCODERS = tuple(enc for enc in BASE_ENCODER_LIST if EncodingDevices.available(enc.device))

    _singleton = None

    updatedEncoder   = _QtCore.pyqtSignal(object) # an Encoder object
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
        self._encoder    = self.DEFAULT_ENCODERS[0]
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
        return out

    def load_dict(self, cfg):
        for key in ("directory", "pattern", "encoder"):
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
        self._proc = self._encoder.open_ffmpeg(self.as_path(self.filename),
                                               descriptor=descriptor,
                                               framerate=framerate)
        self._sink      = self._proc.stdin
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
        if self._proc is not None:
            proc = self._proc
            # 'safely' terminate the process
            try:
                stdout, stderr = proc.communicate(timeout=self.DEFAULT_TIMEOUT)
            except TimeoutExpired:
                proc.kill()
                stdout, stderr = proc.communicate()
            if stdout is not None:
                print(stdout.decode('utf-8'), file=_sys.stdout, flush=True)
            if stderr is not None:
                print(stderr.decode('utf-8'), file=_sys.stderr, flush=True)
            self._proc = None
            del proc

    def is_running(self):
        """returns whether the storage service is currently running the encoder process."""
        return (self._proc is not None)

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
    directory = property(fget=getDirectory, fset=setDirectory)
    pattern   = property(fget=getPattern,   fset=setPattern)
    filename  = property(fget=updateFileName)

from .experiment import Experiment as _Experiment
