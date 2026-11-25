"""Prepare 3.17 reference outlines for the discrete stroke inspector locations."""
import gzip
import json
import sys
from pathlib import Path

from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.ttLib import TTFont


def save_outlines(source, destination):
    font = TTFont(source)
    destination.mkdir(exist_ok=True)
    for weight in (100, 200, 300, 400, 500, 600, 650, 700, 800, 900):
        for width in (100, 107, 125):
            glyphs = font.getGlyphSet(location={"wght": weight, "wdth": width})
            paths = {}
            for name in font.getGlyphOrder():
                pen = SVGPathPen(glyphs, ntos=lambda x: str(round(x)))
                glyphs[name].draw(pen)
                paths[name] = pen.getCommands()
            file = destination / f"{weight}-{width}.json.gz"
            file.write_bytes(gzip.compress(json.dumps(paths, separators=(",", ":")).encode(), mtime=0))


if __name__ == "__main__":
    save_outlines(Path(sys.argv[1]), Path(sys.argv[2]))
