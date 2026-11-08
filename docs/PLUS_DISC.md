# Tsukihime Plus Disc Vita Release

A separate native Vita build for the mirror moon English 1.2 edition of Tsukihime Plus Disc. It uses the same VitaSDK/ONScripter-JH runtime and readability improvements as Tsukihime Vita 1.06.

The PC Plus Disc release uses KiriKiri rather than NScripter. The included preparation tool reads your local `data.xp3` and `patch.xp3`, adapts the four story scripts to the native runtime, and copies their referenced media. No Windows executable, VNDS player, or emulator is used on the Vita.

## Included features

- Alliance of Illusion, Geccha, Geccha 2, and Kinoko's Experimental Theater.
- A native story-selection menu and 24-image gallery.
- Twenty save slots with English labels, readable timestamps, checked writes, and the clock fallback from the main port. This adds saving to the PC English release, which did not provide savegames.
- English word wrapping and page pauses before text can overflow.
- L-trigger cycle: original size, approximately 12%, 24%, and 35% larger, then original. The selection takes effect on the next text page. Both the full-screen dialogue window and the compact dialogue box support the cycle.
- Auto mode, skip, touch input, and backlog. Menus and backlog use their original text size. The size selection lasts for the current app session.
- Dedicated Plus Disc bubble icon, LiveArea background, and launch panel made from the supplied Plus Disc artwork and logo.
- Save/load lists use an 18-pixel font and 20-pixel rows so all twenty slots fit within the screen.
- Optional startup logging and the standard 128 MiB VitaSDK heap.

## Installation

1. Install `TsukihimePlusDiscVita-Release.vpk` using VitaShell. Its title ID is `TSUPL0001`. Install over the existing Plus Disc bubble when updating.
2. Extract your locally prepared `TsukihimePlusDisc-GameData.zip` at the root of `ux0:`. The ZIP already contains the `data/tsukihime_plus_disc/game/` directory structure.
3. Launch **Tsukihime Plus Disc**.

Expected layout:

```text
ux0:data/tsukihime_plus_disc/
  game/
    nscript.dat
    default.ttf
    plus-disc-data.json
    media/
      ...prepared image and audio files...
  save/
    ...created by the application...
  startup.log
```

The separate data and save paths allow this port and the original Tsukihime bubble to coexist. Their save files are not interchangeable. Copy the entire prepared `game/` directory; copying the original XP3 archives directly is not sufficient.

Loading resumes from the original script-page boundary. At larger sizes, a page spanning several screens may replay some text when loaded.

## Controls

| Control | Action |
| --- | --- |
| Circle | Confirm or advance text/pages |
| Cross, held | Fast-forward |
| Triangle | Open the save/load/history menu |
| Square | Enable auto mode |
| L | Cycle four text sizes; applies on the next text page |
| R | Enable skip |
| Select | Cycle text speed |
| Start | Advance text |
| D-pad / left stick | Navigate menus and backlog |
| Front touchscreen | Select or advance |

## Prepare your own data

Python 3 and Pillow are required. Supply the English 1.2 Game folder and an English-capable TrueType font. The existing Tsukihime `default.ttf` works. Some soundtrack cues are not present in the Plus Disc XP3 archives; supply your own Tsukihime CD tracks as `track01.ogg` through `track10.ogg` with `--music`.

```sh
python3 scripts/prepare_plus_disc.py \
  --source '/path/to/Tsukihime PLUS+DISC/Game' \
  --font '/path/to/Tsukihime/Game/default.ttf' \
  --music '/path/to/Tsukihime/Game/CD' \
  --output build/plus-disc-data/game \
  --zip build/TsukihimePlusDisc-GameData.zip
```

Existing output directories and ZIPs are not overwritten. The tool validates XP3 segment checksums, required media, and supported story commands. It rejects unexpected commands or missing media instead of silently dropping them. The preparation manifest records source hashes and the resulting story/media inventory.

The XP3 reader follows the archive layout used by [KiriKiri's reference implementation](https://github.com/krkrz/krkrz/blob/master/base/XP3Archive.cpp).

The prepared data contains your game and translation files. The distributable homebrew VPK contains only the runtime and LiveArea resources; game data is prepared locally from your own copy.

## Build

Use the VitaSDK dependencies in [BUILDING.md](BUILDING.md), then:

```sh
cmake -S . -B build/plus-disc \
  -DTSUKIHIME_EDITION=plus-disc -DCMAKE_BUILD_TYPE=Release
cmake --build build/plus-disc --target vpk -j2
```

Output: `build/plus-disc/TsukihimePlusDiscVita-Release.vpk`. The filename is unnumbered; the internal application version is `01.01` for VitaShell's update handling.

The default CMake edition remains `original`, building the original Tsukihime port.

## Validation and limits

The native VPK builds successfully. Host checks compare all four stories' visible English text and click waits with the input scripts, verify all label destinations and media hashes, and exercise the generated strings through the production script reader. Layout checks cover all four sizes, including the compact dialogue box. Saving uses the tested shared save-support implementation.

The save-list fix passes bounds checks for all twenty populated and empty slots, including the heading. Complete playthrough and hardware checks of the updated save/load screens are still needed.

The menu and gallery use native widgets. KiriKiri rocket/zoom acceleration, some wipe rules, and audio crossfades are simplified to native sprite movement, transitions, and mixer behavior. The gallery displays the 640x480 sample images included in the English patch. The bundled PC trial games and document/wallpaper extras are outside this port.

Startup errors are logged to `ux0:data/tsukihime_plus_disc/startup.log`, with fallback `ux0:data/tsukihime_plus_disc-startup.log`.

Credits and source licensing remain as documented in [THIRD_PARTY.md](../THIRD_PARTY.md). TYPE-MOON and mirror moon retain their rights to the original game, artwork, and English translation.
