#!/usr/bin/env python3
"""Prepare local Plus Disc English 1.2 data for the native Vita runtime.

Reads the user's XP3 archives; generates ONScripter commands and copies referenced
media without shipping any game or translation content in this source file.
"""
import argparse
import collections
import hashlib
import io
import json
import re
import shutil
import struct
import zipfile
import zlib
from pathlib import Path, PurePosixPath

from PIL import Image

STORIES = (
    ("幻視同盟.ks", "Alliance of Illusion"),
    ("げっちゃ.ks", "Geccha"),
    ("真・弓塚夢想3.ks", "Geccha 2"),
    ("きのこ名作実験場.ks", "Kinoko's Experimental Theater"),
)
MAGIC = b"XP3\r\n \n\x1a\x8bg\x01"
MAX_ENTRY = 32 * 1024 * 1024


class PreparationError(ValueError):
    pass


def chunks(data):
    offset = 0
    while offset < len(data):
        if offset + 12 > len(data):
            raise PreparationError("Truncated XP3 chunk")
        tag = data[offset:offset + 4]
        size = struct.unpack_from("<Q", data, offset + 4)[0]
        end = offset + 12 + size
        if end > len(data):
            raise PreparationError("XP3 chunk exceeds its index")
        yield tag, data[offset + 12:end]
        offset = end


def inflate(data, expected):
    if expected > MAX_ENTRY:
        raise PreparationError("XP3 entry exceeds the supported size")
    dec = zlib.decompressobj()
    out = dec.decompress(data, expected + 1)
    if len(out) != expected or not dec.eof or dec.unconsumed_tail:
        raise PreparationError("Invalid compressed XP3 entry")
    return out


class XP3:
    def __init__(self, path):
        self.path = Path(path)
        self.data = self.path.read_bytes()
        if self.data[:11] != MAGIC:
            raise PreparationError(f"Not a standard XP3 archive: {self.path.name}")
        self.entries = {}
        pointer = 11
        visited = set()
        while True:
            offset = struct.unpack_from("<Q", self.data, pointer)[0]
            if offset in visited or offset + 9 > len(self.data):
                raise PreparationError("Invalid XP3 index chain")
            visited.add(offset)
            flags = self.data[offset]
            if flags & 7 == 1:
                packed, raw = struct.unpack_from("<QQ", self.data, offset + 1)
                index = inflate(self.data[offset + 17:offset + 17 + packed], raw)
                pointer = offset + 17 + packed
            elif flags & 7 == 0:
                raw = struct.unpack_from("<Q", self.data, offset + 1)[0]
                if raw > MAX_ENTRY:
                    raise PreparationError("XP3 index is too large")
                index = self.data[offset + 9:offset + 9 + raw]
                if len(index) != raw:
                    raise PreparationError("Truncated XP3 index")
                pointer = offset + 9 + raw
            else:
                raise PreparationError("Unsupported XP3 index encoding")
            for tag, payload in chunks(index):
                if tag != b"File":
                    continue
                fields = dict(chunks(payload))
                info = fields[b"info"]
                protection, size, archived, length = struct.unpack_from("<IQQH", info)
                name = info[22:22 + length * 2].decode("utf-16le")
                if len(info[22:]) != length * 2 or size > MAX_ENTRY:
                    raise PreparationError("Unsupported XP3 entry metadata")
                segments = fields[b"segm"]
                if len(segments) % 28:
                    raise PreparationError("Invalid XP3 segment table")
                self.entries[name] = {
                    "size": size, "archived": archived, "protection": protection,
                    "segments": list(struct.iter_unpack("<IQQQ", segments)),
                    "adler": struct.unpack("<I", fields[b"adlr"])[0],
                }
            if not flags & 0x80:
                break

    def read(self, name):
        entry = self.entries[name]
        parts = []
        for flags, offset, raw, packed in entry["segments"]:
            if offset + packed > len(self.data) or raw > MAX_ENTRY:
                raise PreparationError("XP3 segment exceeds the archive")
            part = self.data[offset:offset + packed]
            if flags & 7 == 1:
                part = inflate(part, raw)
            elif flags & 7 != 0:
                raise PreparationError("Unsupported XP3 segment encoding")
            if len(part) != raw:
                raise PreparationError("Invalid XP3 segment length")
            parts.append(part)
        data = b"".join(parts)
        if len(data) != entry["size"] or zlib.adler32(data) & 0xffffffff != entry["adler"]:
            raise PreparationError(f"XP3 checksum failed: {name}")
        return data


