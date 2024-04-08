from fontParts.world import OpenFont
import fontParts
import glob
from pathlib import Path

SIDEBEARING = 20
FONTWIDTH = 1200
FONTHEIGHT = 1420 #height baseline to cap height for centering of symbol
FONTUPM = 2048

INPUT = Path("original")
OUTPUT = Path("processed")


CLOUDS = [0xE300, 0xE301, 0xE302, 0xE303, 0xE304, 0xE305, 0xE306, 0xE307, 0xE308, 0xE309, 0xE30A, 0xE30B, 0xE30C, 0xE30D, 0xE30E, 0xE30F, 0xE310, 0xE311, 0xE312, 0xE313, 0xE314, 0xE315, 0xE316, 0xE317, 0xE318, 0xE319, 0xE31A, 0xE31B, 0xE31C, 0xE31D, 0xE31E, 0xE31F, 0xE320, 0xE321, 0xE322, 0xE323, 0xE324, 0xE325, 0xE326, 0xE327, 0xE328, 0xE329, 0xE32A, 0xE32B, 0xE32C, 0xE32D, 0xE32E, 0xE32F, 0xE330, 0xE331, 0xE332, 0xE333, 0xE334, 0xE335, 0xE336, 0xE337, 0xE338, 0xE33A, 0xE33B, 0xE33C, 0xE33D, 0xE342, 0xE343, 0xE346, 0xE34B, 0xE34C, 0xE34D, 0xE35C, 0xE35D, 0xE35E, 0xE35F, 0xE360, 0xE361, 0xE362, 0xE363, 0xE364, 0xE365, 0xE366, 0xE367, 0xE36A, 0xE36B, 0xE36C, 0xE36D, 0xE36E, 0xE36F, 0xE370, 0xE371, 0xE372, 0xE373, 0xE374, 0xE375, 0xE376, 0xE377, 0xE378, 0xE379, 0xE37A, 0xE37B, 0xE37C, 0xE37D, 0xE37E, 0xE3AA, 0xE3AB, 0xE3AC, 0xE3AD, 0xE3AE, 0xE3BC, 0xE3BD, 0xE3BE, 0xE3BF, 0xE3C0, 0xE3C1, 0xE3C2, 0xE3C3, 0xE345,0xE34A,0xE351]

#scale groups

