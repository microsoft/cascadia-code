import math
import subprocess
from pathlib import Path

import fontmake.instantiator
import fontTools.designspaceLib
import ufo2ft
import ufoLib2
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

        # 4. Creating NerdFont variants
        instanceNF = generator.generate_instance(instance_descriptor)  #rebuilding these instead of as a deepcopy avoids an error when compiling the TTF
        instancePL = generator.generate_instance(instance_descriptor)


        # 4.1 Modifying some attributes to correct the metadata
        setattr(instance.info,"openTypeOS2Panose",[2,11,6,9,2,0,0,2,0,4])
        setattr(instanceNF.info,"openTypeOS2Panose",[2,11,6,9,2,0,0,2,0,4])
        setattr(instancePL.info,"openTypeOS2Panose",[2,11,6,9,2,0,0,2,0,4])
        
        setattr(instance.info,"openTypeHheaAscender",instance.info.openTypeOS2TypoAscender)
        setattr(instance.info,"openTypeHheaDescender",instance.info.openTypeOS2TypoDescender)
        setattr(instance.info,"openTypeHheaLineGap",instance.info.openTypeOS2TypoLineGap)

        setattr(instanceNF.info,"openTypeHheaAscender",instanceNF.info.openTypeOS2TypoAscender)
        setattr(instanceNF.info,"openTypeHheaDescender",instanceNF.info.openTypeOS2TypoDescender)
        setattr(instanceNF.info,"openTypeHheaLineGap",instanceNF.info.openTypeOS2TypoLineGap)

        setattr(instancePL.info,"openTypeHheaAscender",instancePL.info.openTypeOS2TypoAscender)
        setattr(instancePL.info,"openTypeHheaDescender",instancePL.info.openTypeOS2TypoDescender)
        setattr(instancePL.info,"openTypeHheaLineGap",instancePL.info.openTypeOS2TypoLineGap)

        instanceNF.info.familyName = "Cascadia Code NL"
        instancePL.info.familyName = "Cascadia Code PL"

        #4.2 GET BACK TO WORK

        NF_UFO = ufoLib2.objects.font.Font.open(INPUT_DIR / "nerdfonts" / "NerdfontsNF.ufo")
        PL_UFO = ufoLib2.objects.font.Font.open(INPUT_DIR / "nerdfonts" / "NerdfontsPL.ufo")
        
        #4.5 Adding glyphs
        print ("Adding Nerd Font glyphs")
        for glyph in NF_UFO.glyphOrder:
            if glyph not in instanceNF.glyphOrder:
                instanceNF.addGlyph(NF_UFO.get(glyph))

        for glyph in PL_UFO.glyphOrder:
            if glyph not in instancePL.glyphOrder:
                instancePL.addGlyph(PL_UFO.get(glyph))

        # 5. Generate non-Ligature versions

        instance_noLIG = copy.deepcopy(instance)
        instanceNF_noLIG = copy.deepcopy(instanceNF)
        instancePL_noLIG = copy.deepcopy(instancePL)

        with open(INPUT_DIR / "features" / "features.fea", 'r') as feaCode:
            noLIG_fea = feaCode.read()

        instance_noLIG.features.text = noLIG_fea
        instanceNF_noLIG.features.text = noLIG_fea
        instancePL_noLIG.features.text = noLIG_fea

        instance_noLIG.info.familyName = "Cascadia Mono"
        instanceNF_noLIG.info.familyName = "Cascadia Mono NF"
        instancePL_noLIG.info.familyName = "Cascadia Mono PL"

        # 6. Compile all TTFs
        print ("Compiling")

        instance_font = ufo2ft.compileTTF(instance, removeOverlaps=True, inplace=True)
        instanceNF_font = ufo2ft.compileTTF(instanceNF, removeOverlaps=True, inplace=True)
        instancePL_font = ufo2ft.compileTTF(instancePL, removeOverlaps=True, inplace=True)

        instance_noLIG_font = ufo2ft.compileTTF(instance_noLIG, removeOverlaps=True, inplace=True)
        instanceNF_noLIG_font = ufo2ft.compileTTF(instanceNF_noLIG, removeOverlaps=True, inplace=True)
        instancePL_noLIG_font = ufo2ft.compileTTF(instancePL_noLIG, removeOverlaps=True, inplace=True)

        # 7. Save
        print ("Saving")
        OUTPUT_DIR.mkdir(exist_ok=True)
        instance_font.save(file_path.with_name("Cascadia.ttf"))
        instanceNF_font.save(file_path.with_name("CascadiaNF.ttf"))
        instancePL_font.save(file_path.with_name("CascadiaPL.ttf"))

        instance_noLIG_font.save(file_path.with_name("CascadiaMono.ttf"))
        instanceNF_noLIG_font.save(file_path.with_name("CascadiaMonoNF.ttf"))
        instancePL_noLIG_font.save(file_path.with_name("CascadiaMonoPL.ttf"))

        print ("All done")
        print ("*** *** *** *** *** *** *** *** *** *** *** *** *** *** *** *** *** ***")