import argparse
import multiprocessing
import multiprocessing.pool
import os
import pathlib
from re import L
import subprocess
from pathlib import Path
from typing import cast

from fontTools.ttLib.tables.TupleVariation import TUPLES_SHARE_POINT_NUMBERS

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
import vttLib
import vttLib.transfer
import xml.etree.cElementTree as ET
from fontTools.ttLib.tables.TupleVariation import TupleVariation

VERSION_YEAR_MONTH = 2009
VERSION_DAY = 22

OUTPUT_DIR = Path("build")
OUTPUT_OTF_DIR = OUTPUT_DIR / "otf"
OUTPUT_TTF_DIR = OUTPUT_DIR / "ttf"
OUTPUT_WOFF2_DIR = OUTPUT_DIR / "woff2"
OUTPUT_STATIC_OTF_DIR = OUTPUT_OTF_DIR / "static"
OUTPUT_STATIC_TTF_DIR = OUTPUT_TTF_DIR / "static"
OUTPUT_STATIC_WOFF2_DIR = OUTPUT_WOFF2_DIR / "static"
INPUT_DIR = Path("sources")
VTT_DATA_FILE = INPUT_DIR / "vtt_data" / "CascadiaCode_VTT.ttf"
FEATURES_DIR = INPUT_DIR / "features"
NERDFONTS_DIR = INPUT_DIR / "nerdfonts"

# Font modifications
# ****************************************************************


def step_set_font_name(name: str, source: ufoLib2.Font) -> None:
    source.info.familyName = source.info.familyName.replace("Cascadia Code", name)
    # We have to change the style map family name because that's what
    # Windows uses to map Bold/Regular/Medium/etc. fonts
    source.info.styleMapFamilyName = source.info.styleMapFamilyName.replace("Cascadia Code", name)


def step_merge_glyphs_from_ufo(path: Path, instance: ufoLib2.Font) -> None:
    ufo = ufoLib2.Font.open(path)
    for glyph in ufo.glyphOrder:
        if glyph not in instance.glyphOrder:
            instance.addGlyph(ufo[glyph])


def step_set_feature_file(path: Path, instance: ufoLib2.Font) -> None:
    instance.features.text = path.read_text()


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
            print("Variant name not identified. Please check.")
        set_font_metaData(source.font)
    for instance in designspace.instances:
        instance.name = instance.name.replace("Cascadia Code", name)
        instance.familyName = instance.familyName.replace("Cascadia Code", name)
        instance.styleMapFamilyName = instance.styleMapFamilyName.replace("Cascadia Code", name)


def to_woff2(source_path: Path, target_path: Path) -> None:
    print(f"[WOFF2] Compressing {source_path} to {target_path}")
    font = fontTools.ttLib.TTFont(source_path)
    font.flavor = "woff2"
    target_path.parent.mkdir(exist_ok=True, parents=True)
    font.save(target_path)

class axisStore():
    header = []
    axisTags = []
    originLocs = []
    def copy(self):
        return self
    def items(self):
        return self.header
    def keys(self):
        return self.axisTags
    def get(self,axis,values):
        for o in self.originLocs:
            if axis in o[0]:
                return o[1]
                break



def reWriteTSI1(vtt_font: fontTools.ttLib.TTFont, varFont: fontTools.ttLib.TTFont) -> None:

    glyphOrder = varFont.getGlyphOrder()
    glyphOrder_old = vtt_font.getGlyphOrder()

    for program in varFont["TSI1"].glyphPrograms:
        data = str.encode(varFont["TSI1"].glyphPrograms.get(program))
        data = str(data.decode())

        lines = data.splitlines()

        newdata = ""

        for line in lines:
            if "OFFSET" in line:
                splitLine = line.split(", ")
                name = glyphOrder_old[int(splitLine[1])]
                pos = ""
                if name in glyphOrder:
                    pos = glyphOrder.index(name)
                else:
                    print ("glyph missing from new font file!")
                    break
                
                line = splitLine[0] + ", "+ str(pos)
                i=2
                while i < len(splitLine):
                    line = line+", "+splitLine[i]
                    i+=1
            # If the font has been rehinted for any reason, we want to strip these out as they lead to misalignments of diacritics. 
            elif line == "SVTCA[X]":
                break
            newdata = newdata+"\n"+line 

        varFont["TSI1"].glyphPrograms[program] = newdata
        varFont["TSI1"].glyphPrograms[program].encode()

