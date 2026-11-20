#!/usr/bin/env python3
"""news-r6 deliverer for make.fun entry news-image-20261119.

Copies the rendered entry.png (sitting next to this file) byte-identically
into the output directory and verifies it before and after the copy.
Standard library only: no image library is imported or needed, so this
script runs in a bare interpreter with no third-party packages installed.

Layout of the checks, in order:
  1. source exists, is a file, and is at most 1 MiB (1_048_576 bytes);
  2. first two bytes are the JPEG SOI marker (FF D8);
  3. last two bytes are the JPEG EOI marker (FF D9);
  4. a marker walk finds a baseline/progressive SOF segment and the frame
     inside it measures exactly 1024 x 1024;
  5. the SHA-256 of the delivered file matches the SHA-256 of the source.

The write itself is atomic: bytes go to a temporary file in the destination
directory, are flushed and fsynced, are moved into place with os.replace,
and the destination directory is fsynced; only then is the delivered file
read back and compared. Any failure aborts with a "news-r6:" message and a
non-zero exit status, and never leaves a partial entry.png behind.
"""

import hashlib
import os
import sys

MAX_BYTES = 1_048_576
WANT_WIDTH = 1024
WANT_HEIGHT = 1024

# SOF markers that carry frame dimensions (baseline + progressive + the
# lossless/arithmetic variants). DHT/DAC/JPGn/RSTn/COM are not SOF.
SOF_MARKERS = frozenset(
    [0xC0, 0xC1, 0xC2, 0xC3, 0xC5, 0xC6, 0xC7,
     0xC9, 0xCA, 0xCB, 0xCD, 0xCE, 0xCF]
)


def _u16be(buf, off):
    """Two bytes at off as an unsigned big-endian integer."""
    return (buf[off] << 8) | buf[off + 1]


def _frame_size(data):
    """Return (width, height) from the first SOF segment of a JPEG.

    Walks the marker stream by hand: a marker is FF xx, followed (for
    every marker except SOI, EOI, RSTn and TEM) by a 2-byte segment length
    that includes the length bytes themselves. Returns None when no SOF
    segment is found before the scan data starts.
    """
    if len(data) < 4 or data[0] != 0xFF or data[1] != 0xD8:
        return None
    pos = 2
    end = len(data)
    while pos + 1 < end:
        if data[pos] != 0xFF:
            return None
        marker = data[pos + 1]
        if marker == 0xFF:  # padding byte, step past it
            pos += 1
            continue
        if marker == 0xD9:  # EOI: stream over, no SOF seen
            return None
        if marker == 0xDA:  # SOS: scan data follows, SOF must precede it
            return None
        if marker in SOF_MARKERS:
            if pos + 9 >= end:
                return None
            height = _u16be(data, pos + 5)
            width = _u16be(data, pos + 7)
            return (width, height)
        if marker in (0xD8, 0x01) or 0xD0 <= marker <= 0xD7:
            pos += 2  # standalone marker, no length field
            continue
        if pos + 4 > end:
            return None
        seg_len = _u16be(data, pos + 2)
        if seg_len < 2 or pos + 2 + seg_len > end:
            return None
        pos += 2 + seg_len
    return None


def _check_source(data):
    """Validate raw entry bytes; return (sha256 hex, width, height)."""
    if len(data) > MAX_BYTES:
        raise ValueError(
            "source is %d bytes, over the %d-byte limit" % (len(data), MAX_BYTES)
        )
    if len(data) < 4:
        raise ValueError("source is too short to be a JPEG (%d bytes)" % len(data))
    if data[0] != 0xFF or data[1] != 0xD8:
        raise ValueError("source does not start with the JPEG SOI marker FFD8")
    if data[-2] != 0xFF or data[-1] != 0xD9:
        raise ValueError("source does not end with the JPEG EOI marker FFD9")
    size = _frame_size(data)
    if size is None:
        raise ValueError("no SOF frame segment found in source")
    width, height = size
    if (width, height) != (WANT_WIDTH, WANT_HEIGHT):
        raise ValueError(
            "frame is %dx%d, expected %dx%d"
            % (width, height, WANT_WIDTH, WANT_HEIGHT)
        )
    digest = hashlib.sha256(data).hexdigest()
    return digest, width, height


def _fsync_dir(path):
    """Fsync a directory so a rename inside it is durable. Best effort on
    platforms where opening a directory is not allowed."""
    try:
        fd = os.open(path, os.O_RDONLY)
    except OSError:
        return
    try:
        os.fsync(fd)
    except OSError:
        pass
    finally:
        os.close(fd)


def _deliver(data, digest, dest_dir):
    """Atomically write data as entry.png in dest_dir, then read it back
    and confirm it is byte-identical. Returns the destination path."""
    os.makedirs(dest_dir, exist_ok=True)
    dest = os.path.join(dest_dir, "entry.png")
    tmp = os.path.join(dest_dir, ".entry.png.tmp.%d" % os.getpid())
    try:
        with open(tmp, "wb") as fh:
            fh.write(data)
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp, dest)
        _fsync_dir(dest_dir)
    finally:
        try:
            os.unlink(tmp)
        except OSError:
            pass
    with open(dest, "rb") as fh:
        back = fh.read()
    if back != data:
        raise ValueError("read-back differs from source (%d vs %d bytes)"
                         % (len(back), len(data)))
    if hashlib.sha256(back).hexdigest() != digest:
        raise ValueError("read-back SHA-256 does not match source")
    return dest


def _run(argv):
    here = os.path.dirname(os.path.abspath(__file__))
    src = os.path.join(here, "entry.png")
    dest_dir = os.environ.get("MAKEFUN_OUTPUT_DIR") or "/output"
    if len(argv) > 2:
        raise ValueError("usage: main.py [output-dir]")
    if len(argv) == 2:
        dest_dir = argv[1]
    if not os.path.isfile(src):
        raise ValueError("source entry.png not found next to main.py: %s" % src)
    with open(src, "rb") as fh:
        data = fh.read()
    digest, width, height = _check_source(data)
    dest = _deliver(data, digest, dest_dir)
    sys.stdout.write(
        "news-r6: delivered %s (%d bytes, %dx%d, sha256 %s)\n"
        % (dest, len(data), width, height, digest)
    )
    return 0


def main():
    try:
        return _run(sys.argv)
    except (OSError, ValueError) as exc:
        sys.stderr.write("news-r6: error: %s\n" % exc)
        return 1


if __name__ == "__main__":
    sys.exit(main())
