import struct
import re
from pathlib import Path

MAGIC = b"\x7aV4\x12" 


def is_pak(path):
    try:
        with open(path, "rb") as f:
            return f.read(4) == MAGIC
    except Exception:
        return False


def _dds_total_size(d, off):
    size, flags, height, width, pitch, depth, mip = struct.unpack_from("<7I", d, off + 4)
    mip = max(1, mip)
    fourcc = d[off + 0x54: off + 0x58]
    block = 8 if fourcc == b"DXT1" else 16
    total = 128
    w, h = width, height
    for _ in range(mip):
        total += max(1, (w + 3) // 4) * max(1, (h + 3) // 4) * block
        w = max(1, w // 2)
        h = max(1, h // 2)
    return total


def list_entries(path):
    d = Path(path).read_bytes()
    if d[:4] != MAGIC:
        raise ValueError("not a PAK archive")
    count = struct.unpack_from("<I", d, 4)[0]
    offsets = [m.start() for m in re.finditer(b"DDS ", d)]
    region = d[0x10: offsets[0]] if offsets else b""
    names = [m.group(0).decode("latin-1")
             for m in re.finditer(rb"[A-Za-z0-9_]+\.[A-Za-z0-9]{2,4}", region)]
    entries = []
    for i, off in enumerate(offsets):
        try:
            size = _dds_total_size(d, off)
        except Exception:
            size = (offsets[i + 1] - off) if i + 1 < len(offsets) else (len(d) - off)
        name = names[i] if i < len(names) else f"texture_{i:03d}.tex"
        entries.append({"index": i, "name": Path(name).name, "offset": off, "size": size})
    return {"declared_count": count, "found": len(offsets), "entries": entries}


def extract_all(path, out_dir):
    d = Path(path).read_bytes()
    info = list_entries(path)
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    for e in info["entries"]:
        (out / e["name"]).write_bytes(d[e["offset"]: e["offset"] + e["size"]])
    return info


def extract_one(path, name, out_path):
    d = Path(path).read_bytes()
    for e in list_entries(path)["entries"]:
        if e["name"].lower() == name.lower():
            Path(out_path).write_bytes(d[e["offset"]: e["offset"] + e["size"]])
            return True
    return False
