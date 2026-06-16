import re
from pathlib import Path
KNOWN_FLAGS = {
    "hero": "Counts as a playable hero",
    "super_strength": "Can lift/pull heavy 'super strength' objects",
    "can_grapple": "Can use grapple points",
    "can_super_carry": "Can pick up and carry other characters/objects",
    "can_punch": "Able to melee punch",
    "can_lunge": "Able to lunge attack",
    "combat_roll": "Can dodge-roll in combat",
    "has_whip": "Equipped with a whip (Wonder Woman / Catwoman style)",
    "has_invincibility": "Cannot be killed (jumps back to safe spot)",
    "cannot_be_frozen": "Immune to freeze attacks",
    "immune_to_hot_terrain": "Immune to lava/fire terrain",
    "always_fast_build": "Builds LEGO objects at high speed",
    "always_regenerate_hearts": "Slowly regenerates health",
    "always_doomed_recovery": "Big jump back to safe ground instead of dying",
    "wall_jump": "Can perform wall jumps",
    "swimmer": "Can swim / dive underwater",
    "flight": "Can fly",
    "girl_power": "Female-only ability gate",
    "x_ray_vision": "Has X-ray vision",
    "heat_vision": "Has heat vision (Superman)",
    "super_breath": "Has freeze/super breath",
    "tech": "Tech-suit interaction ability",
    "magnet": "Can use magnetic surfaces",
    "glide": "Can glide",
    "jump_lungeslam": "Can perform a lunge-slam from a jump",
    "super_jump": "Enhanced jump height",
}

KNOWN_VALUES = {
    "hit_points": "Health (number of hearts)",
    "walk_speed": "Walk speed (game units)",
    "run_speed": "Run speed (game units)",
    "sprint_speed": "Sprint speed (game units)",
    "tiptoe_speed": "Tiptoe speed (game units)",
    "jump_speed": "Jump launch speed",
    "air_gravity": "Gravity while airborne (negative)",
    "water_gravity": "Gravity in water",
    "acceleration": "Movement acceleration",
    "turn_rate": "How fast the character turns",
    "scale": "Model scale (1.0 = normal)",
    "radius": "Collision sphere radius",
    "max_aim_targets": "How many lock-on targets",
    "flyBanking": "Banking amount while flying",
}


VEHICLE_FLAGS = {
    "vehicle": "Marks this as a vehicle",
    "car_wheels": "Drives on car wheels",
    "boat": "Is a boat / watercraft",
    "flying": "Can fly",
    "hover": "Hovers above ground",
    "can_fire": "Can fire its weapon",
    "special_can_fire": "Has a second/special weapon",
    "can_take_over": "Player can commandeer it",
    "baddie": "Hostile / enemy vehicle",
    "respawn": "Respawns after being destroyed",
    "can_be_towed": "Can be towed",
    "can_flatten": "Flattens things it drives over",
    "vehicle_explosion": "Explodes when destroyed",
    "has_no_turn": "Cannot steer/turn",
    "turning_circle": "Steers with a turning circle",
    "keep_firing_while_aiming": "Keeps firing while aiming",
    "dontpush": "Can't be pushed by others",
    "complex_shadow": "Uses a detailed shadow",
}
VEHICLE_VALUES = {
    "run_speed": "Top speed",
    "walk_speed": "Cruise speed",
    "tiptoe_speed": "Crawl speed",
    "idle_speed": "Idle speed",
    "acceleration": "Acceleration",
    "speed_up_time": "Time to reach top speed",
    "slow_down_time": "Braking time",
    "turn_rate_1": "Turn rate (low speed)",
    "turn_rate_2": "Turn rate (high speed)",
    "mass": "Mass / weight",
    "firerate": "Fire rate (lower = faster)",
    "hit_points": "Health",
    "scale": "Model scale",
    "banking2": "Banking amount",
    "air_gravity": "Gravity while flying",
    "radius": "Collision radius",
}


class CharDef:
    def __init__(self, path):
        self.path = Path(path)
        self.text = self.path.read_text(encoding="latin-1")
        self.lines = self.text.split("\n")

    @staticmethod
    def _split_comment(line):
        idx = line.find("//")
        if idx >= 0:
            return line[:idx], line[idx:]
        return line, ""

    def directives(self):
        out = []
        for i, line in enumerate(self.lines):
            code, _ = self._split_comment(line)
            s = code.strip()
            if s:
                out.append((i, s))
        return out

    def flags(self):
        return sorted({s for _, s in self.directives() if re.fullmatch(r"[A-Za-z0-9_]+", s)})

    def values(self):
        out = {}
        for _, s in self.directives():
            m = re.fullmatch(r"([A-Za-z0-9_]+)\s*[= ]\s*(-?\d+(?:\.\d+)?)", s)
            if m:
                out[m.group(1)] = m.group(2)
        return out

    def addons(self):
        out = []
        for _, s in self.directives():
            m = re.match(r"^AddOn\s+(\S+)", s)
            if m:
                out.append(m.group(1))
        return out

    def name(self):
        return self.get_value("name")

    def has_flag(self, name):
        return any(s == name for _, s in self.directives())

    def get_value(self, key):
        for _, s in self.directives():
            m = re.match(r"^" + re.escape(key) + r"\s*=\s*(.+)$", s)
            if m:
                return m.group(1).strip()
            m = re.match(r"^" + re.escape(key) + r"\s+(.+)$", s)
            if m:
                return m.group(1).strip()
        return None

    def set_flag(self, name, on):
        if on:
            if not self.has_flag(name):
                self.lines.append(name)
        else:
            keep = []
            for line in self.lines:
                code, _ = self._split_comment(line)
                if code.strip() == name:
                    continue  
                keep.append(line)
            self.lines = keep

    def set_value(self, key, value):
        value = str(value)
        for i, line in enumerate(self.lines):
            code, comment = self._split_comment(line)
            s = code.strip()
            tail = ("  " + comment) if comment else ""
            if re.match(r"^" + re.escape(key) + r"\s*=", s):
                indent = code[: len(code) - len(code.lstrip())]
                self.lines[i] = f"{indent}{key}={value}{tail}"
                return
            if re.match(r"^" + re.escape(key) + r"(\s+|$)", s):
                indent = code[: len(code) - len(code.lstrip())]
                self.lines[i] = f"{indent}{key} {value}{tail}"
                return
        self.lines.append(f"{key} {value}")

    def add_addon(self, name):
        if name not in self.addons():
            self.lines.append(f"AddOn {name}")

    def remove_addon(self, name):
        keep = []
        for line in self.lines:
            code, _ = self._split_comment(line)
            if re.match(r"^AddOn\s+" + re.escape(name) + r"\s*$", code.strip()):
                continue
            keep.append(line)
        self.lines = keep

    def text_out(self):
        return "\n".join(self.lines)

    def save(self, path=None):
        Path(path or self.path).write_text(self.text_out(), encoding="latin-1")

    def cd_sidecar(self):
        cd = self.path.with_suffix(".CD")
        return cd if cd.exists() else None
