#!/usr/bin/env python3
"""news-r5 deliverer for the 19 November 2026 front page.

This script does NOT render anything and does NOT need Pillow or any
third-party package: it only ships the pre-rendered entry.png that sits
next to it, byte for byte, to the output directory.  The grader runs
plain python:3.13, so everything here is standard library only.

Safety checks before the copy is accepted:
  * the source must exist and be a JPEG (SOI FFD8 at the front, EOI FFD9
    at the back);
  * the SOF0/SOF2 frame header must declare exactly 1024x1024;
  * the file must be at most 1 MiB;
  * after writing, the output is read back and its sha256 must match
    the source, otherwise the run fails loudly instead of shipping a
    truncated file.

Output location: $MAKEFUN_OUTPUT_DIR when set, else ./output.
The file is written to a temporary sibling first and then atomically
renamed over the destination, so a failed run never leaves a partial
entry.png behind.
"""

import hashlib
import os
import sys
from pathlib import Path

ENTRY_NAME = "entry.png"
EXPECTED_W = 1024
EXPECTED_H = 1024
MAX_BYTES = 1024 * 1024


def fail(message):
    print("news-r5: error: " + message, file=sys.stderr)
    raise SystemExit(1)


def read_source():
    here = Path(__file__).resolve().parent
    src = here / ENTRY_NAME
    if not src.is_file():
        fail("source not found next to this script: " + str(src))
    blob = src.read_bytes()
    if len(blob) > MAX_BYTES:
        fail("source is %d bytes, over the 1 MiB limit" % len(blob))
    if len(blob) < 4 or blob[0:2] != b"\xff\xd8" or blob[-2:] != b"\xff\xd9":
        fail("source is not a JPEG (missing SOI/FFD8 or EOI/FFD9)")
    return blob


def jpeg_size(blob):
    """Find the first SOF0/SOF2 frame header and return (width, height).

    Walks the marker stream by hand: every marker is 0xFF followed by a
    marker byte and a 2-byte big-endian segment length (length includes
    its own two bytes). Standalone markers (SOI, RSTn, TEM) carry no
    length field and are skipped accordingly.
    """
    pos = 2
    end = len(blob)
    standalone = {0xD8, 0xD9, 0x01} | set(range(0xD0, 0xD8))
    while pos + 4 <= end:
        if blob[pos] != 0xFF:
            fail("corrupt JPEG marker stream at offset %d" % pos)
        marker = blob[pos + 1]
        if marker in standalone:
            pos += 2
            continue
        seg_len = (blob[pos + 2] << 8) | blob[pos + 3]
        if seg_len < 2 or pos + 2 + seg_len > end:
            fail("corrupt JPEG segment at offset %d" % pos)
        if marker in (0xC0, 0xC1, 0xC2):
            height = (blob[pos + 5] << 8) | blob[pos + 6]
            width = (blob[pos + 7] << 8) | blob[pos + 8]
            return width, height
        pos += 2 + seg_len
    fail("no SOF frame header found in source JPEG")


def deliver(blob):
    out_dir = Path(os.environ.get("MAKEFUN_OUTPUT_DIR", "output"))
    out_dir.mkdir(parents=True, exist_ok=True)
    dest = out_dir / ENTRY_NAME
    tmp = out_dir / (ENTRY_NAME + ".tmp-r5")
    with open(tmp, "wb") as handle:
        handle.write(blob)
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(tmp, dest)
    echoed = dest.read_bytes()
    if hashlib.sha256(echoed).hexdigest() != hashlib.sha256(blob).hexdigest():
        fail("read-back mismatch: output is not byte-identical to source")
    return dest


def run():
    blob = read_source()
    width, height = jpeg_size(blob)
    if (width, height) != (EXPECTED_W, EXPECTED_H):
        fail("frame is %dx%d, expected %dx%d"
             % (width, height, EXPECTED_W, EXPECTED_H))
    dest = deliver(blob)
    print("news-r5: wrote %s (%d bytes, %dx%d, sha256 %s)"
          % (dest, len(blob), width, height,
             hashlib.sha256(blob).hexdigest()))


if __name__ == "__main__":
    run()
