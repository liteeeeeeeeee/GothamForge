import re
from pathlib import Path

FLYING_RE = re.compile(
    r"^(\s*)(FlyingStreak)\s+(\d+)\s+(\d+)\s+([0-9.]+)\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)(.*)$", re.I)
NAMED_RE = re.compile(r"^(\s*)streak\s+(\w+)(.*)$", re.I)

KNOWN_STREAK_NAMES = ["yellow", "red", "blue", "green", "white", "cyan", "purple", "orange"]


class StreakFile:
    def __init__(self, path):
        self.path = Path(path)
        self.lines = self.path.read_text(encoding="latin-1").split("\n")

    def flying(self):
        out = []
        for i, line in enumerate(self.lines):
            m = FLYING_RE.match(line)
            if m:
                out.append({"line": i, "idx": int(m.group(3)), "loc": int(m.group(4)),
                            "width": m.group(5), "r": int(m.group(6)), "g": int(m.group(7)),
                            "b": int(m.group(8)), "a": int(m.group(9))})
        return out

    def named(self):
        for i, line in enumerate(self.lines):
            m = NAMED_RE.match(line)
            if m:
                return {"line": i, "name": m.group(2)}
        return None

    def set_flying(self, line, r, g, b, a=None, width=None):
        m = FLYING_RE.match(self.lines[line])
        if not m:
            return False
        indent, tag, idx, loc, w, _r, _g, _b, a0, comment = m.groups()
        a = a0 if a is None else a
        w = w if width is None else width
        self.lines[line] = f"{indent}{tag} {idx} {loc} {w} {int(r)} {int(g)} {int(b)} {int(a)}{comment}"
        return True

    def set_named(self, name):
        n = self.named()
        if n is None:
            return False
        m = NAMED_RE.match(self.lines[n["line"]])
        indent, _name, comment = m.groups()
        self.lines[n["line"]] = f"{indent}streak {name}{comment}"
        return True

    def save(self, path=None):
        Path(path or self.path).write_text("\n".join(self.lines), encoding="latin-1")

    def cd_sidecar(self):
        cd = self.path.with_suffix(".CD")
        return cd if cd.exists() else None


def find_streak_chars(game):
    out = []
    pat = re.compile(r"(?im)^\s*(FlyingStreak|streak)\b")
    for p in game.find_chars():
        try:
            if pat.search(p.read_text(encoding="latin-1")):
                out.append(p)
        except Exception:
            pass
    return out
