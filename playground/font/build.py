"""Build from the OFL UFOs at sxvershenen/sovershenen-pizdets@05db434.
python -m pip install fontmake==3.12.2
python build.py /path/to/upstream/sources /path/to/lab.ttf
"""

import argparse
import subprocess
import sys
import tempfile
from copy import deepcopy
from math import hypot
from itertools import product
from pathlib import Path

from fontTools.designspaceLib import DesignSpaceDocument
from fontTools.misc.transform import Transform
from fontTools.ttLib import TTFont
from fontTools.ttLib.tables import otTables as ot
from fontTools.ttLib.tables._f_v_a_r import Axis
from fontTools.ttLib.tables._g_l_y_f import GlyphCoordinates
from fontTools.ttLib.tables.TupleVariation import TupleVariation
from fontTools.varLib.models import VariationModel
from fontTools.ufoLib.kerning import lookupKerningValue
from glyphsLib.filters.eraseOpenCorners import EraseOpenCornersFilter
from capitals import extend_u, quadratic_tail_span
from identity import set_identity
from u_controls import add_u_controls, u_deltas
from join_repairs import correct_join
from letterforms import correct_glyph, native_round_quadratics, tune_weight
from strokes import extend_rails, cap_straights, extend_fork, q_tail
from ufoLib2 import Font


def edge_geometry(contours, nominal):
    """Measure parallel sides only where the opposing segment covers the sample."""
    edges = []
    for contour in contours:
        points = contour.points
        for a, b in zip(points, points[1:] + points[:1]):
            dx, dy = b.x - a.x, b.y - a.y
            length = hypot(dx, dy)
            tx, ty = (dx / length, dy / length) if length else (0, 0)
            edges.append((a, b, length, tx, ty))
    result = {}
    for a, b, length, tx, ty in edges:
        # UFO outlines wind counterclockwise around the ink. The inward normal
        # intersects the opposite side of an isolated straight stem.
        thick = nominal
        if length > 0.25:
            found = []
            for c, d, other_len, ux, uy in edges:
                alignment = tx * ux + ty * uy
                if other_len < 0.25 or alignment > -0.94:
                    continue
                # Measure over any overlapping portion. The two parallel
                # diagonals of a black M only overlap close to their ends.
                proj1 = (c.x - a.x) * tx + (c.y - a.y) * ty
                proj2 = (d.x - a.x) * tx + (d.y - a.y) * ty
                lo = max(0, min(proj1, proj2))
                hi = min(length, max(proj1, proj2))
                if hi - lo < 0.03 * min(length, other_len):
                    continue
                mx, my = a.x + tx * (hi + lo) / 2, a.y + ty * (hi + lo) / 2
                distance = ((c.y - my) * ux - (c.x - mx) * uy) / alignment
                if 0.09 * nominal < distance < 1.70 * nominal:
                    found.append(distance)
            if found:
                thick = min(found)
        result[id(a)] = tx, ty, thick
    return result


