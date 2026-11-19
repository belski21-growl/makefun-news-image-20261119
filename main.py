"""Entry for make.fun news-image-20261119.

Copies the pre-built front-page image (entry.png, next to this file)
to the output directory as entry.png, byte for byte.

No network, no randomness, no third-party code: the same input bytes
always produce the same output bytes.
"""

import os

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "entry.png")
OUT_DIR = os.environ.get("MAKEFUN_OUTPUT_DIR", "/output")
DST = os.path.join(OUT_DIR, "entry.png")
MAX_BYTES = 1048576


def main():
    if not os.path.isfile(SRC):
        raise SystemExit("missing entry.png next to main.py")
    with open(SRC, "rb") as f:
        data = f.read()
    if len(data) == 0 or len(data) > MAX_BYTES:
        raise SystemExit("entry.png size out of bounds: %d bytes" % len(data))
    is_png = data[:8] == b"\x89PNG\r\n\x1a\n"
    is_jpeg = data[:2] == b"\xff\xd8" and data[-2:] == b"\xff\xd9"
    if not (is_png or is_jpeg):
        raise SystemExit("entry.png is neither a whole PNG nor a whole JPEG")
    os.makedirs(OUT_DIR, exist_ok=True)
    with open(DST, "wb") as f:
        f.write(data)
    with open(DST, "rb") as f:
        written = f.read()
    if written != data:
        raise SystemExit("output bytes differ from entry.png")


if __name__ == "__main__":
    main()
