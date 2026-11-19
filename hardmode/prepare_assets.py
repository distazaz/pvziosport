#!/usr/bin/env python3
"""Build a PvZ-Portable compatible main.pak from a 1.0.0.1051 installation.

The old release stores reanim definitions as compiled 32-bit blobs and lacks a
number of GOTY-only resources. This script:

  * unpacks main.pak
  * converts compiled reanim blobs into XML source files (see convert_reanim.py)
  * adds missing image entries to properties/resources.xml, pointing them at
    existing files or at a blank placeholder
  * fixes the case of the BrianneTod12 font file name
  * writes Properties/ZombatarTOS.txt
  * repacks everything into a new main.pak

Usage:
    python hardmode/prepare_assets.py <game_dir> <output_dir>

<game_dir> must contain main.pak and properties/. The output directory receives
a patched main.pak; copy the original properties/ folder next to it as well.
"""
import re
import struct
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from convert_reanim import convert  # noqa: E402


XOR_KEY = 0xF7
SIGNATURE = b"\xc0\x4a\xc0\xba"


def xor_bytes(data):
    return bytes(b ^ XOR_KEY for b in data)


def parse_pak(path):
    """Return (entries, raw) where entries are [name, extra, size]."""
    raw = path.read_bytes()
    if xor_bytes(raw[:4]) != SIGNATURE:
        raise ValueError("invalid main.pak signature")
    if struct.unpack("<I", xor_bytes(raw[4:8]))[0] != 0:
        raise ValueError("unsupported main.pak version")
    entries = []
    pos = 8
    while True:
        flags = xor_bytes(raw[pos:pos + 1])[0]
        pos += 1
        if flags & 0x80:
            data_start = pos
            break
        name_len = xor_bytes(raw[pos:pos + 1])[0]
        pos += 1
        name = xor_bytes(raw[pos:pos + name_len]).decode("utf-8").replace("\\", "/")
        pos += name_len
        size = struct.unpack("<I", xor_bytes(raw[pos:pos + 4]))[0]
        pos += 4
        extra = xor_bytes(raw[pos:pos + 8])
        pos += 8
        entries.append([name, extra, size, None])
    offset = data_start
    for entry in entries:
        entry[3] = offset
        offset += entry[2]
    return entries, raw


def write_pak(path, files):
    """files: list of (name, data) tuples."""
    index = bytearray()
    data = bytearray()
    for name, payload in files:
        name_raw = name.replace("/", "\\").encode("utf-8")
        if len(name_raw) > 255:
            raise ValueError("name too long: " + name)
        index += b"\x00"
        index += bytes([len(name_raw)])
        index += name_raw
        index += struct.pack("<I", len(payload))
        index += b"\x00" * 8
        data += payload
    index += b"\x80"
    payload = SIGNATURE + struct.pack("<I", 0) + bytes(index) + bytes(data)
    path.write_bytes(xor_bytes(payload))


def manifest_ids(manifest_text):
    """Return full resource IDs, taking SetDefaults idprefix into account."""
    result = set()
    prefix = ""
    for line in manifest_text.splitlines():
        prefix_match = re.search(r'<SetDefaults[^>]*idprefix="([^"]*)"', line)
        if prefix_match:
            prefix = prefix_match.group(1)
        id_match = re.search(r'<(?:Image|Font|Sound)\s+id="([^"]+)"', line)
        if id_match:
            result.add(prefix + id_match.group(1))
    return result