def widen_contours(glyph, scale, nominal):
    """Expand counters while keeping edge-normal stroke widths.

    For a tangent t, horizontal stretch s multiplies normal thickness by
    s / |(s*t.x,t.y)|. Move each transformed boundary inward by half of
    that excess, then intersect its two adjacent tangent lines.
    """
    edges = edge_geometry(glyph.contours, nominal)
    for contour in glyph.contours:
        points = contour.points
        offsets = []
        for p in points:
            tx, ty, thickness = edges[id(p)]
            length = hypot(scale * tx, ty)
            if not length:
                offsets.append((0, 0, 0))
                continue
            nx, ny = -ty / length, scale * tx / length
            offsets.append((nx, ny, thickness / 2 * (scale / length - 1)))
        # A sub-ten-unit bevel or rounded corner is one junction. Intersect
        # the long edges beyond it; independently offsetting microscopic
        # handles produces hooks and opens long flat notches in м and и.
        # Preserve smooth shoulders and joins in letters such as n, r and a.
        # Their short connection is part of a Bezier, not a bevel. The tiny
        # corner roundings of Д feet have sub-unit handles.
        has_long_handle = any(
            (p.type is None or q.type is None) and hypot(q.x - p.x, q.y - p.y) > 2
            for p, q in zip(points, points[1:] + points[:1])
        )
        keep = [
            has_long_handle or hypot(q.x - p.x, q.y - p.y) > max(6, 0.055 * nominal)
            for p, q in zip(points, points[1:] + points[:1])
        ]
        ymin, ymax = min(p.y for p in points), max(p.y for p in points)
        for i, p in enumerate(points):
            before, after = (i - 1) % len(points), i
            if any(keep):
                while not keep[before]:
                    before = (before - 1) % len(points)
                while not keep[after]:
                    after = (after + 1) % len(points)
            ax, ay, da = offsets[before]
            bx, by, db = offsets[after]
            det = ax * by - ay * bx
            if abs(det) > 0.06:
                dx, dy = (da * by - db * ay) / det, (ax * db - bx * da) / det
            else:
                dx, dy = (ax * da + bx * db) / 2, (ay * da + by * db) / 2
            # Prevent singular tangent intersections at folded handles.
            limit = nominal * (scale - 1) * 1.5
            norm = hypot(dx, dy)
            if norm > limit > 0:
                dx, dy = dx * limit / norm, dy * limit / norm
            # Keep beveled joins inside the cap/x-height. A sharp miter
            # between a diagonal and a stem can otherwise reach past the
            # terminal in Black. Blend toward the original bevel there.
            if before != (i - 1) % len(points) or after != i:
                allowed = 0.28 * (ymax - p.y if dy > 0 else p.y - ymin)
                if abs(dy) > allowed and abs(dy) > 0.01:
                    dy = allowed if dy > 0 else -allowed
                    # Slide along the compensated long edges rather than
                    # averaging their normals, which changes stroke weight.
                    left = (da - ay * dy) / ax if abs(ax) > 0.25 else dx
                    right = (db - by * dy) / bx if abs(bx) > 0.25 else dx
                    run = (after - before - 1) % len(points)
                    fraction = ((i - before - 1) % len(points)) / run if run else 0.5
                    dx = left + (right - left) * fraction
            p.x, p.y = scale * p.x + dx, p.y + dy


def diagonal_thickness(start, end, opposite_start, opposite_end):
    """Perpendicular distance to the middle of the opposing straight edge."""
    dx, dy = end.x - start.x, end.y - start.y
    x = (opposite_start.x + opposite_end.x) / 2 - start.x
    y = (opposite_start.y + opposite_end.y) / 2 - start.y
    return abs(dx * y - dy * x) / hypot(dx, dy)


