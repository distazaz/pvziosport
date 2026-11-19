import struct
import sys
from pathlib import Path

data = Path(sys.argv[1]).read_bytes()
if data[:8] == b"\x89PNG\r\n\x1a\n":
    print("PNG", struct.unpack(">II", data[16:24]))
else:
    i = 2
    while i < len(data) - 10:
        if data[i] != 0xFF:
            i += 1
            continue
        marker = data[i + 1]
        length = int.from_bytes(data[i + 2:i + 4], "big")
        if marker in (0xC0, 0xC1, 0xC2):
            height = int.from_bytes(data[i + 5:i + 7], "big")
            width = int.from_bytes(data[i + 7:i + 9], "big")
            print("JPEG", (width, height))
            break
        i += 2 + length
