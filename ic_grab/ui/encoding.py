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

import re as _re

import subprocess as _sp
import warnings as _warnings
from fractions import Fraction as _Fraction
from collections import namedtuple as _namedtuple
from collections import deque as _deque

from av import open as _avopen
from av import VideoFrame as _VideoFrame
from pyqtgraph.Qt import QtCore as _QtCore

from .. import LOGGER as _LOGGER

### encoder-related

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

class Devices:
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

class Encoder(_namedtuple("_Encoder", ("name", "device", "suffix", "vcodec", "pix_fmt", "quality_option"))):
    @property
    def description(self):
        return f"{self.label} (*{self.suffix})"

    @property
    def label(self):
        ret = self.name
        if self.device != Devices.NONE:
            ret += ", " + self.device + "-encoding"
        return ret

    def has_quality_setting(self):
        # return len(self.quality_option(1)) > 0
        return sum(1 for _ in self.quality_option(1)) > 0

    def open_stream(self, outpath, descriptor, framerate=30, quality=75):
        """returns the PyAV (container, stream) for this encoder."""
        if isinstance(framerate, int):
            framerate = _Fraction(str(framerate))
        else:
            framerate = _Fraction(f"{framerate:.1f}")
        container = _avopen(str(outpath), mode="w")
        stream    = container.add_stream(self.vcodec, rate=framerate,
                                         options=dict((k, v) for k, v in self.quality_option(quality)))
        stream.width   = descriptor.width
        stream.height  = descriptor.height
        stream.pix_fmt = self.pix_fmt
        return container, stream

def no_quality_option(value):
    _LOGGER.debug("no quality norm defined")
    yield from ()

def mjpeg_quality_option(value):
    """returns the value from 2 to 31, with a lower value being a higher quality."""
    quality = 31 + round((1 - value) * 29 / 99)
    _LOGGER.debug(f"MJPEG quality norm: {quality}")
    yield ("qscale", str(quality))

def h264_nvenc_quality_option(value):
    """try to convert quality from 10 to 43, with a lower value being a higher quality."""
    quality = 43 + round((1 - value) * 33 / 99)
    _LOGGER.debug(f"NVEnc quality norm: {quality}")
    yield ("rc", "vbr")
    yield ("cq", str(quality))


RAW_VIDEO  = Encoder("Raw video", Devices.NONE,   ".avi", "rawvideo",   "yuv420p",  no_quality_option)
MJPEG_CPU  = Encoder("MJPEG",     Devices.CPU,    ".avi", "mjpeg",      "yuvj420p", mjpeg_quality_option)
MJPEG_QSV  = Encoder("MJPEG",     Devices.QSV,    ".avi", "mjpeg_qsv",  "yuvj420p", mjpeg_quality_option)
H264_NVENC = Encoder("H.264",     Devices.NVIDIA, ".avi", "h264_nvenc", "yuv420p",  h264_nvenc_quality_option)

class Options(_namedtuple("_options", ("encoder", "path", "descriptor", "framerate", "quality"))):
    def __new__(cls,
                encoder=None,
                path=None,
                descriptor=None,
                framerate=30,
                quality=75):
        return super(Options, cls).__new__(cls,
                                           encoder=encoder,
                                           path=path,
                                           descriptor=descriptor,
                                           framerate=framerate,
                                           quality=quality)

    def open_stream(self):
        """returns (container, stream, frame_format)"""
        container, stream = self.encoder.open_stream(self.path,
                                                     descriptor=self.descriptor,
                                                     framerate=self.framerate,
                                                     quality=self.quality)
        return container, stream, self.descriptor.pixel_format.ffmpeg_style

class WriterThread(_QtCore.QThread):
    def __init__(self,
                 options,
                 parent=None):
        super().__init__(parent=parent)
        self._container, self._stream, self._pixfmt  = options.open_stream()
        self._queue   = _deque()
        self._count   = 0
        self._mutex   = _QtCore.QMutex()
        self._signal  = _QtCore.QWaitCondition()
        self._toquit  = False

    def push(self, frame):
        """pushes the copy of the frame into the internal FIFO queue.
        pushing `None` will signal the thread to finish encoding."""
        self._mutex.lock()
        try:
            if frame is None:
                self._queue.appendleft(None)
            else:
                self._queue.appendleft(frame.copy())
            self._count += 1
            self._signal.wakeAll()
        finally:
            self._mutex.unlock()

    # override
    def run(self):
        """runs the storage thread.

        1. waits for the event (either a frame / None is pushed, or signal() is called)
        2. processes the event:
            - a frame: encodes it and writes into the stream.
            - None: finishes the encoding.
            - signal(): aborts encoding without saving any more frames in the FIFO.
        """
        while True:
            self._mutex.lock()
            try:
                if self._count == 0:
                    self._signal.wait(self._mutex)
            except:
                _print_exc()
                self._mutex.unlock()
                break # no more while loop

            if self._toquit == True:
                self._container.close()
                self._mutex.unlock()
                return # just return without doing anything more

            # now there should be a frame in the FIFO
            try:
                img = self._queue.pop()
                self._count -= 1
            finally:
                self._mutex.unlock()

            if img is None:
                break # no more while loop

            try:
                # encode the frame
                for packet in self._stream.encode(_VideoFrame.from_ndarray(img, format=self._pixfmt)):
                    self._container.mux_one(packet) # NOCHECK isinstance(packet, AVPacket)
            except:
                _print_exc()
                break # no more while loop

        # flush stream
        for packet in self._stream.encode():
            self._container.mux_one(packet)
        self._container.close()

    def signal(self):
        """tell the thread to abort waiting for any more frames.
        the frames remaining in the FIFO will not be saved."""
        self._mutex.lock()
        try:
            self._toquit = True
            self._signal.wakeAll()
        finally:
            self._mutex.unlock()