def widen_font(font, scale, u_master=None):
    layer = font.layers.defaultLayer
    names = list(layer.keys())
    boxes = {n: layer[n].getBounds(layer) for n in names}
    w_notch = font["W"].contours[0].points[2].y
    stem = font["H"].contours[0].points
    nominal = abs(stem[1].x - stem[0].x)
    k = font["K"].contours[0].points
    lower_k = font["ka-cy"].contours[0].points
    stems = (k[1].x - k[0].x, lower_k[0].x - lower_k[-1].x)
    h = font["H"].contours[0].points
    o = font["o"].contours
    bars = (
        abs(h[8].y - h[3].y),
        max(p.y for p in o[0].points) - max(p.y for p in o[1].points),
    )
    # Predict the advance gain from the counter span available in H / o.
    growth = tuple(
        (scale - 1) * (boxes[n].xMax - boxes[n].xMin - stem) / font[n].width
        for n, stem in zip(("H", "o"), stems)
    )
    # Lowercase y, z and v use one physical stroke from the approved E.
    e = font["E"].contours[0].points
    reference_bar = e[6].y - e[5].y
    extension = (scale - 1) / 0.77
    wide_bar = (reference_bar + bars[0]) / 2
    round_reference = boxes["e"].xMax - boxes["e"].xMin
    # Add the same counter space as n, with the same weight compensation.
    round_gain = font["n"].width * growth[1]
    h_width = boxes["H"].xMax - boxes["H"].xMin
    o_width = boxes["O"].xMax - boxes["O"].xMin
    cap_gain = (scale - 1) * (h_width - nominal) + extension * 0.7 * (h_width - o_width)
    shifts = {}
    anchor_corrections = {}

    def widen(name):
        if name in shifts:
            return
        g = layer[name]
        for c in g.components:
            widen(c.baseGlyph)
        original = boxes[name]
        size = nominal
        if original:
            size = min(
                size, original.xMax - original.xMin, original.yMax - original.yMin
            )
        if name == "U-cy":
            gain = g.width * growth[0]
            if u_master is not None:
                u_master.update(u_deltas(g, gain, wide_bar, extension))
            extend_u(g, gain, wide_bar, extension)
            corrected = True
        elif name in ("K", "k", "ka-cy", "Zhe-cy", "zhe-cy"):
            lower = name in ("k", "ka-cy", "zhe-cy")
            gain = g.width * growth[lower]
            if name in ("Zhe-cy", "zhe-cy"):
                right, left = [c.points for c in g.contours[1:]]
                # Opposite arms have different winding and retain their own taper.
                fork_shift = 0.24 * gain + 48 * extension
                extend_fork(right, gain / 2, fork_shift)
                extend_fork([left[i] for i in (7, 6, 5, 4, 3, 2, 1, 0, 8)], -gain / 2, -fork_shift)
            else:
                start = 1 if name == "ka-cy" else 2
                extend_fork(g.contours[0].points[start:start + 9], gain, 0.48 * gain, grade=extension)
            corrected = True
        elif name in ("A", "V", "v", "W", "w", "M", "em-cy", "N", "Ii-cy", "ii-cy", "Z", "z"):
            if extension:
                lower = name in ("v", "w", "em-cy", "ii-cy", "z")
                gain = g.width * growth[lower]
                if name == "W":
                    gain *= 0.58
                elif name in ("M", "em-cy"):
                    gain *= 0.945
                widen_contours(g, 1 + gain / (original.xMax - original.xMin), nominal)
                if name == "em-cy":
                    # The generic miter grows a conspicuous square step on each
                    # inner stem in wide Black. Pull the two shoulders back to
                    # the stems and give the center foot room for both arms.
                    p = g.contours[0].points
                    heavy = min(1, max(0, (stems[1] - 62) / 105))
                    for shoulder, corner, foot in ((1, 2, 3), (6, 5, 4)):
                        dx = (p[shoulder].x - p[corner].x) * 0.82 * extension * heavy
                        p[corner].x += dx
                        p[foot].x += 0.50 * dx
                    for center in (11, 12):
                        p[center].y += 25 * extension * heavy
                if name in ("Z", "z"):
                    reduction = 0.22 * extension * bars[lower]
                    bar_grade = 0.13 * extension
                    p = g.contours[0].points
                    if name == "Z":
                        # Long bars and the diagonal accumulate ink in wide Z.
                        # Split the optical grade between the N reference
                        # and the lighter treatment used for lowercase z.
                        widen("N")
                        n = layer["N"].contours[0].points
                        reference = diagonal_thickness(n[10], n[9], n[3], n[4])
                        diagonal = diagonal_thickness(p[8], p[9], p[3], p[4])
                        reduction = (reduction + max(0, diagonal - reference) * extension) / 2
                        bar_grade *= 0.5
                    for corner, end, free, level, direction in (
                        (p[3], p[4], p[2], p[1].y, -1),
                        (p[8], p[9], p[7], p[6].y, 1),
                    ):
                        slope = (end.x - corner.x) / (end.y - corner.y)
                        offset = direction * reduction * hypot(1, slope) / 2
                        dy = (level - corner.y) * bar_grade
                        corner.x += offset + slope * dy
                        corner.y += dy
                        free.y = corner.y
                        end.y -= offset / slope
            corrected = True
        elif name == "won":
            # This composite crosses W with one bar. Keep the overhangs and
            # the clearance to the central notch as the W changes shape.
            if extension:
                base = layer["W"]
                box = base.getBounds(layer)
                dx_left = box.xMin - shifts["W"] - boxes["W"].xMin
                dx_right = box.xMax - shifts["W"] - boxes["W"].xMax
                dy = base.contours[0].points[2].y - w_notch
                for i, pt in enumerate(g.contours[0].points):
                    pt.x += dx_left if i in (0, 3) else dx_right
                    pt.y += dy
            corrected = True
        elif name == "O":
            extend_rails(g, [[(0, 1), (6, 0)], [(0, 0), (6, 1)]], cap_gain)
            corrected = True
        elif name.startswith("Oslash") and g.contours and g.components and g.components[0].baseGlyph == "O":
            if len(g.contours) == 2:
                # The alternate has two separate slash tips. Carry each tip
                # with its own shoulder so it stays joined even in Thin.
                g.contours[0].move((cap_gain, 0))
            elif cap_gain:
                p = g.contours[0].points
                rise = p[2].y - p[1].y
                slope = (p[2].x - p[1].x) / rise
                thickness = (p[1].x - p[0].x) / hypot(1, slope)
                dx = thickness * hypot(1, slope + cap_gain / rise)
                p[0].x = p[1].x - dx
                p[2].x += cap_gain
                p[3].x = p[2].x - dx
            corrected = True
        elif name in ("Q", "Q.BRACKET.varAlt01"):
            for contour in g.contours:
                contour.move((cap_gain, 0))
            corrected = True
        elif name in ("numero", "ohorn", "Ohorn", "uhorn", "Uhorn"):
            # Move the ring or horn with the right shoulder of its base.
            component = g.components[0]
            base = component.baseGlyph
            gain = (layer[base].getBounds(layer).xMax - boxes[base].xMax
                    - shifts[base] + component.transformation.dx * (scale - 1))
            for contour in g.contours:
                contour.move((gain, 0))
            corrected = True
        else:
            corrected = original and (
                correct_join(g, scale, original, growth, layer, shifts)
                or correct_glyph(g, scale, original, stems, bars, growth, reference_bar, nominal, round_reference, round_gain)
            )
        if original and not corrected and scale != 1:
            widen_contours(g, scale, size)
        if name == "seven" and extension:
            p = g.contours[0].points
            slope = (p[2].x - p[1].x) / (p[2].y - p[1].y)
            old_dx = p[1].x - p[0].x
            width = old_dx / hypot(1, slope)
            dx = min(0, 0.5 * (bars[0] - width)) * extension * hypot(1, slope)
            p[0].x -= dx
            p[6].x -= dx
        elif name == "Q" and scale != 1:
            q_tail(g, min(stems[0], bars[0]))
        elif (
            g.contours
            and not corrected
            and g.unicodes
            and chr(g.unicodes[0]).isalpha()
            and name not in ("Zhe-cy", "zhe-cy", "Q")
        ):
            lower = chr(g.unicodes[0]).islower()
            limit = min(bars[lower], stems[lower])
            if name == "AE":
                p, q = [c.points for c in g.contours]
                limit = min(limit, p[10].y - p[9].y, q[0].y - p[2].y)
            elif name == "Delta":
                limit = min(
                    limit, g.contours[1].points[0].y - g.contours[0].points[0].y
                )
            elif name == "Germandbls":
                p = g.contours[0].points
                limit = min(limit, p[7].y - p[28].y, p[35].y - p[0].y)
            if name == "florin":
                p = g.contours[0].points
                limit = min(
                    limit,
                    abs(p[6].y - p[5].y),
                    abs(p[13].y - p[12].y),
                    abs(p[25].y - p[0].y),
                )
                slope = (p[21].x - p[22].x) / (p[21].y - p[22].y)
                for i in (3, 4):
                    x = (
                        p[21].x
                        + slope * (p[i].y - p[21].y)
                        + 0.93 * limit * hypot(1, slope)
                    )
                    if i == 3:
                        p[2].x += x - p[i].x
                    p[i].x = x
                slope = (p[16].x - p[17].x) / (p[16].y - p[17].y)
                for i in (8, 9):
                    x = (
                        p[17].x
                        + slope * (p[i].y - p[17].y)
                        + 0.93 * limit * hypot(1, slope)
                    )
                    if i == 9:
                        p[10].x += x - p[i].x
                    p[i].x = x
            else:
                cap_straights(
                    g, (0.90 if name in ("AE", "Germandbls") else 0.96) * limit
                )
                if name == "AE":
                    p, q = [c.points for c in g.contours]
                    slope = (p[15].x - p[0].x) / (p[15].y - p[0].y)
                    thickness = 0.88 * limit * hypot(1, slope)
                    for pt in (p[1], p[2], q[0], q[1]):
                        pt.x = p[0].x + slope * (pt.y - p[0].y) + thickness
        correction = 0
        if corrected:
            updated = g.getBounds(layer)
            correction = (
                (updated.xMin + updated.xMax) - (original.xMin + original.xMax) * scale
            ) / 2
        elif g.components:
            correction = anchor_corrections[g.components[0].baseGlyph]
        for i, c in enumerate(g.components):
            xx, xy, yx, yy, ox, oy = c.transformation
            dx = (ox * scale - xx * shifts[c.baseGlyph]
                  + (correction if i and not layer[c.baseGlyph].width else 0))
            if extension and name == "Aogonek" and i == 1:
                # The ogonek follows the right foot, including when A grows
                # by less than the global width scale. Keep its native overlap.
                base = g.components[0]
                inset = ox + boxes[c.baseGlyph].xMax - boxes[base.baseGlyph].xMax
                foot = base.transformation.dx + layer[base.baseGlyph].getBounds(layer).xMax
                dx = foot + inset - layer[c.baseGlyph].getBounds(layer).xMax
            c.transformation = Transform(
                xx,
                xy / scale,
                yx * scale,
                yy,
                dx,
                oy,
            )
        for a in g.anchors:
            a.x = a.x * scale + correction
        if original:
            new = g.getBounds(layer)
            # Preserve both original sidebearings. Zero-width marks retain
            # their attachment coordinates in the scaled parent system.
            shift = original.xMin - new.xMin if g.width else 0
            if g.width:
                g.width = new.xMax + shift + (g.width - original.xMax)
            g.move((shift, 0))
        else:
            shift = 0
            g.width *= scale
        shifts[name] = shift
        anchor_corrections[name] = correction

    for name in names:
        widen(name)
    # Alternate Q is composed with its own tail. Use the same advance for
    # both forms, with the default Q's measured right bearing as reference.
    if scale != 1:
        font["Q.BRACKET.varAlt01"].width = font["Q"].width
        ku = ("ka-cy", "u-cy")
        native_kern = font.kerning[ku]
        for pair in font.kerning:
            font.kerning[pair] = round(font.kerning[pair] * scale)
        # The tips face each other at x-height. They retain their bearings
        # even as the large triangular space between the arms grows.
        k_tip = layer["ka-cy"].contours[0].points[6]
        y_tip = layer["y"].contours[0].points[3]
        bare_gap = layer["ka-cy"].width - k_tip.x + y_tip.x
        clearance = max(10, 0.72 * (bare_gap + native_kern))
        fraction = (scale - 1) / 0.77
        font.kerning[ku] = round(native_kern + fraction * (clearance - bare_gap - native_kern))


    # Add exceptions to the inherited pair values in every master. Absolute
    # kerning deltas live on wdth, so 3.17 spacing holds through 125%.
    right_bearing = font["ii-cy"].width - layer["ii-cy"].getBounds(layer).xMax
    tip_gap = right_bearing + boxes["zhe-cy"].xMin
    adjustments = [
        (("be-cy", "el-cy"), 19),
        (("ii-cy", "zhe-cy"), -min(52, 0.61 * tip_gap)),
        (("Ze-cy", "A-cy"), 17),
        (("U-cy", "El-cy"), 23),
    ]
    # Corrections are in units per 1000 em at wdth 175. Use glyph-pair
    # exceptions so inherited class pairs in unrelated words keep their spacing.
    characters = {chr(cp): g.name for g in layer for cp in g.unicodes}
    for delta, pairs in (
        (-17, "ож жк"), (16, "ко"), (10, "же"), (-10, "ЖК"),
        (17, "ТЯ тя"), (-22, "ВС"), (-10, "вс"), (17, "дл"),
        (30, "хб"), (24, "кб Тб"), (18, "ГТ ГЪ"),
        (-118, "AV VA"), (-40, "AW WA"), (-78, "AY TA ТА"),
        (0, "YA AT АТ"), (-64, "РА"), (-92, "LT"), (-110, "LY Гл"),
        (-124, "Ta To"), (-70, "Та То"), (18, "Yi xb kb"),
        (16, "xt TT ТТ"), (-12, "re"), (-8, "ra"),
    ):
        for pair in pairs.split():
            adjustments.append(((characters[pair[0]], characters[pair[1]]), delta))
    for pair, delta in adjustments:
        inherited = lookupKerningValue(pair, font.kerning, font.groups)
        font.kerning[pair] = round(inherited + extension * delta)


