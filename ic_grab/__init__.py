import logging as _logging
import argparse as _ap

import tisgrabber as _tisgrabber

__VERSION__ = "0.1.1.2021072101"

_logging.basicConfig(level=_logging.INFO,
                     format="[%(asctime)s %(name)s] %(levelname)s: %(message)s")

LOGGER = _logging.getLogger(__name__)
LOGGER.setLevel(_logging.INFO)

PARSER = _ap.ArgumentParser(description="grabs videos from an ImagingSource camera.")
PARSER.add_argument("device", nargs='?', default=None,
                    help="the 'unique name' of the device as it shows up on the device selection dialog.")

def parse_commandline():
    run(**vars(PARSER.parse_args()))

def run(device=None):
    LOGGER.info(f"ic-grab version {__VERSION__}")
    from . import ui
    main = ui.MainWindow()
    # TODO: attempt to open the device in case it is not None
    ui.run()
    # grabber = _tisgrabber.TIS_CAM()
    # grabber.showDeviceSelectionDialog()
    # if grabber.isDeviceValid():
    #     LOGGER.info(f"device selected: {grabber.uniqueDeviceName}")
    # else:
    #     LOGGER.info("no device was selected")
    #     return
