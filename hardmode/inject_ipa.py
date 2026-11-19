#!/usr/bin/env python3
"""Inject game assets into an unsigned PvZ Portable IPA.

The iOS build looks for main.pak/properties in Documents first and in the app
bundle second, so embedding the files makes the IPA self-contained.

Usage:
    python hardmode/inject_ipa.py <input.ipa> <assets_dir> <output.ipa>

<assets_dir> must contain main.pak and the properties/ folder.

Note: modifying an IPA invalidates its code signature. Re-sign it when
installing (AltStore/SideStore do this automatically; TrollStore also works).
"""
import sys
import zipfile
from pathlib import Path

APP_PREFIX = "Payload/pvz-portable.app/"


def main():
    ipa = Path(sys.argv[1])
    assets = Path(sys.argv[2])
    output = Path(sys.argv[3])

    main_pak = assets / "main.pak"
    properties = assets / "properties"
    if not main_pak.is_file() or not properties.is_dir():
        raise SystemExit(f"assets directory must contain main.pak and properties/: {assets}")

    with zipfile.ZipFile(ipa, "r") as src, zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as dst:
        for info in src.infolist():
            data = src.read(info.filename)
            dst.writestr(info, data)
        dst.write(main_pak, APP_PREFIX + "main.pak")
        for file in sorted(properties.rglob("*")):
            if file.is_file():
                dst.write(file, APP_PREFIX + "properties/" + file.relative_to(properties).as_posix())

    print(f"wrote {output} ({output.stat().st_size} bytes)")


if __name__ == "__main__":
    main()
