![Cascadia Code](/images/cascadia-code.png)

![Cascadia Code Characters](/images/cascadia-code-characters.png)

# Welcome!

This repository contains the source code of Cascadia Code.

Other related repositories include:

- [Windows Terminal](https://github.com/microsoft/terminal)

# Installation

**You can install the latest version of Cascadia Code from the releases page here:** https://github.com/microsoft/cascadia-code/releases

Clicking on the Cascadia.ttf file will download it to your machine. From there, open the file. This will open a new window displaying the characters included in the font along with the font displayed at different sizes. This window should have an "Install" button that will install the font on your machine when clicked.

👉 **Note:** If you have previously installed a version of Cascadia Code, installing a new version *should* overwrite the previous version. However, in order to ensure it is completely overwritten, it is recommended that you delete the previous version you had before installing another.

**If you use macOS,you can install it by [Homebrew](https://brew.sh/)**

```
brew tap homebrew/cask-fonts 
brew brew cask install font-cascadia
```

# Contributing

This project welcomes contributions and suggestions. Most contributions require you to
agree to a Contributor License Agreement (CLA) declaring that you have the right to,
and actually do, grant us the rights to use your contribution. For details, visit
https://cla.microsoft.com.

When you submit a pull request, a CLA-bot will automatically determine whether you need
to provide a CLA and decorate the PR appropriately (e.g., label, comment). Simply follow the
instructions provided by the bot. You will only need to do this once across all repositories using our CLA.

# Getting Started

## Modifying the Font

Making modifications to the Cascadia Code font requires use, and understanding, of [Glyphs](https://glyphsapp.com/) (Mac) as well as [Microsoft VTT](https://docs.microsoft.com/en-us/typography/tools/vtt/) (Windows) and to a lesser extent [FontTools](https://github.com/fonttools/fonttools). The source for the font is built in Glyphs, and can be modified to a user’s preference. However, please note that hinting built into the font is closely tied to the glyph order and point order—modifications to either will result in needing to manually correct any problems. 

### Modifying a single glyph

1) Make the necessary changes in the Glyphs source and export a TTF file. 
2) Open the previous VTT TTF source file in VTT and locate the code point that you changed in the source. 
3) Import the glyph and overwrite the code point in the source file. If it is to be added to the end of the file, on the import screen choose “append to end of font”.
4) Hint (or re-hint) the glyph. 
5) Ship the production font. 

### Modifying a broad range of glyphs

1) Make the necessary modifications to the Glyphs source and export a TTF file. 
2) Convert both the new TTF and the VTT TTF source file to TTX using FontTools
3) Copy the TSI tables from the VTT TTF source to the new TTF source, and rebuild the TTF file. 
4) Open new TTF file in VTT, compile and check for errors. Correct as necessary. 
5) Ship the production font. 

In cases of extensive glyph modification, the font may need to be re-hinted entirely.

## Creating a Pull Request

At the moment, we do not have a testing framework for verifying proper character creation. When creating a pull request, please heavily document the steps you took along with images displaying your changes. Additionally, please provide images of the updated character(s) at different screen sizes to validate proper hinting.

## Communicating with the Team

The easiest way to communicate with the team is via GitHub issues. Please file new issues, feature requests and suggestions, but **DO search for similar open/closed pre-existing issues before you do**.

Please help us keep this repository clean, inclusive, and fun! We will not tolerate any abusive, rude, disrespectful or inappropriate behavior. Read our [Code of Conduct](https://opensource.microsoft.com/codeofconduct/) for more details.

If you would like to ask a question that you feel doesn't warrant an issue (yet), please reach out to us via Twitter:

Kayla Cinnamon, Program Manager: [@cinnamon_msft](https://twitter.com/cinnamon_msft)

Dustin Howett, Engineering Lead: [@dhowett](https://twitter.com/dhowett)

Michael Niksa, Senior Developer: [@michaelniksa](https://twitter.com/michaelniksa)

Rich Turner, Program Manager: [@richturn_ms](https://twitter.com/richturn_ms)

# Code of Conduct

This project has adopted the [Microsoft Open Source Code of Conduct](https://opensource.microsoft.com/codeofconduct/). For more information see the [Code of Conduct FAQ](https://opensource.microsoft.com/codeofconduct/faq/)
or contact [opencode@microsoft.com](mailto:opencode@microsoft.com) with any additional questions or comments.