def scaleGroup(fileName, glyph, SIDEBEARING):
	xAdjustment = 1
	yAdjustment = 1
	height = glyph.bounds[3] - glyph.bounds[1]
	width = glyph.bounds[2] - glyph.bounds[0]
	modified = False

	if "codicon" in fileName:
		if glyph.unicode in range(0xeb6e,0xeb72): #triangles
			xAdjustment = (FONTWIDTH-(2*SIDEBEARING))/(scaledFont["triangle-down"].bounds[2] - scaledFont["triangle-down"].bounds[0])
			modified = True
		if glyph.unicode in range(0xeab4,0xeab8): #chevrons
			xAdjustment = (FONTWIDTH-(2*SIDEBEARING))/(scaledFont["chevron-down"].bounds[2] - scaledFont["chevron-down"].bounds[0])
			modified = True
		if glyph.unicode in [0xEA9D,0xEA9E,0xEA9F,0xEAA0]:
			xAdjustment = (FONTWIDTH-(2*SIDEBEARING))/(scaledFont["arrow-both"].bounds[2] - scaledFont["arrow-both"].bounds[0])
			modified = True

	elif "devicons" in fileName:
		if glyph.unicode in range(0xe7bd,0xe7c4): #small letters
			xAdjustment = (FONTWIDTH-(2*SIDEBEARING))/(scaledFont["uniE60E"].bounds[2] - scaledFont["uniE60E"].bounds[0])
			modified = True

	elif "FontAwesome" in fileName:
		if glyph.unicode in [0xf005, 0xf006, 0xf089]: #star
			xAdjustment = (FONTWIDTH-(2*SIDEBEARING))/(scaledFont["star"].bounds[2] - scaledFont["star"].bounds[0])
			modified = True
		if glyph.unicode in range(0xF026,0xF029): #volume
			xAdjustment = (FONTWIDTH-(2*SIDEBEARING))/(scaledFont["volume_up"].bounds[2] - scaledFont["volume_up"].bounds[0])
			modified = True
		if glyph.unicode in [0xf02b, 0xf02c]: #tags
			xAdjustment = (FONTWIDTH-(2*SIDEBEARING))/(scaledFont["tags"].bounds[2] - scaledFont["tags"].bounds[0])
			modified = True
		if glyph.unicode in range(0xF031,0xF036): #font stuff
			xAdjustment = (FONTWIDTH-(2*SIDEBEARING))/(scaledFont["text_height"].bounds[2] - scaledFont["text_height"].bounds[0])
			modified = True
		if glyph.unicode in [0xf044, 0xf045, 0xf046]: #edit share check boxes
			xAdjustment = (FONTWIDTH-(2*SIDEBEARING))/(scaledFont["edit"].bounds[2] - scaledFont["edit"].bounds[0])
			modified = True
		if glyph.unicode in range(0xF048,0xF053): #multimedia buttons
			xAdjustment = (FONTWIDTH-(2*SIDEBEARING))/(scaledFont["fast_forward"].bounds[2] - scaledFont["fast_forward"].bounds[0])
			modified = True
		if glyph.unicode in range(0xF060,0xF064): #arrows
			xAdjustment = (FONTWIDTH-(2*SIDEBEARING))/(scaledFont["arrow_up"].bounds[2] - scaledFont["arrow_up"].bounds[0])
			modified = True
		if glyph.unicode in [0xf053, 0xf054, 0xf077, 0xf078]: #chevron all directions
			xAdjustment = (FONTWIDTH-(2*SIDEBEARING))/(scaledFont["chevron_up"].bounds[2] - scaledFont["chevron_up"].bounds[0])
			modified = True
		if glyph.unicode in [0xF07D,0xF07E]: #resize
			xAdjustment = (FONTWIDTH-(2*SIDEBEARING))/(scaledFont["resize_horizontal"].bounds[2] - scaledFont["resize_horizontal"].bounds[0])
			modified = True
		if glyph.unicode in [0xf0a4, 0xf0a5, 0xf0a6, 0xf0a7]: #pointing hands
			xAdjustment = (FONTWIDTH-(2*SIDEBEARING))/(scaledFont["hand_right"].bounds[2] - scaledFont["hand_right"].bounds[0])
			modified = True
		if glyph.unicode in [0xf0d7, 0xf0d8, 0xf0d9, 0xf0da, 0xf0dc, 0xf0dd, 0xf0de]: #carets all directions
			xAdjustment = FONTHEIGHT/(scaledFont["sort"].bounds[3] - scaledFont["sort"].bounds[1])
			modified = True
		if glyph.unicode in range(0xF100,0xF108): #angle
			xAdjustment = (FONTWIDTH-(2*SIDEBEARING))/(scaledFont["double_angle_up"].bounds[2] - scaledFont["double_angle_up"].bounds[0])
			modified = True
		if glyph.unicode in [0xF130,0xF131]: #mic
			xAdjustment = (FONTWIDTH-(2*SIDEBEARING))/(scaledFont["microphone_off"].bounds[2] - scaledFont["microphone_off"].bounds[0])
			modified = True
		if glyph.unicode in [0xF141,0xF142]: #ellipsis
			xAdjustment = (FONTWIDTH-(2*SIDEBEARING))/(scaledFont["ellipsis_horizontal"].bounds[2] - scaledFont["ellipsis_horizontal"].bounds[0])
			modified = True
		if glyph.unicode in range(0xF153,0xF15b): #currencies
			xAdjustment = (FONTWIDTH-(2*SIDEBEARING))/(scaledFont["krw"].bounds[2] - scaledFont["krw"].bounds[0])
			modified = True
		if glyph.unicode in range(0xF157,0xF179): #long arrows
			xAdjustment = (FONTWIDTH-(2*SIDEBEARING))/(scaledFont["long_arrow_left"].bounds[2] - scaledFont["long_arrow_left"].bounds[0])
			modified = True
		if glyph.unicode in [0xF182,0xF183]: #male and female
			xAdjustment = (FONTWIDTH-(2*SIDEBEARING))/(scaledFont["female"].bounds[2] - scaledFont["female"].bounds[0])
			modified = True
		if glyph.unicode in range(0xF221,0xF22E): #gender or so
			xAdjustment = (FONTWIDTH-(2*SIDEBEARING))/(scaledFont["_517"].bounds[2] - scaledFont["_517"].bounds[0])
			modified = True
		if glyph.unicode in range(0xF255,0xF25C): #hand symbols
			xAdjustment = (FONTWIDTH-(2*SIDEBEARING))/(scaledFont["_563"].bounds[2] - scaledFont["_563"].bounds[0])
			modified = True

	elif "octicons" in fileName:
		if glyph.unicode in [0xF476,0xF478,0xF49A]: #bells
			xAdjustment = (FONTWIDTH-(2*SIDEBEARING))/(scaledFont["bell-slash"].bounds[2] - scaledFont["bell-slash"].bounds[0])
			modified = True
		if glyph.unicode in range(0xF4EF,0xF4F3): #move to
			xAdjustment = (FONTWIDTH-(2*SIDEBEARING))/(scaledFont["move-to-end"].bounds[2] - scaledFont["move-to-top"].bounds[0])
			modified = True
		if glyph.unicode in [0xF461,0xF47A,0xF493,0xF533]: #bookmarks
			xAdjustment = (FONTWIDTH-(2*SIDEBEARING))/(scaledFont["bookmark-slash"].bounds[2] - scaledFont["bookmark-slash"].bounds[0])
			modified = True
		if glyph.unicode in [0xF416,0xF424,0xF431,0xF432,0xF433,0xF434,0xF43E,0xF443,0xF45C,0xF46C]: #arrows
			xAdjustment = (FONTWIDTH-(2*SIDEBEARING))/(scaledFont["arrow-both"].bounds[2] - scaledFont["arrow-both"].bounds[0])
			modified = True
		if glyph.unicode in [0xF438,0xF444,0xF445,0xF44A,0xF44B,0xF460,0xF467,0xF470,0xF47B,0xF47C,0xF47D,0xF47E,0xF48B,0xF4C3,0xF51D]: #triangles / small stuff / chevrons / dash / X / github-text
			xAdjustment = (FONTWIDTH-(2*SIDEBEARING))/(scaledFont["smiley"].bounds[2] - scaledFont["smiley"].bounds[0])
			modified = True

	elif "weather" in fileName:
		if glyph.unicode in CLOUDS: # Various
			xAdjustment = (FONTWIDTH-(2*SIDEBEARING))/(scaledFont["uniF003"].bounds[2] - scaledFont["uniF003"].bounds[0])
			modified = True
		if glyph.unicode in [0xE339, 0xE33E, 0xE341]: # degree signs
			xAdjustment = (FONTWIDTH-(2*SIDEBEARING))/(scaledFont["uniF045"].bounds[2] - scaledFont["uniF045"].bounds[0])
			modified = True
		if glyph.unicode in [0xE33F, 0xE340, 0xE344, 0xE347, 0xE348, 0xE349, 0xE352, 0xE353, 0xE37F, 0xE380]: # arrows
			xAdjustment = (FONTWIDTH-(2*SIDEBEARING))/(scaledFont["uniF04C"].bounds[2] - scaledFont["uniF04C"].bounds[0])
			modified = True
		if glyph.unicode in range(0xE34E,0xE351): # thermometers
			xAdjustment = FONTHEIGHT/(scaledFont["uniF053"].bounds[3] - scaledFont["uniF053"].bounds[1])
			modified = True
		if glyph.unicode in range(0xE38D,0xE3A9): # moon phases
			xAdjustment = (FONTWIDTH-(2*SIDEBEARING))/(scaledFont["uniF095"].bounds[2] - scaledFont["uniF095"].bounds[0])
			modified = True
		if glyph.unicode in range(0xE3AF,0xE3BC): # wind speed
			#xAdjustment = (FONTHEIGHT)/(scaledFont["uniF003"].bounds[3] - scaledFont["uniF003"].bounds[1])
			xAdjustment = (FONTWIDTH-(2*SIDEBEARING))/(scaledFont["uniF0BE"].bounds[2] - scaledFont["uniF0BE"].bounds[0])
			modified = True
		if glyph.unicode in [0xE368,0xE369]: #lunar eclipse
			xAdjustment = (FONTWIDTH-(2*SIDEBEARING))/(scaledFont["uniF06E"].bounds[2] - scaledFont["uniF06E"].bounds[0])
			modified = True

	yAdjustment = xAdjustment

	if "Powerline" in fileName:
		#These powerline glyphs should be full width / full height 
		if glyph.unicode in range(0xE0B0,0xE0CE) or glyph.unicode in [0xE0D1,0xE0D2,0xE0D4]:
			yAdjustment = 2706/height
			xAdjustment = yAdjustment
			modified = True
		if glyph.unicode == 9776:
			xAdjustment = (FONTWIDTH-(2*FONTWIDTH*.1))/width # uni2630 requires additional space around it
			modified = True

	if modified == False:

		# Scaling the glyphs. if a narrow glyph is scaled to the width, it can become too tall, so we limit to the lessor ratio (height vs width)			
		if (FONTWIDTH-20)/width < FONTHEIGHT/height:
			xAdjustment = (FONTWIDTH-(2*SIDEBEARING))/width
		else:
			xAdjustment = FONTHEIGHT/height
		yAdjustment = xAdjustment

	
	return xAdjustment, yAdjustment

