"""Capitals with shared reference strokes and width-specific optical corrections."""

from math import atan, hypot, pi, tan

from strokes import extend_rails


def extend_u(glyph, gain, bar, amount, angle=-1, weight=0.6):
    """Open both upper branches by the same angle about their inner junction."""
    if not gain:
        return
    p = glyph.contours[0].points
    top, fork_y = p[16].y, p[14].y
    rise = top - fork_y
    left_angle = atan((p[14].x - p[15].x) / rise)
    right_angle = atan((p[13].x - p[14].x) / rise)
    native_left = (p[15].x - p[16].x) / hypot(1, tan(left_angle))
    native_right = (p[12].x - p[13].x) / hypot(1, tan(right_angle))
    # Retain part of the original diagonal weight, especially in Black.
    fork_y += amount * (0.08 + 0.15 * angle) * (top - fork_y)
    rise = top - fork_y
    left = native_left + 0.72 * amount * (bar - native_left)
    right = native_right + 0.72 * amount * (bar - native_right)
    grade = 1 + 0.18 * amount * weight
    # The short branch ends in a flat ledge; give it a little less ink
    # than the continuous stroke that carries the eye down to the tail.
    left += amount * (0.94 * right - left)
    left *= grade
    right *= grade
    ledge = p[1].x - p[0].x
    right_x = p[12].x + gain
    lo, hi = 0, pi/2 - max(left_angle, right_angle)
    for _ in range(36):
        angle = (lo + hi) / 2
        a, b = tan(left_angle + angle), tan(right_angle + angle)
        dx_left, dx_right = left * hypot(1, a), right * hypot(1, b)
        if rise * (a + b) + dx_left + dx_right < right_x - p[16].x:
            lo = angle
        else:
            hi = angle

    # Slide the ledge up the fork until both endpoints are in order.
    fork_x = p[16].x + dx_left + rise * a
    ledge_y = fork_y - (dx_left - ledge) / (a + b)
    inner_x = right_x - dx_right
    outer_tail = right_x + b * (p[11].y - top) - p[11].x
    inner_tail = inner_x + b * (p[2].y - top) - p[2].x
    native_outer = (p[12].x - p[11].x) / (top - p[11].y)
    native_inner = (p[13].x - p[2].x) / (top - p[2].y)
    for pt in p[2:7]:
        pt.x += inner_tail
    for pt in p[8:12]:
        pt.x += outer_tail
    # The flat end can project farther without stretching the curved turn.
    p[6].x -= 0.055 * gain
    tail_rise = (p[6].y - p[7].y) * (grade - 1)
    for pt in p[4:7]:
        pt.y += tail_rise
    p[7].x = p[6].x
    p[3].x += (b - native_inner) * (p[3].y - p[2].y)
    # In Thin the native tail briefly doubles back through the little ledge.
    clearance = 10 if native_left < 55 else 2
    dy = min(0, ledge_y - clearance - p[2].y)
    for pt in p[2:4]:
        pt.y += dy
        pt.x += b * dy
    p[10].x += (b - native_outer) * (p[10].y - p[11].y)
    p[14].y = fork_y
    p[0].x, p[0].y = p[16].x + a * (top - ledge_y), ledge_y
    p[1].x, p[1].y = p[0].x + ledge, ledge_y
    p[12].x, p[13].x, p[14].x, p[15].x = right_x, inner_x, fork_x, p[16].x + dx_left


def extend_y_cap(glyph, gain):
    """Rotate Y's two arms about the shoulders of the upright."""
    p = glyph.contours[0].points
    top = p[8].y
    notch = p[5].x - p[6].x
    left_t = (p[7].x - p[8].x) / hypot(1, (p[9].x - p[8].x) / (top - p[9].y))
    right_t = (p[3].x - p[4].x) / hypot(1, (p[3].x - p[2].x) / (top - p[2].y))
    for i in (0, 1, 2, 9):
        p[i].x += gain / 2
    p[3].x += gain
    left = (p[9].x - p[8].x) / (top - p[9].y)
    right = (p[3].x - p[2].x) / (top - p[2].y)
    p[7].x = p[8].x + left_t * hypot(1, left)
    p[4].x = p[3].x - right_t * hypot(1, right)
    drop = (p[4].x - p[7].x - notch) / (left + right)
    p[5].x, p[6].x = p[4].x - right * drop, p[7].x + left * drop
    p[5].y = p[6].y = top - drop


