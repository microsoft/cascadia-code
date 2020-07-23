from pathlib import Path

import argparse
import copy
import os

import fontmake.instantiator
import fontTools.designspaceLib
import ufo2ft
import ufoLib2
import glyphsLib.interpolation
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


def build_font_instance(instance, *steps):
    if os.path.exists(OUTPUT_DIR / "static") == False:
        os.mkdir(OUTPUT_DIR / "static")

    for step in steps:
        step(instance)

    familyName = instance.info.familyName
    fontName = familyName +" "+instance.info.styleName

    file_stem = instance.info.familyName.replace(" ", "")

    for format in ["otf","ttf"]:

        set_font_metaData(instance, format)

        file_path = (OUTPUT_DIR / "static" / str(file_stem+"-"+instance.info.styleName)).with_suffix(f".{format}")

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

        print(f"[{fontName}] Saving")
        instance_font.save(file_path)

        print(f"[{fontName}] Done: {file_path}")

def build_variable_fonts(designspace, *steps):
    for font in [source.font for source in designspace.sources]:
        for step in steps:
            step(font)
        set_font_metaData(font, "var")

    familyName = designspace.default.font.info.familyName
    file_stem = familyName.replace(" ", "")
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

    # Disable variable OTF (CFF2) compilation until psautohint can better deal with overlaps: https://github.com/adobe-type-tools/psautohint/issues/40

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

    # Load Designspace and filter out instances that are marked as non-exportable.
    designspace = fontTools.designspaceLib.DesignSpaceDocument.fromfile(
        INPUT_DIR / "CascadiaCode.designspace"
    )
    designspace.instances = [
        s
        for s in designspace.instances
        if s.lib.get("com.schriftgestaltung.export", True)
    ]


    OUTPUT_DIR.mkdir(exist_ok=True)

    step_merge_pl = step_merge_glyphs_from_ufo(
        INPUT_DIR / "nerdfonts" / "NerdfontsPL-Regular.ufo"
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
        # Prepare masters for interpolation.
        generator = fontmake.instantiator.Instantiator.from_designspace(designspace)

        for instance_descriptor in designspace.instances:
            # Generate instances once.
            instance = generator.generate_instance(instance_descriptor)
            glyphsLib.interpolation.apply_instance_data_to_ufo(instance, instance_descriptor, designspace)

            build_font_instance(
                copy.deepcopy(instance),
                step_set_feature_file(INPUT_DIR / "features" / "features_code.fea"),
            )

            if not args.no_mono:
                build_font_instance(
                    copy.deepcopy(instance),
                    step_set_font_name("Cascadia Mono"),
                    step_set_feature_file(INPUT_DIR / "features" / "features_mono.fea"),
                )

            if not args.no_powerline:
                build_font_instance(
                    copy.deepcopy(instance),
                    step_set_font_name("Cascadia Code PL"),
                    step_set_feature_file(INPUT_DIR / "features" / "features_code_PL.fea"),
                    step_merge_pl,
                )

                if not args.no_mono:
                    build_font_instance(
                        copy.deepcopy(instance),
                        step_set_font_name("Cascadia Mono PL"),
                        step_set_feature_file(INPUT_DIR / "features" / "features_mono_PL.fea"),
                        step_merge_pl,
                    )

            if not args.no_nerdfonts:
                build_font_instance(
                    copy.deepcopy(instance),
                    step_set_font_name("Cascadia Code NF"),
                    step_merge_nf,
                )

                if not args.no_mono:
                    build_font_instance(
                        copy.deepcopy(instance),
                        step_set_font_name("Cascadia Mono NF"),
                        step_merge_nf,
                    )

    print ("*** *** *** Building Variable Fonts *** *** ***")

    designspace.loadSourceFonts(ufoLib2.Font.open, lazy=False)
    build_variable_fonts(
        copy.deepcopy(designspace), 
        step_set_feature_file(INPUT_DIR / "features" / "features_code.fea"),
    )

    if not args.no_mono:
        build_variable_fonts(
            copy.deepcopy(designspace),
            step_set_font_name("Cascadia Mono"),
            step_set_feature_file(INPUT_DIR / "features" / "features_mono.fea"),
        )

    if not args.no_powerline:
        build_variable_fonts(
            copy.deepcopy(designspace),
            step_set_font_name("Cascadia Code PL"),
            step_set_feature_file(INPUT_DIR / "features" / "features_code_PL.fea"),
            step_merge_pl,
        )

        if not args.no_mono:
            build_variable_fonts(
                copy.deepcopy(designspace),
                step_set_font_name("Cascadia Mono PL"),
                step_set_feature_file(INPUT_DIR / "features" / "features_mono_PL.fea"),
                step_merge_pl,
            )

    if not args.no_nerdfonts:
        build_variable_fonts(
            copy.deepcopy(designspace),
            step_set_font_name("Cascadia Code NF"),
            step_merge_nf,
        )

        if not args.no_mono:
            build_variable_fonts(
                copy.deepcopy(designspace),
                step_set_font_name("Cascadia Mono NF"),
                step_merge_nf,
            )


    if args.static_fonts == True:
        otfs = list(Path("build").glob("*.otf"))
        if otfs:
            for otf in otfs:
                path = os.fspath(otf)
                print(f"Autohinting {path}")
                subprocess.check_call(["psautohint", "--log", "build/log.txt", path])
                print(f"Compressing {path}")
                subprocess.check_call(["python", "-m", "cffsubr", "-i", path])

        try:
            ttfs = list(Path("build/static").glob("*.ttf"))
            if ttfs:
                for ttf in ttfs:
                    path = os.fspath(ttf)
                    if "-hinted" not in path:
                        print(f"Autohinting {ttf}")
                        subprocess.check_call(["ttfautohint", "--stem-width", "nsn","--reference","build/static/CascadiaCode-Regular.ttf", path, path[:-4]+"-hinted.ttf"])
                        os.remove(path)
                        os.rename(path[:-4]+"-hinted.ttf", path)
        except:
            print ("ttfautohint failed. Please reinstall and try again.")

    print("All done")
    print("*** *** *** *** *** *** *** *** *** *** *** *** *** *** *** *** *** ***")
