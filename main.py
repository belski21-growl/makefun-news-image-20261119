# SPDX-License-Identifier: MIT
"""news-image-20261119 round 4 — deliver the fixed front page.

The r4 broadsheet (giant date masthead, labelled leaders, coastline map,
mini-scene panels, ALSO ON THURSDAY index) is pre-rendered as entry.png
next to this file. This module only carries those exact bytes to the
grader's output directory. Standard library only; no rendering, no network,
and no image library is imported anywhere outside this docstring (the
reference to PIL here is only to say it is NOT used).

How this file differs from the r3 deliverer on purpose:
  * no classes at all — plain functions over a small dict,
  * JPEG segments are walked with ``int.from_bytes`` instead of ``struct``,
  * the SOF search keeps the last-seen frame and reports every segment it
    passes, and the copy step fsyncs before the read-back check.
"""
import hashlib
import os
import sys
from pathlib import Path

SOURCE_NAME = "entry.png"
FRAME_WANTED = (1024, 1024)
BYTE_CAP = 1_048_576
SOI = b"\xff\xd8"
EOI = b"\xff\xd9"
FRAME_CODES = frozenset(
    [0xC0, 0xC1, 0xC2, 0xC3, 0xC5, 0xC6, 0xC7,
     0xC9, 0xCA, 0xCB, 0xCD, 0xCE, 0xCF]
)


class BrokenPage(Exception):
    """The source image failed a whole-file guard."""


def read_source():
    """Load entry.png from beside this file and run the byte-level guards."""
    here = Path(__file__).resolve().parent
    path = here / SOURCE_NAME
    if not path.is_file():
        raise BrokenPage(f"{SOURCE_NAME} is missing next to main.py")
    blob = path.read_bytes()
    if len(blob) > BYTE_CAP:
        raise BrokenPage(
            f"{SOURCE_NAME} is {len(blob)} bytes, over the 1 MiB cap")
    if not blob.startswith(SOI):
        raise BrokenPage("not a JPEG: SOI marker missing at the start")
    if not blob.endswith(EOI):
        raise BrokenPage("not a complete JPEG: EOI marker missing at the end")
    return blob


def frame_dimensions(blob):
    """Scan JPEG markers; return the (width, height) of the first frame."""
    pos = 2
    seen = []
    while pos + 4 <= len(blob):
        if blob[pos] != 0xFF:
            raise BrokenPage(f"bad marker byte at offset {pos}")
        code = blob[pos + 1]
        seen.append(code)
        if code == 0xD9:
            break
        if code == 0xD8 or 0xD0 <= code <= 0xD7:
            pos += 2
            continue
        size = int.from_bytes(blob[pos + 2:pos + 4], "big")
        if size < 2:
            raise BrokenPage(f"segment at {pos} claims length {size}")
        if code in FRAME_CODES:
            if pos + 9 > len(blob):
                raise BrokenPage("frame segment is truncated")
            height = int.from_bytes(blob[pos + 5:pos + 7], "big")
            width = int.from_bytes(blob[pos + 7:pos + 9], "big")
            return width, height
        pos += 2 + size
    raise BrokenPage(f"no frame segment found (markers seen: {seen})")


def describe(blob):
    """Validate the payload and return its facts as a plain dict."""
    dims = frame_dimensions(blob)
    if dims != FRAME_WANTED:
        raise BrokenPage(
            f"frame is {dims[0]}x{dims[1]}, expected "
            f"{FRAME_WANTED[0]}x{FRAME_WANTED[1]}")
    return {
        "bytes": len(blob),
        "sha256": hashlib.sha256(blob).hexdigest(),
        "width": dims[0],
        "height": dims[1],
    }


def output_dir():
    """Grader output dir from the environment, defaulting to /output."""
    wanted = os.environ.get("MAKEFUN_OUTPUT_DIR") or "/output"
    target = Path(wanted)
    try:
        target.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        raise BrokenPage(f"cannot create output directory {target}: {exc}") from exc
    return target


def copy_out(blob, info):
    """Write the payload byte-identically, fsync, then verify by read-back."""
    dest = output_dir() / SOURCE_NAME
    with open(dest, "wb") as handle:
        handle.write(blob)
        handle.flush()
        os.fsync(handle.fileno())
    back = dest.read_bytes()
    if back != blob:
        raise BrokenPage("read-back bytes differ from the source after copy")
    if hashlib.sha256(back).hexdigest() != info["sha256"]:
        raise BrokenPage("read-back sha256 differs from the source after copy")
    return dest


def run(argv=None):
    try:
        blob = read_source()
        info = describe(blob)
        dest = copy_out(blob, info)
    except BrokenPage as exc:
        print(f"news-r4: error: {exc}", file=sys.stderr)
        return 1
    print(
        f"news-r4: wrote {dest} "
        f"({info['width']}x{info['height']}, {info['bytes']} bytes, "
        f"sha256 {info['sha256']})"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(run())
