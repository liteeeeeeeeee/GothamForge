import sys
import subprocess
import tempfile
from pathlib import Path
from shutil import which

try:
    import winsound
except Exception:
    winsound = None

try:
    import soundfile as sf
    import numpy as np
except Exception:
    sf = None
    np = None

_proc = None


def available():
    return winsound is not None or which("ffplay") is not None or sf is not None


def backends():
    b = []
    if winsound:
        b.append("winsound(wav)")
    if sf:
        b.append("soundfile(ogg)")
    if which("ffplay"):
        b.append("ffplay")
    return b


def _winsound_wav(path):
    winsound.PlaySound(str(path), winsound.SND_FILENAME | winsound.SND_ASYNC)


def play(path, tmp_dir=None):
    global _proc
    stop()
    path = Path(path)
    ext = path.suffix.lower()

    if winsound and ext == ".wav":
        _winsound_wav(path)
        return "winsound"

    if winsound and sf is not None:
        data, sr = sf.read(str(path), dtype="int16", always_2d=True)
        if data.shape[1] > 2:           
            data = data[:, :2]
        tmp = Path(tmp_dir or tempfile.gettempdir()) / "_gf_play.wav"
        tmp.parent.mkdir(parents=True, exist_ok=True)
        sf.write(str(tmp), data, sr, subtype="PCM_16")
        _winsound_wav(tmp)
        return "decoded+winsound"

    ff = which("ffplay")
    if ff:
        _proc = subprocess.Popen([ff, "-nodisp", "-autoexit", "-loglevel", "quiet", str(path)])
        return "ffplay"

    if sys.platform == "win32":
        import os
        os.startfile(str(path))  
        return "startfile"
    raise RuntimeError("no audio backend available")


def stop():
    global _proc
    if winsound:
        try:
            winsound.PlaySound(None, winsound.SND_PURGE)
        except Exception:
            pass
    if _proc is not None and _proc.poll() is None:
        try:
            _proc.terminate()
        except Exception:
            pass
    _proc = None
