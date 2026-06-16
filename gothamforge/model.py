import struct
import re
import subprocess
from pathlib import Path

import numpy as np

VERTEX_ATTRS = ["POSITION", "NORMAL", "TEXCOORD", "COLOR", "TANGENT",
                "BINORMAL", "BLENDWEIGHT", "BLENDINDICES", "TEXTURE"]

DDS_MAGIC = b"DDS "

_TYPE_SIZE = {"vec4half": 8, "vec3float": 12, "vec2half": 4, "vec2float": 8,
              "vec4mini": 4, "vec4char": 4, "color4char": 4, "vec4ubyte": 4, "float": 4}


def find_extractor(game):
    tool_dir = Path(__file__).resolve().parents[1]   
    for d in (game.root, tool_dir, game.root / "GothamForge"):
        try:
            if d.is_dir():
                for p in d.glob("*.[eE][xX][eE]"):
                    if "extractnxgmesh" in p.name.lower():
                        return p
        except Exception:
            pass
    return None


def render_mesh(points, faces, yaw, pitch, W=340, H=340, bg=(16, 16, 20),
                base=(165, 175, 195)):
    img = np.zeros((H, W, 3), np.uint8)
    img[:] = bg
    if len(points) == 0:
        return img
    c = (points.max(0) + points.min(0)) / 2.0
    P = points - c
    scale = float(np.abs(P).max()) or 1.0
    P = P / scale
    cy, sy, cp, sp = np.cos(yaw), np.sin(yaw), np.cos(pitch), np.sin(pitch)
    Ry = np.array([[cy, 0, sy], [0, 1, 0], [-sy, 0, cy]])
    Rx = np.array([[1, 0, 0], [0, cp, -sp], [0, sp, cp]])
    R = P @ Ry.T @ Rx.T
    sx = (R[:, 0] * 0.45 + 0.5) * W
    sy_ = (-R[:, 1] * 0.45 + 0.5) * H
    sz = R[:, 2]
    if len(faces) == 0:                                   
        xi = sx.astype(int); yi = sy_.astype(int)
        ok = (xi >= 0) & (xi < W) & (yi >= 0) & (yi < H)
        img[yi[ok], xi[ok]] = base
        return img
    v0, v1, v2 = R[faces[:, 0]], R[faces[:, 1]], R[faces[:, 2]]
    nrm = np.cross(v1 - v0, v2 - v0)
    nl = np.linalg.norm(nrm, axis=1); nl[nl == 0] = 1
    nrm /= nl[:, None]
    light = np.array([0.3, 0.5, 0.8]); light /= np.linalg.norm(light)
    shade = np.clip(np.abs(nrm @ light), 0, 1)
    base = np.asarray(base, float)
    fcol = ((0.25 + 0.75 * shade)[:, None] * base).astype(np.uint8)
    fz = (sz[faces[:, 0]] + sz[faces[:, 1]] + sz[faces[:, 2]]) / 3.0
    zbuf = np.full((H, W), -1e18)
    X = np.stack([sx[faces[:, 0]], sx[faces[:, 1]], sx[faces[:, 2]]], axis=1)
    Y = np.stack([sy_[faces[:, 0]], sy_[faces[:, 1]], sy_[faces[:, 2]]], axis=1)
    front = np.where(nrm[:, 2] >= -0.02)[0]
    order_src = front[np.argsort(fz[front])]
    for f in order_src:                                    
        x0, x1, x2 = X[f]; y0, y1, y2 = Y[f]
        minx = max(int(min(x0, x1, x2)), 0); maxx = min(int(max(x0, x1, x2)) + 1, W)
        miny = max(int(min(y0, y1, y2)), 0); maxy = min(int(max(y0, y1, y2)) + 1, H)
        if minx >= maxx or miny >= maxy:
            continue
        den = (y1 - y2) * (x0 - x2) + (x2 - x1) * (y0 - y2)
        if abs(den) < 1e-9:
            continue
        ys, xs = np.mgrid[miny:maxy, minx:maxx]
        a = ((y1 - y2) * (xs - x2) + (x2 - x1) * (ys - y2)) / den
        b = ((y2 - y0) * (xs - x2) + (x0 - x2) * (ys - y2)) / den
        g = 1 - a - b
        inside = (a >= 0) & (b >= 0) & (g >= 0)
        if not inside.any():
            continue
        z = fz[f]
        reg = zbuf[miny:maxy, minx:maxx]
        win = inside & (z > reg)
        if win.any():
            reg[win] = z
            img[miny:maxy, minx:maxx][win] = fcol[f]
    return img


