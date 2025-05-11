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
