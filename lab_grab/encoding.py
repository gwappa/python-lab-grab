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

import subprocess as _sp
from collections import namedtuple as _namedtuple
from collections import deque as _deque

from pyqtgraph.Qt import QtCore as _QtCore

from . import logger as _logger
from . import backends as _backends

_LOGGER = _logger()

class Devices:
    NONE   = "None"
    CPU    = "CPU"
    QSV    = "Intel-QSV CPU"
    NVIDIA = "NVIDIA GPU"

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

    def check_availability(self):
        return _backends.test_decoder(self.vcodec)

    def has_quality_setting(self):
        # return len(self.quality_option(1)) > 0
        return sum(1 for _ in self.quality_option(1)) > 0

    def as_ffmpeg_command(self, outpath, descriptor, rotation, framerate=30, quality=75):
        """returns a list of options used to encode using the ffmpeg command."""

        ## FIXME: how shall we set e.g. the CRF value / bit rate?
        shape = rotation.transform_shape(descriptor.shape)
        return _backends.ffmpeg_command(with_base_options=True) \
                + _backends.ffmpeg_input_options(
                    width=shape[1],
                    height=shape[0],
                    framerate=framerate,
                    pixel_format=descriptor.color_format.ffmpeg_style
                ) \
                + [ "-vcodec", self.vcodec ] + self.quality_option(quality) \
                + [
                    "-pix_fmt", self.pix_fmt,
                    str(outpath)
                ]

    def open_ffmpeg(self, outpath, descriptor, rotation, framerate=30, quality=75):
        """opens and returns a `subprocess.Popen` object
        corresponding to the encoder process."""
        return _sp.Popen(self.as_ffmpeg_command(outpath, descriptor, rotation, framerate, quality),
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

class Options(_namedtuple("_options", ("encoder",
                                       "path",
                                       "descriptor",
                                       "rotation",
                                       "framerate",
                                       "quality"))):
    def __new__(cls,
                encoder=None,
                path=None,
                descriptor=None,
                rotation=None,
                framerate=30,
                quality=75):
        return super(Options, cls).__new__(cls,
                                           encoder=encoder,
                                           path=path,
                                           descriptor=descriptor,
                                           rotation=rotation,
                                           framerate=framerate,
                                           quality=quality)

    def open_stream(self):
        """returns (process, stream)"""
        proc = self.encoder.open_ffmpeg(self.path,
                                        descriptor=self.descriptor,
                                        rotation=self.rotation,
                                        framerate=self.framerate,
                                        quality=self.quality)
        return proc, proc.stdin
