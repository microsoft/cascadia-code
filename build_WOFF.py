import sys
from pathlib import Path

from fontTools import ttLib

for file in Path("build").glob("*.ttf"):
    ttfile = ttLib.TTFont(file)

    if "TSI0" in ttfile:
        print(f"[{file}] – ERROR: VTT production tables present, WOFF not generated")
        print("Please ship from VTT")
    else:
        print(f"{file}: Generating WOFF2")
        ttfile.flavor = "woff2"
        ttfile.save(file.with_suffix(".woff2"))

print("All done")
print("*** *** *** *** *** *** *** *** *** *** *** *** *** *** *** *** *** ***") 