def tag_args(tag):
    name = tag.split(None, 1)[0].lower()
    attrs = {}
    pattern = r'([A-Za-z_][A-Za-z_0-9]*)=(?:"((?:\\.|[^"\\])*)"|([^\s]*))'
    for match in re.finditer(pattern, tag[len(name):]):
        value = match[2] if match[2] is not None else match[3]
        attrs[match[1].lower()] = value.replace('\\"', '"').replace('\\\\', '\\')
    return name, attrs


def inline_tokens(line):
    """KAG tags may contain a closing bracket inside quoted attributes."""
    pos = 0
    while pos < len(line):
        start = line.find("[", pos)
        if start < 0:
            yield "text", line[pos:]
            break
        if start > pos:
            yield "text", line[pos:start]
        end, quote, escape = start + 1, False, False
        while end < len(line):
            c = line[end]
            if escape:
                escape = False
            elif c == "\\" and quote:
                escape = True
            elif c == '"':
                quote = not quote
            elif c == "]" and not quote:
                break
            end += 1
        if end == len(line):
            raise PreparationError("Unterminated KAG inline tag")
        yield "tag", tag_args(line[start + 1:end])
        pos = end + 1


class Media:
    def __init__(self, archives, output, music=None):
        self.output = output
        self.music = Path(music) if music else None
        self.external = {}
        self.lookup = {}
        self.copied = {}
        self.payloads = {}
        self.images = {}
        for archive in archives:  # patch.xp3 intentionally wins by basename.
            for name in archive.entries:
                if "/CVS/" in name or "protectet archive" in name:
                    continue
                base = PurePosixPath(name).name.lower()
                self.lookup[base] = (archive, name)

    def resolve(self, storage, audio=False):
        base = PurePosixPath(storage.replace("\\", "/")).name.lower()
        candidates = [base] if PurePosixPath(base).suffix else [
            base + ext for ext in ((".ogg", ".wav") if audio else (".png", ".jpg", ".bmp"))]
        for candidate in candidates:
            if candidate in self.lookup:
                return candidate
        if audio and self.music:
            match = re.fullmatch(r"tmcd-0101_(\d{2})", base)
            if match:
                for suffix in (".ogg", ".wav"):
                    path = self.music / ("track" + match[1] + suffix)
                    if path.is_file():
                        key = base + suffix
                        self.external[key] = path
                        return key
        raise PreparationError(f"Missing referenced media: {storage}")

    def use(self, storage, audio=False):
        key = self.resolve(storage, audio)
        if key not in self.copied:
            if key in self.external:
                original = self.external[key].name
                data = self.external[key].read_bytes()
            else:
                archive, original = self.lookup[key]
                data = archive.read(original)
            suffix = PurePosixPath(key).suffix
            relative = "media/" + hashlib.sha256(key.encode()).hexdigest()[:20] + suffix
            self.payloads[relative] = data
            if not audio:
                with Image.open(io.BytesIO(data)) as image:
                    image.verify()
                with Image.open(io.BytesIO(data)) as image:
                    self.images[key] = image.size
            elif not data.startswith((b"OggS", b"RIFF")):
                raise PreparationError(f"Unrecognized audio payload: {original}")
            self.copied[key] = {"path": relative, "bytes": len(data),
                                "sha256": hashlib.sha256(data).hexdigest()}
        return self.copied[key]["path"]

    def dimensions(self, storage):
        self.use(storage)
        return self.images[self.resolve(storage)]


