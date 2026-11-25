"""Shape the common a/а contour and optionally retain its study controls."""
from itertools import product
from fontTools.misc.roundTools import otRound
from fontTools.otlLib.builder import buildStatTable
from fontTools.ttLib.tables._f_v_a_r import Axis
from fontTools.ttLib.tables._g_l_y_f import GlyphCoordinates
from fontTools.ttLib.tables.TupleVariation import TupleVariation
from fontTools.varLib.instancer import NormalizedAxisLimits, instantiateGvarGlyph
from fontTools.varLib import builder
from fontTools.varLib.models import VariationModel

HEIGHT = "ABHT"
THICKNESS = "ABWT"
APPROVED_THICKNESS = 110


def reshape(points, e, native, extension, height_delta, weight_factor):
    """Move both crossbar boundaries independently and refit the adjoining arcs."""
    ay = [y for x, y in points]
    e_bottom, e_top = e[1][1], e[37][1]
    center = (e_bottom + e_top) / 2 + height_delta
    thickness = (e_top - e_bottom) * 0.90 * weight_factor
    top = otRound(center + thickness / 2)
    bottom_delta = otRound(center - thickness / 2) - ay[54]
    offsets = [0.0] * len(ay)
    for i in range(18, 21):
        offsets[i] = (top - ay[21]) * (ay[i] - ay[17]) / (ay[21] - ay[17])
    # Both the shoulder's last handle and the straight run enter horizontally.
    for i in range(20, 26):
        offsets[i] = top - ay[i]
    for i in range(26, 31):
        offsets[i] = (top - ay[25]) * (ay[31] - ay[i]) / (ay[31] - ay[25])
    for i in range(42, 59):
        offsets[i] = bottom_delta * (ay[i] - ay[46]) / (ay[54] - ay[46])
    dx = [0.0] * len(ay)
    mid = midpoint(points)
    handle = (0, 0)
    if extension:
        # Intersect the foot edge with the returning bowl tangent. Trim both
        # lines about that intersection and connect them with one quadratic.
        x, y = points[8]
        foot_slope = (x - points[7][0]) / (y - ay[7])
        ease = 0.10 * (y - ay[7])
        dx[10] = -extension * ease
        bowl_slope = (points[9][0] - points[10][0] + ease) / (ay[9] - ay[10])
        jy = y + (x - points[9][0]) / (bowl_slope - foot_slope)
        jx = x + foot_slope * (jy - y)
        trim = min(0.75 * (jy - ay[10]), 15 + 0.11 * (points[6][0] - points[7][0]))
        for i, slope in ((8, foot_slope), (9, bowl_slope)):
            dx[i] = extension * (jx - slope * trim - points[i][0])
            offsets[i] = extension * (jy - trim - ay[i])
        handle = (otRound(extension * (jx - mid[0])), otRound(extension * (jy - mid[1])))

        # Put the extra span along the bowl floor. Keep the turning handles
        # near the upright instead of stretching them halfway across the bowl.
        for i in (11, 48):
            dx[i] = extension * (x - native[8][0] + native[i][0] - points[i][0])
        for i in range(47, 54):
            ratio = (native[i][1] - native[46][1]) / (native[54][1] - native[46][1])
            target = ay[46] + ratio * (ay[54] + bottom_delta - ay[46])
            offsets[i] += extension * (target - ay[i] - offsets[i])
    deltas = [(otRound(x), otRound(y)) for x, y in zip(dx, offsets)]
    deltas.insert(9, handle)
    return GlyphCoordinates(deltas + [(0, 0)] * 4)


def midpoint(points):
    return tuple(otRound((a + b) / 2) for a, b in zip(points[8], points[9]))



