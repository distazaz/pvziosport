#!/usr/bin/env python3
"""Check which reanim files expected by the port are missing from a given main.pak."""
import re
import sys
from pathlib import Path


def read_xor(f, size):
    data = f.read(size)
    if len(data) != size:
        raise ValueError("unexpected end of main.pak")
    return bytes(b ^ 0xF7 for b in data)


def pak_files(pak_path):
    with pak_path.open("rb") as f:
        if read_xor(f, 4) != b"\xc0\x4a\xc0\xba":
            raise ValueError("invalid main.pak signature")
        if int.from_bytes(read_xor(f, 4), "little") != 0:
            raise ValueError("unsupported main.pak version")
        names = []
        while True:
            flags = read_xor(f, 1)[0]
            if flags & 0x80:
                break
            name_width = read_xor(f, 1)[0]
            name = read_xor(f, name_width).decode("utf-8").replace("\\", "/").lower()
            size = int.from_bytes(read_xor(f, 4), "little")
            read_xor(f, 8)
            names.append(name)
    return set(names)


def main():
    pak = Path(sys.argv[1])
    source = Path(sys.argv[2]) if len(sys.argv) > 2 else Path("src/PvzpLib/Reanimator.cpp")
    expected = set(re.findall(r'mReanimFileName\s*=\s*"([^"]+)"', source.read_text(encoding="utf-8")))
    present = pak_files(pak)
    missing = sorted(name for name in expected if name.lower() not in present)
    print(f"expected reanim files: {len(expected)}")
    print(f"found: {len(expected) - len(missing)}")
    print(f"missing: {len(missing)}")
    for name in missing:
        print("  " + name)


if __name__ == "__main__":
    main()
