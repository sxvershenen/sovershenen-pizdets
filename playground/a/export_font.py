"""Pin the two a-crossbar controls while retaining the release axes."""
from io import BytesIO
from pathlib import Path

from fontTools.otlLib.builder import buildStatTable
from fontTools.ttLib import TTFont
from fontTools.varLib.instancer import instantiateVariableFont
from font.identity import set_identity


def export_font(height, thickness):
    if type(height) is not int or not -16 <= height <= 16:
        raise ValueError("Высота вне диапазона")
    if type(thickness) is not int or not 85 <= thickness <= 115:
        raise ValueError("Толщина вне диапазона")
    font = TTFont(Path(__file__).with_name("after.ttf"), recalcTimestamp=False)
    instantiateVariableFont(font, {"ABHT": height, "ABWT": thickness}, inplace=True)
    set_identity(font, "Sovershenen Pizdets v4 A Study")
    buildStatTable(font, [{"tag": a.axisTag, "name": a.axisNameID} for a in font["fvar"].axes])
    buf = BytesIO()
    font.save(buf)
    return buf.getvalue()