class Compiler:
    def __init__(self, media):
        self.media = media
        self.lines = []
        self.counts = collections.Counter()
        self.effects = {}
        self.sound_channels = {}
        self.story_reports = []
        self.dialogue = []
        self.compact = False

    def emit(self, *lines):
        self.lines.extend(lines)

    def effect(self, attrs, default=800):
        duration = attrs.get("time", str(default))
        if not duration.isdigit():
            # English 1.2 has one source typo: Japanese dialogue was appended
            # directly to a numeric time attribute. Retain its numeric prefix.
            match = re.fullmatch(r"(\d+)[^\x00-\x7f].*", duration)
            if not match:
                raise PreparationError(f"Invalid transition time: {duration}")
            duration = match[1]
            self.counts["source_time_typo"] += 1
        duration = min(int(duration), 10000)
        if duration == 0:
            return 1
        rule = attrs.get("rule", "")
        # Native NScripter effects corresponding to the source wipe rules.
        kind = {"シャッター左から": 2, "シャッター右から": 3,
                "シャッター上から": 4, "シャッター下から": 5,
                "カーテン左から": 6, "カーテン右から": 7,
                "カーテン上から": 8, "カーテン下から": 9}.get(rule, 10)
        key = kind, duration
        if key not in self.effects:
            self.effects[key] = len(self.effects) + 2
        return self.effects[key]

    def window(self, compact=False):
        self.compact = compact
        if compact:
            self.emit("setwindow 37,349,33,4,17,17,0,4,22,1,1,#aaaaaa,16,344,623,463")
        else:
            self.emit("setwindow 18,18,36,21,17,17,0,4,22,1,1,#aaaaaa,0,0,639,479")

    def text(self, text):
        if not text:
            return
        if not text.isascii() or any(c in text for c in "`@\\_\r\n"):
            raise PreparationError("Unsupported literal character in English dialogue")
        self.dialogue.append(text)
        self.emit("puttext `" + text + "`")

    @staticmethod
    def position(attrs):
        pos = attrs.get("pos", "c")
        pos = {"left": "l", "right": "r", "center": "c",
               "left_center": "lc", "right_center": "rc"}.get(pos, pos)
        if pos == "all":
            return pos, 0, 0
        if pos not in {"l", "r", "c", "lc", "rc"}:
            raise PreparationError(f"Unknown character position: {pos}")
        return pos, {"l": 14, "r": 13, "lc": 12, "rc": 11, "c": 10}[pos], {
            "l": 160, "lc": 240, "c": 320, "rc": 400, "r": 480}[pos]

    def command(self, name, attrs):
        self.counts[name] += 1
        if name in {"wrap", "wq", "wrocket"}:
            return
        if name in {"pg", "p"}:
            self.emit("puttext `\\`", "csp 0")
        elif name in {"cm", "ct"}:
            self.emit("textclear", "csp 0")
        elif name == "r":
            self.emit("br")
        elif name == "l":
            self.emit("puttext `@`")
        elif name in {"texton", "textoff"}:
            self.emit(name)
        elif name in {"position", "resetposition2"}:
            self.window()
        elif name == "position2":
            self.window(True)
        elif name in {"fadein", "bg", "black", "blackout", "white", "flushover"}:
            if name in {"bg", "black", "white"}:
                self.emit("textoff")
            storage = {"black": "black", "blackout": "black",
                       "white": "white", "flushover": "white"}.get(name, attrs.get("file"))
            path = self.media.use(storage)
            if attrs.get("noclear", "false") != "true":
                self.emit(*[f"csp {i}" for i in range(10, 15)])
            self.emit(f'bg "{path}",{self.effect(attrs)}')
            if name in {"bg", "black", "white"}:
                self.emit("texton")
        elif name in {"ld", "ld_auto", "ld_notrans"}:
            pos, sprite, center = self.position(attrs)
            path = self.media.use(attrs["file"])
            width, height = self.media.dimensions(attrs["file"])
            horizon = int(attrs.get("horizon", "0"))
            if name == "ld":
                self.emit("textoff")
            self.emit(f'lsp {sprite},":a;{path}",{center - width // 2},{480 - height - horizon}')
            if name != "ld_notrans":
                self.emit(f"print {self.effect(attrs)}")
            if name == "ld":
                self.emit("texton")
        elif name in {"cl", "cl_auto", "cl_notrans"}:
            pos, sprite, _ = self.position({"pos": attrs.get("pos", "all")})
            if name == "cl":
                self.emit("textoff")
            self.emit(*[f"csp {i}" for i in (range(10, 15) if pos == "all" else [sprite])])
            if name != "cl_notrans":
                self.emit(f"print {self.effect(attrs)}")
            if name == "cl":
                self.emit("texton")
        elif name in {"play", "xchgbgm"}:
            path = self.media.use(attrs.get("file", attrs.get("storage")), True)
            duration = int(attrs.get("time", attrs.get("overlap", "0")))
            self.emit(f"bgmfadein {duration}", f'bgm "{path}"')
        elif name == "playstop":
            self.emit(f'bgmfadeout {int(attrs.get("time", "0"))}', "bgmstop")
        elif name == "bgmopt":
            self.emit(f'bgmvol {int(attrs.get("volume", "100"))}')
        elif name in {"wave", "waveloop"}:
            storage = attrs["file"]
            path = self.media.use(storage, True)
            # Reuse a channel per looping sample, preserving simultaneous sounds.
            if name == "waveloop":
                channel = self.sound_channels.setdefault(storage, 1 + len(self.sound_channels))
                if channel > 12:
                    raise PreparationError("Too many simultaneous sound channels")
                self.emit(f'dwaveloop {channel},"{path}"')
            else:
                self.emit(f'dwave 15,"{path}"')
        elif name == "wavestop":
            storage = attrs.get("file")
            channels = [self.sound_channels[storage]] if storage in self.sound_channels else self.sound_channels.values()
            self.emit(*[f"dwavestop {i}" for i in channels])
        elif name == "wait":
            self.emit(f'wait {int(attrs["time"])}')
        elif name == "flash":
            # A short native negative-image flash keeps the timing and scene.
            self.emit("nega 1", "print 1", f'wait {int(attrs.get("time", "200"))}', "nega 0", "print 1")
        elif name == "quake":
            self.emit(f'quake {max(int(attrs.get("hmax", "4")), int(attrs.get("vmax", "4")))},{int(attrs.get("time", "400"))}')
        elif name == "rocket":
            pos, sprite, _ = self.position({"pos": attrs["layer"]})
            self.emit(f'msp {sprite},0,{int(attrs.get("my", "0"))},0',
                      f'print {self.effect({"time": attrs.get("time", "800")})}')
        elif name == "jump":
            if attrs.get("storage") != "タイトル.ks":
                raise PreparationError("Unexpected story jump")
            self.emit("goto *main_menu")
        elif name == "graph":
            path = self.media.use(attrs["storage"])
            self.emit("getcursorpos %970,%971", f'lsp 0,":a;{path}",%970,%971', "print 1")
            self.text("   ")
        else:
            raise PreparationError(f"Unsupported story command: {name}")

    def story(self, index, source):
        filename, title = STORIES[index]
        self.emit(f"*story_{index}", "saveon", "textclear", "csp -1", "bgmstop")
        self.window()
        before = len(self.dialogue)
        before_lines = len(self.lines)
        for lineno, line in enumerate(source.splitlines(), 1):
            if not line or line.startswith(";"):
                continue
            try:
                if line.startswith("*"):
                    # Page labels are linear; no translated story branches use them.
                    label = line[1:].split("|", 1)[0]
                    self.emit(f"*s{index}_{hashlib.sha256(label.encode()).hexdigest()[:12]}")
                elif line.startswith("@"):
                    name, attrs = tag_args(line[1:])
                    self.command(name, attrs)
                else:
                    text = ""
                    for kind, item in inline_tokens(line):
                        if kind == "text":
                            text += item
                        elif item[0] == "wrap":
                            self.counts["wrap"] += 1
                        else:
                            self.text(text)
                            text = ""
                            self.command(*item)
                    self.text(text)
            except (KeyError, ValueError, TypeError) as exc:
                raise PreparationError(f"{filename}:{lineno}: {exc}") from exc
        self.emit("goto *main_menu")
        visible = "".join(self.dialogue[before:])
        self.story_reports.append({"title": title, "source": filename,
                                   "source_lines": len(source.splitlines()),
                                   "generated_commands": len(self.lines) - before_lines,
                                   "text_segments": len(self.dialogue) - before,
                                   "visible_characters": len(visible),
                                   "text_sha256": hashlib.sha256(visible.encode()).hexdigest()})

    def menu(self):
        self.emit("*start", "goto *main_menu", "*main_menu", "saveoff", "textclear", "csp -1", "bgmstop",
                  'setwindow 36,140,34,12,16,16,0,6,22,1,1,#999999,0,0,639,479',
                  f'bg "{self.media.use("menu_bg")}",1')
        options = [f'`{title}`,*story_{i}' for i, (_, title) in enumerate(STORIES)]
        options += ['`Gallery`,*gallery_0', '`Load saved game`,*load_menu', '`Quit`,*quit_port']
        self.emit("select " + ",".join(options), "*load_menu", "systemcall load", "goto *main_menu",
                  "*quit_port", "end")

    def gallery(self):
        # The English patch supplies one localized copy of each of the 24
        # gallery images; the base archive also holds Japanese duplicates.
        names = sorted(k for k in self.media.lookup if k.endswith("_smpl.jpg") and k.isascii())
        if not names:
            raise PreparationError("No Plus Disc gallery samples were found")
        groups = [names[i:i + 6] for i in range(0, len(names), 6)]
        for page, group in enumerate(groups):
            self.emit(f"*gallery_{page}", "saveoff", "textclear", "csp -1",
                      'setwindow 36,80,34,16,16,16,0,6,22,1,1,#999999,0,0,639,479', 'bg black,1')
            choices = []
            for j, name in enumerate(group):
                title = name[:-9].replace("_", " ").title()
                choices.append(f'`{title}`,*gallery_view_{page}_{j}')
            if page:
                choices.append(f'`Previous page`,*gallery_{page - 1}')
            if page + 1 < len(groups):
                choices.append(f'`Next page`,*gallery_{page + 1}')
            choices.append('`Return to title`,*main_menu')
            self.emit("select " + ",".join(choices))
            for j, name in enumerate(group):
                self.emit(f"*gallery_view_{page}_{j}", "textclear", "textoff",
                          f'bg "{self.media.use(name)}",1', "click", f"goto *gallery_{page}")
        return len(names)

    def compile(self, sources):
        self.menu()
        gallery_count = self.gallery()
        for i, (filename, _) in enumerate(STORIES):
            self.story(i, sources[filename])
        header = [";mode640", "*define", 'caption "Tsukihime Plus Disc Vita"', "english",
                  "savenumber 20", "globalon", "clickstr ``,2",
                  "rmenu `Save game`,save,`Load game`,load,`History`,lookback,`Hide text`,windowerase,`Return to title`,reset",
                  "savename `Save game`,`Load game`,`Slot`", "lookbackcolor #ffffd0"]
        for (kind, time), number in self.effects.items():
            header.append(f"effect {number},{kind},{time}")
        script = "\n".join(header + ["game"] + self.lines) + "\n"
        return script, gallery_count