def add_axes(font):
    for tag, name, lo, neutral, hi in (
        (HEIGHT, "Crossbar lift", -16, 0, 16),
        (THICKNESS, "Crossbar thickness", 85, 100, 115),
    ):
        axis = Axis()
        axis.axisTag, axis.axisNameID = tag, font["name"].addName(name)
        axis.minValue, axis.defaultValue, axis.maxValue = lo, neutral, hi
        font["fvar"].axes.append(axis)
        font["avar"].segments[tag] = {-1: -1, 0: 0, 1: 1}
        for inst in font["fvar"].instances:
            inst.coordinates[tag] = neutral
    for key in ("HVAR", "VVAR", "MVAR", "GDEF", "BASE", "COLR"):
        if key in font and (store := getattr(font[key].table, "VarStore", None)):
            regions = store.VarRegionList
            regions.RegionAxisCount += 2
            for region in regions.Region:
                region.VarRegionAxis.extend(builder.buildVarRegionAxis((0, 0, 0)) for _ in range(2))
    buildStatTable(font, [{"tag": a.axisTag, "name": a.axisNameID} for a in font["fvar"].axes])


def apply_crossbar(font, *, interactive=False):
    variations = font["gvar"].variations
    for name in font.getGlyphOrder():
        _ = variations[name]
    axes = variations["a"]
    glyf = font["glyf"]
    original, controls = glyf._getCoordinatesAndControls("a", font["hmtx"].metrics)
    assert controls.endPts == [41, 58] and glyf["e"].endPtsOfContours == [35, 48]
    for tup in axes:
        tup.calcInferredDeltas(original, controls.endPts)
        tup.roundDeltas()
    knots = {tag: sorted({0.0, *(t.axes[tag][1] for t in axes if tag in t.axes)})
             for tag in ("wght", "wdth")}
    locations, values = [], []
    native_width = knots["wdth"][1]  # 125% on the 100..175 axis
    for weight, width in product(knots["wght"], knots["wdth"]):
        loc = {"wght": weight, "wdth": width}
        gs = font.getGlyphSet(location=loc, normalized=True)
        a, e = [gs[n]._getGlyphInstance().coordinates for n in ("a", "e")]
        ref = font.getGlyphSet(location={**loc, "wdth": native_width}, normalized=True)
        native = ref["a"]._getGlyphInstance().coordinates
        extension = max(0, (width - native_width) / (1 - native_width))
        for h, t in product((-1, 0, 1), repeat=2):
            coord = {**loc, HEIGHT: h, THICKNESS: t}
            locations.append({k: v for k, v in coord.items() if v})
            values.append(reshape(a, e, native, extension, h * 16, 1 + t * .15))
    model = VariationModel(locations, axisOrder=["wght", "wdth", HEIGHT, THICKNESS])
    # An off-curve point at the midpoint exactly represents the original
    # straight shelf in the native masters. Give it a handle in extended ones.
    glyph = glyf["a"]
    points = list(glyph.coordinates)
    points.insert(9, midpoint(points))
    glyph.coordinates = GlyphCoordinates(points)
    glyph.flags.insert(9, 0)
    glyph.endPtsOfContours = [i + 1 for i in glyph.endPtsOfContours]
    for tup in axes:
        tup.coordinates.insert(9, midpoint(tup.coordinates))
    if interactive:
        add_axes(font)
    for support, delta in zip(model.supports, model.getDeltas(values)):
        delta.toInt()
        if not support:
            glyf["a"].coordinates += GlyphCoordinates(delta[:-4])
        elif any(x or y for x, y in delta):
            axes.append(TupleVariation(support, list(delta)))
    # Quantize each horizontal as a unit so rounding and interpolation cannot
    # introduce a one-unit taper between the middle and the right upright.
    for coords in (glyph.coordinates, *(t.coordinates for t in axes)):
        for indices in (range(21, 27), range(55, 58)):
            y = coords[indices[1]][1]
            for i in indices:
                coords[i] = (coords[i][0], y)
    if not interactive:
        limits = NormalizedAxisLimits({
            HEIGHT: 0,
            THICKNESS: round((APPROVED_THICKNESS - 100) / 15 * 16384) / 16384,
        })
        instantiateGvarGlyph(font, "a", limits)
