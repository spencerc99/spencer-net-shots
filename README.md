# spencer-net-shots

a simple way to regularly archive screenshots from different websites to a Github repo or S3 bucket.

## Getting Started

1. Configure shots.yml using the `shot-scraper` documentation for each site you want to archive.
2. Configure your access tokens for Github / AWS

TODO:

- [ ] the shots.yml repo should probably be separate from the repo for archiving shots to avoid needing to pull those assets. (use spencer-net-shots-archive as submodule)
- [ ] add a way to customize how often you want to take shots for each source, naming scheme should support this if more granular than day
      manual steps to add a new source

- add a new source to shots.yml, note the output name will become the directory name in the archive

## Timelapses

`timelapses.yml` lists the archives that get turned into videos. After each daily capture, the `Render timelapses` workflow re-renders them and replaces the assets on the [`timelapses` release](../../releases/tag/timelapses), so each video has a stable URL:

```
https://github.com/spencerc99/spencer-net-shots/releases/download/timelapses/<name>.mp4
```

Render locally (needs `ffmpeg`):

```bash
python timelapse.py                        # everything in timelapses.yml → dist/
python timelapse.py cursor-park --layout scroll --suffix=-scroll
python timelapse.py cursor-park --pages "1,40-44"  # only some pages
```

Multi-page sources (one folder per day, `<date>/page-N.png`) support three layouts: `grid` (all pages at once), `scroll` (camera pans down the pages as days advance), and `pages` (each page's full timelapse in turn).

### Google Docs (cursor park)

`capture-gdoc.py` exports a doc as PDF and saves each page as a PNG. The daily workflow uses the public export, so the doc must be shared as "Anyone with the link can view".

To backfill history from the doc's revisions (run once locally, as the doc owner):

```bash
brew install poppler
gcloud auth login --enable-gdrive-access
python capture-gdoc.py 1gxuxSTYS8ta912nr-GY7wToVM3yFe-PFXDa1NLQsSp8 cursor-park --backfill
```

Google merges older revisions, so early history may be sparser than one snapshot per day.
