"""Keep extended symbols and marks joined to their supporting contours."""

from fontTools.misc.transform import Transform

# The horizontal accent and the ornament inside the shield have little room
# for expansion. Their native outlines can move intact with the parent anchor.
COMPACT = {"tilde", "ogonek", "uniEFFD", "bar.ss02", "exclam.ss02",
           "apostrophemod", "comma", "semicolon", "quotesinglbase", "quoteleft", "quoteright",
           "commaaccentcomb", "commaaccentcomb.case", "commaturnedabovecomb", "commaturnedabovecomb.case"}
for suffix in ("", ".case"):
    for mark in (
        "tildecomb", "ogonekcomb", "hookabovecomb", "brevecomb_tildecomb",
        "circumflexcomb_tildecomb", "brevecomb_hookabovecomb", "circumflexcomb_hookabovecomb",
    ):
        COMPACT.add(mark + suffix)
# Keep the same width behaviour across the figure set used in fractions.
for digit in ("zero", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine"):
    COMPACT.update((digit + ".numr", digit + ".dnom"))


def set_bar(p, left, right):
    p[0].x = p[3].x = left
    p[1].x = p[2].x = right


def correct_join(glyph, scale, box, growth, layer, shifts):
    name = glyph.name
    if name in COMPACT:
        # Space the base independently of the accent. Compound mark stacks
        # retain their registration with each other, including in Black.
        dx = (box.xMin + box.xMax) * (scale - 1) / 2
        for contour in glyph.contours:
            contour.move((dx, 0))
    elif name in ("quotedblleft", "quotedblright", "quotedblbase"):
        for contour in glyph.contours:
            bounds = contour.bounds
            contour.move(((bounds.xMin + bounds.xMax) * (scale - 1) / 2, 0))
    elif name == "dieresiscomb":
        # Open the space between the dots. As heavy dots become wider than
        # they are tall, taper that excess while preserving their height.
        for contour in glyph.contours:
            b = contour.bounds
            center = (b.xMin + b.xMax) / 2
            width, height = b.xMax - b.xMin, b.yMax - b.yMin
            reduction = 0.85 * (scale - 1) / 0.77 * max(0, width-height) / width
            for point in contour.points:
                point.x = center * scale + (point.x-center) * (1-reduction)
    elif name in ("asciitilde", "approxequal"):
        gain = glyph.width * growth[0]
        for c in glyph.contours:
            p = c.points
            # Keep both terminal bends rigid, widen just the sloping bridge.
            # Corresponding points on the two sides follow the same progression.
            for i in (5, 6, 7, 8, 9, 18, 19, 20, 21, 22):
                p[i].x += gain * ((i-4)/6 if i<10 else (23-i)/6)
            for i in range(10, 18):
                p[i].x += gain
    elif name in ("aogonek", "uogonek"):
        if scale != 1:
            body, hook = glyph.components
            b = layer[body.baseGlyph].getBounds(layer)
            mark = layer[hook.baseGlyph].getBounds(layer)
            # The source tip lies one unit beyond the right upright. The
            # general anchor correction is centred on the enlarged base.
            center_shift = (b.xMin + b.xMax - scale * (box.xMin + box.xMax)) / 2
            target = b.xMax - shifts[body.baseGlyph] + 1
            x = (target - mark.xMax + shifts[hook.baseGlyph] - center_shift) / scale
            hook.transformation = Transform().translate(x, hook.transformation.dy)
    elif name == "leftOpenDialog":
        first, second = glyph.components
        stem, bars = first.baseGlyph, second.baseGlyph
        dx = layer[stem].getBounds(layer).xMax - shifts[stem] + shifts[bars]
        # The shared component transform in widen_font will scale this offset.
        # Keep the horizontal rails anchored on the upright's right edge.
        if scale != 1:
            second.transformation = Transform().translate(dx / scale, 0)
    elif name in ("zero.tf.zero", "zero.tosf.zero"):
        if scale != 1:
            comp = glyph.components[0]
            base = layer[comp.baseGlyph]
            bounds = base.getBounds(layer)
            dx = comp.transformation.dx * scale - shifts[base.name]
            # The crossbar spans both inner walls of the extended zero. Its
            # ends lie just inside the outer walls, where they are hidden.
            inset = 0.025 * (bounds.xMax - bounds.xMin)
            set_bar(glyph.contours[0].points, dx+bounds.xMin+inset, dx+bounds.xMax-inset)
    elif name == "y.loclGUA":
        comp = glyph.components[0]
        base = layer[comp.baseGlyph]
        p = base.contours[0].points
        dx = comp.transformation.dx * scale - shifts[base.name]
        # Continue both parallel edges of the actual v down to its descender;
        # overlap at the vertex also protects the join during interpolation.
        leg = glyph.contours[0].points
        slope = (p[2].x - p[1].x) / (p[2].y - p[1].y)
        thickness_x = p[2].x - p[3].x
        for i, pt in enumerate(leg):
            if i >= 2:
                pt.y = p[1].y + 2
            pt.x = dx + p[1].x + slope * (pt.y-p[1].y)
            if i in (0, 3):
                pt.x -= thickness_x
    elif name in ("peso", "peso.BRACKET.varAlt01"):
        if scale != 1:
            comp = glyph.components[0]
            base = layer[comp.baseGlyph]
            bounds = base.getBounds(layer)
            dx = comp.transformation.dx * scale - shifts[base.name]
            # The P already preserves its sidebearings. Recover the overhangs
            # of the source bars and connect their inner ends to the walls.
            right_gain = base.width - glyph.width
            left = dx + min(pt.x for c in glyph.contours for pt in c.points)
            right = dx + max(pt.x for c in glyph.contours for pt in c.points) + right_gain
            outer, inner = (c.points for c in base.contours)
            right_join = dx + (inner[4].x + outer[4].x) / 2
            left_join = dx + (bounds.xMin + outer[0].x) / 2
            for i, c in enumerate(glyph.contours):
                if len(glyph.contours) == 2:
                    set_bar(c.points, left, right)
                elif i < 2:
                    set_bar(c.points, right_join, right)
                else:
                    set_bar(c.points, left, left_join)
    else:
        return False
    return True