ZHE_AXES = [
    ("ZEXT", "Zhe shelf"),
    ("ZANG", "Zhe joint height"),
    ("ZWGT", "Zhe leg weight"),
]


CUSTOM = ZHE_AXES + [("UANG", "Cyrillic U fork angle"), ("UWGT", "Cyrillic U stroke weight")]


def add_shape_controls(font, u_masters):
    # Build each control as a glyph-local delta, interpolated over the actual
    # weight/width master grid. Pure contours retain their normal advances.
    samples = []
    for wd in (100, 125, 150, 175):
        for w in (0, 0.6129150390625, 0.845458984375, 1):
            loc = {k: v for k, v in [("wght", w), ("wdth", (wd - 100) / 75)] if v}
            loc = {k: round(v * 16384) / 16384 for k, v in loc.items()}
            samples.append(loc)
    tags = [tag for tag, _ in ZHE_AXES]
    controls = list(product((-1, 0, 1), repeat=3))
    grid = [
        {**loc, **{tag: v for tag, v in zip(tags, values) if v}}
        for loc in samples
        for values in controls
    ]
    model = VariationModel(grid, axisOrder=["wght", "wdth", *tags])
    pending = {}
    cmap = font.getBestCmap()
    for name in (cmap[ord("Ж")], cmap[ord("ж")]):
        adjustments = []
        for loc in samples:
            gs = font.getGlyphSet(location=loc, normalized=True)
            g = gs[name]._getGlyphInstance() if loc else font["glyf"][name]
            coords = list(g.coordinates)
            assert g.endPtsOfContours == [3, 12, 21]
            top = max(y for x, y in coords)
            center = sum(x for x, y in coords[:4]) / 4
            for extension, height, weight in controls:
                delta = GlyphCoordinates([(0, 0)] * (len(coords) + 4))
                if extension or height or weight:
                    for ids in (range(4, 13), range(13, 22)):
                        side = 1 if sum(coords[i][0] - center for i in ids) > 0 else -1
                        middle = sorted(
                            (i for i in ids if 1 < coords[i][1] < top - 1),
                            key=lambda i: side * (coords[i][0] - center),
                        )
                        attach, corners, fork = middle[:2], middle[2:4], middle[4]
                        shift = side * 0.065 * top * extension
                        rise = 0.09 * top * height
                        for i in attach:
                            delta[i] = (0, rise)
                        delta[fork] = (shift, rise)
                        for end_y in (0, top):
                            inner, outer = sorted(
                                (i for i in ids if abs(coords[i][1] - end_y) < 1),
                                key=lambda i: side * coords[i][0],
                            )
                            corner = min(
                                corners, key=lambda i: abs(coords[i][1] - end_y)
                            )
                            fx, fy = coords[fork]
                            ox, oy = coords[outer]
                            slope = (ox - fx) / (oy - fy)
                            # Keep the native optical taper at the tip and at
                            # the joint independently when changing the angle.
                            cx, cy = coords[corner]
                            normal = hypot(1, slope)
                            tip_weight = (ox - coords[inner][0]) / normal
                            joint_weight = (fx + slope * (cy - fy) - cx) / normal
                            slope = (ox - fx - shift) / (oy - fy - rise)
                            scale = hypot(1, slope) * (1 + 0.14 * weight)
                            delta[inner] = (ox - tip_weight * scale - coords[inner][0], 0)
                            delta[corner] = (fx + shift + slope * (cy - fy) - joint_weight * scale - cx, rise)
                adjustments.append(delta)
        pending[name] = []
        for delta, support in zip(model.getDeltas(adjustments), model.supports):
            delta.toInt()
            if any(x or y for x, y in delta):
                pending[name].append(TupleVariation(support, list(delta)))
    for name, variations in pending.items():
        font["gvar"].variations[name].extend(variations)
    add_u_controls(font, samples, u_masters)
    for tag, desc in CUSTOM:
        axis = Axis()
        axis.axisTag = tag
        axis.minValue, axis.defaultValue, axis.maxValue = (
            0,
            {"ZEXT": 48, "UANG": 0, "UWGT": 80}.get(tag, 50),
            100,
        )
        axis.axisNameID = font["name"].addName(desc)
        font["fvar"].axes.append(axis)
        for instance in font["fvar"].instances:
            instance.coordinates[tag] = axis.defaultValue
        font["avar"].segments[tag] = {-1.0: -1.0, 0.0: 0.0, 1.0: 1.0}
        if "STAT" in font:
            stat = font["STAT"].table
            record = ot.AxisRecord()
            record.AxisTag, record.AxisNameID = tag, axis.axisNameID
            record.AxisOrdering = len(stat.DesignAxisRecord.Axis)
            stat.DesignAxisRecord.Axis.append(record)
            stat.DesignAxisCount = len(stat.DesignAxisRecord.Axis)

    def expand(table):
        if isinstance(table, ot.VarRegionList):
            table.RegionAxisCount += len(CUSTOM)
            for region in table.Region:
                for _ in CUSTOM:
                    axis = ot.VarRegionAxis()
                    axis.StartCoord = axis.PeakCoord = axis.EndCoord = 0
                    region.VarRegionAxis.append(axis)
            return
        for entry in table.iterSubTables():
            expand(entry.value)

    for tag in ["HVAR", "MVAR", "GDEF", "GPOS"]:
        if tag in font:
            expand(font[tag].table)


