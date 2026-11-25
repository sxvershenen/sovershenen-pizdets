"""Build an optical-spacing axis from editable (CSS px, thousandths of em) knots."""
from io import BytesIO
from math import isfinite

from fontTools.misc.roundTools import otRound
from fontTools.ttLib import TTFont, newTable
from fontTools.ttLib.tables import otTables as ot
from fontTools.ttLib.tables._f_v_a_r import Axis
from fontTools.ttLib.tables.TupleVariation import TupleVariation
from fontTools.varLib import builder
from fontTools.varLib.instancer import instantiateVariableFont

DEFAULT = [[8, 54], [12, 38], [24, 20], [48, 0]]
ZHE_AXES = ('ZEXT', 'ZANG', 'ZWGT')
U_AXES = ('UANG', 'UWGT')


def validated_points(raw):
    if not isinstance(raw, list) or not 2 <= len(raw) <= 16:
        raise ValueError('Нужно от 2 до 16 точек.')
    result = []
    for pair in raw:
        if not isinstance(pair, list) or len(pair) != 2:
            raise ValueError('У точки должны быть размер и трекинг.')
        px, track = pair
        if not all(type(x) in (int, float) and isfinite(x) for x in pair):
            raise ValueError('Введите числовые значения.')
        if not (6 <= px <= 200 and px == int(px) and -80 <= track <= 1000):
            raise ValueError('Размер 6–200 целых px, трекинг от −80 до 1000 ‰ em.')
        result.append((int(px), track))
    result.sort()
    if len(set(px for px, _ in result)) != len(result):
        raise ValueError('Размеры точек должны различаться.')
    return result


def spacing(points, px):
    if px <= points[0][0]:
        return points[0][1]
    for (a, v), (b, w) in zip(points, points[1:]):
        if px <= b:
            return v + (w - v) * (px - a) / (b - a)
    return points[-1][1]


def add_axis(font, bounds):
    fvar = font['fvar']
    # gvar decoding needs the original axis count.
    variations = font['gvar'].variations
    for name in list(variations):
        _ = variations[name]
    axis = Axis()
    axis.axisTag = 'opsz'
    axis.minValue, axis.defaultValue, axis.maxValue = bounds
    axis.axisNameID = font['name'].addName('Optical Size')
    fvar.axes.append(axis)
    for instance in fvar.instances:
        instance.coordinates['opsz'] = axis.defaultValue
    if 'avar' in font:
        font['avar'].segments['opsz'] = {-1: -1, 0: 0, 1: 1}
    if 'STAT' in font:
        stat = font['STAT'].table
        record = ot.AxisRecord()
        record.AxisTag, record.AxisNameID = 'opsz', axis.axisNameID
        record.AxisOrdering = max(a.AxisOrdering for a in stat.DesignAxisRecord.Axis) + 1
        stat.DesignAxisRecord.Axis.append(record)
        stat.DesignAxisCount = len(stat.DesignAxisRecord.Axis)
    for tag in ('HVAR', 'VVAR', 'MVAR', 'GDEF', 'BASE', 'COLR'):
        if tag in font and (store := getattr(font[tag].table, 'VarStore', None)):
            regions = store.VarRegionList
            for region in regions.Region:
                region.VarRegionAxis.append(builder.buildVarRegionAxis((0, 0, 0)))
            regions.RegionAxisCount += 1


def extend_hvar(font, supports, deltas_by_name):
    tags = [a.axisTag for a in font['fvar'].axes]
    names = font.getGlyphOrder()
    if 'HVAR' not in font:
        table = ot.HVAR()
        table.Version = 0x10000
        table.AdvWidthMap = table.LsbMap = table.RsbMap = None
        table.VarStore = builder.buildVarStore(builder.buildVarRegionList([], tags),
                                                [builder.buildVarData([], [[] for _ in names])])
        font['HVAR'] = newTable('HVAR')
        font['HVAR'].table = table
    table = font['HVAR'].table
    store = table.VarStore
    regions = store.VarRegionList
    first = len(regions.Region)
    regions.Region.extend(builder.buildVarRegion(s, tags) for s in supports)
    regions.RegionCount = len(regions.Region)
    extra = list(range(first, regions.RegionCount))
    groups, entries = {}, []
    for gid, name in enumerate(names):
        idx = table.AdvWidthMap.mapping[name] if table.AdvWidthMap else gid
        if idx == 0xffffffff:
            indices, values = (), ()
        else:
            data = store.VarData[idx >> 16]
            indices, values = tuple(data.VarRegionIndex), tuple(data.Item[idx & 65535])
        group = groups.setdefault(indices, {})
        entry = values + deltas_by_name[name]
        inner = group.setdefault(entry, len(group))
        entries.append((indices, inner))
    outer = {}
    for indices, items in groups.items():
        outer[indices] = len(store.VarData)
        store.VarData.append(builder.buildVarData(list(indices) + extra, list(items)))
    store.VarDataCount = len(store.VarData)
    table.AdvWidthMap = builder.buildVarIdxMap([(outer[indices] << 16) + i for indices, i in entries], names)


def build_font(path, points, shape=None):
    font = TTFont(path, recalcTimestamp=False)
    if shape:
        if not set(ZHE_AXES) <= set(shape) <= set(ZHE_AXES + U_AXES) or not all(type(x) in (float, int) and isfinite(x) and 0 <= x <= 100 for x in shape.values()):
            raise ValueError('Параметры Жж и У должны быть в диапазоне от 0 до 100.')
        shape = {**{a.axisTag: a.defaultValue for a in font["fvar"].axes if a.axisTag in U_AXES}, **shape}
        font = instantiateVariableFont(font, shape, inplace=True)
    # The default is a knot so the response remains exactly piecewise linear.
    lo, hi = points[0][0], points[-1][0]
    default = max(lo, min(16, hi))
    sizes = sorted(set([default, *(px for px, _ in points)]))
    def normalized(px):
        if px == default:
            return 0
        return (px - default) / ((default - lo) if px < default else (hi - default))
    supports = []
    for i, px in enumerate(sizes):
        if px != default:
            neighbors = (sizes[max(0, i-1)], px, sizes[min(i+1, len(sizes)-1)])
            supports.append({'opsz': tuple(map(normalized, neighbors))})
    # Chromium auto optical sizing selects the numeric CSS pixel size.
    add_axis(font, (lo, default, hi))
    upm = font['head'].unitsPerEm
    glyf, metrics = font['glyf'], font['hmtx'].metrics
    gd = font['GDEF'].table if 'GDEF' in font else None
    classes = getattr(getattr(gd, 'GlyphClassDef', None), 'classDefs', {})
    deltas = {}
    for name in font.getGlyphOrder():
        advance, lsb = metrics[name]
        tracked = advance > 0 and classes.get(name) != 3
        def offset(px):
            return max(-advance, otRound(spacing(points, px) * upm / 1000)) if tracked else 0
        base = offset(default)
        metrics[name] = (advance + base, lsb)
        values = tuple(offset(px) - base for px in sizes if px != default)
        deltas[name] = values
        if any(values):
            glyph = glyf[name]
            count = len(glyph.components) if glyph.isComposite() else len(getattr(glyph, 'coordinates', []))
            for support, value in zip(supports, values):
                if value:
                    # Unspecified outline points all infer zero. Keep the left phantom fixed.
                    coords = [None] * count + [(0, 0), (value, 0), None, None]
                    font['gvar'].variations.setdefault(name, []).append(TupleVariation(support, coords))
    extend_hvar(font, supports, deltas)
    buf = BytesIO()
    font.save(buf)
    return buf.getvalue()
