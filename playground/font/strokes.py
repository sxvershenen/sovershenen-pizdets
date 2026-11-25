"""Matched shoulders, direct K/я geometry and limits for straight stroke pairs."""

from math import hypot
from ufoLib2.objects import Point

# (on-curve point where a horizontal run starts, zone after that point).
# Extra advance is inserted at horizontal tangents. Both sides of the old
# bend, including the spur at its base, travel as one piece.
RAILS = {
    "n": [[(5, 1), (14, 0)]],
    "h": [[(5, 1), (14, 0)]],
    "m": [[(5, 1), (14, 2), (23, 1), (30, 0)]],
    "r": [[(5, 1), (6, 0)]],
    "u": [[(0, 1), (12, 0)]],
    "d": [[(0, 1), (13, 0)], [(0, 0), (6, 1)]],
    "q": [[(8, 0), (14, 1)], [(0, 0), (6, 1)]],
    "g": [[(2, 0), (9, 1), (19, 0), (25, 1)], [(5, 1), (17, 0)]],
    "b": [[(0, 1), (6, 0)], [(0, 0), (12, 1)]],
    "p": [[(6, 1), (12, 0)], [(0, 0), (12, 1)]],
}


def crown_pair(outer, i, inner, j, thickness):
    # End both curves at the same x so one side does not start bending while
    # the other is still horizontal. Keep adjacent handles horizontal.
    a, b = outer[i], inner[j]
    center = (a.x + b.x) / 2
    a.x = b.x = center
    shift = a.y + (thickness if b.y > a.y else -thickness) - b.y
    for index in ((j - 1) % len(inner), j, (j + 1) % len(inner)):
        if index == j or inner[index].type is None:
            inner[index].y += shift


def rail_glyph(g, extra, bar):
    contours = [c.points for c in g.contours]
    p = contours[0]
    if g.name in ("h", "n", "m"):
        crown_pair(p, 14 if g.name != "m" else 30, p, 5, bar)
        if g.name == "m":
            crown_pair(p, 23, p, 14, bar)
    elif g.name == "u":
        crown_pair(p, 0, p, 12, bar)
    elif g.name == "r":
        # Keep the left upright rectangular up to its cap; preserve the
        # original shoulder and extend the terminal at constant thickness.
        for i in (9, 10, 11):
            p[i].x = max(p[i].x, p[1].x)
        dy = p[6].y - bar - p[5].y
        p[4].y += dy
        p[5].y += dy
    else:
        q = contours[1]
        pairs = {
            "d": [(0, 0), (13, 6)],
            "q": [(14, 0), (8, 6)],
            "g": [(25, 17), (19, 5)],
            "b": [(0, 0), (6, 12)],
            "p": [(6, 0), (12, 12)],
        }
        for i, j in pairs[g.name]:
            crown_pair(p, i, q, j, bar)
    extend_rails(g, RAILS[g.name], extra)


def extend_rails(g, contour_cuts, extra):
    for c, cuts in zip(g.contours, contour_cuts, strict=True):
        if not cuts:
            continue
        transitions = dict(cuts)
        zone = cuts[-1][1]
        rebuilt = []
        for i, p in enumerate(c.points):
            start_x = p.x
            p.x = start_x + zone * extra
            rebuilt.append(p)
            if i in transitions:
                zone = transitions[i]
                rebuilt.append(Point(start_x + zone * extra, p.y, "line"))
        c.points[:] = rebuilt


def lower_ya(g, extra, bar, amount):
    """Open the native bowl at its flat runs and keep the left stem intact."""
    if not extra:
        return
    stem, leg, outer, inner = [c.points for c in g.contours]
    # Let part of the gain reach the rounded end. The two extrema at
    # mid-height stay put, so the outside and counter retain their side weight.
    for points in (outer, inner):
        wall = points[8].x
        radius = points[5].x - wall
        for i in (0, 1, 2, 5, 6, 7):
            points[i].x += 0.21 * extra * (points[i].x - wall) / radius
    for pt in (*stem, *outer[3:5], *inner[3:5]):
        pt.x += extra
    # Rotate the foot into the bowl, preserving its original height of
    # attachment and easing its normal thickness toward the lowercase bar.
    slope = (leg[3].x - leg[0].x) / (leg[3].y - leg[0].y)
    thick = (leg[1].x - leg[0].x) / hypot(1, slope)
    leg[3].x += 0.38 * extra
    slope = (leg[3].x - leg[0].x) / (leg[3].y - leg[0].y)
    dx = (thick + amount * (0.98 * bar - thick)) * hypot(1, slope)
    leg[1].x = leg[0].x + dx
    leg[2].x = leg[3].x + dx


