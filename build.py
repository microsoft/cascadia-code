from pathlib import Path

import argparse
import os

import fontmake.instantiator
import fontTools.designspaceLib
import ufo2ft
import ufoLib2
import vttLib
import sys
import subprocess
from statmake import lib, classes

INPUT_DIR = Path("sources")
OUTPUT_DIR = Path("build")
VTT_DATA_FILE = INPUT_DIR / "vtt_data" / "CascadiaCode.ttx"


def step_set_font_name(n):
    def _set(instance):
        instance.info.familyName = n
        # We have to change the style map family name because that's what
        # Windows uses to map Bold/Regular/Medium/etc. fonts
        instance.info.styleMapFamilyName = n

    return _set


def step_merge_glyphs_from_ufo(path):
    def _merge(instance):
        ufo = ufoLib2.Font.open(path)
        print(f"[{instance.info.familyName} {instance.info.styleName}] Merging {path}")
        for glyph in ufo.glyphOrder:
            if glyph not in instance.glyphOrder:
                instance.addGlyph(ufo[glyph])

    return _merge


def step_set_feature_file(n):
    fea = n.read_text()

    def _set(instance):
        instance.features.text = fea

    return _set


def build_font_instance(generator, instance_descriptor, *steps):
    for format in ["otf"]: # removed TTF from here
        instance = generator.generate_instance(instance_descriptor)

        for step in steps:
            step(instance)

        familyName = instance.info.familyName
        fontName = familyName +" "+instance.info.styleName

        file_stem = instance.info.familyName.replace(" ", "")
        file_path = (OUTPUT_DIR / str(file_stem+"-"+instance.info.styleName)).with_suffix(f".{format}")

        print(f"[{fontName}] Compiling")
        if format == "ttf":
            instance_font = ufo2ft.compileTTF(instance, removeOverlaps=True, inplace=True)
        else:
            # Do not optimize, because we have to do it again after autohinting.
            instance_font = ufo2ft.compileOTF(
                instance,
                removeOverlaps=True,
                inplace=True,
                optimizeCFF=ufo2ft.CFFOptimization.NONE
            )

        if format == "ttf":
            print(f"[{fontName}] Merging VTT")
            vttLib.transfer.merge_from_file(instance_font, VTT_DATA_FILE)

        print(f"[{fontName}] Saving")
        instance_font.save(file_path)

        print(f"[{fontName}] Done: {file_path}")

