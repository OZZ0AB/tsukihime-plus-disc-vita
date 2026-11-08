#!/usr/bin/env python3
"""Check a prepared local Plus Disc script against its source and media."""
import argparse
import collections
import hashlib
import importlib.util
import json
import re
from pathlib import Path

root = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("plusprep", root / "scripts/prepare_plus_disc.py")
prep = importlib.util.module_from_spec(spec)
spec.loader.exec_module(prep)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("prepared", type=Path)
    args = parser.parse_args()
    manifest = json.loads((args.prepared / "plus-disc-data.json").read_text())
    encoded = bytes(c ^ 0x84 for c in (args.prepared / "nscript.dat").read_bytes())
    assert hashlib.sha256(encoded).hexdigest() == manifest["script_sha256"]
    script = encoded.decode("ascii")
    labels = re.findall(r"^\*([a-zA-Z_0-9]+)$", script, re.M)
    assert len(labels) == len(set(labels))
    # All jump/selection destinations exist; no dangling story or gallery links.
    destinations = re.findall(r"(?:goto |,)\*([a-zA-Z_0-9]+)", script)
    assert set(destinations) <= set(labels)
    lut = "\n".join(p.read_text(errors="replace") for p in (
        root / "engine/src/onsjh/ONScripter_lut.cpp",
        root / "engine/src/onsjh/ScriptParser.cpp"))
    commands = set(re.findall(r'\{\s*"([a-z0-9_]+)"', lut))
    generated = set(re.findall(r"^([a-z][a-z0-9_]*)", script, re.M))
    assert generated <= commands, generated - commands

    for media in manifest["media"].values():
        data = (args.prepared / media["path"]).read_bytes()
        assert len(data) == media["bytes"]
        assert hashlib.sha256(data).hexdigest() == media["sha256"]
    refs = set(re.findall(r"media/[a-z0-9]+\.[a-z]+", script))
    assert refs == {x["path"] for x in manifest["media"].values()}

    patch = prep.XP3(args.source / "patch.xp3")
    for i, (filename, title) in enumerate(prep.STORIES):
        source = patch.read(filename).decode("utf-16")
        original = []
        for line in source.splitlines():
            if not line or line.startswith(("@", ";", "*")):
                continue
            # Independent quote-aware tag removal: wrap's attribute is metadata,
            # and each word following the tag is the visible English text.
            original.append(re.sub(r'\[(?:[^"\]]|"[^"]*")*\]', '', line))
        block = script.split(f"*story_{i}\n", 1)[1]
        if i + 1 < len(prep.STORIES):
            block = block.split(f"*story_{i + 1}\n", 1)[0]
        converted = re.findall(r"^puttext `([^`]*)`$", block, re.M)
        converted = [t for t in converted if t not in ("@", "\\")]
        normalize = lambda text: re.sub(r"\s+", "", text)
        assert normalize("".join(original)) == normalize("".join(converted)), title
        assert len(re.findall(r"\[l\]", source)) + sum(line == "@l" for line in source.splitlines()) == sum(
            1 for t in re.findall(r"^puttext `([^`]*)`$", block, re.M) if t == "@"), title
        print(f"{title}: visible English text and click waits preserved")
    assert manifest["gallery_images"] == 24
    print(f"{len(labels)} labels, {len(refs)} media references, all four stories and 24 gallery entries: OK")


if __name__ == "__main__":
    main()
