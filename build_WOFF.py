import sys
from pathlib import Path

from fontTools import ttLib

for file in Path("build").glob("*.ttf"):
    ttfile = ttLib.TTFont(file)

    if "TSI0" in ttfile:
        print(f"Warning! VTT production files present in font: {file}")
        print("Please run VTT ship before converting")
        print("*** *** *** *** *** *** *** *** *** *** *** *** *** *** *** *** *** ***")
    else:
        print(f"{file}: Generating WOFF2")
        ttfile.flavor = "woff2"
        ttfile.save(file.with_suffix(".woff2"))

print("All done")
print("*** *** *** *** *** *** *** *** *** *** *** *** *** *** *** *** *** ***") 