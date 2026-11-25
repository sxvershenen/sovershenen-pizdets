"""Audit individual contour segments. python stroke_review.py font.ttf report-dir"""

import argparse
from collections import defaultdict
from concurrent.futures import ProcessPoolExecutor
import gzip
import json
from pathlib import Path

import numpy as np
import uharfbuzz as hb
from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.ttLib import TTFont
from audit import Edges

WEIGHTS = (100, 200, 300, 400, 500, 600, 650, 700, 800, 900)
WIDTHS = (100, 107, 125, 137.5, 150, 162.5, 175)
REFS = "QEUTPHF"


def measure(gs, name):
    pen = Edges(gs)
    gs[name].draw(pen)
    paths = pen.parts
    if not paths:
        return ["", 0, [], []]
    start = []
    ends = []
    ids = []
    positions = []
    tangents = []
    source = []
    lengths = []
    for i, part in enumerate(paths):
        start.extend(part[:-1])
        ends.extend(part[1:])
        ids.extend([i] * (len(part) - 1))
        lengths.append(sum(abs(b - a) for a, b in zip(part, part[1:])))
        for t in (0.18, 0.34, 0.5, 0.66, 0.82):
            j = int(t * (len(part) - 1))
            v = part[j + 1] - part[j]
            if abs(v) < 0.05:
                continue
            positions.append(part[j] + v * (t * (len(part) - 1) - j))
            tangents.append(v / abs(v))
            source.append(i)
    a = np.asarray(start)
    edges = np.asarray(ends) - a
    ids = np.asarray(ids)
    tangent = edges / np.maximum(abs(edges), 1.0e-9)
    groups = defaultdict(list)
    for lo in range(0, len(source), 96):
        pos = np.asarray(positions[lo : lo + 96])[:, None]
        t = np.asarray(tangents[lo : lo + 96])[:, None]
        n = -1j * t
        det = (n.conj() * edges).imag
        rel = a - pos
        with np.errstate(divide="ignore", invalid="ignore"):
            d = (rel.conj() * edges).imag / det
            u = (rel.conj() * n).imag / det
        hits = np.where((u >= 0) & (u < 1) & (d > 0.05), d, np.inf)

        def winding(pt):
            with np.errstate(divide="ignore", invalid="ignore"):
                x = a.real + (pt.imag - a.imag) * edges.real / edges.imag
            up = (a.imag <= pt.imag) & (pt.imag < (a + edges).imag)
            down = (a.imag > pt.imag) & (pt.imag >= (a + edges).imag)
            return np.sum((x > pt.real) * (up.astype(int) - down.astype(int)), axis=1)

        inside = winding(pos + 0.05 * n)
        outside = winding(pos - 0.05 * n)
        # Walk across overlapping contours to the first transition back to empty.
        order = hits.argsort(axis=1)
        index = np.arange(len(pos))
        changes = np.where(np.isfinite(hits), -np.sign(det), 0)
        exits = (
            inside[:, None] + np.take_along_axis(changes, order, axis=1).cumsum(axis=1)
            == 0
        )
        hit = order[index, exits.argmax(axis=1)]
        distance = hits[index, hit]
        alignment = (t[:, 0].conj() * tangent[hit]).real
        usable = (
            (inside != 0)
            & (outside == 0)
            & exits.any(axis=1)
            & np.isfinite(distance)
            & (distance > 0.5)
            & (alignment < -0.95)
        )
        for r in np.flatnonzero(usable):
            i = source[lo + r]
            j = int(ids[hit[r]])
            v = float(distance[r])
            angle = abs(t[r, 0].real)
            direction = 0 if angle < 0.2 else 1 if angle > 0.98 else 2
            straight = len(paths[i]) == len(paths[j]) == 2
            reliable = (
                straight
                and min(lengths[i], lengths[j]) > 1.1 * v
                and alignment[r] < -0.988
            )
            if reliable:
                start, end = sorted(
                    ((p - paths[i][0]) * t[r, 0].conjugate()).real for p in paths[j]
                )
                reliable = min(end, lengths[i]) - max(0, start) > 0.85 * v
            kind = direction + (0 if reliable else 3 if not straight else 6)
            groups[i, j, kind].append((v, pos[r, 0], pos[r, 0] + n[r, 0] * v))
    pairs = []
    for (i, j, k), vals in groups.items():
        vals.sort(key=lambda z: z[0])
        v, x, y = vals[len(vals) // 2]
        pairs.append(
            [
                i,
                j,
                k,
                round(float(np.median([p[0] for p in vals])), 1),
                round(vals[0][0], 1),
                round(vals[-1][0], 1),
                len(vals),
                round(x.real),
                round(x.imag),
                round(y.real),
                round(y.imag),
            ]
        )
    shape = SVGPathPen(gs, ntos=lambda x: str(round(x)))
    gs[name].draw(shape)
    unseen = sorted(set(range(len(paths))) - {v[0] for v in pairs})
    return [shape.getCommands(), len(paths), pairs, unseen]


def reference(rows, ids):
    # Use a per-reference median. Curved terminals and long straight stems
    # are compared separately. Q has only a short straight diagonal tail.
    bands = []
    for k in range(9):
        values = []
        for i in ids:
            samples = [p[3] for p in rows[i][2] if p[2] == k and p[6] >= 2]
            if samples:
                values.append(float(np.median(samples)))
        if k == 2 or k >= 6 or not values:
            values = bands[1 if k % 3 == 2 else k % 3] if k >= 2 else [0, 0]
        bands.append([round(min(values), 1), round(max(values), 1)])
    return bands


def classify(pair, bands):
    _, _, k, v, minimum, maximum, n, *_ = pair
    low, high = bands[k]
    tol = max(2, 0.075 * (low + high) / 2)
    # Curved intersections and short/oblique chords remain visible with lower confidence.
    if k >= 3:
        tol = max(4, tol * 2)
    return (
        round(min(0, v - low + tol) if v < low else max(0, v - high - tol), 1)
        if n >= 2
        else 0
    )


def at_location(args):
    font_path, out, w, d = args
    f = TTFont(font_path)
    gs = f.getGlyphSet(location={"wght": w, "wdth": d})
    names = f.getGlyphOrder()
    shaping_font = hb.Font(hb.Face(font_path.read_bytes()))
    shaping_font.set_variations({"wght": w, "wdth": d})
    buffer = hb.Buffer()
    buffer.add_str(REFS)
    buffer.guess_segment_properties()
    hb.shape(shaping_font, buffer)
    reference_ids = [item.codepoint for item in buffer.glyph_infos]
    assert len(reference_ids) == len(REFS)
    rows = [measure(gs, n) for n in names]
    bands = reference(rows, reference_ids)
    overview = []
    for _, count, pairs, missing in rows:
        scores = [classify(p, bands) for p in pairs]
        significant = [s for s, p in zip(scores, pairs) if s and p[2] < 3]
        overview.append(
            [
                min([0, *significant]),
                max([0, *significant]),
                sum(s != 0 for s in scores),
                len(missing),
                count,
                len(pairs),
                sum(p[2] < 3 and p[6] >= 2 for p in pairs),
                sum(
                    p[2] < 3
                    and p[6] >= 2
                    and (
                        p[4] < bands[p[2]][0] - max(2, 0.075 * sum(bands[p[2]]) / 2)
                        or p[5] > bands[p[2]][1] + max(2, 0.075 * sum(bands[p[2]]) / 2)
                    )
                    for p in pairs
                ),
            ]
        )
    key = f"{w}-{d}"
    data = json.dumps(
        dict(bands=bands, reference_ids=reference_ids, rows=rows, summary=overview), separators=(",", ":")
    ).encode()
    (out / (key + ".json.gz")).write_bytes(
        gzip.compress(data, compresslevel=3, mtime=0)
    )
    return key, overview


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("font", type=Path)
    ap.add_argument("out", type=Path)
    args = ap.parse_args()
    args.out.mkdir(exist_ok=True, parents=True)
    f = TTFont(args.font)
    names = f.getGlyphOrder()
    rev = defaultdict(str)
    for cp, n in f.getBestCmap().items():
        rev[n] += chr(cp)
    jobs = [(args.font, args.out, w, d) for w in WEIGHTS for d in WIDTHS]
    with ProcessPoolExecutor(max_workers=6) as pool:
        summary = dict(pool.map(at_location, jobs, chunksize=1))
    data = dict(
        glyphs=[[n, rev[n]] for n in names],
        weights=WEIGHTS,
        widths=WIDTHS,
        summary=summary,
    )
    (args.out / "index.json.gz").write_bytes(
        gzip.compress(json.dumps(data, separators=(",", ":")).encode(), mtime=0)
    )


if __name__ == "__main__":
    main()
