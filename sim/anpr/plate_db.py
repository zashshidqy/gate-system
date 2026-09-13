import json
import re
from pathlib import Path

from . import config


class PlateDb:
    def __init__(self, path=None):
        self.path = Path(path) if path else config.PLATE_DB
        self.plates = set()
        self.load()

    def load(self):
        try:
            with open(self.path, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, list):
                self.plates = {PlateDb.normalize(p) for p in data if PlateDb.normalize(p)}
        except (FileNotFoundError, json.JSONDecodeError):
            self.plates = set()
            self.save()

    def save(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.path, "w", encoding="utf-8") as f:
            json.dump(sorted(self.plates), f, indent=2, ensure_ascii=False)

    @staticmethod
    def normalize(plate):
        p = (plate or "").strip().upper()
        p = re.sub(r"[^A-Z0-9]", "", p)
        return p

    @staticmethod
    def is_valid(plate):
        return bool(re.fullmatch(config.PLATE_REGEX, plate))

    def contains(self, plate):
        return PlateDb.normalize(plate) in self.plates

    def add(self, plate):
        p = PlateDb.normalize(plate)
        if p and PlateDb.is_valid(p):
            self.plates.add(p)
            self.save()
            return p
        return None

    def remove(self, plate):
        p = PlateDb.normalize(plate)
        if p in self.plates:
            self.plates.discard(p)
            self.save()
            return True
        return False

    def allowed(self, plate):
        p = PlateDb.normalize(plate)
        if not p:
            return None
        if p in self.plates:
            return p
        variant = self._find_fuzzy(p)
        return variant

    def _find_fuzzy(self, plate):
        for variant in self._variants(plate):
            if variant in self.plates:
                return variant
        return None

    def _variants(self, plate):
        cands = [plate]
        for i, ch in enumerate(plate):
            if ch not in config.CHAR_CONFUSION:
                continue
            base = list(plate)
            for v in config.CHAR_CONFUSION[ch]:
                alt = list(plate)
                alt[i] = v
                cands.append("".join(alt))
        return cands

    def list(self):
        return sorted(self.plates)