def prepare(source, font, output, zip_path=None, music=None):
    source, font, output = Path(source), Path(font), Path(output)
    if output.exists():
        raise PreparationError("Output already exists; choose a new folder to preserve prior data")
    if zip_path and Path(zip_path).exists():
        raise PreparationError("Data ZIP already exists")
    archives = [XP3(source / name) for name in ("data.xp3", "patch.xp3")]
    media = Media(archives, output, music)
    sources = {}
    for filename, _ in STORIES:
        if filename.lower() not in media.lookup:
            raise PreparationError(f"English 1.2 story not found: {filename}")
        archive, name = media.lookup[filename.lower()]
        raw = archive.read(name)
        sources[filename] = raw.decode("utf-16")
        if "[wrap text=" not in sources[filename]:
            raise PreparationError("This preparer requires the mirror moon English 1.2 patch")
    if not font.is_file() or font.stat().st_size < 1024:
        raise PreparationError("Supply an English-capable TrueType font with --font")
    compiler = Compiler(media)
    script, gallery_count = compiler.compile(sources)
    encoded = script.encode("ascii")
    output.mkdir(parents=True, exist_ok=True)
    for relative, data in media.payloads.items():
        dest = output / relative
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(data)
    shutil.copyfile(font, output / "default.ttf")
    (output / "nscript.dat").write_bytes(bytes(c ^ 0x84 for c in encoded))
    manifest = {"format": 1, "edition": "tsukihime-plus-disc-english-1.2",
                "runtime": "native-onscripter-jh", "title_id": "TSUPL0001",
                "script_sha256": hashlib.sha256(encoded).hexdigest(),
                "archives": {a.path.name: hashlib.sha256(a.data).hexdigest() for a in archives},
                "stories": compiler.story_reports, "gallery_images": gallery_count,
                "media": media.copied, "source_commands": dict(compiler.counts),
                "external_music": [path.name for path in media.external.values()],
                "adaptations": ["Native ONS menu and gallery navigation replace TJS widgets.",
                                "Rocket effects use native sprite movement; zoom acceleration is simplified.",
                                "Unsupported source wipe rules use native crossfades.",
                                "Sound fades use the native mixer; overlapping BGM changes start the new track."]}
    (output / "plus-disc-data.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n")
    if zip_path:
        zip_path = Path(zip_path)
        if zip_path.exists():
            raise PreparationError("Data ZIP already exists")
        zip_path.parent.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
            for path in sorted(output.rglob("*")):
                if path.is_file():
                    archive.write(path, "data/tsukihime_plus_disc/game/" + str(path.relative_to(output)))
    return manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True, help="Plus Disc Game folder containing data.xp3 and patch.xp3")
    parser.add_argument("--font", type=Path, required=True)
    parser.add_argument("--music", type=Path, help="Tsukihime CD tracks for soundtrack cues not included in the Plus Disc XP3")
    parser.add_argument("--output", type=Path, default=Path("build/plus-disc-data/game"))
    parser.add_argument("--zip", dest="zip_path", type=Path)
    args = parser.parse_args()
    try:
        result = prepare(args.source, args.font, args.output, args.zip_path, args.music)
    except (PreparationError, OSError, struct.error, zlib.error, UnicodeError) as exc:
        parser.exit(1, f"Preparation failed: {exc}\n")
    print(json.dumps({"stories": result["stories"], "gallery_images": result["gallery_images"],
                      "media_files": len(result["media"]), "output": str(args.output)}, indent=2))


if __name__ == "__main__":
    main()
