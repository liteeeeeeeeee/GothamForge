import csv
from pathlib import Path


class TextTable:
    def __init__(self, path):
        self.path = Path(path)
        self.header = []
        self.rows = []
        self._lead_blanks = 0  
        self.load()

    def load(self):
        with open(self.path, "r", encoding="utf-8-sig", newline="") as f:
            raw = list(csv.reader(f))
        if not raw:
            raise ValueError("empty CSV")
        self.header = raw[0]
        i = 1
        self._lead_blanks = 0
        while i < len(raw) and (not raw[i] or all(c == "" for c in raw[i])):
            self._lead_blanks += 1
            i += 1
        self.rows = [r for r in raw[i:] if r and any(c != "" for c in r)]

    def languages(self):
        return self.header[3:]

    def col_index(self, lang):
        return self.header.index(lang)

    def types(self):
        return sorted({r[2] for r in self.rows if len(r) > 2})

    def find(self, query="", typ=None, lang=None):
        q = (query or "").lower()
        out = []
        cols = [self.col_index(lang)] if lang else None
        for i, row in enumerate(self.rows):
            if typ and (len(row) < 3 or row[2] != typ):
                continue
            if q:
                hay = [row[c] for c in cols if c < len(row)] if cols else row
                if not any(q in (c or "").lower() for c in hay):
                    continue
            out.append((i, row))
        return out

    def label(self, i):
        return self.rows[i][0]

    def get(self, i, lang):
        c = self.col_index(lang)
        row = self.rows[i]
        return row[c] if c < len(row) else ""

    def set(self, i, lang, value):
        c = self.col_index(lang)
        row = self.rows[i]
        while len(row) <= c:
            row.append("")
        row[c] = value

    def find_by_label(self, label):
        for i, row in enumerate(self.rows):
            if row and row[0] == label:
                return i
        return None

    def save(self, path=None):
        path = Path(path or self.path)
        with open(path, "w", encoding="utf-8", newline="") as f:
            w = csv.writer(f, quoting=csv.QUOTE_ALL, lineterminator="\r\n")
            w.writerow(self.header)
            for _ in range(self._lead_blanks):
                f.write("\r\n")
            for row in self.rows:
                w.writerow(row)
