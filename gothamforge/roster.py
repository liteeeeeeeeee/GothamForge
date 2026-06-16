import re
from pathlib import Path

COLLECT_RE = re.compile(r'^(\s*)collect\s+"([^"]+)"\s*(.*?)\s*(//.*)?$')


class Collection:
    def __init__(self, path):
        self.path = Path(path)
        self.lines = self.path.read_text(encoding="latin-1").split("\n")

    def entries(self):
        out = []
        for i, line in enumerate(self.lines):
            m = COLLECT_RE.match(line)
            if m:
                indent, name, spec, comment = m.groups()
                out.append({"line": i, "name": name, "comment": comment or "",
                            **self._parse_spec(spec)})
        return out

    @staticmethod
    def _parse_spec(spec):
        spec = spec.strip()
        method, cost, area = None, None, None
        if re.search(r"\bbuy_in_shop\b", spec):
            method = "buy_in_shop"
            m = re.search(r"buy_in_shop\s+(\d+)", spec)
            cost = int(m.group(1)) if m else 0
        elif re.search(r"\barea_complete\b", spec):
            method = "area_complete"
            m = re.search(r'area_complete\s+"([^"]+)"', spec)
            area = m.group(1) if m else ""
        elif re.search(r"\bminikit\b", spec):
            method = "minikit"
        elif re.search(r"\bstory\b", spec):
            method = "story"
        cc = re.search(r'cheat_code\s+"([^"]+)"', spec)
        return {"method": method, "cost": cost, "area": area,
                "customiser": "customiser_parts" in spec,
                "cheat_code": cc.group(1) if cc else None,
                "cheat_code_only": bool(re.search(r"\bcheat_code_only\b", spec))}

    @staticmethod
    def _compose(e):
        parts = []
        if e["cheat_code"]:
            parts.append(f'cheat_code "{e["cheat_code"]}"')
        if e["cheat_code_only"]:
            parts.append("cheat_code_only")
        elif e["method"] == "story":
            parts.append("story")
        elif e["method"] == "buy_in_shop":
            parts.append(f"buy_in_shop {int(e['cost'] or 0)}")
        elif e["method"] == "area_complete":
            parts.append(f'area_complete "{e["area"] or ""}"')
        elif e["method"] == "minikit":
            parts.append("minikit")
        if e["customiser"]:
            parts.append("customiser_parts")
        return " ".join(parts)

    def find(self, name):
        for e in self.entries():
            if e["name"].lower() == name.lower():
                return e
        return None

    def _set(self, name, **changes):
        for i, line in enumerate(self.lines):
            m = COLLECT_RE.match(line)
            if m and m.group(2).lower() == name.lower():
                indent, _n, spec, comment = m.groups()
                e = self._parse_spec(spec)
                e.update(changes)
                new_spec = self._compose(e)
                tail = ("  " + comment) if comment else ""
                self.lines[i] = (f'{indent}collect "{name}" {new_spec}'.rstrip() + tail)
                return True
        return False

    def set_unlock(self, name, method, cost=None, area=None, customiser=None):
        ch = {"method": "story" if method == "free" else method}
        if cost is not None:
            ch["cost"] = cost
        if area is not None:
            ch["area"] = area
        if customiser is not None:
            ch["customiser"] = customiser
        if method in ("free", "story", "minikit"):
            ch["cheat_code_only"] = False  
        return self._set(name, **ch)

    def set_cost(self, name, cost):
        return self._set(name, method="buy_in_shop", cost=int(cost), cheat_code_only=False)

    def make_free(self, name):
        return self._set(name, method="story", cheat_code_only=False)

    def set_cheat_code(self, name, code):
        return self._set(name, cheat_code=(code or None))

    def set_cheat_code_only(self, name, on):
        return self._set(name, cheat_code_only=bool(on))

    def cheat_entries(self):
        return self.entries()

    def save(self, path=None):
        Path(path or self.path).write_text("\n".join(self.lines), encoding="latin-1")


class CharData:

    def __init__(self, path):
        self.path = Path(path)
        self.text = self.path.read_text(encoding="latin-1")

    def registered(self):
        return [m.group(1) for m in re.finditer(r'validate\s+"([^"]+)"', self.text)]