def makeCVAR (varFont: fontTools.ttLib.TTFont, tree: ET.ElementTree) -> None:
    root = tree.getroot()
    TSIC = root.find("TSIC")

    axisSet = []
    for axis in TSIC.findall("AxisArray"):
        axisSet.append(axis.get("value"))

    locations = []
    for loc in TSIC.findall("RecordLocations"):
        axisLoc = []
        for axis in loc.findall("Axis"):
            axisLoc.append([axis.get("index"),axis.get("value")])
        locations.append(axisLoc)
    print (locations)
    CVT_num = []
    CVT_val = []
    for rec in TSIC.findall("Record"):
        RecNum = []
        RecVal = []
        for num in rec.findall("CVTArray"):
            RecNum.append(int(num.get("value")))
        for pos in rec.findall("CVTValueArray"):
            RecVal.append(int(pos.get("value")))
        CVT_num.append(RecNum)
        CVT_val.append(RecVal)

    variations = []

    # Now let's play the game of making TupleVariation happy, somehow. 
    for x, l in enumerate(locations):

        for loc in l:
            support = axisStore()

            for tag in axisSet:
                support.axisTags.append(tag)

            #support.originLocs.append((x,(-1, -1, 0)))

            for aPos in loc:
                axisChoice = int(float(loc[0]))
                if float(aPos[1]) < 0:
                    support.header.append([axisSet[axisChoice],float(aPos[1])])
                elif float(aPos[1]) > 0:
                    support.header.append([axisSet[axisChoice],float(aPos[1])])
            print (support.header)

        #    if n-1 > 0:
        #        support = support+", "
        #    axisChoice = int(float(loc[0]))
        #    if float(loc[1]) < 0:
        #        support = axisSet[axisChoice]+"=("+loc[1]+", "+loc[1]+", 0)"
        #    elif float(loc[1]) > 0:
        #        support = axisSet[axisChoice]+"=(0, "+loc[1]+", "+loc[1]+")"

            delta = []
            for i in range(0, len(varFont["cvt "])-1):
                if i in CVT_num[x]:
                    deltaVal = CVT_val[x][CVT_num[x].index(i)]
                    delta.append(deltaVal)
                else:
                    delta.append(None)
            
            var = TupleVariation(support, delta)
            print (var)
            variations.append(var)

    varFont["cvar"] = fontTools.ttLib.newTable('cvar')
    varFont["cvar"].version = 1
    varFont["cvar"].variations = variations


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
    compile_static_and_save(instance, name)


# Export fonts
# ****************************************************************


def compile_variable_and_save(
    designspace: fontTools.designspaceLib.DesignSpaceDocument,
    vtt_compile: bool = True,
) -> None:
    familyName = designspace.default.font.info.familyName
    file_stem = familyName.replace(" ", "")
    file_path: Path = (OUTPUT_TTF_DIR / file_stem).with_suffix(".ttf")

    print(f"[{familyName}] Compiling")
    varFont = ufo2ft.compileVariableTTF(designspace, inplace=True)

    print(f"[{familyName}] Adding STAT table")
    styleSpace = statmake.classes.Stylespace.from_file(INPUT_DIR / "STAT.plist")
    statmake.lib.apply_stylespace_to_variable_font(styleSpace, varFont, {})

    print(f"[{familyName}] Merging VTT")

    font_vtt = fontTools.ttLib.TTFont(VTT_DATA_FILE)

    for table in ["TSI0", "TSI1", "TSI2", "TSI3", "TSI5", "TSIC", "maxp"]:
        varFont[table] = fontTools.ttLib.newTable(table)
        varFont[table] = font_vtt[table]

    # this will correct the OFFSET[R] commands in TSI1 and remove any icky SVTCA[X]
    if font_vtt.getGlyphOrder() != varFont.getGlyphOrder():
        reWriteTSI1(font_vtt, varFont)

    if vtt_compile:
        print(f"[{familyName}] Compiling VTT")
    
        tree = ET.ElementTree()
        if os.path.isfile(OUTPUT_DIR / "Cascadia_TSIC.ttx"):
            tree = ET.parse(OUTPUT_DIR / "Cascadia_TSIC.ttx")
        else:
            varFont.saveXML(OUTPUT_DIR / "Cascadia_TSIC.ttx", tables=["TSIC"])
            tree = ET.parse(OUTPUT_DIR / "Cascadia_TSIC.ttx")
        os.remove(OUTPUT_DIR / "Cascadia_TSIC.ttx")
        varFont.saveXML(OUTPUT_DIR / "Cascadia_TSIC.ttx", tables=["TSIC"])
        vttLib.compile_instructions(varFont, ship=True)
        makeCVAR(varFont, tree)

    else:
        file_path = Path(str(file_path)[:-4]+"_VTT.ttf")

    set_overlap_flag(varFont)

    # last minute manual corrections to set things correctly
    varFont["head"].flags = 0x000b

    print(f"[{familyName}] Saving")
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

    file_name = name.replace(" ", "") + "-"  + instance.info.styleName
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
    parser.add_argument("-M", "--no-mono", action="store_false", dest="mono")
    parser.add_argument("-S", "--static-fonts", action="store_true")
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
        INPUT_DIR / "CascadiaCode.designspace"
    )
    designspace.instances = [
        s
        for s in designspace.instances
        if s.lib.get("com.schriftgestaltung.export", True)
    ]

    # Stage 1: Make all the things.
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
    del processes, pool

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
