import logging as _logging

import tisgrabber as _tisgrabber

__VERSION__ = "0.1.0.2021071601"

_logging.basicConfig(level=_logging.INFO,
                     format="[%(asctime)s %(name)s] %(levelname)s: %(message)s")

LOGGER = _logging.getLogger(__name__)
LOGGER.setLevel(_logging.INFO)

def parse_commandline():
    LOGGER.info(f"ic-grab version {__VERSION__}")
    grabber = _tisgrabber.TIS_CAM()
    grabber.showDeviceSelectionDialog()
    if grabber.isDeviceValid():
        LOGGER.info(f"device selected: {grabber.uniqueDeviceName}")
    else:
        LOGGER.info("no device was selected")
        return