def main():
    game_dir = Path(sys.argv[1])
    out_dir = Path(sys.argv[2])
    pak_path = game_dir / "main.pak"
    out_dir.mkdir(parents=True, exist_ok=True)
    entries, raw = parse_pak(pak_path)

    files = {}
    for name, extra, size, offset in entries:
        files[name] = xor_bytes(raw[offset:offset + size])

    # Convert compiled reanim definitions to XML and drop the stale compiled blobs.
    converted = {}
    dropped = []
    for name, payload in list(files.items()):
        match = re.fullmatch(r"compiled/reanim/(.+)\.reanim\.compiled", name, re.IGNORECASE)
        if not match:
            continue
        reanim_name = "reanim/" + match.group(1) + ".reanim"
        blob_path = out_dir / "_blob.tmp"
        blob_path.write_bytes(payload)
        try:
            converted[reanim_name] = convert(blob_path).encode("utf-8")
        finally:
            blob_path.unlink(missing_ok=True)
        dropped.append(name)
    for name in dropped:
        del files[name]
    files.update(converted)

    # The single compiled trail definition has the same schema problem.
    # A minimal trail definition is enough for the boss ice effect.
    trail_name = "particles/IceTrail.trail"
    for name in list(files):
        if name.lower() == "compiled/particles/icetrail.trail.compiled":
            del files[name]
    files[trail_name] = (
        "<Image>IMAGE_ICETRAIL</Image>\n"
        "<MaxPoints>20</MaxPoints>\n"
        "<MinPointDistance>3</MinPointDistance>\n"
        "<Loops>1</Loops>\n"
        "<WidthOverLength>1</WidthOverLength>\n"
        "<WidthOverTime>1</WidthOverTime>\n"
        "<AlphaOverLength>1</AlphaOverLength>\n"
        "<AlphaOverTime>1</AlphaOverTime>\n"
        "<TrailDuration>100</TrailDuration>\n"
    ).encode("utf-8")

    # Fix case-sensitive font path.
    for name, payload in list(files.items()):
        if name.lower() == "properties/resources.xml":
            text = payload.decode("utf-8")
            text = text.replace('path="BrianneTod12.txt"', 'path="briannetod12.txt"')
            files[name] = text.encode("utf-8")
            manifest_name = name
            break
    else:
        raise ValueError("properties/resources.xml not found")

    # Add image entries required by the engine but absent from the manifest.
    source = (Path(__file__).resolve().parents[1] / "src" / "Resources.cpp").read_text(encoding="utf-8")
    required = set(re.findall(r'GetImageThrow\("IMAGE_([^"]+)"\)', source))
    manifest = files[manifest_name].decode("utf-8")
    existing = manifest_ids(manifest)
    missing = sorted("IMAGE_" + x for x in required if "IMAGE_" + x not in existing)

    lowered = {name.lower(): name for name in files}
    reanim_entries = []
    image_entries = []
    for full_id in missing:
        short_id = full_id.removeprefix("IMAGE_")
        base = short_id.lower()
        candidates = [f"reanim/{base}.png", f"images/{base}.png", f"data/{base}.png"]
        found = next((lowered[c] for c in candidates if c in lowered), None)
        if found and found.lower().startswith("reanim/"):
            path = "../" + found[:-4]
        elif found:
            path = found.split("/", 1)[-1][:-4]
        else:
            path = "blank"
        if short_id.startswith("REANIM_"):
            reanim_entries.append(f'<Image id="{short_id}" path="{path}" />')
        else:
            image_entries.append(f'<Image id="{short_id}" path="{path}" />')

    # Entries must live in a group that is actually loaded. "Init" is loaded at
    # startup; a separate group would be parsed but never loaded, and
    # GetImageThrow() requires resources to be already loaded.
    additions = ""
    all_entries = reanim_entries + image_entries
    if all_entries:
        additions = '\n  <SetDefaults path="images" idprefix="IMAGE_" />\n'
        additions += "\n".join("  " + line for line in all_entries) + "\n"
    manifest = manifest.replace("</Resources>", additions + "</Resources>", 1)
    files[manifest_name] = manifest.encode("utf-8")

    files["Properties/ZombatarTOS.txt"] = b""

    out_dir.mkdir(parents=True, exist_ok=True)
    write_pak(out_dir / "main.pak", sorted(files.items()))
    print(f"wrote {out_dir / 'main.pak'} ({len(files)} files, {len(missing)} image stubs)")


if __name__ == "__main__":
    main()
