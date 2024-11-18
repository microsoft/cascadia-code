import argparse
import multiprocessing
import multiprocessing.pool
import os
import subprocess
from pathlib import Path
from typing import cast
import xml.etree.cElementTree as ET
import tempfile
import glob

import cffsubr.__main__
import fontmake.instantiator
import fontTools.designspaceLib
import fontTools.ttLib
import fontTools.ttLib.tables._g_l_y_f as _g_l_y_f
import psautohint.__main__
from gftools.stat import gen_stat_tables_from_config
import yaml
import ufo2ft
import ufoLib2
import vttLib
import vttLib.transfer
from vttmisc import tsi1, tsic

VERSION_YEAR_MONTH = 2407
VERSION_DAY = 24
OUTPUT_DIR = Path("build")
OUTPUT_OTF_DIR = OUTPUT_DIR / "otf"
OUTPUT_TTF_DIR = OUTPUT_DIR / "ttf"
OUTPUT_WOFF2_DIR = OUTPUT_DIR / "woff2"
OUTPUT_STATIC_OTF_DIR = OUTPUT_OTF_DIR / "static"
OUTPUT_STATIC_TTF_DIR = OUTPUT_TTF_DIR / "static"
OUTPUT_STATIC_WOFF2_DIR = OUTPUT_WOFF2_DIR / "static"
INPUT_DIR = Path("sources")
VTT_DATA_FILE = INPUT_DIR / "vtt_data" / "CascadiaCode_VTT.ttf"
ITALIC_VTT_DATA_FILE = INPUT_DIR / "vtt_data" / "CascadiaCodeItalic_VTT.ttf"
FEATURES_DIR = INPUT_DIR / "features"
NERDFONTS_DIR = INPUT_DIR / "nerdfonts"

# Font modifications
# ****************************************************************


def step_set_font_name(name: str, source: ufoLib2.Font) -> None:
    source.info.familyName = source.info.familyName.replace("Cascadia Code", name)
    # We have to change the style map family name because that's what
    # Windows uses to map Bold/Regular/Medium/etc. fonts
    if source.info.styleMapFamilyName:
        source.info.styleMapFamilyName = source.info.styleMapFamilyName.replace("Cascadia Code", name)


def step_merge_glyphs_from_ufo(path: Path, instance: ufoLib2.Font) -> None:
    unicodes = []
    for glyph in instance:
        unicodes.append(glyph.unicode)
    ufo = ufoLib2.Font.open(path)
    for glyph in ufo:
        if glyph.unicode:
            if glyph.unicode not in unicodes:
                newName = str(hex(glyph.unicode)).upper().replace("0X","uni")
                instance.layers.defaultLayer.insertGlyph(ufo[glyph.name],newName, overwrite=False, copy=False)
        else:
            instance.addGlyph(ufo[glyph.name])


def step_set_feature_file(path: Path, name: str, instance: ufoLib2.Font) -> None:
    featureSet = ""
    if "Italic" in name: #until I can come up with a more elegent solution, this'll do. 
        featureList = [
            "header_italic", # adds definitions, language systems
            "aalt_italic",
            "ccmp",
            "locl_italic", 
            "calt_italic", 
            "figures_italic", # contains subs/sinf/sups/numr/dnom
            "frac", 
            "ordn", 
            "case", 
            "salt",
            "ss01",
            "ss02",
            "ss03", 
            "ss19", 
            "ss20", 
            "rclt", 
            "zero"
            ]
    else:
        featureList = [
            "header", # adds definitions, language systems
            "aalt",
            "ccmp",
            "locl", 
            "calt",
            "figures", # contains subs/sinf/sups/numr/dnom
            "frac", 
            "ordn", 
            "case", 
            "ss02", 
            "ss19", 
            "ss20", 
            "rclt", 
            "zero",
            "init",
            "medi",
            "fina",
            "rlig",
            ]

    for item in featureList:
        if "PL" in name and item == "rclt":
            featureSet += Path(path / str("rclt_PL.fea")).read_text()
        elif "NF" in name and item == "rclt":
            featureSet += Path(path / str("rclt_PL.fea")).read_text()
        elif "Mono" in name and "calt" in item:
            featureSet += Path(path / str(item+"_mono.fea")).read_text() #both Italic and Regular can use same mono
        else:
            featureSet += Path(path / str(item+".fea")).read_text()
    instance.features.text = featureSet   


