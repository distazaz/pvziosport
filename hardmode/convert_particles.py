#!/usr/bin/env python3
"""Convert compiled 32-bit particle definitions into the XML source format.

Usage:
    python hardmode/convert_particles.py <unpacked_dir>

The compiled blobs live in <unpacked_dir>/compiled/particles/*.xml.compiled.
XML files are written next to them in <unpacked_dir>/particles/.
"""
import re
import struct
import sys
import zlib
from pathlib import Path

TRACK_FIELDS_BEFORE_ARRAYS = [
    "SystemDuration", "CrossFadeDuration", "SpawnRate", "SpawnMinActive",
    "SpawnMaxActive", "SpawnMaxLaunched", "EmitterRadius", "EmitterOffsetX",
    "EmitterOffsetY", "EmitterBoxX", "EmitterBoxY", "EmitterSkewX",
    "EmitterSkewY", "EmitterPath", "ParticleDuration", "LaunchSpeed",
    "LaunchAngle", "SystemRed", "SystemGreen", "SystemBlue", "SystemAlpha",
    "SystemBrightness",
]
TRACK_FIELDS_AFTER_ARRAYS = [
    "ParticleRed", "ParticleGreen", "ParticleBlue", "ParticleAlpha",
    "ParticleBrightness", "ParticleSpinAngle", "ParticleSpinSpeed",
    "ParticleScale", "ParticleStretch", "CollisionReflect", "CollisionSpin",
    "ClipTop", "ClipBottom", "ClipLeft", "ClipRight", "AnimationRate",
]
EMITTER_SYMBOLS = {0: "Circle", 1: "Box", 2: "BoxPath", 3: "CirclePath", 4: "CircleEvenSpacing"}
FIELD_SYMBOLS = {
    1: "Friction", 2: "Acceleration", 3: "Attractor", 4: "MaxVelocity", 5: "Velocity",
    6: "Position", 7: "SystemPosition", 8: "GroundConstraint", 9: "Shake", 10: "Circle", 11: "Away",
}
FLAG_SYMBOLS = {
    0: "RandomLaunchSpin", 1: "AlignLaunchSpin", 2: "AlignToPixel", 4: "ParticleLoops",
    3: "SystemLoops", 5: "ParticlesDontFollow", 6: "RandomStartTime", 7: "DieIfOverloaded",
    8: "Additive", 9: "FullScreen", 10: "SoftwareOnly", 11: "HardwareOnly",
}


class Reader:
    def __init__(self, data):
        self.data = data
        self.pos = 0

    def take(self, n):
        result = self.data[self.pos:self.pos + n]
        if len(result) != n:
            raise ValueError(f"unexpected end of data at {self.pos}")
        self.pos += n
        return result

    def u32(self):
        return struct.unpack("<I", self.take(4))[0]

    def i32(self):
        return struct.unpack("<i", self.take(4))[0]

    def f32(self):
        return struct.unpack("<f", self.take(4))[0]

    def string(self):
        length = self.u32()
        return self.take(length).decode("utf-8", errors="replace")

    def track(self):
        count = self.u32()
        values = []
        for _ in range(count):
            time, low, high, curve, distribution = struct.unpack("<5f", self.take(20))
            values.append((low + high) * 0.5)
        return " ".join(f"{v:.9g}" for v in values) if values else "0"

    def field_array(self, tag):
        elem_size = self.u32()
        count = self.u32()
        if elem_size != 20:
            raise ValueError(f"unexpected ParticleField size {elem_size}")
        result = []
        for _ in range(count):
            field_type = self.i32()
            x_track = self.track()
            y_track = self.track()
            result.append(
                f"  <{tag}>\n"
                f"    <FieldType>{FIELD_SYMBOLS.get(field_type, 'Velocity')}</FieldType>\n"
                f"    <x>{x_track}</x>\n"
                f"    <y>{y_track}</y>\n"
                f"  </{tag}>"
            )
        return result


def escape(text):
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def convert(path):
    raw = zlib.decompress(path.read_bytes()[8:])
    r = Reader(raw)
    r.u32()  # schema hash
    r.u32()  # emitter array pointer placeholder
    emitter_count = r.i32()
    emitter_size = r.u32()
    # The cache stores all raw structs first, then dynamic data for each element.
    emitters = []
    for _ in range(emitter_count):
        emitter = r.take(emitter_size)
        image_ptr, image_col, image_row, image_frames, animated, flags, emitter_type = struct.unpack_from("<7i", emitter, 0)
        emitters.append((image_col, image_row, image_frames, animated, flags, emitter_type))

    lines = []
    for image_col, image_row, image_frames, animated, flags, emitter_type in emitters:
        lines.append("<Emitter>")
        image = r.string()
        if image:
            lines.append(f"  <Image>{escape(image)}</Image>")
        lines.append(f"  <ImageCol>{image_col}</ImageCol>")
        lines.append(f"  <ImageRow>{image_row}</ImageRow>")
        lines.append(f"  <ImageFrames>{image_frames}</ImageFrames>")
        lines.append(f"  <Animated>{animated}</Animated>")
        for bit, name in FLAG_SYMBOLS.items():
            if flags & (1 << bit):
                lines.append(f"  <{name}>1</{name}>")
        lines.append(f"  <EmitterType>{EMITTER_SYMBOLS.get(emitter_type, 'Circle')}</EmitterType>")
        lines.append(f"  <Name>{escape(r.string())}</Name>")
        lines.append(f"  <SystemDuration>{r.track()}</SystemDuration>")
        lines.append(f"  <OnDuration>{escape(r.string())}</OnDuration>")
        for name in TRACK_FIELDS_BEFORE_ARRAYS[1:]:
            lines.append(f"  <{name}>{r.track()}</{name}>")
        lines.extend(r.field_array("Field"))
        lines.extend(r.field_array("SystemField"))
        for name in TRACK_FIELDS_AFTER_ARRAYS:
            lines.append(f"  <{name}>{r.track()}</{name}>")
        lines.append("</Emitter>")
    return "\n".join(lines) + "\n"


def main():
    root = Path(sys.argv[1])
    compiled_dir = root / "compiled" / "particles"
    files = sorted(compiled_dir.glob("*.xml.compiled"))
    if not files:
        raise SystemExit(f"no compiled particle files in {compiled_dir}")
    out_dir = root / "particles"
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
    print(f"converted {ok}/{len(files)} particle definitions to {out_dir}")
    for error in errors:
        print("  ERROR " + error)


if __name__ == "__main__":
    main()
