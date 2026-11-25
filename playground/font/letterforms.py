"""Optical corrections for the Saira-derived UFO topology used by the lab."""

from math import atan, hypot, pi, tan

from fontTools.misc.bezierTools import splitCubicAtT
from ufoLib2.objects import Point

from capitals import rounded_b, extend_four, extend_iu, extend_y_cap
from strokes import RAILS, extend_rails, lower_ya, rail_glyph


def native_round_quadratics(font):
    # Native cu2qu counts for consecutive cubics in each 3.17 contour.
    # If cu2qu chooses a finer split for an extended shoulder, that split
    # would otherwise change the rounding in every native master as well.
    counts = {
        "a": [(4, 4, 4, 4, 3, 3, 3, 3), (3, 3, 2, 3)],
        "e": [(4, 4, 4, 4, 4, 4), (4, 4)],
        "g": [(4, 3, 4, 4, 3, 4, 4, 2), (4, 4, 2, 2, 2, 2)],
    }
    for name, patterns in counts.items():
        for contour, pattern in zip(font[name].contours, patterns, strict=True):
            points = contour.points
            ends = (i for i, p in enumerate(points) if p.type == "curve")
            controls = {}
            for end, n in zip(ends, pattern, strict=True):
                cubic = [(points[end+i].x, points[end+i].y) for i in (-3, -2, -1, 0)]
                pieces = splitCubicAtT(*cubic, *(i/n for i in range(1, n)))
                handles = []
                for j, piece in enumerate(pieces):
                    a, b, c, d = (complex(*xy) for xy in piece)
                    left, right = a + 1.5*(b-a), d + 1.5*(c-d)
                    q = left + (right-left) * j / (n-1)
                    handles.append(Point(q.real, q.imag))
                controls[end] = handles
            rebuilt = []
            for i, pt in enumerate(points):
                if pt.type is None:
                    continue
                if i in controls:
                    rebuilt.extend(controls[i])
                    pt.type = "qcurve"
                rebuilt.append(pt)
            points[:] = rebuilt


def point_groups(glyph, groups, amount):
    """Translate complete features together, including their Bézier handles."""
    assert len(groups) == len(glyph.contours)
    for contour, weights in zip(glyph.contours, groups):
        assert len(contour.points) == len(weights), glyph.name
        for point, weight in zip(contour.points, weights):
            point.x += amount * int(weight) / 4


# 0 = left shoulder, 4 = right shoulder, 2 = middle. Each group is a contour.
# Counter expansion only moves in x. Tangent handles on the top, floor and
# terminals travel with their on-curve point, so a horizontal cut stays level.
GROUPS = {
    "Omega": ("000000002444444444444444442000000000",),
    "bracketleft": ("04400440",),
    "bracketright": ("04400440",),
    "longs": ("11112442111111",),
    "s": ("44420000011444442000000002444443300000244444",),
    "e": ("444200000244444444200004", "000244440"),
    "a": ("442000000244443210000022444444", "00000244444422"),
}
GROUPS["S"] = GROUPS["s"]


def set_polygon(points, coords):
    assert len(points) == len(coords)
    for point, (x, y) in zip(points, coords):
        point.x, point.y = x, y


def normal_width(a, b, c):
    return abs((b.x - a.x) * (a.y - c.y) - (a.x - c.x) * (b.y - a.y)) / hypot(
        b.x - a.x, b.y - a.y
    )


def redraw_x(glyph, left, width, limit, extension):
    p = glyph.contours[0].points
    h = p[7].y
    t = (normal_width(p[0], p[13], p[1]) + normal_width(p[5], p[6], p[4])) / 2
    gap = max(2, p[3].x - p[2].x)
    center = left + width / 2
    narrow_dx = t
    for _ in range(12):
        narrow_slope = (width - narrow_dx) / h
        narrow_dx = t * hypot(1, narrow_slope)
    classical = (width - 2 * narrow_dx - gap) / (2 * narrow_slope)
    lo = classical * (1 - extension) + (h - limit) * extension / 2
    gap += extension * 0.14 * width
    # Solve the slope with both ink boundaries at the requested normal distance.
    low, high = 0, width / (2 * lo)
    for _ in range(32):
        slope = (low + high) / 2
        dx = t * hypot(1, slope)
        if dx + slope * lo < (width - gap) / 2:
            low = slope
        else:
            high = slope
    crotch = h / 2 - lo
    r = left + width
    set_polygon(
        p,
        [
            (left, 0),
            (left + dx, 0),
            (center - gap / 2, h / 2 - crotch),
            (center + gap / 2, h / 2 - crotch),
            (r - dx, 0),
            (r, 0),
            (left + width - slope * h / 2, h / 2),
            (r, h),
            (r - dx, h),
            (center + gap / 2, h / 2 + crotch),
            (center - gap / 2, h / 2 + crotch),
            (left + dx, h),
            (left, h),
            (left + slope * h / 2, h / 2),
        ],
    )