def set_font_metaData(font: ufoLib2.Font) -> None:
    font.info.versionMajor = VERSION_YEAR_MONTH
    font.info.versionMinor = VERSION_DAY

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

def prepare_fonts(
    designspace: fontTools.designspaceLib.DesignSpaceDocument, name: str
) -> None:
    designspace.loadSourceFonts(ufoLib2.Font.open)
    for source in designspace.sources:

        step_set_feature_file(FEATURES_DIR, name, source.font)

        if "PL" in name or "NF" in name or "Mono" in name:
            step_set_font_name(name, source.font)

        if "PL" in name or "NF" in name:
            print(f"[{name} {source.styleName}] Merging PL glyphs")
            step_merge_glyphs_from_ufo(
                NERDFONTS_DIR / "NerdfontsPL-Regular.ufo", source.font
            )

        if "NF" in name:
            print(f"[{name} {source.styleName}] Merging NF glyphs")
            for ufo in Path(NERDFONTS_DIR/"full"/"processed").glob("*.ufo"):
                step_merge_glyphs_from_ufo(
                    ufo, source.font
                )

        set_font_metaData(source.font)
    for instance in designspace.instances:
        instance.name = instance.name.replace("Cascadia Code", name)
        instance.familyName = instance.familyName.replace("Cascadia Code", name)
        if instance.styleMapFamilyName:
            instance.styleMapFamilyName = instance.styleMapFamilyName.replace("Cascadia Code", name)


def to_woff2(source_path: Path, target_path: Path) -> None:
    print(f"[WOFF2] Compressing {source_path} to {target_path}")
    font = fontTools.ttLib.TTFont(source_path)
    font.flavor = "woff2"
    target_path.parent.mkdir(exist_ok=True, parents=True)
    font.save(target_path)

# Build fonts
# ****************************************************************


def build_font_variable(
    designspace: fontTools.designspaceLib.DesignSpaceDocument,
    name: str,
    vtt_compile: bool = True,
) -> None:
    prepare_fonts(designspace, name)
    compile_variable_and_save(designspace, vtt_compile)


def build_font_static(
    designspace: fontTools.designspaceLib.DesignSpaceDocument,
    instance_descriptor: fontTools.designspaceLib.InstanceDescriptor,
    name: str,
) -> None:
    prepare_fonts(designspace, name)

    generator = fontmake.instantiator.Instantiator.from_designspace(designspace)
    instance = generator.generate_instance(instance_descriptor)
    instance.info.familyName = instance.info.familyName.replace(" Italic","")
    if instance.info.styleMapFamilyName:
        instance.info.styleMapFamilyName = instance.info.styleMapFamilyName.replace(" Italic","")
    compile_static_and_save(instance, name.replace(" Italic",""))


# Export fonts
# ****************************************************************


def compile_variable_and_save(
    designspace: fontTools.designspaceLib.DesignSpaceDocument,
    vtt_compile: bool = True,
) -> None:
    
    if "Italic" in designspace.default.font.info.familyName: #Some weird stuff happens with Italics
        designspace.default.font.info.familyName = designspace.default.font.info.familyName.replace(" Italic", "")
    
    familyName = designspace.default.font.info.familyName
    styleName = designspace.default.font.info.styleName
    file_stem = familyName.replace(" ", "")
    if "Italic" in styleName and "Italic" not in file_stem:
        file_stem = file_stem+"Italic"
    file_path: Path = (OUTPUT_TTF_DIR / file_stem).with_suffix(".ttf")

    print(f"[{familyName} {styleName}] Compiling")
    varFont = ufo2ft.compileVariableTTF(designspace, inplace=True)

    print(f"[{familyName} {styleName}] Merging VTT")

    if "Italic" in styleName:
        font_vtt = fontTools.ttLib.TTFont(ITALIC_VTT_DATA_FILE)
    else:
        font_vtt = fontTools.ttLib.TTFont(VTT_DATA_FILE)
    

    for table in ["TSI0", "TSI1", "TSI2", "TSI3", "TSI5", "TSIC", "maxp"]:
        varFont[table] = fontTools.ttLib.newTable(table)
        varFont[table] = font_vtt[table]

    # this will correct the OFFSET[R] commands in TSI1
    if font_vtt.getGlyphOrder() != varFont.getGlyphOrder():
        tsi1.fixOFFSET(varFont, font_vtt)
        pass

    if vtt_compile:
        print(f"[{familyName} {styleName}] Compiling VTT")
        vttLib.compile_instructions(varFont, ship=True)
    else:
        file_path = (OUTPUT_TTF_DIR / str(file_stem+"_VTT")).with_suffix(".ttf")

    # last minute manual corrections to set things correctly
    # set two flags to enable proper rendering (one for overlaps in Mac, the other for windows hinting)
    # Helping mac office generage the postscript name correctly for variable fonts when an italic is present
    set_overlap_flag(varFont)
    varFont["head"].flags = 0x000b

    if "Regular" in styleName:
        varFont["name"].setName(familyName.replace(" ","")+"Roman", 25, 3, 1, 1033)

    print(f"[{familyName} {styleName}] Saving")
    file_path.parent.mkdir(exist_ok=True, parents=True)
    varFont.save(file_path)

    print(f"[{familyName}] Done: {file_path}")