def extend_iu(glyph, gain):
    """Keep the native stem-to-bowl gap. Put the full gain in the oval."""
    extend_rails(glyph, [[], [], [(5, 0), (11, 1)], [(5, 1), (11, 0)]], gain)


def extend_four(glyph, gain, bar, amount):
    outer, counter = [c.points for c in glyph.contours]
    slope = (outer[10].x - outer[0].x) / (outer[10].y - outer[0].y)
    native = (counter[2].x - outer[0].x - slope * (counter[2].y - outer[0].y)) / hypot(1, slope)
    for pt in outer[2:]:
        pt.x += gain
    for pt in counter[:2]:
        pt.x += gain
    slope = (outer[10].x - outer[0].x) / (outer[10].y - outer[0].y)
    weight = native + amount * 0.5 * (bar - native)
    counter[2].x = outer[0].x + slope * (counter[2].y - outer[0].y) + weight * hypot(1, slope)
    counter[0].y = counter[2].y + (counter[0].x - counter[2].x) / slope


def rounded_b(glyph, extra, stem, bar):
    outer, bottom, top = [c.points for c in glyph.contours]
    left = outer[18].x
    h = outer[16].y
    waist = (bottom[0].y + top[-1].y) / 2
    r = outer[3].x + extra
    u = outer[12].x + extra
    neck = u - 0.78 * stem
    # Only flat runs take additional width. Inner and outer corner radii
    # share their tangencies and retain P's stem and roof proportions.
    upper_radius = min(0.45 * (h - waist) + 0.42 * stem, 0.46 * (u - left))
    lower_radius = min(0.45 * waist + 0.42 * stem, 0.46 * (r - left))
    k = 0.69
    glyph.contours.clear()
    pen = glyph.getPen()
    pen.moveTo((left, 0))
    pen.lineTo((r - lower_radius, 0))
    mid = waist * 0.51
    pen.curveTo((r - lower_radius + k * lower_radius, 0), (r, mid * (1 - k)), (r, mid))
    pen.curveTo(
        (r, mid + k * (waist - mid)), (neck + k * (r - neck), waist), (neck, waist)
    )
    mid = waist + (h - waist) * 0.5
    pen.curveTo((neck + k * (u - neck), waist), (u, mid - k * (mid - waist)), (u, mid))
    pen.curveTo(
        (u, mid + k * (h - mid)),
        (u - upper_radius + k * upper_radius, h),
        (u - upper_radius, h),
    )
    pen.lineTo((left, h))
    pen.closePath()
    for xmax, radius, lo, hi in (
        (r, lower_radius, bar, waist - bar / 2),
        (u, upper_radius, waist + bar / 2, h - bar),
    ):
        xr = xmax - stem
        rad = max(12, radius - stem)
        xc = xr - rad
        yc = (lo + hi) / 2
        pen.moveTo((left + stem, lo))
        pen.lineTo((left + stem, hi))
        pen.lineTo((xc, hi))
        pen.curveTo((xc + k * rad, hi), (xr, yc + k * (hi - yc)), (xr, yc))
        pen.curveTo((xr, yc - k * (yc - lo)), (xc + k * rad, lo), (xc, lo))
        pen.closePath()


def quadratic_tail_span(glyph, start_index):
    # The stock tail segment has two quadratics. Using its original
    # subdivision in every master keeps cu2qu from changing the native outline
    # when the extended masters need a different approximation.
    p = glyph.contours[0].points
    start, first, second, end = p[start_index : start_index + 4]
    assert [first.type, second.type, end.type] == [None, None, "curve"]
    for handle, anchor in ((first, start), (second, end)):
        handle.x = anchor.x + 0.75 * (handle.x - anchor.x)
        handle.y = anchor.y + 0.75 * (handle.y - anchor.y)
    end.type = "qcurve"
