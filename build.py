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
    font.info.versionMajor = 2009
    font.info.versionMinor = 14

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

def overlapFlag(varFont):
    
    tt = varFont
    glyf = tt["glyf"]

    for glyph_name in glyf.keys():
        glyph = glyf[glyph_name]
        # Set OVERLAP_COMPOUND bit for compound glyphs
        if glyph.isComposite():
            glyph.components[0].flags |= 0x400
        # Set OVERLAP_SIMPLE bit for simple glyphs
        elif glyph.numberOfContours > 0:
            glyph.flags[0] |= 0x40
    return tt


def build_fonts(designspace, static, *steps):
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

    varFont = overlapFlag(varFont)

    print(f"[{familyName}] Saving")
    varFont.save(file_path)

    print(f"[{familyName}] Done: {file_path}")

    if static:
        generator = fontmake.instantiator.Instantiator.from_designspace(designspace)
        print(f"[{familyName}] Building static instances")
        for instance_descriptor in designspace.instances:
            instance = generator.generate_instance(instance_descriptor)
            print(f"[{familyName}] "+instance.info.styleName)
            instance = generator.generate_instance(instance_descriptor)
            staticTTF = ufo2ft.compileTTF(instance,removeOverlaps=True)
            staticOTF = ufo2ft.compileOTF(instance,removeOverlaps=True)

            file_name = file_stem+"-"+instance.info.styleName

            file_path_static = (OUTPUT_DIR / "static" / file_name).with_suffix(f".ttf")
            file_path_static_otf = (OUTPUT_DIR / "static" / file_name).with_suffix(f".otf")

            staticTTF.save(file_path_static)
            staticOTF.save(file_path_static_otf)

        print(f"[{familyName}] Done building static instances")


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

    print ("*** *** *** Building Variable Fonts *** *** ***")

    designspace.loadSourceFonts(ufoLib2.Font.open, lazy=False)
    build_fonts(
        copy.deepcopy(designspace), 
        args.static_fonts,
        step_set_feature_file(INPUT_DIR / "features" / "features_code.fea"),
    )

    if not args.no_mono:
        build_fonts(
            copy.deepcopy(designspace),
            args.static_fonts,
            step_set_font_name("Cascadia Mono"),
            step_set_feature_file(INPUT_DIR / "features" / "features_mono.fea"),
        )

    if not args.no_powerline:
        build_fonts(
            copy.deepcopy(designspace),
            args.static_fonts,
            step_set_font_name("Cascadia Code PL"),
            step_set_feature_file(INPUT_DIR / "features" / "features_code_PL.fea"),
            step_merge_pl,
        )

        if not args.no_mono:
            build_fonts(
                copy.deepcopy(designspace),
                args.static_fonts,
                step_set_font_name("Cascadia Mono PL"),
                step_set_feature_file(INPUT_DIR / "features" / "features_mono_PL.fea"),
                step_merge_pl,
            )

    if not args.no_nerdfonts:
        build_fonts(
            copy.deepcopy(designspace),
            args.static_fonts,
            step_set_font_name("Cascadia Code NF"),
            step_merge_nf,
        )

        if not args.no_mono:
            build_fonts(
                copy.deepcopy(designspace),
                args.static_fonts,
                step_set_font_name("Cascadia Mono NF"),
                step_merge_nf,
            )

    print("All done")
    print("*** *** *** *** *** *** *** *** *** *** *** *** *** *** *** *** *** ***")


    if args.static_fonts == True:
    
        print ("*** *** *** Autohinting Static Fonts *** *** ***")

        otfs = list(Path("build/static").glob("*.otf"))
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