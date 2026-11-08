#!/usr/bin/env python3
"""Export the Plus Disc source and public runtime release without game data."""
import argparse
import json
import re
import shutil
import struct
import tarfile
import zipfile
from pathlib import Path

from prepare_github_release import copy_tree, sha256

REPOSITORY = "tsukihime-plus-disc-vita"
VERSION = "01.01"
TAG = "v1.01"
UPSTREAM = "01955d7c1a4ecdff4245aa6e3fc08fd64625e4a9"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path("publish/plus-disc-release"))
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    output = args.output.resolve()
    if root / "publish" not in output.parents or output.exists():
        raise SystemExit("Choose a new directory inside publish/; existing exports are preserved.")
    vpk = root / "build/TsukihimePlusDiscVita-Release.vpk"
    with zipfile.ZipFile(vpk) as archive:
        if archive.testzip() or set(archive.namelist()) != {
            "eboot.bin", "sce_sys/param.sfo", "sce_sys/icon0.png",
            "sce_sys/livearea/contents/bg.png", "sce_sys/livearea/contents/startup.png",
            "sce_sys/livearea/contents/template.xml",
        }:
            raise SystemExit("Unexpected VPK contents or failed integrity check")
        data = archive.read("sce_sys/param.sfo")
        _, _, keys, values, count = struct.unpack_from("<5I", data)
        fields = {}
        for i in range(count):
            key, _, size, _, offset = struct.unpack_from("<HHIII", data, 20 + i * 16)
            name = data[keys + key:data.index(b"\0", keys + key)].decode()
            fields[name] = data[values + offset:values + offset + size].rstrip(b"\0")
        if fields["APP_VER"] != VERSION.encode() or fields["TITLE_ID"] != b"TSUPL0001":
            raise SystemExit("VPK does not match the Plus Disc release identity")

    repository = output / REPOSITORY
    assets = output / "release-assets"
    repository.mkdir(parents=True)
    assets.mkdir()
    for name in (".gitignore", "CMakeLists.txt", "LICENSE", "THIRD_PARTY.md", "CHANGELOG.md"):
        shutil.copy2(root / name, repository / name)
    for name in ("assets/livearea", "assets/plus-disc-livearea", "diagnostics", "docs",
                 "scripts", "engine/license", "engine/src/onsjh", "engine/src/common"):
        copy_tree(root / name, repository / name)
    shutil.copy2(root / "engine/UPSTREAM.md", repository / "engine/UPSTREAM.md")
    (repository / "releases").mkdir()
    shutil.copy2(root / "releases/plus-disc-release.md", repository / "releases/plus-disc-release.md")

    # The two editions share source. This dedicated repository builds Plus Disc
    # by default; its runtime is otherwise identical to the explicit profile.
    cmake = (repository / "CMakeLists.txt").read_text()
    old = 'set(TSUKIHIME_EDITION "original" CACHE STRING'
    if cmake.count(old) != 1:
        raise SystemExit("Cannot identify the default CMake edition")
    (repository / "CMakeLists.txt").write_text(cmake.replace(old, 'set(TSUKIHIME_EDITION "plus-disc" CACHE STRING'))

    readme = (root / "docs/PLUS_DISC.md").read_text()
    readme = readme.replace("# Tsukihime Plus Disc Vita Release\n", "# Tsukihime Plus Disc Vita\n")
    readme = readme.replace("[BUILDING.md](BUILDING.md)", "[BUILDING.md](docs/BUILDING.md)")
    readme = readme.replace("[THIRD_PARTY.md](../THIRD_PARTY.md)", "[THIRD_PARTY.md](THIRD_PARTY.md)")
    readme = readme.replace("The default CMake edition remains `original`, building the original Tsukihime port.",
                            "This repository builds the `plus-disc` edition by default. The shared engine also retains the original Tsukihime build profile.")
    download = ("![Plus Disc LiveArea artwork](assets/plus-disc-livearea/bg.png)\n\n"
                "## Download\n\n"
                "Download [TsukihimePlusDiscVita-Release.vpk](https://github.com/OZZ0AB/tsukihime-plus-disc-vita/releases/latest/download/TsukihimePlusDiscVita-Release.vpk) from the [latest release](https://github.com/OZZ0AB/tsukihime-plus-disc-vita/releases/latest). The release includes corresponding source and checksums.\n\n"
                "Prepare the game data on your computer using the tool below. Game archives, scripts, translation, font, and music are supplied from your own compatible copy.\n\n")
    readme = readme.replace("## Included features\n", download + "## Included features\n", 1)
    readme = readme.replace("Python 3 and Pillow are required.",
                            "Download and extract the release source archive, or clone this repository, then open a terminal in that folder. Python 3 and Pillow are required. Install Pillow with `python -m pip install Pillow` (use `python3` on systems where that is the Python 3 command).")
    (repository / "README.md").write_text(readme)
    notices = (repository / "THIRD_PARTY.md").read_text()
    notices += ("\n## Plus Disc adaptation\n\n"
                "The preparation tool adapts local KiriKiri XP3 scripts and media to this native ONScripter runtime. Game and translation data are generated locally and are excluded from the source repository and public release. The archive layout is documented by [KiriKiri's reference XP3 reader](https://github.com/krkrz/krkrz/blob/master/base/XP3Archive.cpp). The native menu, script adapter, and Plus Disc build profile accompany the shared Tsukihime Vita changes under GPL-2.0-or-later.\n")
    (repository / "THIRD_PARTY.md").write_text(notices)

    forbidden = {".nsa", ".sar", ".xp3", ".ogg", ".wav", ".ttf", ".exe", ".dll", ".vpk", ".ks", ".tjs", ".pyc", ".zip"}
    emoji = re.compile("[\U0001F000-\U0001FAFF\u2600-\u27BF]")
    for path in repository.rglob("*"):
        if not path.is_file():
            continue
        relative = path.relative_to(repository)
        if path.suffix.lower() in forbidden or path.name in {"nscript.dat", "plus-disc-data.json"}:
            raise SystemExit(f"Unexpected game/binary file in source: {relative}")
        if any(p in {".git", ".aws", ".codex", ".agents", ".vitasdk", "build", "Tsukihime", "Tsukihime Plus Disc", "__pycache__"} for p in relative.parts):
            raise SystemExit(f"Unexpected private path in source: {relative}")
        if path.suffix == ".md":
            text = path.read_text()
            if emoji.search(text) or "/home/bashar/" in text or "/media/bashar/" in text:
                raise SystemExit(f"Private path or emoji in public documentation: {relative}")

    shutil.copy2(vpk, assets / vpk.name)
    source = assets / "TsukihimePlusDiscVita-Release-source.tar.gz"
    with tarfile.open(source, "w:gz") as archive:
        archive.add(repository, arcname="TsukihimePlusDiscVita-Release-source")
    files = (assets / vpk.name, source)
    (assets / "SHA256SUMS").write_text("".join(f"{sha256(path)}  {path.name}\n" for path in files))
    manifest = {"repository_name": REPOSITORY, "release_tag": TAG, "app_version": VERSION,
                "title_id": "TSUPL0001", "upstream_commit": UPSTREAM,
                "source_files": sum(p.is_file() for p in repository.rglob("*")),
                "release_assets": [{"name": p.name, "bytes": p.stat().st_size, "sha256": sha256(p)} for p in files]}
    (output / "release-manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()
