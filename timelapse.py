# ABOUTME: Renders dated screenshot archives into timelapse MP4s.
# ABOUTME: Reads timelapses.yml; supports single-image and multi-page (paged) sources.
import argparse
import hashlib
import math
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

import yaml
from PIL import Image, ImageDraw, ImageFont

DATE_RE = re.compile(r"^(\d{4})-(\d{1,2})-(\d{1,2})$")
LAYOUTS = ("grid", "scroll", "pages")
FONT_PATHS = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf",
    "/System/Library/Fonts/SFNSMono.ttf",
    "/System/Library/Fonts/Menlo.ttc",
]


def normalize_date(name):
    """Return YYYY-MM-DD for names like 2024-9-30, or None if not a date."""
    match = DATE_RE.match(name)
    if not match:
        return None
    year, month, day = map(int, match.groups())
    return f"{year}-{month:02d}-{day:02d}"


def page_sort_key(path):
    numbers = re.findall(r"\d+", path.stem)
    return int(numbers[-1]) if numbers else 0


def load_days(source):
    """
    Return [(date, [page paths])] sorted by date.

    Flat sources hold one image per day (`fridge-poem/2024-02-23.png`).
    Paged sources hold one folder per day (`cursor-park/2024-02-23/page-1.png`).
    """
    days = {}
    for entry in Path(source).iterdir():
        if entry.is_dir():
            date = normalize_date(entry.name)
            pages = sorted(entry.glob("*.png"), key=page_sort_key)
            if date and pages:
                days[date] = pages
        elif entry.suffix == ".png":
            date = normalize_date(entry.stem)
            if date:
                days[date] = [entry]
    return sorted(days.items())


def load_font(size):
    for path in FONT_PATHS:
        if os.path.exists(path):
            return ImageFont.truetype(path, size)
    return ImageFont.load_default(size=size)


