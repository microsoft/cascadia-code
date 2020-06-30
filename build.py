from pathlib import Path

import argparse

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

def set_font_metaData(font, sort):
    font.info.versionMajor = 2007
    font.info.versionMinor = 1

    font.info.openTypeOS2Panose = [2, 11, 6, 9, 2, 0, 0, 2, 0, 4]

    font.info.openTypeOS2TypoAscender = 1900
    font.info.openTypeOS2TypoDescender = -480
    font.info.openTypeOS2TypoLineGap = 0

    font.info.openTypeHheaAscender = font.info.openTypeOS2TypoAscender
    font.info.openTypeHheaDescender = font.info.openTypeOS2TypoDescender
    font.info.openTypeHheaLineGap = font.info.openTypeOS2TypoLineGap

    font.info.openTypeOS2WinAscent = 2226
    font.info.openTypeOS2WinDescent = abs(font.info.openTypeOS2TypoDescender)

    if sort != "otf":
        font.info.openTypeGaspRangeRecords =[
            {
                "rangeMaxPPEM" : 9,
                "rangeGaspBehavior" : [1,3]
            },
            {
                "rangeMaxPPEM" : 50,
                "rangeGaspBehavior" : [0,1,2,3]
            },
            {
                "rangeMaxPPEM" : 65535,
                "rangeGaspBehavior" : [1,3]
            },
        ]

def build_font_instance(generator, instance_descriptor, *steps):
    for format in ["otf"]: # removed TTF from here
        instance = generator.generate_instance(instance_descriptor)

        for step in steps:
            step(instance)


        set_font_metaData(instance, format)

        familyName = instance.info.familyName
        fontName = familyName +" "+instance.info.styleName

        file_stem = instance.info.familyName.replace(" ", "")
        file_path = (OUTPUT_DIR / str(file_stem+"-"+instance.info.styleName)).with_suffix(f".{format}")

        print(f"[{fontName}] Compiling")
        if format == "ttf":
            instance_font = ufo2ft.compileTTF(instance, removeOverlaps=True, inplace=True)
        else:
            instance_font = ufo2ft.compileOTF(instance, removeOverlaps=True, inplace=True)

        if format == "ttf":
            print(f"[{fontName}] Merging VTT")
            vttLib.transfer.merge_from_file(instance_font, VTT_DATA_FILE)

        print(f"[{fontName}] Saving")
        instance_font.save(file_path)

        print(f"[{fontName}] Done: {file_path}")

def build_variable_fonts(designspace, *steps):

    sourceFonts = [ufoLib2.Font.open(INPUT_DIR / designspace.sources[0].filename), ufoLib2.Font.open(INPUT_DIR / designspace.sources[1].filename), ufoLib2.Font.open(INPUT_DIR / designspace.sources[2].filename)]

    for source in sourceFonts:
        set_font_metaData(source, "var")

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
                        step_remove_ligatures,
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
                step_remove_ligatures,
                step_merge_nf,
            )

    if args.static_fonts == True:
        print("Autohinting OTFs")
        for file in Path("build").glob("*.otf"):
            subprocess.run(['psautohint --log "build/log.txt" '+str(file)], shell=True)

    print("All done")
    print("*** *** *** *** *** *** *** *** *** *** *** *** *** *** *** *** *** ***")
