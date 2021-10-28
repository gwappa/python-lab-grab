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

class NvidiaGPU(_namedtuple("_NvidiaGPU", ("index", "name", "uuid"))):
    NAME_PATTERN = _re.compile(r"GPU (\d+): ([a-zA-Z0-9 -]+) \(UUID: ([a-zA-Z0-9-]+)\)")
    THREADS_PER_CORE = 3
    from . import nvenc as NVENC

    @classmethod
    def parse(cls, line):
        matches = cls.NAME_PATTERN.match(line.strip())
        if not matches:
            _LOGGER.warning(f"failed to parse: {line.strip()}")
            return cls(-1, "<unknown>", "0")
        index = int(matches.group(1))
        name  = str(matches.group(2))
        uuid  = str(matches.group(3))
        return cls(index, name, uuid)

    def has_nvenc_h264(self):
        if ("Quadro" in self.name) or ("NVS" in self.name) or ("Tesla" in self.name):
            ## FIXME
            _LOGGER.warning("note that having this type of GPUs does not ascertain the availability of NVEnc functionality: " \
                         "check the list of supported GPUs at: https://developer.nvidia.com/video-encode-and-decode-gpu-support-matrix-new")
            return True
        elif self.name in self.NVENC.NONE.keys():
            _LOGGER.warning(f"{self.name} appears to have no NVENC core.")
            return False
        elif self.name in self.NVENC.AMBIG.keys():
            _LOGGER.warning(f"unable to determine whether {self.name} has an NVENC core. NVENC functionality may not work properly.")
            return True
        elif self.name not in self.NVENC.COMPAT.keys():
            _LOGGER.warning(f"{self.name} is not registered in the list of NVENC-compatible NVIDIA cores. This may mean the core is either too old or too new. Consult the developer if you think it is a bug.")
            return False
        else:
            n_cores = [self.NVENC.NVENC_CORES_H264.get(coretype, 0) for coretype in self.NVENC.COMPAT[self.name]]
            min_cores = min(n_cores)
            max_cores = max(n_cores)
            if min_cores == max_cores:
                _LOGGER.info(f"{self.name}: number of NVENC cores: {max_cores} " \
                             f"(up to {max_cores*self.THREADS_PER_CORE} simultaneous encoding)")
            else:
                _LOGGER.info(f"{self.name}: number of NVENC cores: {min_cores}-{max_cores}" \
                             f"(depends; possibly up to {max_cores*self.THREADS_PER_CORE} simultaneous encoding)")
            if min_cores == 0:
                _LOGGER.warning(f"note that {self.name} may _not_ have an NVENC-compatible core, and the functionality may not work properly.")
            return max_cores > 0

def number_of_nvenc_gpus():
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

    GPUs = [NvidiaGPU.parse(item.strip()) for item in proc.stdout.decode().split("\n") if len(item.strip()) > 0]
    if len(GPUs) > 0:
        names = f" ({', '.join(core.name for core in GPUs)})"
    else:
        names = ""
    _LOGGER.info(f"number of NVIDIA GPUs available: {len(GPUs)}{names}")
    return len([core for core in GPUs if core.has_nvenc_h264()])

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

def QSV_is_available():
    if FFMPEG_PATH is None:
        return False # no meaning in asking the question
    from pathlib import Path
    testdir = Path(__file__).resolve().parent
    filepat = testdir / "qsvtest" / "%03d.jpg"
    outfile = testdir / "qsvtest.avi"
    if outfile.exists():
        outfile.unlink() # just in case
    try:
        proc    = _sp.run([FFMPEG_PATH,] + BASE_OPTIONS + \
                          ["-f", "image2",
                           "-framerate", "1",
                           "-i", str(filepat),
                           "-r", "1",
                           "-c:v", "mjpeg_qsv",
                           str(outfile)])
        if outfile.exists():
            status = "output file is generated"
        else:
            status = "output file does not exist"
        _LOGGER.info(f"testing QSV functionality: ffmpeg returned code {proc.returncode}; {status}")
        return (proc.returncode == 0) and outfile.exists()
    except:
        from traceback import print_exc
        print_exc()
        return False
    finally:
        if outfile.exists():
            outfile.unlink()