def build(sources, output, tmp):
    design = DesignSpaceDocument.fromfile(next(sources.glob("*.designspace")))
    design.getAxis("Width").maximum = 175
    u_masters = {}
    for source in list(design.sources):
        base = Path(source.path)
        font = Font.open(base)
        # Resolve upstream open-corner hints before changing the geometry.
        # Running that filter after the transform can change master topology.
        EraseOpenCornersFilter()(font)
        font.lib.pop("com.github.googlei18n.ufo2ft.filters", None)
        thin_name = "ExpandedThin" if source.location["Width"] == 125 else "Thin"
        thin = Font.open(sources / f"SovershenenPizdets-{thin_name}.ufo")
        EraseOpenCornersFilter()(thin)
        tune_weight(font, thin)
        if source.location["Width"] == 125:
            for width, scale in ((150, 1.385), (175, 1.77)):
                wide = deepcopy(font)
                # Long horizontal bands darken these bowls in extended text.
                # Open the counters from the homologous Thin master, keeping
                # the width and upright geometry independently controlled.
                for name, grade in (("e", 0.12), ("ereversed-cy", 0.15),
                                    ("Ze-cy", 0.16), ("Ereversed-cy", 0.16), ("Iu-cy", 0.07), ("Ia-cy", 0.045)):
                    amount = grade * (scale - 1) / 0.77
                    for contour, light in zip(wide[name].contours, thin[name].contours, strict=True):
                        for point, target in zip(contour.points, light.points, strict=True):
                            point.y += amount * (target.y - point.y)
                # Match the two outer bands of з to в at the same weight.
                # Carry each inner bend with its two horizontal handles;
                # keep the middle tongue, terminals and outside extrema fixed.
                ze = wide["ze-cy"].contours[0].points
                outer, lower, upper = (c.points for c in wide["ve-cy"].contours)
                amount = (scale - 1) / 0.77
                top_shift = (ze[45].y - ze[4].y - (outer[16].y - upper[0].y)) * amount
                bottom_shift = (lower[7].y - outer[0].y - (ze[20].y - ze[30].y)) * amount
                for i in range(2, 8):
                    ze[i].y += top_shift
                for i in range(18, 24):
                    ze[i].y += bottom_shift
                weight = (source.location["Weight"] - 36) / (186.1 - 36)
                key = tuple(round(v * 16384) / 16384 for v in ((width - 100) / 75, weight))
                u_masters[key] = {}
                widen_font(wide, scale, u_masters[key])
                quadratic_tail_span(wide["U-cy"], 2)
                quadratic_tail_span(wide["y"], 5)
                quadratic_tail_span(wide["y"], 11)
                native_round_quadratics(wide)
                new = deepcopy(source)
                new.location = {**source.location, "Width": width}
                new.name = (source.name or base.stem) + f".extended{width}"
                new.path = str(tmp / (f"Wide{width}-" + base.name))
                new.styleName = f"Wide{width}" + source.styleName
                wide.info.styleName = new.styleName
                wide.save(new.path)
                design.addSource(new)
        widen_font(font, 1)
        quadratic_tail_span(font["U-cy"], 2)
        quadratic_tail_span(font["y"], 5)
        quadratic_tail_span(font["y"], 11)
        native_round_quadratics(font)
        source.path = str(tmp / base.name)
        font.save(source.path)
    path = tmp / "Lab.designspace"
    design.write(path)
    intermediate = tmp / "built.ttf"
    subprocess.run(
        [
            str(Path(sys.executable).with_name("fontmake")),
            "-m",
            str(path),
            "-o",
            "variable",
            "--output-path",
            str(intermediate),
            "--verbose",
            "WARNING",
        ],
        check=True,
    )
    font = TTFont(intermediate)
    add_shape_controls(font, u_masters)
    set_identity(font, "Sovershenen Pizdets v4 Lab")
    font.save(output)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("sources", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    with tempfile.TemporaryDirectory(prefix="sp-lab-") as directory:
        build(args.sources.resolve(), args.output.resolve(), Path(directory))
