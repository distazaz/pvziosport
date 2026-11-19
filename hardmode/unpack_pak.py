#!/usr/bin/env python3
"""Unpack all files from a PvZ main.pak into a directory."""
import sys
from pathlib import Path


def read_xor(f, size):
    data = f.read(size)
    if len(data) != size:
        raise ValueError("unexpected end of main.pak")
    return bytes(b ^ 0xF7 for b in data)


def main():
    pak = Path(sys.argv[1])
    out_dir = Path(sys.argv[2])
    with pak.open("rb") as f:
        if read_xor(f, 4) != b"\xc0\x4a\xc0\xba":
            raise ValueError("invalid main.pak signature")
        if int.from_bytes(read_xor(f, 4), "little") != 0:
            raise ValueError("unsupported main.pak version")
        entries = []
        offset = 0
        while True:
            flags = read_xor(f, 1)[0]
            if flags & 0x80:
                data_start = f.tell()
                break
            name_width = read_xor(f, 1)[0]
            name = read_xor(f, name_width).decode("utf-8").replace("\\", "/")
            size = int.from_bytes(read_xor(f, 4), "little")
            read_xor(f, 8)
            entries.append((name, offset, size))
            offset += size
        for name, file_offset, size in entries:
            f.seek(data_start + file_offset)
            data = read_xor(f, size)
            target = out_dir / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(data)
        print(f"unpacked {len(entries)} files to {out_dir}")


if __name__ == "__main__":
    main()