def compile_static_and_save(instance: ufoLib2.Font, name:str) -> None:
    family_name = name
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
    file_path_static = (OUTPUT_STATIC_TTF_DIR / file_name).with_suffix(".ttf")
    file_path_static_otf = (OUTPUT_STATIC_OTF_DIR / file_name).with_suffix(".otf")

    file_path_static.parent.mkdir(exist_ok=True, parents=True)
    static_ttf.save(file_path_static)
    file_path_static_otf.parent.mkdir(exist_ok=True, parents=True)
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
            "--increase-x-height",
            "0",
            "--reference",
            os.fspath(OUTPUT_STATIC_TTF_DIR / "CascadiaCode-Regular.ttf"),
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
    parser.add_argument("-NF", "--no-nerdfonts", action="store_false", dest="nerdfonts")
    parser.add_argument("-M", "--no-mono", action="store_false", dest="mono")
    parser.add_argument("-S", "--static-fonts", action="store_true")
    parser.add_argument("-I", "--no-italic", action="store_false", dest="italic")
    parser.add_argument(
        "-V",
        "--no-vtt-compile",
        action="store_false",
        dest="vtt_compile",
        help="Do not compile VTT code but leave in the VTT sources.",
    )
    parser.add_argument("-W", "--web-fonts", action="store_true")
    args = parser.parse_args()

    # Load Designspace and filter out instances that are marked as non-exportable.
    designspace = fontTools.designspaceLib.DesignSpaceDocument.fromfile(
        INPUT_DIR / "CascadiaCode_variable.designspace"
    )

    designspace.instances = [
        s
        for s in designspace.instances
        if s.lib.get("com.schriftgestaltung.export", True)
    ]

    designspaceItalic = fontTools.designspaceLib.DesignSpaceDocument.fromfile(
        INPUT_DIR / "CascadiaCode_variable_italic.designspace"
    )

    designspaceItalic.instances = [
        s
        for s in designspaceItalic.instances
        if s.lib.get("com.schriftgestaltung.export", True)
    ]


    #Stage 1: Make all the things.
    pool = multiprocessing.pool.Pool(processes=multiprocessing.cpu_count())
    processes = []
    processes.append(
        pool.apply_async(
            build_font_variable,
            (
                designspace,
                "Cascadia Code",
                args.vtt_compile,
            ),
        )
    )
    if args.italic:
        processes.append(
            pool.apply_async(
                build_font_variable,
                (
                    designspaceItalic,
                    "Cascadia Code Italic",
                    args.vtt_compile,
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
                    args.vtt_compile,
                ),
            )
        )
        if args.italic:
            processes.append(
                pool.apply_async(
                    build_font_variable,
                    (
                        designspaceItalic,
                        "Cascadia Mono Italic",
                        args.vtt_compile,
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
                    args.vtt_compile,
                ),
            )
        )
        if args.italic:
            processes.append(
                pool.apply_async(
                    build_font_variable,
                    (
                        designspaceItalic,
                        "Cascadia Code PL Italic",
                        args.vtt_compile,
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
                        args.vtt_compile,
                    ),
                )
            )
            if args.italic:
                processes.append(
                    pool.apply_async(
                        build_font_variable,
                        (
                            designspaceItalic,
                            "Cascadia Mono PL Italic",
                            args.vtt_compile,
                        ),
                    )
                )
    if args.nerdfonts:
        processes.append(
            pool.apply_async(
                build_font_variable,
                (
                    designspace,
                    "Cascadia Code NF",
                    args.vtt_compile,
                ),
            )
        )
        if args.italic:
            processes.append(
                pool.apply_async(
                    build_font_variable,
                    (
                        designspaceItalic,
                        "Cascadia Code NF Italic",
                        args.vtt_compile,
                    ),
                )
            )
        if args.mono:
            processes.append(
                pool.apply_async(
                    build_font_variable,
                    (
                        designspace,
                        "Cascadia Mono NF",
                        args.vtt_compile,
                    ),
                )
            )
            if args.italic:
                processes.append(
                    pool.apply_async(
                        build_font_variable,
                        (
                            designspaceItalic,
                            "Cascadia Mono NF Italic",
                            args.vtt_compile,
                        ),
                    )
                )

    if args.static_fonts:
        # Build the Regulars
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
            if args.nerdfonts:
                processes.append(
                    pool.apply_async(
                        build_font_static,
                        (
                            designspace,
                            instance_descriptor,
                            "Cascadia Code NF",
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
                                "Cascadia Mono NF",
                            ),
                        )
                    )
        if args.italic:
            # Build the Regulars
            for instance_descriptor in designspaceItalic.instances:
                processes.append(
                    pool.apply_async(
                        build_font_static,
                        (
                            designspaceItalic,
                            instance_descriptor,
                            "Cascadia Code Italic",
                        ),
                    )
                )
                if args.mono:
                    processes.append(
                        pool.apply_async(
                            build_font_static,
                            (
                                designspaceItalic,
                                instance_descriptor,
                                "Cascadia Mono Italic",
                            ),
                        )
                    )
                if args.powerline:
                    processes.append(
                        pool.apply_async(
                            build_font_static,
                            (
                                designspaceItalic,
                                instance_descriptor,
                                "Cascadia Code PL Italic",
                            ),
                        )
                    )
                    if args.mono:
                        processes.append(
                            pool.apply_async(
                                build_font_static,
                                (
                                    designspaceItalic,
                                    instance_descriptor,
                                    "Cascadia Mono PL Italic",
                                ),
                            )
                        )
                if args.nerdfonts:
                    processes.append(
                        pool.apply_async(
                            build_font_static,
                            (
                                designspaceItalic,
                                instance_descriptor,
                                "Cascadia Code NF Italic",
                            ),
                        )
                    )
                    if args.mono:
                        processes.append(
                            pool.apply_async(
                                build_font_static,
                                (
                                    designspaceItalic,
                                    instance_descriptor,
                                    "Cascadia Mono NF Italic",
                                ),
                            )
                        )

    pool.close()
    pool.join()
    for process in processes:
        process.get()
    del processes, pool

    # Step 1.5: Adding STAT tables in one go
    print ("[Cascadia Variable fonts] Fixing STAT tables")
    fontSTAT = [fontTools.ttLib.TTFont(f) for f in list(OUTPUT_TTF_DIR.glob("*.ttf"))]
    with open(INPUT_DIR/"stat.yaml") as f:
        config = yaml.load(f, Loader=yaml.SafeLoader)
    gen_stat_tables_from_config(config, fontSTAT)

    for font in fontSTAT:
        font.save(font.reader.file.name)

    # Stage 2: Autohint and maybe compress all the static things.
    if args.static_fonts is True:
        otfs = list(OUTPUT_STATIC_OTF_DIR.glob("*.otf"))
        if otfs:
            pool = multiprocessing.Pool(processes=multiprocessing.cpu_count())
            processes = [pool.apply_async(autohint, (otf,)) for otf in otfs]
            pool.close()
            pool.join()
            for process in processes:
                process.get()
            del processes, pool

        try:
            for ttf_path in OUTPUT_STATIC_TTF_DIR.glob("*.ttf"):
                if not ttf_path.stem.endswith("-hinted"):
                    ttfautohint(os.fspath(ttf_path))
        except Exception as e:
            print(f"ttfautohint failed. Please reinstall and try again. {str(e)}")

    # Stage 3: Have some web fonts.
    if args.web_fonts:
        pool = multiprocessing.Pool(processes=multiprocessing.cpu_count())
        processes = [
            pool.apply_async(
                to_woff2,
                (
                    path,
                    # This removes build/ttf from the found files and prepends
                    # build/woff2 instead, keeping the sub-structure.
                    OUTPUT_WOFF2_DIR
                    / path.relative_to(OUTPUT_TTF_DIR).with_suffix(".woff2"),
                ),
            )
            for path in OUTPUT_TTF_DIR.glob("**/*.ttf")
        ]
        pool.close()
        pool.join()
        for process in processes:
            process.get()

    print("All done.")