def center(glyph):
	newHeight = glyph.bounds[3] - glyph.bounds[1]
	currentY = glyph.bounds[1]
	adjustment = (FONTHEIGHT-newHeight)/2-currentY
	return adjustment

#for file in ["original/octicons.ufo"]:
for file in INPUT.glob("*.ufo"):
	print ("processing",str(file).split("/")[1])
	font = OpenFont(str(file))
	originalUPM = font.info.unitsPerEm 
	font.info.unitsPerEm = FONTUPM

	for glyph in font: # need to produce a scaled version before we adjust everything else so that there's a reference for the scale groups
		glyph.transformBy((FONTUPM/originalUPM, 0, 0, FONTUPM/originalUPM, 0, 0))

	scaledFont = font.copy()

	for glyph in font:
		if glyph.bounds is not None:
			

			glyph.correctDirection()

			xAdjustment, yAdjustment = scaleGroup(str(file),glyph,SIDEBEARING)
			glyph.transformBy((xAdjustment, 0, 0, yAdjustment, 0, 0))

			if glyph.unicode in [0xF159,0xF16A]: # There's some dumb rounding bug that is causing these two to be too wide.
				glyph.transformBy((1200/(glyph.bounds[2] - glyph.bounds[0]), 0, 0, 1, 0, 0))

			# Positioning the glyph. Looking to center it in the glyph width, and to the cap height value.
			newWidth = glyph.bounds[2] - glyph.bounds[0]
			if glyph.unicode in range(0xE38E,0xE39B): # MOON WAXING exception
				widthAdjustment = FONTWIDTH-SIDEBEARING-newWidth
			elif glyph.unicode in range(0xE39C,0xE3A9): # MOON WANING exception
				widthAdjustment = SIDEBEARING
			else:
				widthAdjustment = (FONTWIDTH-newWidth)/2

			glyph.leftMargin = widthAdjustment
			glyph.width = FONTWIDTH


			if "FontAwesome" in str(file) and glyph.unicode in [0xF0DC, 0xF0DD, 0xF0DE]:
					heightAdjustment = 65
			elif "weather" in str(file):
				if glyph.unicode in CLOUDS:
					heightAdjustment = 423
				elif glyph.unicode in [0xF053,0xF054,0xF055]:
					pass
				elif glyph.unicode == 0xE33E:
					heightAdjustment = -361
				else:
					heightAdjustment = center(glyph)
			elif "Powerline" in str(file):
				heightAdjustment = 151
			else:
				heightAdjustment = center(glyph)

			glyph.transformBy((1,0,0,1,0,heightAdjustment))
		else:
			glyph.width = 1200
	font.layers[0].round()

	font.save(str(OUTPUT / str(file).split("/")[1]))