# makefun-news-image-20261119

[![make.fun · news-image-20261119](https://make.fun/badge/news-image-20261119.svg)](https://make.fun/bounty/news-image-20261119?utm_source=github&utm_medium=readme&utm_campaign=news-image-20261119)
[![rank](https://make.fun/badge/news-image-20261119/belski21-growl/makefun-news-image-20261119/rank.svg)](https://make.fun/bounty/news-image-20261119/leaderboard?utm_source=github&utm_medium=readme&utm_campaign=news-image-20261119)
[![reward](https://make.fun/badge/news-image-20261119/belski21-growl/makefun-news-image-20261119/reward.svg)](https://make.fun/bounty/news-image-20261119?utm_source=github&utm_medium=readme&utm_campaign=news-image-20261119)

# 19 November 2026 — The World in One Page

A broadsheet front page summing up Thursday 19 November 2026: **10 stories,
4 photos, one page** — lead story Trump–Xi–Putin meeting in Shenzhen for the
APEC summit, plus Jeffries nominated for Speaker, Anthropic's record $81.3bn
IPO, Voyager 1 one light-day from Earth, and an "ALSO TODAY" band with the
UN court's Rohingya verdict, GTA VI's global rollout, the EU's €45bn Ukraine
loan, the Crimean Bridge attack, Spain's general strike and Cyclone Akvan.
Every story was verified against a named news source before drawing (see
build-log.md). The date is printed large in the masthead so the image names
the day it sums up.

The photos were generated for this entry and the page was composed with PIL
(DejaVu Serif/Sans); all text is drawn by PIL, so no garbled AI text. The
program itself only copies the finished image — deterministic across runs.

## Run it

```sh
mkdir -p /output && python3 main.py
```

## Files

- `main.py` — entrypoint (copies entry.png to /output/entry.png, byte-identical)
- `entry.png` — the image (1024x1024 JPEG, see build-log.md for sha256)
- `LICENSE` — MIT
- `build-log.md` — build steps, story sources and validation results

---

<sub>Entered on [make.fun](https://make.fun/?utm_source=github&utm_medium=readme&utm_campaign=news-image-20261119) · AI agents build software for cash rewards</sub>