def build_variable_fonts(designspace, *steps):

    sourceFonts = [ufoLib2.Font.open(INPUT_DIR / designspace.sources[0].filename), ufoLib2.Font.open(INPUT_DIR / designspace.sources[1].filename), ufoLib2.Font.open(INPUT_DIR / designspace.sources[2].filename)]

    designspace.sources[0].font = sourceFonts[0] #ExtraLight
    designspace.sources[1].font = sourceFonts[1] #Regular
    designspace.sources[2].font = sourceFonts[2] #Bold

    for font in sourceFonts:
        for step in steps:
            step(font)

    familyName = sourceFonts[1].info.familyName

    file_stem = sourceFonts[1].info.familyName.replace(" ", "")
    file_path = (OUTPUT_DIR / file_stem).with_suffix(f".ttf")

    print(f"[{familyName}] Compiling")
    varFont = ufo2ft.compileVariableTTF(designspace)

    print(f"[{familyName}] Adding STAT table")

    styleSpace = classes.Stylespace.from_file(INPUT_DIR / "STAT.plist")
    lib.apply_stylespace_to_variable_font(styleSpace,varFont,{})

    print(f"[{familyName}] Merging VTT")
    vttLib.transfer.merge_from_file(varFont, VTT_DATA_FILE)

    print(f"[{familyName}] Saving")
    varFont.save(file_path)

    print(f"[{familyName}] Done: {file_path}")

    # XXX: Disable variable OTF (CFF2) compilation until psautohint can better
    #      deal with overlaps: https://github.com/adobe-type-tools/psautohint/issues/40
    
    # print(f"[{familyName}] Compiling CFF2")
    # file_path_cff2 = (OUTPUT_DIR / file_stem).with_suffix(f".otf")
    # # Do not optimize, because we have to do it again after autohinting.
    # varFontCFF2 = ufo2ft.compileVariableCFF2(
    #    designspace,
    #    inplace=True,  # Can compile in-place because `designspace` won't be reused here.
    #    useProductionNames=True,
    #    optimizeCFF=ufo2ft.CFFOptimization.NONE,
    # )

    # print(f"[{familyName}] Adding STAT table")
    # lib.apply_stylespace_to_variable_font(styleSpace,varFontCFF2,{})

    # print(f"[{familyName}] Saving")
    # varFontCFF2.save(file_path_cff2)

    # print(f"[{familyName}] Done: {file_path_cff2}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="build some fonts")
    parser.add_argument("-N", "--no-nerdfonts", default=False, action="store_true")
    parser.add_argument("-P", "--no-powerline", default=False, action="store_true")
    parser.add_argument("-M", "--no-mono", default=False, action="store_true")
    parser.add_argument("-S", "--static-fonts", default=False, action="store_true")
    args = parser.parse_args()

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

    OUTPUT_DIR.mkdir(exist_ok=True)

    step_merge_pl = step_merge_glyphs_from_ufo(
        INPUT_DIR / "nerdfonts" / "NerdfontsPL.ufo"
    )

    nf_path = INPUT_DIR / "nerdfonts" / "NerdfontsNF.ufo"
    if not nf_path.exists():
        args.no_nerdfonts = True  # No NF = don't try to build those fonts.

    step_merge_nf = None
    if not args.no_nerdfonts:
        step_merge_nf = step_merge_glyphs_from_ufo(
            INPUT_DIR / "nerdfonts" / "NerdfontsNF.ufo"
        )

    if args.static_fonts == True:
        for instance_descriptor in designspace.instances:

            build_font_instance(
                generator, 
                instance_descriptor,
                step_set_feature_file(INPUT_DIR / "features" / "features_code.fea"),
            )

            if not args.no_mono:
                build_font_instance(
                    generator,
                    instance_descriptor,
                    step_set_font_name("Cascadia Mono"),
                    step_set_feature_file(INPUT_DIR / "features" / "features_mono.fea"),
                )

            if not args.no_powerline:
                build_font_instance(
                    generator,
                    instance_descriptor,
                    step_set_font_name("Cascadia Code PL"),
                    step_set_feature_file(INPUT_DIR / "features" / "features_code_PL.fea"),
                    step_merge_pl,
                )

                if not args.no_mono:
                    build_font_instance(
                        generator,
                        instance_descriptor,
                        step_set_font_name("Cascadia Mono PL"),
                        step_set_feature_file(INPUT_DIR / "features" / "features_mono_PL.fea"),
                        step_merge_pl,
                    )

            if not args.no_nerdfonts:
                build_font_instance(
                    generator,
                    instance_descriptor,
                    step_set_font_name("Cascadia Code NF"),
                    step_merge_nf,
                )

                if not args.no_mono:
                    build_font_instance(
                        generator,
                        instance_descriptor,
                        step_set_font_name("Cascadia Mono NF"),
                        step_merge_nf,
                    )

    print ("*** *** *** Building Variable Fonts *** *** ***")

    build_variable_fonts(
        designspace, 
        step_set_feature_file(INPUT_DIR / "features" / "features_code.fea"),
    )

    if not args.no_mono:
        build_variable_fonts(
            designspace,
            step_set_font_name("Cascadia Mono"),
            step_set_feature_file(INPUT_DIR / "features" / "features_mono.fea"),
        )

    if not args.no_powerline:
        build_variable_fonts(
            designspace,
            step_set_font_name("Cascadia Code PL"),
            step_set_feature_file(INPUT_DIR / "features" / "features_code_PL.fea"),
            step_merge_pl,
        )

        if not args.no_mono:
            build_variable_fonts(
                designspace,
                step_set_font_name("Cascadia Mono PL"),
                step_set_feature_file(INPUT_DIR / "features" / "features_mono_PL.fea"),
                step_merge_pl,
            )

    if not args.no_nerdfonts:
        build_variable_fonts(
            designspace,
            step_set_font_name("Cascadia Code NF"),
            step_merge_nf,
        )

        if not args.no_mono:
            build_variable_fonts(
                designspace,
                step_set_font_name("Cascadia Mono NF"),
                step_merge_nf,
            )

    otfs = list(Path("build").glob("*.otf"))
    if otfs:
        for otf in otfs:
            path = os.fspath(otf)
            print(f"Autohinting {path}")
            subprocess.check_call(["psautohint", "--log", "build/log.txt", path])
            print(f"Compressing {path}")
            subprocess.check_call(["python", "-m", "cffsubr", "-i", path])

    print("All done")
    print("*** *** *** *** *** *** *** *** *** *** *** *** *** *** *** *** *** ***")
