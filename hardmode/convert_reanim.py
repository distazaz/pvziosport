#!/usr/bin/env python3
"""Convert PvZ 1.0.0.1051 compiled reanim definitions into the XML source format
expected by PvZ-Portable.

Usage:
    python hardmode/convert_reanim.py <input_dir> <output_dir>

<input_dir> should contain compiled/reanim/*.reanim.compiled (e.g. an unpacked
main.pak). XML files are written to <output_dir>/reanim/*.reanim.
"""
import struct
import sys
import zlib
from pathlib import Path

OLD_DEF_SIZE = 16       # ReanimatorDefinition (32-bit)
OLD_TRACK_SIZE = 12     # ReanimatorTrack (32-bit)
OLD_TRANSFORM_SIZE = 44 # ReanimatorTransform (32-bit)


class Reader:
    def __init__(self, data):
        self.data = data
        self.pos = 0

    def take(self, n):
        result = self.data[self.pos:self.pos + n]
        if len(result) != n:
            raise ValueError(f"unexpected end of compiled data at {self.pos}")
        self.pos += n
        return result

    def u32(self):
        return struct.unpack("<I", self.take(4))[0]

    def f32(self):
        return struct.unpack("<f", self.take(4))[0]

    def string(self):
        length = self.u32()
        raw = self.take(length)
        return raw.decode("utf-8", errors="replace")


def escape(text):
    return (text.replace("&", "&amp;").replace("<", "&lt;")
                .replace(">", "&gt;").replace('"', "&quot;"))


def fmt(value):
    return f"{value:.9g}"


def convert(path):
    compressed = path.read_bytes()
    raw = zlib.decompress(compressed[8:])
    r = Reader(raw)
    def_hash = r.u32()  # noqa: F841 - old schema hash, discarded

    track_count = struct.unpack_from("<I", raw, 4 + 4)[0]
    fps = struct.unpack_from("<f", raw, 4 + 8)[0]
    r.take(OLD_DEF_SIZE)

    track_array_size = r.u32()
    if track_array_size != OLD_TRACK_SIZE:
        raise ValueError(f"{path}: unexpected track size {track_array_size}")
    track_raw = r.take(OLD_TRACK_SIZE * track_count)
    tracks = []
    for i in range(track_count):
        name_ptr, transform_ptr, transform_count = struct.unpack_from("<III", track_raw, i * OLD_TRACK_SIZE)
        tracks.append((transform_count, name_ptr, transform_ptr))

    # The engine reads a flat sequence of field elements; there is no root tag.
    lines = [f"<fps>{fmt(fps)}</fps>"]
    for transform_count, _, _ in tracks:
        name = r.string()
        lines.append("  <track>")
        lines.append(f"    <name>{escape(name)}</name>")
        transform_size = r.u32()
        if transform_size != OLD_TRANSFORM_SIZE:
            raise ValueError(f"{path}: unexpected transform size {transform_size}")
        transforms_raw = r.take(OLD_TRANSFORM_SIZE * transform_count)
        for i in range(transform_count):
            values = struct.unpack_from("<8f", transforms_raw, i * OLD_TRANSFORM_SIZE)
            image = r.string()
            font = r.string()
            text = r.string()
            lines.append("    <t>")
            for key, value in zip(("x", "y", "kx", "ky", "sx", "sy", "f", "a"), values):
                lines.append(f"      <{key}>{fmt(value)}</{key}>")
            if image:
                lines.append(f"      <i>{escape(image)}</i>")
            if font:
                lines.append(f"      <font>{escape(font)}</font>")
            if text:
                lines.append(f"      <text>{escape(text)}</text>")
            lines.append("    </t>")
        lines.append("  </track>")
    return "\n".join(lines) + "\n"


def main():
    source = Path(sys.argv[1])
    target = Path(sys.argv[2])
    compiled_dir = source / "compiled" / "reanim"
    files = sorted(compiled_dir.glob("*.reanim.compiled"))
    if not files:
        raise SystemExit(f"no compiled reanim files in {compiled_dir}")
    out_dir = target / "reanim"
    out_dir.mkdir(parents=True, exist_ok=True)
    ok = 0
    errors = []
    for file in files:
        name = file.name[:-len(".compiled")]
        try:
            (out_dir / name).write_text(convert(file), encoding="utf-8")
            ok += 1
        except Exception as exc:
            errors.append(f"{name}: {exc}")
    print(f"converted {ok}/{len(files)} reanim definitions to {out_dir}")
    for error in errors:
        print("  ERROR " + error)


if __name__ == "__main__":
    main()