class NxgMesh:

    def __init__(self, path, exe):
        self.path = Path(path)
        self.exe = Path(exe)
        self.points = np.zeros((0, 3), np.float32)
        self.faces = np.zeros((0, 3), np.int32)
        self.vertex_lists = 0
        self.parts = 0
        self.error = None
        self._extract()

    @staticmethod
    def _data_end(addrs, count_addr, nbytes):
        for a in addrs:
            if a >= count_addr + nbytes:
                return a
        return None

    def _extract(self):
        d = self.path.read_bytes()
        try:
            dump = subprocess.run([str(self.exe), str(self.path)],
                                  capture_output=True, text=True, timeout=120).stdout
        except Exception as e:
            self.error = f"extractor failed: {e}"
            return
        L = [(int(m.group(1), 16), m.group(2).strip())
             for ln in dump.splitlines() if (m := re.match(r"^([0-9a-fA-F]{8})\s(.*)$", ln))]
        addrs = [a for a, _ in L]

        vls, ils, cv, ci = {}, {}, None, None
        for a, t in L:
            if (m := re.match(r"New Vertex List 0x([0-9a-fA-F]+)", t)):
                cv = {"defs": [], "stride": 0}
                vls[int(m.group(1), 16)] = cv
            elif t.startswith(("vec", "color", "float")) and cv is not None and "count" not in cv:
                p = t.split()
                cv["defs"].append((p[0], p[1] if len(p) > 1 else ""))
                cv["stride"] += _TYPE_SIZE.get(p[0], 0)
            elif (m := re.match(r"Number of Vertices: ([0-9a-fA-F]+)", t)) and cv is not None:
                cv["count"], cv["caddr"] = int(m.group(1), 16), a
            elif (m := re.match(r"New Index List 0x([0-9a-fA-F]+)", t)):
                ci = {}
                ils[int(m.group(1), 16)] = ci
            elif (m := re.match(r"Number of Indices: ([0-9a-fA-F]+)", t)) and ci is not None:
                ci["count"], ci["caddr"] = int(m.group(1), 16), a

        for vl in vls.values():
            vl["pos"] = self._read_positions(d, addrs, vl)
        for il in ils.values():
            if "count" in il:
                n = il["count"]
                de = self._data_end(addrs, il["caddr"], n * 2)
                il["idx"] = np.frombuffer(d[de - n * 2:de], ">u2") if de else np.zeros(0, ">u2")

        parts = []
        cur = None
        for a, t in L:
            if t.startswith("Part 0x"):
                cur = {}
                parts.append(cur)
            if cur is None:
                continue
            if (m := re.match(r"(?:Vertex List Reference to|New Vertex List) 0x([0-9a-fA-F]+)", t)):
                cur.setdefault("vref", int(m.group(1), 16))
            if (m := re.match(r"(?:Index List Reference to|New Index List) 0x([0-9a-fA-F]+)", t)):
                cur.setdefault("iref", int(m.group(1), 16))
            for k, lab in [("oi", "Offset Indices"), ("ni", "Number Indices"),
                           ("ov", "Offset Vertices"), ("nv", "Number Vertices")]:
                if (m := re.match(lab + r": 0x([0-9a-fA-F]+)", t)):
                    cur.setdefault(k, int(m.group(1), 16))
        self.parts = len(parts)

        built = []   
        for p in parts:
            if not all(x in p for x in ("vref", "iref", "oi", "ni", "ov", "nv")):
                continue
            vl, il = vls.get(p["vref"]), ils.get(p["iref"])
            if vl is None or vl["pos"] is None or il is None or "idx" not in il:
                continue
            vs = vl["pos"][p["ov"]:p["ov"] + p["nv"]]
            idx = il["idx"][p["oi"]:p["oi"] + p["ni"]]
            if len(vs) < p["nv"] or len(idx) < 3:
                continue
            tri = idx[:(len(idx) // 3) * 3].reshape(-1, 3).astype(np.int64)
            if len(tri) == 0 or tri.max() >= len(vs):
                continue
            built.append((np.asarray(vs, np.float32), tri, vl["defs"][0][0]))


        half = [b for b in built if b[2] == "vec4half"]
        built = [(v, t) for v, t, _ in (half if half else built)]
        built = self._reject_outlier_parts(built)
        V, F, base = [], [], 0
        for vs, tri in built:
            V.append(vs)
            F.append((tri + base).astype(np.int32))
            base += len(vs)
        self.vertex_lists = len(built)
        if V:
            self.points = np.vstack(V)
            self.faces = np.vstack(F)

    @staticmethod
    def _reject_outlier_parts(built):
        if len(built) <= 2:
            return built
        cents = np.array([vs.mean(0) for vs, _ in built])
        exts = np.array([float((vs.max(0) - vs.min(0)).max()) for vs, _ in built])
        med_c = np.median(cents, axis=0)
        med_e = max(float(np.median(exts)), 0.05)
        keep = [(vs, tri) for (vs, tri), c, e in zip(built, cents, exts)
                if e <= med_e * 3 and np.linalg.norm(c - med_c) <= med_e * 5]
        return keep or built

    def to_obj(self, path):
        p = Path(path)
        with open(p, "w") as f:
            f.write(f"# GothamForge export of {self.path.name}\n")
            for v in self.points:
                f.write(f"v {v[0]:.5f} {v[1]:.5f} {v[2]:.5f}\n")
            for t in self.faces:
                f.write(f"f {t[0] + 1} {t[1] + 1} {t[2] + 1}\n")
        return p

    def _read_positions(self, d, addrs, vl):
        if not vl.get("defs") or vl["defs"][0][1] != "position" or "count" not in vl:
            return None
        fmt, stride, n = vl["defs"][0][0], vl["stride"], vl["count"]
        if stride <= 0 or n <= 0 or fmt not in ("vec4half", "vec3float"):
            return None
        de = self._data_end(addrs, vl["caddr"], n * stride)
        if de is None:
            return None
        for s in range(de - n * stride - 3, de - n * stride + 4):   
            raw = d[s:s + n * stride]
            if len(raw) < n * stride:
                continue
            a = np.frombuffer(raw, np.uint8).reshape(n, stride)
            if fmt == "vec4half":
                p4 = a[:, :8].copy().view(np.float16).astype(np.float32)
                if np.isfinite(p4).all() and (np.abs(p4[:, :3]) < 50).all() and (np.abs(p4[:, 3]) < 4).all():
                    return p4[:, :3]
            else:
                p = a[:, :12].copy().view("<f4")
                if np.isfinite(p).all() and (np.abs(p) < 50).all():
                    return p
        return None


def _dds_total_size(d, off):
    _sz, _flags, height, width, _pitch, _depth, mip = struct.unpack_from("<7I", d, off + 4)
    mip = max(1, mip)
    fourcc = d[off + 0x54: off + 0x58]
    block = 8 if fourcc == b"DXT1" else 16
    total, w, h = 128, width, height
    for _ in range(mip):
        total += max(1, (w + 3) // 4) * max(1, (h + 3) // 4) * block
        w = max(1, w // 2)
        h = max(1, h // 2)
    return total


class GhgModel:
    def __init__(self, path):
        self.path = Path(path)
        self.d = self.path.read_bytes()
        self.file_id, self.version = struct.unpack_from(">II", self.d, 0)
        self.root_tag = self.d[8:12][::-1].decode("latin-1", "replace")  

    def strings(self, minlen=4):
        return [m.group(0).decode("latin-1") for m in re.finditer(rb"[ -~]{%d,}" % minlen, self.d)]

    def info(self):
        ss = self.strings()
        user = next((s for s in ss if re.fullmatch(r"uk[a-z]+", s)), None)
        date = next((s for s in ss if re.match(r"^(Mon|Tue|Wed|Thu|Fri|Sat|Sun) ", s)), None)
        src = next((s for s in ss if s.upper().endswith(".GHG") and ("\\" in s or ":" in s)), None)
        return {"user": user, "date": date, "source": src}

    def mesh_parts(self):
        names = []
        for s in self.strings():
            if re.search(r"(_Mesh|_CUTSCENE|BlowUp|_LOD\d|Mesh\b)", s) and len(s) < 48 and "\\" not in s:
                names.append(s)
        seen, out = set(), []
        for n in names:
            if n not in seen:
                seen.add(n)
                out.append(n)
        return out

    def attributes(self):
        return [a for a in VERTEX_ATTRS if a.encode() in self.d]

    def texture_refs(self):
        out = []
        for s in self.strings():
            low = s.lower()
            if low.endswith((".tex", ".dds")) or (("_nxg" in low) and "\\" not in s and len(s) < 48):
                out.append(s)
        seen, res = set(), []
        for s in out:
            if s not in seen:
                seen.add(s)
                res.append(s)
        return res[:40]

    def summary(self):
        info = self.info()
        return {
            "file": self.path.name,
            "bytes": len(self.d),
            "file_id": hex(self.file_id),
            "version": self.version,
            "root": self.root_tag,
            "build_user": info["user"],
            "build_date": info["date"],
            "source_path": info["source"],
            "attributes": self.attributes(),
            "mesh_parts": self.mesh_parts(),
            "texture_refs": self.texture_refs(),
        }

    def embedded_textures(self):
        out = []
        for m in re.finditer(re.escape(DDS_MAGIC), self.d):
            off = m.start()
            try:
                _s, _f, h, w, _p, _d, mip = struct.unpack_from("<7I", self.d, off + 4)
                fourcc = self.d[off + 0x54: off + 0x58].decode("latin-1", "replace").rstrip("\x00")
                size = _dds_total_size(self.d, off)
            except Exception:
                continue
            if 0 < w <= 4096 and 0 < h <= 4096 and off + size <= len(self.d):
                out.append({"index": len(out), "offset": off, "size": size,
                            "width": w, "height": h, "fourcc": fourcc})
        return out

    def export_textures(self, out_dir, as_png=False):
        from . import tex as _tex
        out = Path(out_dir)
        out.mkdir(parents=True, exist_ok=True)
        written = []
        for e in self.embedded_textures():
            blob = self.d[e["offset"]: e["offset"] + e["size"]]
            base = f"{self.path.stem}_tex{e['index']:02d}"
            tp = out / (base + ".tex")
            tp.write_bytes(blob)
            written.append(tp)
            if as_png:
                try:
                    from PIL import Image
                    import io
                    pp = out / (base + ".png")
                    Image.open(io.BytesIO(blob), formats=["DDS"]).convert("RGBA").save(pp)
                    written.append(pp)
                except Exception:
                    pass
        return written

    def point_cloud(self, lo=0.01, hi=2.0, max_points=6000):
        n = len(self.d) // 4
        f = np.frombuffer(self.d[: n * 4], dtype="<f4").astype(np.float32, copy=True)
        f[~np.isfinite(f)] = 0.0
        m = (np.abs(f) > lo) & (np.abs(f) < hi)
        if n < 3:
            return np.zeros((0, 3), np.float32)
        tri = m[0:n - 2] & m[1:n - 1] & m[2:n]
        idx = np.where(tri)[0]
        if len(idx) == 0:
            return np.zeros((0, 3), np.float32)
        pts = np.stack([f[idx], f[idx + 1], f[idx + 2]], axis=1)
        key = np.round(pts, 3)
        _, u = np.unique(key, axis=0, return_index=True)
        pts = pts[np.sort(u)]
        if len(pts) > max_points:
            step = len(pts) // max_points + 1
            pts = pts[::step]
        return pts
