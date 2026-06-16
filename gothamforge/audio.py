import struct
import re
import subprocess
from pathlib import Path

PAC_MAGIC = b"\x7aV4\x12" 
CBX_MAGIC = b"!B0X"


def list_ogg(game):
    base = game.root / "AUDIO" / "TRACKS"
    if not base.is_dir():
        base = game.root / "AUDIO"
    return sorted((p for p in base.rglob("*") if p.suffix.lower() == ".ogg"),
                  key=lambda p: str(p).lower())


class Bank:

    def __init__(self, path):
        self.path = Path(path)
        self.d = self.path.read_bytes()
        if self.d[:4] != PAC_MAGIC:
            raise ValueError("not a sound bank / PAC archive")
        self.count = struct.unpack_from("<I", self.d, 4)[0]
        self.entries = self._parse()

    def _parse(self):
        out = []
        for i in range(self.count):
            rec = 0x10 + i * 28
            if rec + 20 > len(self.d):
                break
            _f1, _f2, name_off, data_off, size = struct.unpack_from("<ffIII", self.d, rec)
            end = self.d.find(b"\x00", name_off)
            name = self.d[name_off:end].decode("latin-1", "replace") if 0 <= name_off < len(self.d) else f"sample_{i}"
            tag = self.d[data_off:data_off + 4]
            kind = "wav" if tag == b"RIFF" else ("cbx" if tag == CBX_MAGIC else "raw")
            out.append({"index": i, "name": name, "offset": data_off, "size": size, "kind": kind})
        return out

    def data(self, entry):
        return self.d[entry["offset"]: entry["offset"] + entry["size"]]

    def extract(self, entry, out_path):
        Path(out_path).write_bytes(self.data(entry))
        return out_path

    def find(self, substr):
        s = substr.lower()
        return [e for e in self.entries if s in e["name"].lower()]


def list_banks(game):
    return sorted(p for p in (game.root / "AUDIO").glob("*.PAC"))


def find_cbxdecoder(game):
    for c in [game.root / "CBXDecoder" / "CBXDecoder.exe", game.root / "CBXDecoder.exe"]:
        if c.exists():
            return c
    return None


def decode_cbx(cbx_path, decoder_exe):

    cbx_path = Path(cbx_path)
    r = subprocess.run([str(decoder_exe), str(cbx_path)],
                       input="\n", capture_output=True, text=True, timeout=120)
    wav = cbx_path.with_suffix(".wav")
    if wav.exists() and "success" in (r.stdout or "").lower():
        return wav
    raise RuntimeError("CBX decode failed: " + ((r.stdout or "") + (r.stderr or ""))[:200])


def extract_and_decode(bank, entry, work_dir, decoder_exe):
    work = Path(work_dir)
    work.mkdir(parents=True, exist_ok=True)
    base = Path(entry["name"]).name
    if entry["kind"] == "wav":
        out = work / (Path(base).stem + ".wav")
        bank.extract(entry, out)
        return out
    if entry["kind"] == "cbx":
        cbx = work / (Path(base).stem + ".cbx")
        bank.extract(entry, cbx)
        if not decoder_exe:
            raise RuntimeError("CBXDecoder.exe not found; cannot decode CBX.")
        return decode_cbx(cbx, decoder_exe)
    raise RuntimeError(f"entry '{entry['name']}' is neither WAV nor CBX")


class SamplesCfg:
    SAMPLE_RE = re.compile(r'^\s*Sample\s+name\s+"([^"]+)"\s+Filename\s+"([^"]+)"(.*)$', re.I)

    def __init__(self, path):
        self.path = Path(path)
        self.lines = self.path.read_text(encoding="latin-1").split("\n")

    def samples(self):
        out = []
        for i, line in enumerate(self.lines):
            m = self.SAMPLE_RE.match(line)
            if m:
                name, filename, rest = m.groups()
                out.append({"line": i, "name": name, "filename": filename,
                            "filetype": self._filetype(rest), "props": self._props(rest)})
        return out

    @staticmethod
    def _filetype(rest):
        m = re.search(r"FileType\s+(\w+)", rest, re.I)
        return m.group(1) if m else "WAV"  

    @staticmethod
    def _props(rest):
        props = {}
        toks = rest.split()
        i = 0
        while i < len(toks):
            t = toks[i]
            if t.lower() == "filetype" and i + 1 < len(toks):
                props["FileType"] = toks[i + 1]
                i += 2
            elif i + 1 < len(toks) and re.match(r"^-?\d*\.?\d+$", toks[i + 1]):
                props[t] = toks[i + 1]
                i += 2
            else:
                props[t] = True
                i += 1
        return props

    def find(self, name):
        for s in self.samples():
            if s["name"].lower() == name.lower():
                return s
        return None

    def set_filetype(self, name, filetype):
        for i, line in enumerate(self.lines):
            m = self.SAMPLE_RE.match(line)
            if m and m.group(1).lower() == name.lower():
                if re.search(r"FileType\s+\w+", line, re.I):
                    self.lines[i] = re.sub(r"FileType\s+\w+", f"FileType {filetype}", line, flags=re.I)
                else:
                    self.lines[i] = line.rstrip("\r") + f" FileType {filetype}" + ("\r" if line.endswith("\r") else "")
                return True
        return False

    def set_prop(self, name, key, value):
        for i, line in enumerate(self.lines):
            m = self.SAMPLE_RE.match(line)
            if m and m.group(1).lower() == name.lower():
                if re.search(rf"\b{re.escape(key)}\s+-?\d*\.?\d+", line):
                    self.lines[i] = re.sub(rf"(\b{re.escape(key)}\s+)-?\d*\.?\d+",
                                           rf"\g<1>{value}", line)
                else:
                    self.lines[i] = line.rstrip("\r") + f" {key} {value}" + ("\r" if line.endswith("\r") else "")
                return True
        return False

    def save(self, path=None):
        Path(path or self.path).write_text("\n".join(self.lines), encoding="latin-1")


def loose_sample_path(game, filename, ext="wav"):
    return game.root / "Audio" / "Samples" / (filename.replace("\\", "/") + "." + ext)
