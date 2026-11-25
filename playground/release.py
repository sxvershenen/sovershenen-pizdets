"""Export the approved v4 tracking profile and letterforms as TTF and WOFF2."""

from io import BytesIO
from pathlib import Path

from fontTools.otlLib.builder import buildStatTable
from fontTools.ttLib import TTFont

from font.identity import set_identity
from optical import DEFAULT, build_font


def main():
    directory = Path(__file__).resolve().parent
    fonts = directory.parent / "fonts"
    master = directory / "font" / "lab.ttf"
    with TTFont(master) as source:
        shape = {
            axis.axisTag: axis.defaultValue for axis in source["fvar"].axes
            if axis.axisTag not in ("wght", "wdth")
        }
    profile = build_font(master, DEFAULT, shape)
    font = TTFont(BytesIO(profile), recalcTimestamp=False)
    set_identity(font, "Sovershenen Pizdets", version="4.002")
    # Only the three public axes are selectable in the installed release.
    buildStatTable(font, [
        {"tag": axis.axisTag, "name": axis.axisNameID}
        for axis in font["fvar"].axes
    ])
    for folder, extension in (("variable", "ttf"), ("webfonts", "woff2")):
        font.flavor = None if extension == "ttf" else "woff2"
        font.save(fonts / folder / ("SovershenenPizdetsV4." + extension))


if __name__ == "__main__":
    main()
