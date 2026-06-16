import os
from pathlib import Path

MARKER_FILE = "GAMEVERSION.TXT"
MARKER_DIR = "CHARS"


class GameInstall:
    def __init__(self, root):
        self.root = Path(root).resolve()
        self.version = {}
        self._read_version()

    def _read_version(self):
        vf = self.root / MARKER_FILE
        if vf.exists():
            for line in vf.read_text(errors="replace").splitlines():
                if ":" in line:
                    k, v = line.split(":", 1)
                    self.version[k.strip()] = v.strip()

    @property
    def is_valid(self):
        return (self.root / MARKER_FILE).exists() and (self.root / MARKER_DIR).is_dir()

    def path(self, *parts):
        return self.root.joinpath(*parts)

    @property
    def chars_dir(self):
        return self.root / "CHARS"

    @property
    def text_csv(self):
        return self.root / "STUFF" / "TEXT" / "TEXT.CSV"

    @property
    def icons_dir(self):
        return self.root / "STUFF" / "ICONS"

    @property
    def icons_pak(self):
        return self.root / "ICONS_TEX.PAK"

    def find_chars(self):
        if not self.chars_dir.is_dir():
            return []
        return sorted(self.chars_dir.rglob("*.TXT"), key=lambda p: p.name.lower())

    def find_vehicles(self):
        vd = self.chars_dir / "VEHICLES"
        if not vd.is_dir():
            return []
        return sorted(vd.rglob("*.TXT"), key=lambda p: p.name.lower())

    def find_textures(self):
        return sorted(self.root.rglob("*.TEX"), key=lambda p: str(p).lower())

    def __repr__(self):
        return f"<GameInstall {self.root} build={self.version.get('BuildRecordId','?')}>"


def find_game(start=None):
    candidates = []
    if start:
        candidates.append(Path(start))
    env = os.environ.get("LB2_PATH")
    if env:
        candidates.append(Path(env))
    here = Path(__file__).resolve()
    candidates.append(here.parents[2])
    candidates.append(Path.cwd())
    for p in list(candidates):
        try:
            candidates.extend(list(p.parents)[:4])
        except Exception:
            pass

    seen = set()
    for c in candidates:
        try:
            c = c.resolve()
        except Exception:
            continue
        if c in seen:
            continue
        seen.add(c)
        if (c / MARKER_FILE).exists() and (c / MARKER_DIR).is_dir():
            return GameInstall(c)
    return None
