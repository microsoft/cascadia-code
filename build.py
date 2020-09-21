import argparse
import multiprocessing
import multiprocessing.pool
import os
import subprocess
from pathlib import Path
from typing import cast

import cffsubr.__main__
import fontmake.instantiator
import fontTools.designspaceLib
import fontTools.ttLib
import fontTools.ttLib.tables._g_l_y_f as _g_l_y_f
import psautohint.__main__
import statmake.classes
import statmake.lib
import ufo2ft
import ufoLib2
import vttLib.transfer

INPUT_DIR = Path("sources")
OUTPUT_DIR = Path("build")
OUTPUT_STATIC_DIR = OUTPUT_DIR / "static"
VTT_DATA_FILE = INPUT_DIR / "vtt_data" / "CascadiaCode.ttx"
FEATURES_DIR = INPUT_DIR / "features"
NERDFONTS_DIR = INPUT_DIR / "nerdfonts"

# Font modifications
# ****************************************************************


def step_set_font_name(name: str, instance: ufoLib2.Font) -> None:
    instance.info.familyName = name
    # We have to change the style map family name because that's what
    # Windows uses to map Bold/Regular/Medium/etc. fonts
    instance.info.styleMapFamilyName = name


def step_merge_glyphs_from_ufo(path: Path, instance: ufoLib2.Font) -> None:
    ufo = ufoLib2.Font.open(path)
    for glyph in ufo.glyphOrder:
        if glyph not in instance.glyphOrder:
            instance.addGlyph(ufo[glyph])


def step_set_feature_file(path: Path, instance: ufoLib2.Font) -> None:
    instance.features.text = path.read_text()


def set_font_metaData(font: ufoLib2.Font) -> None:
    font.info.versionMajor = 2009
    font.info.versionMinor = 21

    font.info.openTypeOS2TypoAscender = 1900
    font.info.openTypeOS2TypoDescender = -480
    font.info.openTypeOS2TypoLineGap = 0

    font.info.openTypeHheaAscender = font.info.openTypeOS2TypoAscender
    font.info.openTypeHheaDescender = font.info.openTypeOS2TypoDescender
    font.info.openTypeHheaLineGap = font.info.openTypeOS2TypoLineGap

    font.info.openTypeOS2WinAscent = 2226
    font.info.openTypeOS2WinDescent = abs(font.info.openTypeOS2TypoDescender)

    font.info.openTypeGaspRangeRecords = [
        {"rangeMaxPPEM": 9, "rangeGaspBehavior": [1, 3]},
        {"rangeMaxPPEM": 50, "rangeGaspBehavior": [0, 1, 2, 3]},
        {"rangeMaxPPEM": 65535, "rangeGaspBehavior": [1, 3]},
    ]


def set_overlap_flag(varfont: fontTools.ttLib.TTFont) -> fontTools.ttLib.TTFont:
    glyf = cast(_g_l_y_f.table__g_l_y_f, varfont["glyf"])
    for glyph_name in glyf.keys():
        glyph = glyf[glyph_name]
        if glyph.isComposite():
            # Set OVERLAP_COMPOUND bit for compound glyphs
            glyph.components[0].flags |= 0x400
        elif glyph.numberOfContours > 0:
            # Set OVERLAP_SIMPLE bit for simple glyphs
            glyph.flags[0] |= 0x40

    return varfont


def prepare_fonts(
    designspace: fontTools.designspaceLib.DesignSpaceDocument, name: str
) -> None:
    designspace.loadSourceFonts(ufoLib2.Font.open)
    for source in designspace.sources:
        if "Mono" in name and "PL" in name:
            step_set_feature_file(FEATURES_DIR / "features_mono_PL.fea", source.font)
            print(f"[{name} {source.styleName}] Merging PL glyphs")
            step_merge_glyphs_from_ufo(
                NERDFONTS_DIR / "NerdfontsPL-Regular.ufo", source.font
            )
            step_set_font_name(name, source.font)
        elif "Mono" in name:
            step_set_feature_file(FEATURES_DIR / "features_mono.fea", source.font)
            step_set_font_name(name, source.font)
        elif "PL" in name:
            step_set_feature_file(FEATURES_DIR / "features_code_PL.fea", source.font)
            print(f"[{name} {source.styleName}] Merging PL glyphs")
            step_merge_glyphs_from_ufo(
                NERDFONTS_DIR / "NerdfontsPL-Regular.ufo", source.font
            )
            step_set_font_name(name, source.font)
        elif name == "Cascadia Code":
            step_set_feature_file(FEATURES_DIR / "features_code.fea", source.font)
        else:
            print ("Variant name not identified. Please check.")
        set_font_metaData(source.font)


# Build fonts
# ****************************************************************


def build_font_variable(
    designspace: fontTools.designspaceLib.DesignSpaceDocument, name: str
) -> None:
    prepare_fonts(designspace, name)
    compile_variable_and_save(designspace)


def build_font_static(
    designspace: fontTools.designspaceLib.DesignSpaceDocument,
    instance_descriptor: fontTools.designspaceLib.InstanceDescriptor,
    name: str,
) -> None:
    prepare_fonts(designspace, name)
    generator = fontmake.instantiator.Instantiator.from_designspace(designspace)
    instance = generator.generate_instance(instance_descriptor)
    step_set_font_name(name, instance)
    compile_static_and_save(instance)


# Export fonts
# ****************************************************************


