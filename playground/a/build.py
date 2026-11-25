"""Rebuild the adjustable comparison using the archived pre-edit outline."""
import sys
from pathlib import Path

from fontTools.ttLib import TTFont

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT.parent))
from font.crossbar import APPROVED_THICKNESS, apply_crossbar
from a.export_font import export_font


if __name__ == "__main__":
    font = TTFont(ROOT / "before.woff2", recalcTimestamp=False)
    apply_crossbar(font, interactive=True)
    font.flavor = None
    font.save(ROOT / "after.ttf")
    (ROOT / "SovershenenPizdets-A-Study.ttf").write_bytes(export_font(0, APPROVED_THICKNESS))
