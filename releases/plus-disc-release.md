# Tsukihime Plus Disc Vita Release

A native PS Vita adaptation of the mirror moon English 1.2 release, built with VitaSDK and ONScripter-JH. The included tool prepares the KiriKiri XP3 story data for this runtime on your computer.

## Included

- Four stories and a native 24-image gallery.
- Twenty save slots with English labels, readable date/time fields, and checked writes.
- A save/load list sized to fit all twenty slots on screen.
- English word wrapping and page-overflow handling.
- L-trigger text sizes: original, approximately 12%, 24%, and 35% larger, then original. Changes apply on the next text page.
- Dedicated Plus Disc bubble icon, LiveArea background, and launch panel.
- Separate application identity and save/data folders from the original Tsukihime Vita port.

## Installation

1. Download `TsukihimePlusDiscVita-Release.vpk` and install it with VitaShell. Install over the existing Plus Disc bubble when updating.
2. For a first installation, download the source archive and follow the [data preparation instructions](https://github.com/OZZ0AB/tsukihime-plus-disc-vita#prepare-your-own-data). You need your own compatible English Plus Disc files, an English-capable TrueType font, and the Tsukihime CD tracks used by the game.
3. Extract your locally generated `TsukihimePlusDisc-GameData.zip` at the root of `ux0:`. It creates `ux0:data/tsukihime_plus_disc/game/`.
4. Launch **Tsukihime Plus Disc**. Use **Triangle** for save/load/history and **Circle** to confirm or advance.

Existing prepared game data works with this update. Saves reside in `ux0:data/tsukihime_plus_disc/save/`. The title ID is `TSUPL0001`; the internal app version is `01.01`, while the VPK filename remains unnumbered.

## Release files

- `TsukihimePlusDiscVita-Release.vpk`: installable native application.
- `TsukihimePlusDiscVita-Release-source.tar.gz`: corresponding runtime source, preparation tool, and documentation.
- `SHA256SUMS`: checksums for the VPK and source archive.

The native build and host script/media/layout checks passed. The updated save/load screen still needs hardware confirmation and a complete playthrough has not been performed. KiriKiri-specific rocket/zoom effects, some transitions, and audio crossfades are simplified. See the README for controls, troubleshooting, credits, and licensing.

Game archives, scripts, translation, fonts, music, and prepared game-data ZIPs are supplied separately from your own compatible copy.
