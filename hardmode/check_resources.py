#!/usr/bin/env python3
"""List resource IDs requested by the engine but absent from a resources.xml."""
import re
import sys
from pathlib import Path


def main():
    source = Path(sys.argv[1]).read_text(encoding="utf-8")
    manifest = Path(sys.argv[2]).read_text(encoding="utf-8")
    images = set(re.findall(r'GetImageThrow\("([^"]+)"\)', source))
    fonts = set(re.findall(r'GetFontThrow\("([^"]+)"\)', source))
    sounds = set(re.findall(r'GetSoundThrow\("([^"]+)"\)', source))
    missing_images = sorted(x for x in images if f'id="{x.removeprefix("IMAGE_")}"' not in manifest)
    missing_fonts = sorted(x for x in fonts if f'id="{x.removeprefix("FONT_")}"' not in manifest)
    missing_sounds = sorted(x for x in sounds if f'id="{x.removeprefix("SOUND_")}"' not in manifest or f'id="{x}"' not in manifest)
    print(f"required images: {len(images)}, missing from manifest: {len(missing_images)}")
    for name in missing_images:
        print("  IMAGE " + name)
    print(f"required fonts: {len(fonts)}, missing from manifest: {len(missing_fonts)}")
    for name in missing_fonts:
        print("  FONT " + name)
    print(f"required sounds: {len(sounds)}, missing from manifest: {len(missing_sounds)}")
    for name in missing_sounds:
        print("  SOUND " + name)


if __name__ == "__main__":
    main()
