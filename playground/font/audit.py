"""Compare normal chords of homologous outline segments across the width axis.

Usage: python audit.py font.ttf readings.json (requires fontTools and numpy).
Result: weight → glyph ID name → width-ordered records. Each record contains
three directional medians (vertical, horizontal, diagonal), matched count,
median signed difference and P90 absolute difference from width 125, segment
count and advance, three long straight-pair medians and maximum straight
diagonal width (0 if unavailable). Lengths are in font units.
"""

import json, sys
import numpy as np
from fontTools.ttLib import TTFont
from fontTools.pens.basePen import BasePen
from pathlib import Path
from multiprocessing import Pool

weights = [100, 400, 650, 800, 900]
widths = [100, 107, 125, 137.5, 150, 162.5, 175]


class Edges(BasePen):
    def __init__(self, gs):
        super().__init__(gs)
        self.parts = []

    def _moveTo(self, p):
        self.first = self.last = complex(*p)

    def _lineTo(self, q):
        q = complex(*q)
        self.parts.append([self.last, q])
        self.last = q

    def _qCurveToOne(self, c, q):
        a, b, d = self.last, complex(*c), complex(*q)
        self.parts.append(
            [
                (1 - t) ** 2 * a + 2 * t * (1 - t) * b + t * t * d
                for t in (0, 0.125, 0.25, 0.375, 0.5, 0.625, 0.75, 0.875, 1)
            ]
        )
        self.last = d

    def _closePath(self):
        if self.last != self.first:
            self._lineTo((self.first.real, self.first.imag))


def readings(gs, name):
    p = Edges(gs)
    gs[name].draw(p)
    if not p.parts:
        return {}, [], 0
    start = []
    end = []
    ids = []
    probes = []
    tangents = []
    keys = []
    for i, part in enumerate(p.parts):
        start.extend(part[:-1])
        end.extend(part[1:])
        ids.extend([i] * (len(part) - 1))
        for j, t in enumerate((0.22, 0.5, 0.78)):
            ix = min(int(t * (len(part) - 1)), len(part) - 2)
            a = part[ix]
            v = part[ix + 1] - a
            if abs(v) * (len(part) - 1) > 10:
                probes.append(a + v * (t * (len(part) - 1) - ix))
                tangents.append(v / abs(v))
                keys.append(i * 3 + j)
    a = np.array(start)
    e = np.array(end) - a
    ids = np.array(ids)
    if not probes:
        return {}, [], len(p.parts)
    direction = e / np.maximum(abs(e), 1e-9)
    out = {}
    stats = []
    for lo in range(0, len(probes), 100):
        pos = np.array(probes[lo : lo + 100])[:, None]
        tan = np.array(tangents[lo : lo + 100])[:, None]
        n = -1j * tan
        rel = a - pos
        det = (n.conj() * e).imag
        with np.errstate(invalid="ignore", divide="ignore"):
            k = (rel.conj() * e).imag / det
            u = (rel.conj() * n).imag / det
        # First actual boundary, then require near-parallel opposite side. Check
        # nonzero winding at an interior probe so overlaps/holes cannot stand in for ink.
        crossing = (u >= 0) & (u < 1) & (k > 0.1)
        dist = np.where(crossing, k, np.inf)
        j = dist.argmin(axis=1)
        ii = np.arange(len(j))
        v = dist[ii, j]
        mid = pos + n * 0.1
        with np.errstate(invalid="ignore", divide="ignore"):
            cross = a.real + (mid.imag - a.imag) * e.real / e.imag
        winding = np.sum(
            (
                (a.imag <= mid.imag) & (mid.imag < (a + e).imag) & (cross > mid.real)
            ).astype(int)
            - (
                (a.imag > mid.imag) & (mid.imag >= (a + e).imag) & (cross > mid.real)
            ).astype(int),
            axis=1,
        )
        # Reject internal edges in overlapping component contours.
        outside = pos - n * 0.1
        with np.errstate(invalid="ignore", divide="ignore"):
            cross = a.real + (outside.imag - a.imag) * e.real / e.imag
        winding2 = np.sum(
            (
                (a.imag <= outside.imag)
                & (outside.imag < (a + e).imag)
                & (cross > outside.real)
            ).astype(int)
            - (
                (a.imag > outside.imag)
                & (outside.imag >= (a + e).imag)
                & (cross > outside.real)
            ).astype(int),
            axis=1,
        )
        for r in np.flatnonzero(
            (v > 1)
            & (v < 400)
            & ((tan[:, 0].conj() * direction[j]).real < -0.95)
            & (winding != 0)
            & (winding2 == 0)
        ):
            angle = abs(tan[r, 0].real)
            kind = 0 if angle < 0.20 else 1 if angle > 0.98 else 2
            out[keys[lo + r]] = (int(ids[j[r]]), kind, round(float(v[r]), 2))
            segment = keys[lo + r] // 3
            opposite = ids[j[r]]
            long_pair = (
                len(p.parts[segment]) == 2
                and len(p.parts[opposite]) == 2
                and min(abs(p.parts[segment][-1] - p.parts[segment][0]), abs(e[j[r]]))
                > v[r] * 1.10
                and (tan[r, 0].conj() * direction[j[r]]).real < -0.988
            )
            stats.append((kind, v[r], long_pair))
    return out, stats, len(p.parts)


def median(vals):
    return round(float(np.median(vals)), 2) if len(vals) else None


def task(weight):
    f = TTFont(sys.argv[1])
    sets = {wd: f.getGlyphSet(location={"wght": weight, "wdth": wd}) for wd in widths}
    results = {}
    for name in f.getGlyphOrder():
        base, _, _ = readings(sets[125], name)
        records = []
        for wd in widths:
            data, st, n = readings(sets[wd], name)
            ds = [
                val - b[2]
                for k, (opp, kind, val) in data.items()
                if (b := base.get(k)) and b[0] == opp and b[1] == kind
            ]
            records.append(
                [
                    *[median([v for k, v, _ in st if k == i]) for i in range(3)],
                    len(ds),
                    median(ds),
                    round(float(np.percentile(np.abs(ds), 90)), 2) if ds else None,
                    n,
                    round(sets[wd][name].width, 1),
                    *[
                        median([v for k, v, ok in st if ok and k == i])
                        for i in range(3)
                    ],
                    round(
                        float(max((v for k, v, ok in st if ok and k == 2), default=0)),
                        2,
                    ),
                ]
            )
        results[name] = records
    return weight, results


if __name__ == "__main__":
    with Pool(5) as pool:
        results = dict(pool.imap_unordered(task, weights))
    Path(sys.argv[2]).write_text(json.dumps(results, separators=(",", ":")))
