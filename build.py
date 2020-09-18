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
import multiprocessing
import multiprocessing.pool

INPUT_DIR = Path("sources")
OUTPUT_DIR = Path("build")
VTT_DATA_FILE = INPUT_DIR / "vtt_data" / "CascadiaCode.ttx"

def step_set_font_name(n, instance):
    instance.info.familyName = n
    # We have to change the style map family name because that's what
    # Windows uses to map Bold/Regular/Medium/etc. fonts
    instance.info.styleMapFamilyName = n

    return instance


def step_merge_glyphs_from_ufo(path, instance):
    ufo = ufoLib2.Font.open(path)
    print(f"[{instance.info.familyName} {instance.info.styleName}] Merging {path}")
    for glyph in ufo.glyphOrder:
        if glyph not in instance.glyphOrder:
            instance.addGlyph(ufo[glyph])

    return ufo

def step_set_feature_file(n, instance):
    fea = n.read_text()
    instance.features.text = fea
    return instance

def set_font_metaData(font):
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

def generateStatic(instance,file_stem):
    staticTTF = ufo2ft.compileTTF(instance,removeOverlaps=True)
    staticOTF = ufo2ft.compileOTF(instance,removeOverlaps=True)

    file_name = file_stem+"-"+instance.info.styleName

    file_path_static = (OUTPUT_DIR / "static" / file_name).with_suffix(f".ttf")
    file_path_static_otf = (OUTPUT_DIR / "static" / file_name).with_suffix(f".otf")

    staticTTF.save(file_path_static)
    staticOTF.save(file_path_static_otf)

def build_fonts(designspace, static, **mods):
    for font in [source.font for source in designspace.sources]:
        if "fname" in mods:
            step_set_font_name(mods["fname"],font)
        if "fea" in mods:
            step_set_feature_file(mods["fea"], font)
        if "merge" in mods:
            if mods["merge"] == "PL":
                step_merge_glyphs_from_ufo(INPUT_DIR / "nerdfonts" / "NerdfontsPL-Regular.ufo", font)
            else:
                pass
        set_font_metaData(font)

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
        if os.path.exists(OUTPUT_DIR / "static") == False:
            os.mkdir(OUTPUT_DIR / "static")
        generator = fontmake.instantiator.Instantiator.from_designspace(designspace)
        print(f"[{familyName}] Building static instances")
        
        staticProcesses = []
        staticPool = multiprocessing.Pool(processes=multiprocessing.cpu_count())

        for instance_descriptor in designspace.instances:
            instance = generator.generate_instance(instance_descriptor)
            staticProcesses.append(
                staticPool.apply_async(
                    generateStatic,
                    args=(instance,file_stem,),
                )
            )
        staticPool.close()
        staticPool.join()

        for process in staticProcesses:
            process.get()
        
        
        print(f"[{familyName}] Done building static instances")

def autohint(otf):
    path = os.fspath(otf)
    print(f"Autohinting {path}")
    subprocess.check_call(["psautohint", "--log", "build/log.txt", path])
    print(f"Compressing {path}")
    subprocess.check_call(["python", "-m", "cffsubr", "-i", path])

# By defining our own Pool process here, we are able to instantiate the workers as non-daemon, which allows another Pool to be called from within it. Risky business, but it works. 

class NoDaemonProcess(multiprocessing.Process):
    @property
    def daemon(self):
        return False

    @daemon.setter
    def daemon(self, value):
        pass

class NoDaemonContext(type(multiprocessing.get_context())):
    Process = NoDaemonProcess

class MyPool(multiprocessing.pool.Pool):
    def __init__(self, *args, **kwargs):
        kwargs['context'] = NoDaemonContext()
        super(MyPool, self).__init__(*args, **kwargs)

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

    nf_path = INPUT_DIR / "nerdfonts" / "NerdfontsNF.ufo"
    if not nf_path.exists():
        args.no_nerdfonts = True  # No NF = don't try to build those fonts.

    print ("*** *** *** Building Variable Fonts *** *** ***")

    designspace.loadSourceFonts(ufoLib2.Font.open, lazy=False)

    buildProcesses = []
    buildPool = MyPool(processes=multiprocessing.cpu_count())

    buildProcesses.append(
        buildPool.apply_async(
            build_fonts,
            (                                   # passes font info and designspace
                copy.deepcopy(designspace), 
                args.static_fonts,
            ),
            {                                   # passes keyword arguments
                'fea':INPUT_DIR / "features" / "features_code.fea",
            },
        )
    )

    if not args.no_mono:
        buildProcesses.append(
            buildPool.apply_async(
                build_fonts,
                (
                    copy.deepcopy(designspace), 
                    args.static_fonts,
                ),
                {
                    'fname': "Cascadia Mono",
                    'fea': INPUT_DIR / "features" / "features_mono.fea",
                },
            )
        )

    if not args.no_powerline:
        buildProcesses.append(
            buildPool.apply_async(
                build_fonts,
                (
                    copy.deepcopy(designspace), 
                    args.static_fonts,
                ),
                {
                    'fname': "Cascadia Code PL",
                    'fea': INPUT_DIR / "features" / "features_code_PL.fea",
                    'merge': "PL",
                },
            )
        )

        if not args.no_mono:
            buildProcesses.append(
                buildPool.apply_async(
                    build_fonts,
                    (
                        copy.deepcopy(designspace), 
                        args.static_fonts,
                    ),
                    {
                        'fname': "Cascadia Mono PL",
                        'fea': INPUT_DIR / "features" / "features_mono_PL.fea",
                        'merge': "PL",
                    },
                )
            )

    if not args.no_nerdfonts:
        buildProcesses.append(
            buildPool.apply_async(
                build_fonts,
                (
                    copy.deepcopy(designspace), 
                    args.static_fonts,
                ),
                {
                    'fname': "Cascadia Code NF",
                    'merge': "NF",
                },
            )
        )

        if not args.no_mono:
            buildProcesses.append(
                buildPool.apply_async(
                    build_fonts,
                    (
                        copy.deepcopy(designspace), 
                        args.static_fonts,
                    ),
                    {
                        'fname': "Cascadia Mono NF",
                        'merge': "NF",
                    },
                )
            )

    buildPool.close()
    buildPool.join()
    for process in buildProcesses:
        process.get()

    print("All done")
    print("*** *** *** *** *** *** *** *** *** *** *** *** *** *** *** *** *** ***")


    if args.static_fonts == True:
    
        print ("*** *** *** Autohinting Static Fonts *** *** ***")

        otfs = list(Path("build/static").glob("*.otf"))
        if otfs:
            hintProcesses = []
            hintPool = multiprocessing.Pool(processes=multiprocessing.cpu_count())
            for otf in otfs:
                hintProcesses.append(
                    hintPool.apply_async(
                        autohint,
                        (otf,),
                    )
                )
            hintPool.close()
            hintPool.join()
            for process in hintProcesses:
                process.get()


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