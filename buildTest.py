import math
import subprocess
from pathlib import Path

import fontmake.instantiator
import fontTools.designspaceLib
from fontParts.base import *
from fontParts.world import *
import vttLib
import copy

INPUT_DIR = Path("sources")
OUTPUT_DIR = Path("build")

if __name__ == "__main__":
    # 1. Load Designspace and filter out instances that are marked as non-exportable.
    designspace = fontTools.designspaceLib.DesignSpaceDocument.fromfile(
        INPUT_DIR / "CascadiaCode-Regular.designspace"
    )
    designspace.instances = [
        s
        for s in designspace.instances
        if s.lib.get("com.schriftgestaltung.export", True)
    ]

    # 2. Prepare masters.
    generator = fontmake.instantiator.Instantiator.from_designspace(designspace)

    for instance_descriptor in designspace.instances:
        # 3. Generate instance UFO.
        instance = generator.generate_instance(instance_descriptor)
        print ("Creating instance",instance.info.familyName, instance.info.styleName)
        file_name = f"{instance.info.familyName}.ttf".replace(
            " ", ""
        )
        file_path = OUTPUT_DIR / file_name
        file_pathNF = OUTPUT_DIR / "CascadiaNF.ttf"
        file_pathPL = OUTPUT_DIR / "CascadiaPL.ttf"

        instance.save("temp.ufo",overwrite=True)

        # 4. Creating NerdFont variants

        source = OpenFont("temp.ufo", showInterface=False)
        NF_UFO = OpenFont("sources/nerdfonts/NerdfontsNF.ufo", showInterface=False)
        PL_UFO = OpenFont("sources/nerdfonts/NerdfontsNF.ufo", showInterface=False)

        instanceNF = source.copy()
        instancePL = source.copy()

        # Adding glyphs
        print ("Adding Nerd Font glyphs")
        for glyph in NF_UFO.glyphOrder:
            if glyph in instanceNF.glyphOrder:
                pass
            else:
                instanceNF.insertGlyph(NF_UFO.defaultLayer[glyph].copy())
            print (NF_UFO.defaultLayer[glyph])

        for glyph in PL_UFO.glyphOrder:
            if glyph in instancePL.glyphOrder:
                pass
            else:
                instancePL.insertGlyph(PL_UFO.defaultLayer[glyph].copy())

        # 5. Generate non-Ligature versions

        # 6. Compile all TTFs
        print ("Compiling")
#        instance_font = ufo2ft.compileTTF(instance, removeOverlaps=True, inplace=True)
#        instanceNF_font = ufo2ft.compileTTF(instanceNF, removeOverlaps=True, inplace=True)
#        instancePL_font = ufo2ft.compileTTF(instancePL, removeOverlaps=True, inplace=True)

        # 7. Save
        print ("Saving")
#        OUTPUT_DIR.mkdir(exist_ok=True)
#        instance_font.save(file_path.with_name("Cascadia.ttf"))
#        instanceNF_font.save(file_path.with_name("CascadiaNF.ttf"))
#        instancePL_font.save(file_path.with_name("CascadiaPL.ttf"))

        print ("All done")
        print ("*** *** *** *** *** *** *** *** *** *** *** *** *** *** *** *** *** ***")