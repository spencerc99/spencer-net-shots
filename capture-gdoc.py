# ABOUTME: Archives a Google Doc as one PNG per page, under <out>/<YYYY-MM-DD>/page-N.png.
# ABOUTME: Daily mode uses the public PDF export; --backfill pulls past revisions via the Drive API.
import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
import urllib.request
from collections import OrderedDict
from datetime import datetime, timezone
from pathlib import Path

EXPORT_URL = "https://docs.google.com/document/d/{doc_id}/export?format=pdf"
REVISIONS_URL = (
    "https://www.googleapis.com/drive/v3/files/{doc_id}/revisions"
    "?fields=nextPageToken,revisions(id,modifiedTime,exportLinks)&pageSize=200"
)


def fetch(url, token=None):
    request = urllib.request.Request(url)
    if token:
        request.add_header("Authorization", f"Bearer {token}")
    with urllib.request.urlopen(request, timeout=60) as response:
        return response.headers.get("Content-Type", ""), response.read()


def rasterize(pdf_bytes, day_dir, dpi):
    """Write each PDF page to day_dir/page-N.png; return the page count."""
    if not shutil.which("pdftoppm"):
        sys.exit("pdftoppm not found; install poppler (brew install poppler / apt install poppler-utils)")
    with tempfile.TemporaryDirectory() as tmp:
        pdf_path = Path(tmp) / "doc.pdf"
        pdf_path.write_bytes(pdf_bytes)
        subprocess.run(
            ["pdftoppm", "-png", "-r", str(dpi), str(pdf_path), str(Path(tmp) / "page")],
            check=True,
        )
        pages = sorted(Path(tmp).glob("page-*.png"), key=lambda p: int(p.stem.split("-")[-1]))
        if day_dir.exists():
            shutil.rmtree(day_dir)
        day_dir.mkdir(parents=True)
        for index, page in enumerate(pages, 1):
            shutil.move(str(page), day_dir / f"page-{index}.png")
    return len(pages)


def capture_today(doc_id, out, dpi):
    content_type, body = fetch(EXPORT_URL.format(doc_id=doc_id))
    if "pdf" not in content_type:
        sys.exit(
            f"export returned {content_type!r} instead of a PDF; "
            "is the doc shared as 'Anyone with the link can view'?"
        )
    date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    count = rasterize(body, out / date, dpi)
    print(f"captured {count} page(s) → {out / date}")


def access_token(explicit):
    token = explicit or os.environ.get("GOOGLE_ACCESS_TOKEN")
    if token:
        return token
    if shutil.which("gcloud"):
        result = subprocess.run(
            ["gcloud", "auth", "print-access-token"], capture_output=True, text=True
        )
        if result.returncode == 0:
            return result.stdout.strip()
    sys.exit(
        "no Google access token. Run `gcloud auth login --enable-gdrive-access` "
        "(signed in as the doc owner), or pass --token / set GOOGLE_ACCESS_TOKEN."
    )


def list_revisions(doc_id, token):
    revisions, page_token = [], None
    while True:
        url = REVISIONS_URL.format(doc_id=doc_id)
        if page_token:
            url += f"&pageToken={page_token}"
        _, body = fetch(url, token)
        data = json.loads(body)
        revisions.extend(data.get("revisions", []))
        page_token = data.get("nextPageToken")
        if not page_token:
            return revisions


def backfill(doc_id, out, dpi, token, overwrite):
    revisions = list_revisions(doc_id, token)
    # Keep the last revision of each UTC day, matching the daily capture's date.
    per_day = OrderedDict()
    for revision in sorted(revisions, key=lambda r: r["modifiedTime"]):
        per_day[revision["modifiedTime"][:10]] = revision
    print(f"{len(revisions)} revisions across {len(per_day)} days")

    for date, revision in per_day.items():
        day_dir = out / date
        if day_dir.exists() and not overwrite:
            print(f"{date}: already archived, skipping")
            continue
        link = revision.get("exportLinks", {}).get("application/pdf")
        if not link:
            print(f"{date}: revision {revision['id']} has no PDF export, skipping")
            continue
        _, body = fetch(link, token)
        count = rasterize(body, day_dir, dpi)
        print(f"{date}: {count} page(s) from revision {revision['id']}")


def main():
    parser = argparse.ArgumentParser(description="Archive a Google Doc as dated page PNGs")
    parser.add_argument("doc_id")
    parser.add_argument("out", type=Path, help="archive folder, e.g. cursor-park")
    parser.add_argument("--dpi", type=int, default=100)
    parser.add_argument("--backfill", action="store_true", help="export past revisions (needs owner access)")
    parser.add_argument("--token", help="Google OAuth access token with Drive read access")
    parser.add_argument("--overwrite", action="store_true", help="re-export days already archived")
    args = parser.parse_args()

    if args.backfill:
        backfill(args.doc_id, args.out, args.dpi, access_token(args.token), args.overwrite)
    else:
        capture_today(args.doc_id, args.out, args.dpi)


if __name__ == "__main__":
    main()
