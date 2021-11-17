import warnings as _warnings
import re as _re
import subprocess as _sp

from . import LOGGER as _LOGGER

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


FFMPEG_PATH  = find_command('ffmpeg')
BASE_OPTIONS = [
    "-hide_banner", "-loglevel", "warning", "-stats", # render the command to be (more) quiet
    "-y", # overwrite by default
]
if FFMPEG_PATH is not None:
    _LOGGER.debug(f"found 'ffmpeg' at: {FFMPEG_PATH}")

def ffmpeg_command(with_base_options=True):
    if with_base_options:
        return [FFMPEG_PATH,] + BASE_OPTIONS
    else:
        return [FFMPEG_PATH,]

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

def test_decoder(codec):
    if FFMPEG_PATH is None:
        return False # no meaning in asking the question
    from pathlib import Path
    testdir = Path(__file__).resolve().parent
    filepat = testdir / "enctest" / "%03d.jpg"
    outfile = testdir / "enctest.avi"
    if outfile.exists():
        outfile.unlink() # just in case
    try:
        proc    = _sp.run([FFMPEG_PATH,] + BASE_OPTIONS + \
                          ["-f", "image2",
                           "-framerate", "1",
                           "-i", str(filepat),
                           "-r", "1",
                           "-c:v", str(codec),
                           str(outfile)], capture_output=True)
        if outfile.exists():
            status = "output file is generated"
        else:
            status = "output file does not exist"
        _LOGGER.info(f"testing encoder '{codec}': ffmpeg returned code {proc.returncode}; {status}")
        if proc.returncode != 0:
            for line in proc.stderr.decode().split("\n"):
                line = line.strip()
                if len(line) > 0:
                    _LOGGER.error(line)
        return (proc.returncode == 0) and outfile.exists()
    except:
        from traceback import print_exc
        print_exc()
        return False
    finally:
        if outfile.exists():
            outfile.unlink()
