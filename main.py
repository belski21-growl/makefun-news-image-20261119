# SPDX-License-Identifier: MIT
"""Deliver the r2 front page for make.fun news-image-20261119.

Copies the pre-rendered broadsheet (entry.png, JPEG 1024x1024, 40 stories)
byte-identically to the output directory. Standard library only; no network.
"""
import hashlib
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
SOURCE_NAME = "entry.png"
BYTE_CAP = 1_048_576
MAX_EDGE = 1024
JPEG_SOI = b"\xff\xd8"
JPEG_EOI = b"\xff\xd9"


def _fail(message):
    print(f"frontpage-deliver: error: {message}", file=sys.stderr)
    raise SystemExit(1)


def _inspect_jpeg(payload):
    """Return (ok, reason) for the JPEG whole-file guards."""
    if len(payload) > BYTE_CAP:
        return False, f"image is {len(payload)} bytes, over the 1 MiB cap"
    if not payload.startswith(JPEG_SOI):
        return False, "missing JPEG start-of-image marker"
    if not payload.rstrip(b"\x00").endswith(JPEG_EOI):
        return False, "missing JPEG end-of-image marker"
    dims = _jpeg_dimensions(payload)
    if dims is None:
        return False, "cannot parse JPEG frame dimensions"
    width, height = dims
    if width > MAX_EDGE or height > MAX_EDGE:
        return False, f"image is {width}x{height}, over the {MAX_EDGE}px cap"
    return True, ""


def _jpeg_dimensions(payload):
    """Parse width/height from the first SOFn marker (stdlib only)."""
    pos = 2
    while pos + 9 < len(payload):
        if payload[pos] != 0xFF:
            return None
        marker = payload[pos + 1]
        if marker in (0xD8, 0xD9) or 0xD0 <= marker <= 0xD7:
            pos += 2
            continue
        size = (payload[pos + 2] << 8) | payload[pos + 3]
        if marker in (0xC0, 0xC1, 0xC2):
            height = (payload[pos + 5] << 8) | payload[pos + 6]
            width = (payload[pos + 7] << 8) | payload[pos + 8]
            return width, height
        pos += 2 + size
    return None


def _read_source():
    source = HERE / SOURCE_NAME
    if not source.is_file():
        _fail(f"{SOURCE_NAME} not found next to main.py")
    payload = source.read_bytes()
    ok, reason = _inspect_jpeg(payload)
    if not ok:
        _fail(reason)
    return payload


def _target_dir():
    wanted = os.environ.get("MAKEFUN_OUTPUT_DIR") or "/output"
    target = Path(wanted)
    try:
        target.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        _fail(f"cannot create output directory {target}: {exc}")
    return target


def publish_front_page():
    payload = _read_source()
    digest = hashlib.sha256(payload).hexdigest()
    width, height = _jpeg_dimensions(payload)
    target = _target_dir() / SOURCE_NAME
    with open(target, "wb") as handle:
        handle.write(payload)
    # Read-back: the delivered bytes must match the source exactly.
    delivered = target.read_bytes()
    if delivered != payload:
        _fail("read-back mismatch: delivered bytes differ from entry.png")
    if hashlib.sha256(delivered).hexdigest() != digest:
        _fail("read-back mismatch: sha256 differs after copy")
    print(f"frontpage-deliver: wrote {target} ({width}x{height}, {len(payload)} bytes, sha256 {digest})")
    return 0


if __name__ == "__main__":
    raise SystemExit(publish_front_page())
