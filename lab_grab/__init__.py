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

import logging as _logging
import argparse as _ap

import tisgrabber as _tisgrabber

__VERSION__  = "0.6.1.2021120604"

PARSER = _ap.ArgumentParser(description="grabs videos from an ImagingSource camera.")
PARSER.add_argument("--debug", action="store_true",
                    help="enables the debug-level logging.")

LOGGER = None
DEBUG  = False

def init_logger():
    global LOGGER
    level = _logging.DEBUG if DEBUG == True else _logging.INFO
    _logging.basicConfig(level=level,
                         format="[%(asctime)s %(name)s] %(levelname)s: %(message)s")
    LOGGER = _logging.getLogger(__name__)
    LOGGER.setLevel(level)

def logger():
    global LOGGER
    if LOGGER is None:
        init_logger()
    return LOGGER

def parse_commandline():
    run(**vars(PARSER.parse_args()))

def run(debug=False):
    global DEBUG
    if debug == True:
        DEBUG = True
    init_logger()

    LOGGER.info(f"lab-grab version {__VERSION__}")
    if DEBUG == True:
        LOGGER.info("")
        LOGGER.info("  ========== DEBUG MODE ==========  ")
        LOGGER.info("")
    from . import ui
    main = ui.MainWindow()
    # TODO: attempt to open the device in case it is not None
    ui.run()
