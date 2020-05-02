import glob, os
from fontTools import ttLib


os.chdir("build")

for file in glob.glob("*.ttf"):
    ttfile = ttLib.TTFont(file)

    try:
        vttPresent = ttfile.getTableData("TSI0")
        print ("Warning! VTT production files present in font: "+file)
        print ("Please ship the font out of VTT before converting")
        print("*** *** *** *** *** *** *** *** *** *** *** *** *** *** *** *** *** ***")
    except:
        print (file+": Generating WOFF2")
        ttfile.flavor = 'woff2'
        ttfile.save(file[:-3]+"woff2")
        print("All done")
        print("*** *** *** *** *** *** *** *** *** *** *** *** *** *** *** *** *** ***")