def extend_fork(points, gain, fork_shift, grade=0):
    """Open an original K or Ж arm without substituting the crossbar's weight."""
    if not gain:
        return
    _, lo, foot, outer_foot, fork, outer_tip, tip, hi, _ = points
    for inner, outer, joint in ((foot, outer_foot, lo), (tip, outer_tip, hi)):
        slope = (outer.x - fork.x) / (outer.y - fork.y)
        normal = hypot(1, slope)
        tip_weight = (outer.x - inner.x) / normal
        joint_weight = (fork.x + slope * (joint.y - fork.y) - joint.x) / normal
        # In wide K the short horizontal shoulder makes its two long arms
        # look heavy. Limit their normal thickness against that shoulder.
        if grade:
            shelf = abs(hi.y - lo.y)
            peak = max(abs(tip_weight), abs(joint_weight))
            ratio = min(0.96, (1 + shelf / peak) / 2)
            tip_weight *= 1 + grade * (ratio - 1)
            joint_weight *= 1 + grade * (ratio - 1)
        outer.x += gain
        slope = (outer.x - fork.x - fork_shift) / (outer.y - fork.y)
        inner.x = outer.x - tip_weight * hypot(1, slope)
        joint.x = fork.x + fork_shift + slope * (joint.y - fork.y) - joint_weight * hypot(1, slope)
    fork.x += fork_shift


def cap_straights(g, limit):
    """Offset only paired straight diagonal edges, intersecting adjacent edges
    to preserve the original cap height, baseline and rectangular uprights."""
    edges = []
    for contour in g.contours:
        ps = contour.points
        for i, p in enumerate(ps):
            q = ps[(i + 1) % len(ps)]
            if p.type is None or q.type != "line":
                continue
            a = complex(p.x, p.y)
            v = complex(q.x - p.x, q.y - p.y)
            if abs(v) < max(12, 0.52 * limit):
                continue
            t = v / abs(v)
            if min(abs(t.real), abs(t.imag)) < 0.16:
                continue
            edges.append((id(p), a, v, t))
    offsets = {}
    for key, a, v, t in edges:
        overlaps = []
        for _, b, w, u in edges:
            if (u.conjugate() * t).real > -0.988:
                continue
            p = (b - a) * t.conjugate()
            q = (b + w - a) * t.conjugate()
            lo = max(0, min(p.real, q.real))
            hi = min(abs(v), max(p.real, q.real))
            if hi - lo < max(8, 0.15 * min(abs(v), abs(w))):
                continue
            mid = (lo + hi) / 2
            width = p.imag + (q.imag - p.imag) * (mid - p.real) / (q.real - p.real)
            if 0.45 * limit < width < 1.8 * limit:
                overlaps.append(width)
        if overlaps:
            off = max(0, (min(overlaps) - 0.97 * limit) / 2)
            if off > 0.1:
                offsets[key] = off
    if not offsets:
        return
    for contour in g.contours:
        ps = contour.points
        old = [complex(p.x, p.y) for p in ps]
        for i, p in enumerate(ps):
            before = (i - 1) % len(ps)
            da, db = offsets.get(id(ps[before]), 0), offsets.get(id(p), 0)
            if not da and not db:
                continue
            a, b = old[i] - old[before], old[(i + 1) % len(ps)] - old[i]
            if not abs(a) or not abs(b):
                continue
            a, b = a / abs(a), b / abs(b)
            det = (a.conjugate() * b).imag
            delta = (
                (a * db - b * da) / (-det)
                if abs(det) > 0.09
                else 1j * (a * da + b * db) / 2
            )
            if abs(delta) > limit * 0.35:
                delta *= limit * 0.35 / abs(delta)
            p.x += delta.real
            p.y += delta.imag


def q_tail(glyph, limit):
    p = glyph.contours[0].points
    slope = (p[3].x - p[2].x) / (p[3].y - p[2].y)
    dx = min(abs(p[4].x - p[3].x), 0.94 * limit * hypot(1, slope))
    for i in (4, 0):
        p[i].x = p[2].x + (p[i].y - p[2].y) * slope - dx
