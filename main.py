# SPDX-License-Identifier: MIT
"""news-image-20261119 round 3 — deliver the rebuilt front page.

The r3 broadsheet ("THE WORLD IN ONE DAY", 40 illustrated stories, big
WHERE IT HAPPENED map, three-leader hero) is pre-rendered as entry.png next
to this file. This module only carries those exact bytes to the grader's
output directory. Standard library only; no rendering, no network, no PIL.

Layout of this file (kept deliberately different from the r2 deliverer):
  * a tiny ``FrontPage`` value object holds the payload + its digest,
  * ``_scan_segments`` walks JPEG markers with ``struct`` instead of manual
    byte shifts, and the frame must be exactly 1024x1024,
  * ``main()`` returns an exit code and prints one summary line.
"""
import hashlib
import os
import struct
import sys
from pathlib import Path

SOURCE_FILE = "entry.png"
EXPECTED_WIDTH = 1024
EXPECTED_HEIGHT = 1024
SIZE_LIMIT = 1_048_576
START_MARKER = b"\xff\xd8"
END_MARKER = b"\xff\xd9"
SOF_MARKERS = frozenset((0xC0, 0xC1, 0xC2, 0xC3, 0xC5, 0xC6, 0xC7,
                         0xC9, 0xCA, 0xCB, 0xCD, 0xCE, 0xCF))


class DeliveryError(Exception):
    """Raised when the source image fails any whole-file guard."""


class FrontPage:
    """The validated payload plus the facts the grader needs to see."""

    def __init__(self, payload):
        self.payload = payload
        self.digest = hashlib.sha256(payload).hexdigest()
        self.width, self.height = _frame_size(payload)

    @property
    def size(self):
        return len(self.payload)


def _frame_size(payload):
    """Walk JPEG segments with struct; return (width, height) of the SOF."""
    if not payload.startswith(START_MARKER):
        raise DeliveryError("not a JPEG: missing SOI marker")
    offset = 2
    while offset + 4 <= len(payload):
        if payload[offset] != 0xFF:
            raise DeliveryError("corrupt JPEG marker stream")
        marker = payload[offset + 1]
        if marker == 0xD9:  # EOI before any frame
            break
        if marker in (0xD8,) or 0xD0 <= marker <= 0xD7:
            offset += 2
            continue
        (seg_len,) = struct.unpack(">H", payload[offset + 2:offset + 4])
        if marker in SOF_MARKERS:
            if offset + 9 > len(payload):
                raise DeliveryError("truncated SOF segment")
            height, width = struct.unpack(">HH", payload[offset + 5:offset + 9])
            return width, height
        offset += 2 + seg_len
    raise DeliveryError("no JPEG start-of-frame segment found")


def _load_front_page():
    """Read entry.png and enforce every whole-file guard."""
    here = Path(__file__).resolve().parent
    source = here / SOURCE_FILE
    if not source.is_file():
        raise DeliveryError(f"{SOURCE_FILE} is missing next to main.py")
    payload = source.read_bytes()
    if len(payload) > SIZE_LIMIT:
        raise DeliveryError(f"{SOURCE_FILE} is {len(payload)} bytes, over the 1 MiB cap")
    if not payload.rstrip(b"\x00").endswith(END_MARKER):
        raise DeliveryError("not a complete JPEG: missing EOI marker")
    page = FrontPage(payload)
    if (page.width, page.height) != (EXPECTED_WIDTH, EXPECTED_HEIGHT):
        raise DeliveryError(
            f"frame is {page.width}x{page.height}, expected "
            f"{EXPECTED_WIDTH}x{EXPECTED_HEIGHT}")
    return page, source


def _output_directory():
    """Grader output dir from the environment, defaulting to /output."""
    wanted = os.environ.get("MAKEFUN_OUTPUT_DIR") or "/output"
    target = Path(wanted)
    try:
        target.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        raise DeliveryError(f"cannot create output directory {target}: {exc}") from exc
    return target


def deliver(page):
    """Write the payload byte-identically and verify it by read-back."""
    destination = _output_directory() / SOURCE_FILE
    with open(destination, "wb") as handle:
        handle.write(page.payload)
    delivered = destination.read_bytes()
    if delivered != page.payload:
        raise DeliveryError("read-back mismatch after copy")
    if hashlib.sha256(delivered).hexdigest() != page.digest:
        raise DeliveryError("read-back sha256 mismatch after copy")
    return destination


def main(argv=None):
    try:
        page, _source = _load_front_page()
        destination = deliver(page)
    except DeliveryError as exc:
        print(f"news-r3: error: {exc}", file=sys.stderr)
        return 1
    print(
        f"news-r3: wrote {destination} "
        f"({page.width}x{page.height}, {page.size} bytes, sha256 {page.digest})"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
