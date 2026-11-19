#!/usr/bin/env python3
"""Extract one file from a PvZ main.pak (for diagnostics)."""
import sys
from pathlib import Path


def read_xor(f, size):
    data = f.read(size)
    if len(data) != size:
        raise ValueError("unexpected end of main.pak")
    return bytes(b ^ 0xF7 for b in data)


def main():
    pak = Path(sys.argv[1])
    wanted = sys.argv[2].replace("\\", "/").lower()
    out = Path(sys.argv[3])
    with pak.open("rb") as f:
        if read_xor(f, 4) != b"\xc0\x4a\xc0\xba":
            raise ValueError("invalid main.pak signature")
        if int.from_bytes(read_xor(f, 4), "little") != 0:
            raise ValueError("unsupported main.pak version")
        entries = {}
        offset = 0
        while True:
            flags = read_xor(f, 1)[0]
            if flags & 0x80:
                data_start = f.tell()
                break
            name_width = read_xor(f, 1)[0]
            name = read_xor(f, name_width).decode("utf-8").replace("\\", "/").lower()
            size = int.from_bytes(read_xor(f, 4), "little")
            read_xor(f, 8)
            entries[name] = (offset, size)
            offset += size
        if wanted not in entries:
            raise SystemExit(f"not found: {wanted}")
        file_offset, size = entries[wanted]
        f.seek(data_start + file_offset)
        out.write_bytes(read_xor(f, size))
        print(f"extracted {wanted} ({size} bytes) -> {out}")


if __name__ == "__main__":
    main()
