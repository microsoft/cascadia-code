import math
import subprocess
from pathlib import Path

import fontmake.instantiator
import fontTools.designspaceLib
import ufo2ft
import ufoLib2
import vttLib

INPUT_DIR = Path("sources")
OUTPUT_DIR = Path("build")


def expand_ligature_width(ufo: ufoLib2.Font):
    def glyph_add_lsb(glyph: ufoLib2.objects.Glyph, lsb_diff: int):
        for contour in glyph.contours:
            for point in contour:
                point.x += lsb_diff
        for component in glyph.components:
            # Some components have a scale of -1, which means we have to
            # translate in the opposite direction.
            component_scale = component.transformation[0]
            lsb_diff_adjusted = math.copysign(lsb_diff, component_scale)
            component.transformation = component.transformation.translate(
                lsb_diff_adjusted, 0
            )
        glyph.width += lsb_diff

    for glyph in ufo:
        if glyph.markColor == "0.97,1,0,1":  # Glyphs color 3, 2x width
            glyph_add_lsb(glyph, 1200)
        elif glyph.markColor == "0.67,0.95,0.38,1":  # Glyphs color 4, 3x width
            glyph_add_lsb(glyph, 2400)
        elif glyph.markColor == "0.98,0.36,0.67,1":  # Glyphs color 9, 4x width
            glyph_add_lsb(glyph, 3600)


if __name__ == "__main__":
    # 1. Load Designspace and filter out instances that are marked as non-exportable.
    designspace = fontTools.designspaceLib.DesignSpaceDocument.fromfile(
        INPUT_DIR / "CascadiaCode.designspace"
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
        file_name = f"{instance.info.familyName}-{instance.info.styleName}.ttf".replace(
            " ", ""
        )
        file_path = OUTPUT_DIR / file_name

        # 3.1 Expand ligatures to their intended width
        expand_ligature_width(instance)

        # 3.5. Optionally write instance UFO to disk, for debugging.
        # instance.save(file_path.with_suffix(".ufo"), overwrite=True)

        # 4. Compile instance TTF.
        instance_font = ufo2ft.compileTTF(instance, removeOverlaps=True, inplace=True)

        # 5. Import VTT hinting data, must be precompiled by VTT.
        vtt_data_file = (INPUT_DIR / "vtt_data" / file_name).with_suffix(".ttx")
        vttLib.transfer.merge_from_file(instance_font, vtt_data_file)
        vttLib.compile_instructions(instance_font, ship=True)

        # 6. Save
        OUTPUT_DIR.mkdir(exist_ok=True)
        instance_font.save(file_path)

        # 7. Optionally produce OTF and hint with psautohint
        instance_font_otf = ufo2ft.compileOTF(
            instance, removeOverlaps=True, inplace=True
        )
        file_path_otf = file_path.with_suffix(".otf")
        instance_font_otf.save(file_path_otf)
        subprocess.run(["psautohint", str(file_path_otf)])
