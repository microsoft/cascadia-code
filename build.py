from pathlib import Path

import fontmake.instantiator
import fontTools.designspaceLib
import ufo2ft
import vttLib

INPUT_DIR = Path("sources")
OUTPUT_DIR = Path("build")

# 1. Load Designspace and filter out instances that are marked as non-exportable.
designspace = fontTools.designspaceLib.DesignSpaceDocument.fromfile(
    INPUT_DIR / "CascadiaCode.designspace"
)
designspace.instances = [
    s for s in designspace.instances if s.lib.get("com.schriftgestaltung.export", True)
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
