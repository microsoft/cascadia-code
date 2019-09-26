from pathlib import Path

import ufoLib2

for ufo_path in (Path(__file__).parent.parent / "sources").glob("*.ufo"):
    ufo = ufoLib2.Font.open(ufo_path)

    for layer in ufo.layers:
        for glyph in layer:
            if "com.schriftgestaltung.Glyphs.lastChange" in glyph.lib:
                # Not necessary when using Git.
                del glyph.lib["com.schriftgestaltung.Glyphs.lastChange"]

    ufo.save()