def compile_variable_and_save(
    designspace: fontTools.designspaceLib.DesignSpaceDocument,
) -> None:
    familyName = designspace.default.font.info.familyName
    file_stem = familyName.replace(" ", "")
    file_path = (OUTPUT_DIR / file_stem).with_suffix(f".ttf")

    print(f"[{familyName}] Compiling")
    varFont = ufo2ft.compileVariableTTF(designspace, inplace=True)

    print(f"[{familyName}] Adding STAT table")
    styleSpace = statmake.classes.Stylespace.from_file(INPUT_DIR / "STAT.plist")
    statmake.lib.apply_stylespace_to_variable_font(styleSpace, varFont, {})

    print(f"[{familyName}] Merging VTT")
    vttLib.transfer.merge_from_file(varFont, VTT_DATA_FILE)

    varFont = set_overlap_flag(varFont)

    print(f"[{familyName}] Saving")
    varFont.save(file_path)

    print(f"[{familyName}] Done: {file_path}")


def compile_static_and_save(instance: ufoLib2.Font) -> None:
    family_name = instance.info.familyName
    style_name = instance.info.styleName
    print(f"[{family_name}] Building static instance: {style_name}")

    # Use pathops backend for overlap removal because it is, at the time of this
    # writing, massively faster than booleanOperations and thanks to autohinting,
    # there is no need to keep outlines compatible to previous releases.
    static_ttf = ufo2ft.compileTTF(
        instance, removeOverlaps=True, overlapsBackend="pathops"
    )
    static_otf = ufo2ft.compileOTF(
        instance,
        removeOverlaps=True,
        overlapsBackend="pathops",
        # Can do inplace now because TTF is already done.
        inplace=True,
        # Don't optimize here, will be optimized after autohinting.
        optimizeCFF=ufo2ft.CFFOptimization.NONE,
    )

    file_name = f"{family_name}-{style_name}".replace(" ", "")
    file_path_static = (OUTPUT_STATIC_DIR / file_name).with_suffix(".ttf")
    file_path_static_otf = (OUTPUT_STATIC_DIR / file_name).with_suffix(".otf")

    static_ttf.save(file_path_static)
    static_otf.save(file_path_static_otf)
    print(f"[{family_name}] Done: {file_path_static}, {file_path_static_otf}")


# Font hinting
# ****************************************************************


def autohint(otf_path: Path) -> None:
    path = os.fspath(otf_path)

    print(f"Autohinting {path}")
    psautohint.__main__.main([path])

    print(f"Compressing {path}")
    cffsubr.__main__.main(["-i", path])


def ttfautohint(path: str) -> None:
    print(f"Autohinting {path}")
    subprocess.check_call(
        [
            "ttfautohint",
            "--stem-width",
            "nsn",
            "--reference",
            "build/static/CascadiaCode-Regular.ttf",
            path,
            path[:-4] + "-hinted.ttf",
        ]
    )
    os.remove(path)
    os.rename(path[:-4] + "-hinted.ttf", path)


# Main build script
# ****************************************************************

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="build some fonts")
    parser.add_argument("-P", "--no-powerline", action="store_false", dest="powerline")
    parser.add_argument("-M", "--no-mono", action="store_false", dest="mono")
    parser.add_argument("-S", "--static-fonts", action="store_true")
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
    if args.static_fonts:
        OUTPUT_STATIC_DIR.mkdir(exist_ok=True)

    # Stage 1: Make all the things.
    pool = multiprocessing.pool.Pool(processes=multiprocessing.cpu_count())
    processes = []
    processes.append(
        pool.apply_async(
            build_font_variable,
            (
                designspace,
                "Cascadia Code",
            ),
        )
    )
    if args.mono:
        processes.append(
            pool.apply_async(
                build_font_variable,
                (
                    designspace,
                    "Cascadia Mono",
                ),
            )
        )
    if args.powerline:
        processes.append(
            pool.apply_async(
                build_font_variable,
                (
                    designspace,
                    "Cascadia Code PL",
                ),
            )
        )
        if args.mono:
            processes.append(
                pool.apply_async(
                    build_font_variable,
                    (
                        designspace,
                        "Cascadia Mono PL",
                    ),
                )
            )

    if args.static_fonts:
        for instance_descriptor in designspace.instances:
            processes.append(
                pool.apply_async(
                    build_font_static,
                    (
                        designspace,
                        instance_descriptor,
                        "Cascadia Code",
                    ),
                )
            )
            if args.mono:
                processes.append(
                    pool.apply_async(
                        build_font_static,
                        (
                            designspace,
                            instance_descriptor,
                            "Cascadia Mono",
                        ),
                    )
                )
            if args.powerline:
                processes.append(
                    pool.apply_async(
                        build_font_static,
                        (
                            designspace,
                            instance_descriptor,
                            "Cascadia Code PL",
                        ),
                    )
                )
                if args.mono:
                    processes.append(
                        pool.apply_async(
                            build_font_static,
                            (
                                designspace,
                                instance_descriptor,
                                "Cascadia Mono PL",
                            ),
                        )
                    )

    pool.close()
    pool.join()
    for process in processes:
        process.get()
    del processes
    del pool

    # Stage 2: Autohint and maybe compress all the static things.
    if args.static_fonts is True:
        otfs = list(Path("build/static").glob("*.otf"))
        if otfs:
            pool = multiprocessing.Pool(processes=multiprocessing.cpu_count())
            processes = [pool.apply_async(autohint, (otf,)) for otf in otfs]
            pool.close()
            pool.join()
            for process in processes:
                process.get()

        try:
            for ttf_path in Path("build/static").glob("*.ttf"):
                if not ttf_path.stem.endswith("-hinted"):
                    ttfautohint(os.fspath(ttf_path))
        except Exception as e:
            print(f"ttfautohint failed. Please reinstall and try again. {str(e)}")

    print("All done.")