def draw_label(img, text, font):
    draw = ImageDraw.Draw(img)
    pad = font.size // 2
    box = draw.textbbox((pad, pad), text, font=font)
    draw.rectangle(
        (box[0] - pad // 2, box[1] - pad // 2, box[2] + pad // 2, box[3] + pad // 2),
        fill=(255, 255, 255),
    )
    draw.text((pad, pad), text, fill=(0, 0, 0), font=font)


def fit(img, width, height, background):
    """Scale img to fit inside width x height, centered horizontally, top-aligned."""
    scale = min(width / img.width, height / img.height)
    resized = img.resize(
        (max(1, round(img.width * scale)), max(1, round(img.height * scale))),
        Image.Resampling.LANCZOS,
    )
    canvas = Image.new("RGB", (width, height), background)
    canvas.paste(resized, ((width - resized.width) // 2, 0))
    return canvas


def even(n):
    return n - (n % 2)


def open_rgb(path):
    with Image.open(path) as img:
        return img.convert("RGB")


class Renderer:
    def __init__(self, config, days):
        self.days = days
        self.background = tuple(config.get("background", [255, 255, 255]))
        self.label = config.get("label", True)
        self.layout = config.get("layout", "grid")
        if self.layout not in LAYOUTS:
            raise ValueError(f"unknown layout {self.layout!r}, expected one of {LAYOUTS}")

        first_page = open_rgb(days[-1][1][0])
        self.page_aspect = first_page.width / first_page.height
        self.max_pages = max(len(pages) for _, pages in days)

        if "width" in config and "height" in config:
            self.width, self.height = config["width"], config["height"]
        elif self.max_pages > 1 and self.layout == "grid":
            self.width, self.height = 1920, 1080
        elif self.max_pages > 1:
            # One page at a time reads best in portrait (4:5).
            self.width, self.height = 1080, 1350
        else:
            # Single image: keep its aspect ratio, longest side = `size`.
            size = config.get("size", 1080)
            scale = size / max(first_page.width, first_page.height)
            self.width = round(first_page.width * scale)
            self.height = round(first_page.height * scale)
        self.width, self.height = even(self.width), even(self.height)
        self.font = load_font(max(16, self.height // 36))

    def frames(self):
        if self.max_pages == 1 or self.layout == "grid":
            yield from self._grid_frames()
        elif self.layout == "scroll":
            yield from self._scroll_frames()
        else:
            yield from self._page_frames()

    def frame_count(self):
        if self.max_pages > 1 and self.layout == "pages":
            return len(self.days) * self.max_pages
        return len(self.days)

    def _grid_frames(self):
        # Pick the column count that makes pages largest on screen.
        n = self.max_pages
        best = None
        for cols in range(1, n + 1):
            rows = math.ceil(n / cols)
            cell_w = self.width / cols
            cell_h = min(self.height / rows, cell_w / self.page_aspect)
            if best is None or cell_h > best[2]:
                best = (cols, rows, cell_h)
        cols, rows, cell_h = best
        cell_h = int(cell_h)
        cell_w = int(cell_h * self.page_aspect)
        gap = max(2, cell_w // 60)
        grid_w = cols * cell_w + (cols - 1) * gap
        grid_h = rows * cell_h + (rows - 1) * gap
        scale = min(self.width / grid_w, self.height / grid_h, 1)
        cell_w, cell_h, gap = int(cell_w * scale), int(cell_h * scale), int(gap * scale)
        x0 = (self.width - (cols * cell_w + (cols - 1) * gap)) // 2
        y0 = (self.height - (rows * cell_h + (rows - 1) * gap)) // 2

        for date, pages in self.days:
            frame = Image.new("RGB", (self.width, self.height), self.background)
            for i, page in enumerate(pages):
                col, row = i % cols, i // cols
                tile = fit(open_rgb(page), cell_w, cell_h, self.background)
                frame.paste(tile, (x0 + col * (cell_w + gap), y0 + row * (cell_h + gap)))
            if self.label:
                draw_label(frame, date, self.font)
            yield frame

    def _scroll_frames(self):
        # Pages stacked into one tall strip; the camera pans top to bottom while days advance.
        page_w = self.width
        page_h = int(page_w / self.page_aspect)
        gap = max(4, page_h // 80)
        strip_h = self.max_pages * page_h + (self.max_pages - 1) * gap
        travel = max(0, strip_h - self.height)
        total = len(self.days)

        for index, (date, pages) in enumerate(self.days):
            progress = index / max(1, total - 1)
            offset = int(travel * progress)
            frame = Image.new("RGB", (self.width, self.height), self.background)
            first = offset // (page_h + gap)
            last = min(self.max_pages - 1, (offset + self.height) // (page_h + gap))
            for i in range(first, last + 1):
                if i >= len(pages):
                    continue
                tile = fit(open_rgb(pages[i]), page_w, page_h, self.background)
                frame.paste(tile, (0, i * (page_h + gap) - offset))
            if self.label:
                draw_label(frame, date, self.font)
            yield frame

    def _page_frames(self):
        # Full timelapse of page 1, then page 2, and so on.
        for page_index in range(self.max_pages):
            for date, pages in self.days:
                frame = Image.new("RGB", (self.width, self.height), self.background)
                if page_index < len(pages):
                    tile = fit(open_rgb(pages[page_index]), self.width, self.height, self.background)
                    frame.paste(tile, (0, 0))
                if self.label:
                    draw_label(frame, f"{date}  ·  page {page_index + 1}", self.font)
                yield frame


def find_ffmpeg():
    path = os.environ.get("FFMPEG") or shutil.which("ffmpeg")
    if not path and os.path.exists("/opt/homebrew/bin/ffmpeg"):
        path = "/opt/homebrew/bin/ffmpeg"
    if not path:
        sys.exit("ffmpeg not found; install it or set FFMPEG=/path/to/ffmpeg")
    return path


def frame_digest(frame):
    return hashlib.md5(frame.resize((64, 64)).tobytes()).hexdigest()


def render(config, out_dir):
    name = config["name"]
    days = load_days(config.get("source", name))
    start, end = config.get("start"), config.get("end")
    days = [
        (date, pages)
        for date, pages in days
        if (not start or date >= str(start)) and (not end or date <= str(end))
    ]
    if not days:
        print(f"[{name}] no images found, skipping")
        return None

    renderer = Renderer(config, days)
    fps = config.get("fps", 8)
    output = Path(out_dir) / f"{config.get('output', name)}.mp4"
    output.parent.mkdir(parents=True, exist_ok=True)
    print(
        f"[{name}] {len(days)} days ({days[0][0]} → {days[-1][0]}), "
        f"{renderer.max_pages} page(s), layout={renderer.layout}, "
        f"{renderer.width}x{renderer.height} @ {fps}fps → {output}"
    )

    ffmpeg = subprocess.Popen(
        [
            find_ffmpeg(), "-y", "-loglevel", "error",
            "-f", "rawvideo", "-pix_fmt", "rgb24",
            "-s", f"{renderer.width}x{renderer.height}", "-r", str(fps),
            "-i", "-",
            "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "20",
            "-preset", "medium", "-movflags", "+faststart",
            str(output),
        ],
        stdin=subprocess.PIPE,
    )

    skip_unchanged = config.get("skip_unchanged", False)
    last_digest = None
    written = 0
    total = renderer.frame_count()
    for index, frame in enumerate(renderer.frames(), 1):
        if skip_unchanged:
            # Compare without the date label so unchanged days are dropped.
            digest = frame_digest(frame.crop((0, frame.height // 10, frame.width, frame.height)))
            if digest == last_digest:
                continue
            last_digest = digest
        ffmpeg.stdin.write(frame.tobytes())
        written += 1
        if index % 50 == 0 or index == total:
            print(f"[{name}] {index}/{total} frames", flush=True)

    # Hold the final frame for a second so the latest state is readable.
    for _ in range(fps):
        ffmpeg.stdin.write(frame.tobytes())

    ffmpeg.stdin.close()
    if ffmpeg.wait() != 0:
        raise RuntimeError(f"ffmpeg failed for {name}")
    print(f"[{name}] wrote {written} frames to {output}")
    return output


def main():
    parser = argparse.ArgumentParser(description="Render timelapses from timelapses.yml")
    parser.add_argument("names", nargs="*", help="timelapse names to render (default: all)")
    parser.add_argument("--config", default="timelapses.yml")
    parser.add_argument("--out", default="dist")
    parser.add_argument("--layout", choices=LAYOUTS, help="override the layout for paged sources")
    parser.add_argument("--source", help="override the source folder (e.g. sample data)")
    parser.add_argument("--start", help="override the start date (YYYY-MM-DD)")
    parser.add_argument("--suffix", default="", help="append to output filenames")
    args = parser.parse_args()

    with open(args.config) as f:
        configs = yaml.safe_load(f)

    selected = [c for c in configs if not args.names or c["name"] in args.names]
    if args.names and not selected:
        sys.exit(f"no timelapse named {args.names} in {args.config}")

    for config in selected:
        config = dict(config)
        if args.layout:
            config["layout"] = args.layout
        if args.source:
            config["source"] = args.source
        if args.start:
            config["start"] = args.start
        config["output"] = config.get("output", config["name"]) + args.suffix
        render(config, args.out)


if __name__ == "__main__":
    main()
