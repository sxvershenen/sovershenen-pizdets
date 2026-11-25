"""Glyph-local gvar controls for Cyrillic У on the extended width masters."""

from copy import deepcopy

from fontTools.misc.bezierTools import splitCubicAtT
from fontTools.ttLib.tables._g_l_y_f import GlyphCoordinates
from fontTools.ttLib.tables.TupleVariation import TupleVariation
from fontTools.varLib.models import VariationModel

from capitals import extend_u, quadratic_tail_span


# (normalized fvar location, drawing parameter). Keep the original middle
# shape as a control knot after moving the neutral master to low / 80.
ANGLE_KNOTS = ((0, -1), (0.5, 0), (1, 1))
WEIGHT_KNOTS = ((-1, -1), (-0.375, 0), (0, 0.6), (1, 1))


def quadratic_coordinates(glyph):
    # glyf stores this contour in reverse order. The native outer and inner
    # curves use three and two quadratic handles respectively in every master.
    quadratic_tail_span(glyph, 2)
    points = [(p.x, p.y) for p in glyph.contours[0].points]
    pieces = splitCubicAtT(*points[8:12], 1 / 3, 2 / 3)
    handles = []
    for i, piece in enumerate(pieces):
        a, b, c, d = (complex(*pt) for pt in piece)
        left, right = a + 1.5 * (b - a), d + 1.5 * (c - d)
        q = left + (right - left) * i / 2
        handles.append((q.real, q.imag))
    return GlyphCoordinates([points[0], *points[16:10:-1], *reversed(handles),
                             *points[8:0:-1], *[(0, 0)] * 4])


def u_deltas(glyph, gain, bar, extension):
    neutral = deepcopy(glyph)
    extend_u(neutral, gain, bar, extension)
    base = quadratic_coordinates(neutral)
    result = {}
    for a, angle in ANGLE_KNOTS:
        for w, weight in WEIGHT_KNOTS:
            alt = deepcopy(glyph)
            extend_u(alt, gain, bar, extension, angle=angle, weight=weight)
            result[a, w] = quadratic_coordinates(alt) - base
    return result


def add_u_controls(font, samples, masters):
    name = font.getBestCmap()[ord("У")]
    count = len(font["glyf"][name].coordinates) + 4
    zero = GlyphCoordinates.zeros(count)
    locations, values = [], []
    for loc in samples:
        master = masters.get((loc.get("wdth", 0), loc.get("wght", 0)), {})
        for angle, _ in ANGLE_KNOTS:
            for weight, _ in WEIGHT_KNOTS:
                coordinates = {**loc, "UANG": angle, "UWGT": weight}
                locations.append({k: v for k, v in coordinates.items() if v})
                value = master.get((angle, weight), zero)
                assert len(value) == count
                values.append(value)
    model = VariationModel(locations, axisOrder=["wght", "wdth", "UANG", "UWGT"])
    for support, delta in zip(model.supports, model.getDeltas(values)):
        delta.toInt()
        if any(x or y for x, y in delta):
            font["gvar"].variations[name].append(TupleVariation(support, list(delta)))