def tune_weight(font, thin):
    # Blend toward homologous thin-master outlines. This lightens bars and
    # diagonals together without shearing the ends or altering glyph topology.
    for name, amount in {
        "s": 0.14,
        "S": 0.085,
    }.items():
        for a, b in zip(font[name].contours, thin[name].contours, strict=True):
            for p, q in zip(a.points, b.points, strict=True):
                p.x += (q.x - p.x) * amount
                p.y += (q.y - p.y) * amount


def ligature_e_counter(glyph, thickness):
    # These two UFOs have an overlapping diagonal segment at the foot of
    # the right counter. Keep its roof and square up the corner of the e.
    body = glyph.contours[0].points
    counter = glyph.contours[2].points
    floor = body[16].y
    old_roof = counter[2].y
    shift = (thickness - (old_roof - floor)) / 2
    base = body[13].y
    for pt in body[14:18]:
        pt.y -= shift * (pt.y - base) / (floor - base)
    roof = old_roof + shift
    top = counter[5].y
    for pt in counter:
        pt.y += shift * (top - pt.y) / (top - old_roof)
    right = counter[7].x
    counter[0].x = counter[1].x = right
    counter[1].y = counter[2].y = roof
    counter[0].y = roof + 1
    counter[3].x = counter[2].x
    counter[4].y = counter[6].y = top
    if glyph.name == "oe":
        counter[8].x = right
        counter[8].y = roof + 2


def extended_y(glyph, gain, amount, reference_bar):
    if not gain:
        return
    p = glyph.contours[0].points
    height = p[3].y
    a0 = (p[4].x - p[3].x) / height
    b0 = (p[15].x - p[14].x) / (height - p[14].y)
    alpha, beta = atan(a0), atan(b0)
    # Open both arms by the same angle. Their projected runs must sum to
    # the requested change in width; their native angular difference survives.
    low, high = 0, pi / 2 - max(alpha, beta)
    for _ in range(32):
        angle = (low + high) / 2
        a, b = tan(alpha + angle), tan(beta + angle)
        if height * (a - a0 + b - b0) < gain:
            low = angle
        else:
            high = angle
    left = (p[2].x - p[3].x) / hypot(1, a0)
    right = (p[15].x - p[0].x) / hypot(1, b0)
    inner_a = a + (1 - amount) * ((p[1].x - p[2].x) / (height - p[1].y) - a0)
    original_b = (p[0].x - p[1].x) / (height - p[1].y)
    inner_b = b + (1 - amount) * (original_b - b0)
    heel_offset = p[5].x - (p[0].x - original_b * height)
    native_ledge = p[5].x - p[4].x
    x5, x14 = p[5].x, p[14].x
    p[15].x += gain
    p[14].x = p[15].x - b * (height - p[14].y)
    p[4].x = p[3].x + a * height
    p[2].x = p[3].x + left * hypot(1, a)
    p[0].x = p[15].x - right * hypot(1, b)
    depth = (p[0].x - p[2].x) / (inner_a + inner_b)
    p[1].x, p[1].y = p[2].x + inner_a * depth, height - depth
    p[5].x = p[0].x - inner_b * height + (1 - amount) * heel_offset

    # Let the two rails continue a little below the baseline when their
    # intersection would otherwise leave a growing slab above the hook.
    drop = min(0.3 * abs(p[6].y), max(0, (p[5].x - p[4].x - native_ledge) / (a + inner_b)))
    p[4].x += a * drop
    p[5].x -= inner_b * drop
    p[4].y = p[5].y = -drop

    # Translate the terminal as a single curve. Only the two root handles
    # follow the rotation, so the hook does not get stretched across the page.
    dx5, dx14 = p[5].x - x5, p[14].x - x14
    shift = (dx5 + dx14) / 2 + 0.55 * (b - b0) * (p[11].y - p[14].y)
    for pt in p[7:13]:
        pt.x += shift
    p[6].x += dx5 + (b - b0) * (p[6].y - p[5].y)
    p[13].x += dx14 + (b - b0) * (p[13].y - p[14].y)
    cap = p[9].y - p[10].y
    taper = amount * (min(cap, 0.87 * reference_bar) - cap)
    for pt in p[7:10]:
        pt.y += taper
    p[6].y += taper / 3


