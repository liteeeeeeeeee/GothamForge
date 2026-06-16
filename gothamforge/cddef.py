import struct
from pathlib import Path

from . import tex

MAT_PREFIX = "MiniFigs\\Super_Characters\\"
COLOUR_DIR = "MiniFigs\\Super_Characters\\LEGO_Colours\\"

LAYER_BYTE1 = [("Left hand", 0x01), ("Right hand", 0x02), ("Torso", 0x04), ("Left arm", 0x08),
               ("Right arm", 0x10), ("Head", 0x20), ("Neck", 0x40), ("Hips", 0x80)]
LAYER_BYTE2 = [("Left leg", 0x01), ("Right leg", 0x02), ("Cape", 0x04), ("Addon 1", 0x08),
               ("Addon 2", 0x10), ("Addon 3", 0x20), ("Addon 4", 0x40), ("Addon 5", 0x80)]
LAYER_BYTE3 = [("Attachment", 0x01), ("Glasses", 0x02), ("Hair", 0x04), ("Hat", 0x08),
               ("Special 1", 0x10), ("Special 2", 0x20), ("Special 3", 0x40), ("Special 4", 0x80)]
LAYER_PRESETS = {  
    "Standard minifig (BF)": 0xBF,
    "Custom head (DF)": 0xDF,
    "Everything (FF)": 0xFF,
}


def find_layer_block(d):
    start = int(len(d) * 0.5)
    for q in range(max(start, 3), len(d) - 12):
        if d[q] != 0 and d[q - 3:q] == b"\xff\xff\xff" and d[q + 8] == d[q] and d[q + 9] == d[q + 1]:
            return q
    return None


def _scan(d):
    out = []
    i, n = 0, len(d)
    while i + 4 < n:
        L = struct.unpack_from("<I", d, i)[0]
        if 2 < L < 128 and i + 4 + L <= n and d[i + 4 + L - 1:i + 4 + L] == b"\x00" \
                and all(32 <= c < 127 for c in d[i + 4:i + 4 + L - 1]):
            out.append((i + 4, d[i + 4:i + 4 + L - 1].decode("latin-1")))
            i += 4 + L
        else:
            i += 1
    return out


class LegoColours:

    def __init__(self, game):
        self.dir = game.root / "CHARS" / "MINIFIGS" / "SUPER_CHARACTERS" / "LEGO_COLOURS"
        self._rgb = {}
        self._files = {}
        if self.dir.is_dir():
            for p in self.dir.glob("*.TEX"):
                name = p.stem.upper().replace("_NXG", "")
                self._files[name] = p

    def names(self):
        return sorted(self._files)

    def rgb(self, name):
        name = name.upper()
        if name in self._rgb:
            return self._rgb[name]
        p = self._files.get(name)
        if not p:
            return None
        try:
            from PIL import Image
            col = tex.to_image(p).resize((1, 1), Image.LANCZOS).getpixel((0, 0))[:3]
        except Exception:
            col = (128, 128, 128)
        self._rgb[name] = col
        return col

    def all_rgb(self):
        return {n: self.rgb(n) for n in self.names()}


def head_catalogue(game):

    out = {}
    for d in game.root.rglob("HEADS"):
        if d.is_dir():
            for p in d.glob("*.TEX"):
                out[p.stem.upper().replace("_NXG", "")] = p
    return out


class CdFile:
    def __init__(self, path):
        self.path = Path(path)
        self.d = bytearray(self.path.read_bytes())

    def materials(self):
        out = []
        for off, val in _scan(self.d):
            if val.startswith(MAT_PREFIX):
                out.append({
                    "index": len(out),
                    "offset": off,
                    "path": val,
                    "name": val.split("\\")[-1],
                    "kind": "colour" if "\\lego_colours\\" in val.lower() else "texture",
                })
        return out

    def set_colour(self, mat_index, colour_name):
        mats = self.materials()
        if not (0 <= mat_index < len(mats)):
            return False
        m = mats[mat_index]
        if m["kind"] == "colour" and "\\" in m["path"]:
            parent = m["path"].rsplit("\\", 1)[0]
            new_path = f"{parent}\\{colour_name}"
        else:
            new_path = COLOUR_DIR + colour_name
        return self._replace(m["offset"], new_path)

    def set_material(self, mat_index, new_leaf):

        mats = self.materials()
        if not (0 <= mat_index < len(mats)):
            return False
        m = mats[mat_index]
        parent = m["path"].rsplit("\\", 1)[0] if "\\" in m["path"] else m["path"]
        return self._replace(m["offset"], f"{parent}\\{new_leaf}")

    def head_materials(self):
        return [m for m in self.materials() if "\\heads\\" in m["path"].lower()]

    def _replace(self, value_off, new_value):
        d = self.d
        end = d.find(b"\x00", value_off)
        old_len = end - value_off
        nb = new_value.encode("latin-1")
        new_block = struct.pack("<I", len(nb) + 1) + nb + b"\x00"
        before = len(_scan(d))
        spliced = bytearray(d[:value_off - 4]) + new_block + bytearray(d[value_off + old_len + 1:])
        if len(_scan(spliced)) != before:
            return False                       
        self.d = spliced
        return True

    def is_minifig(self):
        return bool(self.materials())

    def layers(self):
        if not self.is_minifig():
            return None
        q = find_layer_block(self.d)
        if q is None:
            return None
        return {"offset": q, "byte1": self.d[q], "byte2": self.d[q + 1], "byte3": self.d[q + 2]}

    def set_layers(self, byte1, byte2, byte3):
        if not self.is_minifig():
            return False
        q = find_layer_block(self.d)
        if q is None:
            return False
        for base in (q, q + 8):          
            self.d[base] = byte1 & 0xFF
            self.d[base + 1] = byte2 & 0xFF
            self.d[base + 2] = byte3 & 0xFF
        return True

    def save(self, path=None):
        Path(path or self.path).write_bytes(self.d)
