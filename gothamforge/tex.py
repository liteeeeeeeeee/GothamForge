import struct
import shutil
from pathlib import Path

import numpy as np
from PIL import Image

from . import dxt

DDS_MAGIC = b"DDS "
NU2T = b"NU2T"

_DDSD = 0x1 | 0x2 | 0x4 | 0x1000 | 0x20000 | 0x80000  
_DDSCAPS_TEXTURE = 0x1000
_DDSCAPS_MIPMAP = 0x400000
_DDSCAPS_COMPLEX = 0x8


def read_info(path):
    with open(path, "rb") as f:
        d = f.read(128)
    if d[:4] != DDS_MAGIC:
        raise ValueError(f"{path}: not a DDS/TEX (magic={d[:4]!r})")
    size, flags, height, width, pitch, depth, mipcount = struct.unpack_from("<7I", d, 4)
    fourcc = d[0x54:0x58]
    caps4 = d[0x78:0x7C]
    return {
        "width": width,
        "height": height,
        "mipcount": mipcount,
        "fourcc": fourcc.decode("latin-1").rstrip("\x00"),
        "nu2t": caps4 == NU2T,
        "filesize": Path(path).stat().st_size,
    }


def to_dds(tex_path, dds_path):
    shutil.copyfile(tex_path, dds_path)
    return dds_path


def to_png(tex_path, png_path):
    img = Image.open(tex_path, formats=["DDS"]).convert("RGBA")
    img.save(png_path)
    return png_path


def to_image(tex_path):
    return Image.open(tex_path, formats=["DDS"]).convert("RGBA")


def _build_header(w, h, fmt, mipcount, linsize):
    hdr = bytearray(128)
    hdr[0:4] = DDS_MAGIC
    caps = _DDSCAPS_TEXTURE
    if mipcount > 1:
        caps |= _DDSCAPS_MIPMAP | _DDSCAPS_COMPLEX
    struct.pack_into("<7I", hdr, 4, 124, _DDSD, h, w, linsize, 0, mipcount)
    struct.pack_into("<2I", hdr, 0x4C, 32, 0x4)
    hdr[0x54:0x58] = b"DXT1" if fmt == "DXT1" else b"DXT5"
    struct.pack_into("<I", hdr, 0x6C, caps)
    hdr[0x78:0x7C] = NU2T  
    return bytes(hdr)


def _linsize(w, h, fmt):
    block = 8 if fmt == "DXT1" else 16
    return max(1, (w + 3) // 4) * max(1, (h + 3) // 4) * block


def encode_to_tex(src, tex_path, fmt=None, match=None, gen_mips=True):
    target_size = None
    if match:
        info = read_info(match)
        target_size = (info["width"], info["height"])
        if fmt is None:
            fmt = "DXT1" if info["fourcc"] == "DXT1" else "DXT5"

    img = Image.open(src) if isinstance(src, (str, Path)) else src
    img = img.convert("RGBA")
    if target_size and img.size != target_size:
        img = img.resize(target_size, Image.LANCZOS)

    if fmt is None:
        alpha = np.asarray(img)[..., 3]
        fmt = "DXT5" if (alpha < 255).any() else "DXT1"

    data, mipcount = dxt.encode(img, fmt, gen_mips=gen_mips)
    w, h = img.size
    header = _build_header(w, h, fmt, mipcount, _linsize(w, h, fmt))
    with open(tex_path, "wb") as f:
        f.write(header)
        f.write(data)
    return {"format": fmt, "size": (w, h), "mips": mipcount, "bytes": len(header) + len(data)}


def import_dds_as_tex(dds_path, tex_path):
    d = bytearray(Path(dds_path).read_bytes())
    if bytes(d[:4]) != DDS_MAGIC:
        raise ValueError("source is not a DDS file")
    if len(d) >= 0x7C:
        d[0x78:0x7C] = NU2T
    Path(tex_path).write_bytes(d)
    return read_info(tex_path)
