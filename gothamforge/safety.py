import json
import shutil
import hashlib
import time
from pathlib import Path


def sha1(path):
    h = hashlib.sha1()
    h.update(Path(path).read_bytes())
    return h.hexdigest()


class Safety:
    def __init__(self, game_root, store_dir):
        self.game_root = Path(game_root).resolve()
        self.store = Path(store_dir).resolve()
        self.bdir = self.store / "backups"
        self.manifest_path = self.store / "backups_manifest.json"
        self.bdir.mkdir(parents=True, exist_ok=True)
        self.manifest = {}
        if self.manifest_path.exists():
            try:
                self.manifest = json.loads(self.manifest_path.read_text())
            except Exception:
                self.manifest = {}

    def rel(self, path):
        return str(Path(path).resolve().relative_to(self.game_root)).replace("\\", "/")

    def _save(self):
        self.manifest_path.write_text(json.dumps(self.manifest, indent=2))

    def backup(self, path):
        path = Path(path)
        rel = self.rel(path)
        if rel in self.manifest:
            return False
        dest = self.bdir / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        if path.exists():
            shutil.copy2(path, dest)
            self.manifest[rel] = {
                "existed": True,
                "size": path.stat().st_size,
                "sha1": sha1(path),
                "time": time.time(),
            }
        else:
            self.manifest[rel] = {"existed": False, "time": time.time()}
        self._save()
        return True

    def restore(self, rel):
        rel = rel.replace("\\", "/")
        info = self.manifest.get(rel)
        if not info:
            return False
        target = self.game_root / rel
        if info.get("existed"):
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(self.bdir / rel, target)
        else:
            if target.exists():
                target.unlink()
        return True

    def restore_all(self):
        n = 0
        for rel in list(self.manifest):
            if self.restore(rel):
                n += 1
        return n

    def forget(self, rel):
        rel = rel.replace("\\", "/")
        if rel in self.manifest:
            del self.manifest[rel]
            f = self.bdir / rel
            if f.exists():
                f.unlink()
            self._save()
            return True
        return False

    def is_modified(self, path):
        rel = self.rel(path)
        info = self.manifest.get(rel)
        if not info or not info.get("existed"):
            return None
        try:
            return sha1(path) != info["sha1"]
        except Exception:
            return None

    def list(self):
        return dict(self.manifest)
