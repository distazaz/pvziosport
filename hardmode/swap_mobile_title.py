#!/usr/bin/env python3
"""Replace the GOTY title/loading background with the HD mobile-version art."""
import io
import sys
from pathlib import Path

from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent))
from prepare_assets import parse_pak, write_pak  # noqa: E402


def main():
    pak_path = Path(sys.argv[1])
    png_path = Path(sys.argv[2])
    out_path = Path(sys.argv[3]) if len(sys.argv) > 3 else pak_path

    img = Image.open(png_path).convert("RGB").resize((1080, 600), Image.LANCZOS)
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=92)
    jpeg = buf.getvalue()

    entries, raw = parse_pak(pak_path)
    files = {}
    for name, extra, size, offset in entries:
        from prepare_assets import xor_bytes
        files[name] = xor_bytes(raw[offset:offset + size])

    target = "images/titlescreen.jpg"
    if target not in files:
        raise SystemExit(f"{target} not found in {pak_path}")
    files[target] = jpeg

    write_pak(out_path, sorted(files.items()))
    print(f"patched {out_path}: {target} <- {png_path.name} ({len(jpeg)} bytes)")


if __name__ == "__main__":
    main()