### encoding-related classes

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
            return QSV_is_available()
        elif device == cls.NVIDIA:
            return (number_of_nvenc_gpus() > 0)
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

    def as_ffmpeg_command(self, outpath, descriptor, framerate=30, quality=75):
        """returns a list of options used to encode using the ffmpeg command."""

        ## FIXME: how shall we set e.g. the CRF value / bit rate?
        return [FFMPEG_PATH,] + BASE_OPTIONS \
                + ffmpeg_input_options(
                    width=descriptor.width,
                    height=descriptor.height,
                    framerate=framerate,
                    pixel_format=descriptor.pixel_format.ffmpeg_style
                ) \
                + [ "-vcodec", self.vcodec ] + self.quality_option(quality) \
                + [
                    "-pix_fmt", self.pix_fmt,
                    str(outpath)
                ]

    def open_ffmpeg(self, outpath, descriptor, framerate=30, quality=75):
        """opens and returns a `subprocess.Popen` object
        corresponding to the encoder process."""
        return _sp.Popen(self.as_ffmpeg_command(outpath, descriptor, framerate, quality),
                            stdin=_sp.PIPE)

def no_quality_option(value):
    _LOGGER.debug("no quality norm defined")
    return []

def mjpeg_quality_option(value):
    """returns the value from 2 to 31, with a lower value being a higher quality."""
    quality = 31 + round((1 - value) * 29 / 99)
    _LOGGER.debug(f"MJPEG quality norm: {quality}")
    return [ "-q:v", str(quality) ]

def h264_nvenc_quality_option(value):
    """try to convert quality from 10 to 43, with a lower value being a higher quality."""
    quality = 43 + round((1 - value) * 33 / 99)
    _LOGGER.debug(f"NVEnc quality norm: {quality}")
    return [ "-rc:v", "vbr", "-cq:v", str(quality) ]


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
        """returns (process, stream)"""
        proc = self.encoder.open_ffmpeg(self.path,
                                        descriptor=self.descriptor,
                                        framerate=self.framerate,
                                        quality=self.quality)
        return proc, proc.stdin

class WriterThread(_QtCore.QThread):
    DEFAULT_TIMEOUT       = 3.0

    def __init__(self,
                 options,
                 buffer=None,
                 parent=None):
        super().__init__(parent=parent)
        self._buffer  = buffer
        self._proc, self._sink = options.open_stream()
        self._queue   = _deque()
        self._count   = 0
        self._mutex   = _QtCore.QMutex()
        self._signal  = _QtCore.QWaitCondition()
        self._toquit  = False

    def push(self, frame):
        """pushes the frame (not copied) into the internal FIFO queue.
        pushing `None` will signal the thread to finish encoding."""
        self._mutex.lock()
        try:
            if frame is None:
                self._queue.appendleft(None)
            else:
                self._queue.appendleft(frame) ### CAUTION: NO COPY OCCURS HERE
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
                self._sink.write(img.tobytes())
                self._buffer.recycle(img)
            except:
                _print_exc()
                break # no more while loop

        # close the pipe
        proc = self._proc
        stdout, stderr = self._terminate_safely(proc)
        if stdout is not None:
            print(stdout.decode('utf-8'), file=_sys.stdout, flush=True)
        if stderr is not None:
            print(stderr.decode('utf-8'), file=_sys.stderr, flush=True)
        self._proc = None
        del proc

    def _terminate_safely(self, proc):
        # 'safely' terminate the process
        try:
            stdout, stderr = proc.communicate(timeout=self.DEFAULT_TIMEOUT)
        except TimeoutExpired:
            _LOGGER.error("The encoder process did not seem to finish within the expected time window.")
            proc.kill()
            stdout, stderr = proc.communicate()
        return stdout, stderr

    def signal(self):
        """tell the thread to abort waiting for any more frames.
        the frames remaining in the FIFO will not be saved."""
        self._mutex.lock()
        try:
            self._toquit = True
            self._signal.wakeAll()
        finally:
            self._mutex.unlock()