def correct_glyph(glyph, scale, box, stems, bars, growth, reference_bar, reference_stem, round_reference, round_gain):
    name = glyph.name
    left = box.xMin
    span = (box.xMax - left) * (scale - 1)
    lower = bool(glyph.unicodes and chr(glyph.unicodes[0]).islower())
    limit = min(stems[lower], bars[lower])
    if name in RAILS or name == "ia-cy":
        span = glyph.width * growth[lower]
    extension = min(1, (scale - 1) / 0.77)
    if name in ("a", "e", "o", "g", "c", "ereversed-cy"):
        # Converge on the extended e, leaving one fifth of the original
        # width difference so each letter retains a little of its rhythm.
        native_width = box.xMax - left
        span = round_gain + extension * 0.8 * (round_reference - native_width)
    elif name == "s":
        # Keep the narrower s/e proportion of the original 125% master.
        # Whole shoulders move with their handles; the strokes aren't scaled.
        span = round_gain * (box.xMax - left) / round_reference
    if name in ("x", "X", "Y") and scale == 1:
        return True
    if name == "te-cy":
        # Keep the original t/o proportion without stretching the upright.
        gain = round_gain * (box.xMax - left) / round_reference
        point_groups(glyph, ("22440022",), gain)
    elif name in ("Ereversed-cy", "ereversed-cy"):
        if name == "Ereversed-cy":
            # Keep the right arc and the open terminals at their native widths.
            # Extend the counters along the flat tangents, as for lowercase э.
            span = glyph.width * growth[0]
        extend_rails(glyph, [[(2, 0), (9, 1), (15, 0), (22, 1)], []], span)
        bar = glyph.contours[1].points
        for p in bar:
            p.x += span * (1 if p.x > (box.xMin + box.xMax) / 2 else 0.54)
    elif name == "y":
        extended_y(glyph, glyph.width * growth[1], extension, reference_bar)
    elif name in ("c", "o"):
        # Insert the extra straight only at horizontal tangencies. Moving the
        # whole bend preserves both its aperture and its normal thickness.
        cuts = [[(2, 1), (9, 0), (15, 1), (22, 0)]] if name == "c" else [
            [(0, 1), (6, 0)], [(0, 0), (6, 1)]
        ]
        extend_rails(glyph, cuts, span)
    elif name == "ze-cy":
        # The four split extrema in з already have a straight segment in the
        # source. Separate their endpoints and keep the two bowls rigid.
        p = glyph.contours[0].points
        for i in (*range(5, 21), *range(31, 46)):
            p[i].x += span
        for i in (12, 13):
            p[i].x -= 0.62 * span
        # Open the curved returns without thinning the long horizontal bands.
        inset = min(4, 0.036 * stems[1]) * extension
        for i in (0, 1, 2, 3, 22, 23, 24, 25):
            p[i].x -= inset
        for i in (6, 7, 8, 9, 10, 15, 16, 17, 18, 19):
            p[i].x += inset
    elif name == "g":
        if scale == 1:
            extend_rails(glyph, RAILS[name], 0)
        else:
            rail_glyph(glyph, span, bars[1])
    elif name in RAILS:
        rail_glyph(glyph, 2 + span / (2 if name == "m" else 1), bars[1])
    elif name in (
        "bullet",
        "bulletoperator",
        "copyright",
        "orn.001",
        "orn.007",
        "upDownbaseArrow",
        "ring",
        "ringcomb",
        "ringcomb.case",
        "degree",
    ):
        return True
    elif name in ("percent", "perthousand"):
        circles = glyph.contours[1::2]
        centers = [c.points[0].x for c in circles]
        gain = glyph.width * growth[0]
        x0, x1 = min(centers), max(centers)
        for i, c in enumerate(glyph.contours[1:]):
            dx = gain * (centers[i // 2] - x0) / (x1 - x0)
            c.move((dx, 0))
        p = glyph.contours[0].points
        t = normal_width(p[0], p[3], p[1])
        bottom, top = p[0].x, p[3].x
        p[0].x = bottom + gain * (bottom - x0) / (x1 - x0)
        p[3].x = top + gain * (top - x0) / (x1 - x0)
        slope = (p[3].x - p[0].x) / (p[3].y - p[0].y)
        p[1].x = p[0].x + t * hypot(1, slope)
        p[2].x = p[3].x + t * hypot(1, slope)
    elif name == "ve-cy":
        point_groups(glyph, ("4" * 17 + "00", "044444440", "0444444440"), glyph.width * growth[1])
    elif name == "mu":
        point_groups(glyph, ("0" * 7 + "2" + "4" * 11 + "2" + "0" * 5,), glyph.width * growth[1])
    elif name == "ordfeminine":
        point_groups(glyph, ("244444444420000002444442200000", "20000024444442"), glyph.width * growth[1])
    elif name in ("ae", "oe"):
        # Keep the left, shared and right stems together with their handles.
        # Added width belongs to the counters on either side of the joint.
        shared = "112223333444332224444332221"
        if name == "ae":
            groups = (shared + "11000011222221100000", "10000012222221", "44222344")
        else:
            groups = (shared + "100000", "100000122222", "442223444")
        point_groups(glyph, groups, glyph.width * growth[1])
        ligature_e_counter(glyph, reference_bar)
    elif name == "R.ss01":
        point_groups(glyph, ("0000" + "4" * 17 + "0", "004444444"), glyph.width * growth[0])
    elif name == "G":
        point_groups(glyph, ("4442000002244442244442200000244444",), glyph.width * growth[0])
        p = glyph.contours[0].points
        # A reversed control below the counter floor is almost invisible at
        # 125%, but turns into a long notch as the bowl opens.
        p[18].y = max(p[21].y + 4, min(p[17].y - 2, p[18].y))
        p[19].y = max(p[21].y, min(p[18].y, p[19].y))
        p[20].y = p[21].y
    elif name in ("Tse-cy", "tse-cy", "Shcha-cy", "shcha-cy"):
        main = "00444400" if len(glyph.contours[0].points) == 8 else "004444222200"
        counter_gain = glyph.width * growth[lower]
        if name in ("Tse-cy", "tse-cy"):
            counter_gain *= 0.94
        point_groups(glyph, (main, "4444", "4444"), counter_gain)
        if lower:
            for contour in glyph.contours[1:]:
                p = contour.points
                p[0].x = p[3].x = p[1].x - reference_stem
        if name in ("Tse-cy", "tse-cy"):
            body = glyph.contours[0].points
            body[5].y = body[6].y = bars[lower]
            for contour in glyph.contours[1:2]:
                contour.points[2].y = contour.points[3].y = bars[lower]
    elif name in GROUPS:
        point_groups(glyph, GROUPS[name], span)
        if name == "a":
            outer, counter = [c.points for c in glyph.contours]
            # Thicken the thin waist on both sides while keeping the native
            # slant and a positive aperture above and below it in Black.
            mid = (outer[13].y + outer[16].y) / 2 - counter[5].y
            delta = extension * max(0, 0.98 * reference_bar - mid)
            for pt in outer[13:18]:
                pt.y += 0.22 * delta
            outer[18].y += 0.11 * delta
            for pt in counter[3:8]:
                pt.y -= 0.78 * delta
            counter[8].y -= 0.39 * delta
    elif name in ("Yeru-cy", "yeru-cy"):
        widen_yeru(glyph, scale)
    elif name in ("De-cy", "de-cy"):
        # Move the complete left shoulder together; width belongs in the counter.
        point_groups(
            glyph,
            ("044440", "0000000000", "0440", "0000000000", "4444444444"),
            glyph.width * growth[lower],
        )
        if name == "De-cy":
            # Keep the advance and the two feet, and give each ledge a modest
            # share of the gain. Translate whole shoulders with their handles.
            ledge = 0.09 * glyph.width * growth[0]
            cap = glyph.contours[0].points
            for idx, pt in enumerate(cap):
                pt.x += ledge if idx in (0, 5) else -ledge
            glyph.contours[1].move((ledge, 0))
    elif name in ("R", "Ia-cy"):
        # Extend only the flat runs. Bowl, leg, attachment and foot travel
        # together. Width compensation keeps the leg on its original outside edge.
        if name == "R":
            point_groups(
                glyph, ("000444444444444440", "004444444"), glyph.width * growth[0]
            )
        else:
            point_groups(
                glyph, ("400000000000000444", "000000044"), glyph.width * growth[0]
            )
        points = glyph.contours[0].points
        if extension:
            # At the inside of the native leg the bowl can double back over the
            # diagonal in Black. Taper the return up to its horizontal tangent.
            if name == "R":
                foot, join = points[8], points[7]
                waist, shoulder, curve, side = points[6], points[3], points[4:7], -1
            else:
                foot, join = points[9], points[10]
                waist, shoulder, curve, side = points[11], points[14], points[11:14], 1
            t = (waist.y - foot.y) / (join.y - foot.y)
            leg_x = foot.x + t * (join.x - foot.x)
            shift = side * max(0, side * (leg_x - waist.x) + 2)
            span = shoulder.x - waist.x
            if span:
                for pt in curve:
                    pt.x += shift * (shoulder.x - pt.x) / span
    elif name == "Y":
        extend_y_cap(glyph, glyph.width * growth[0])
    elif name in ("Iu-cy", "iu-cy"):
        extend_iu(glyph, glyph.width * growth[lower])
    elif name == "four":
        if extension:
            extend_four(glyph, 0.83 * glyph.width * growth[0], bars[0], extension)
    elif name == "Soft-cy":
        # Extend the flat runs of the bowl. Keep its bends, stem and sidebearings.
        point_groups(glyph, ("0000", "4444444400", "0444444440"), 0.78 * glyph.width * growth[0])
        if extension:
            for contour, idx, direction in ((glyph.contours[1], 3, 1), (glyph.contours[2], 4, -1)):
                p = contour.points
                gap = direction * (p[idx + 1].y - p[idx].y)
                shift = direction * max(0, 2 - gap) / 2
                for i in (idx - 1, idx):
                    p[i].y -= shift
                for i in (idx + 1, idx + 2):
                    p[i].y += shift
    elif name == "five":
        point_groups(glyph, ("000440", "024444420000000024444420"), glyph.width * growth[0])
    elif name in ("guarani", "guarani.BRACKET.varAlt01"):
        body = "244442244442000002244442200000"
        point_groups(glyph, (body,) + ("2222",) * (len(glyph.contours)-1), glyph.width * growth[0])
    elif name in ("Che-cy", "che-cy"):
        point_groups(glyph, ("4444", "000244200000"), glyph.width * growth[lower])
    elif name in ("El-cy", "el-cy"):
        point_groups(glyph, ("044440", "0000000000"), glyph.width * growth[lower])
        if name == "El-cy":
            # The expanded 600-weight upright is about 119 units; heavier
            # masters progressively give the hook clearance under the arch.
            reach = 0.65 * max(0, stems[0] - 119) * extension
            for pt in glyph.contours[1].points[2:8]:
                pt.x -= reach * (1 - pt.y / glyph.contours[1].points[1].y)
    elif name in ("Hard-cy", "hard-cy"):
        point_groups(
            glyph,
            ("0000", "0000", "2444444200", "0244444420"),
            glyph.width * growth[lower],
        )
        # Remove the minute overlap at the bowl extrema (same source topology as ы).
        for contour, i in ((glyph.contours[2], 3), (glyph.contours[3], 4)):
            a, b = contour.points[i : i + 2]
            a.y = b.y = (a.y + b.y) / 2
    elif name == "B":
        rounded_b(glyph, glyph.width * growth[0], stems[0], bars[0] * (1 - 0.058 * extension))
    elif name == "ia-cy":
        lower_ya(glyph, 0.86 * span, bars[1], extension)
    elif name in ("x", "X"):
        redraw_x(
            glyph,
            left,
            box.xMax - left + glyph.width * growth[lower],
            min(stems[0], limit * 1.065) if name == "X" else limit,
            extension,
        )
    else:
        return False
    return True


def widen_yeru(glyph, scale):
    stem, bowl, counter, _ = glyph.contours
    for points, i in ((bowl.points, 3), (counter.points, 4)):
        # These adjacent on-curve points straddle a sub-unit overlap upstream.
        a, b = points[i : i + 2]
        a.y = b.y = (a.y + b.y) / 2
    span = (max(p.x for p in bowl.points) - min(p.x for p in stem.points)) * (scale - 1)
    point_groups(glyph, ["0000", "2444444200", "0244444420", "4444"], span)
