# spencer-net-shots

a simple way to regularly archive screenshots from different websites to a Github repo or S3 bucket.

## Getting Started

1. Configure shots.yml using the `shot-scraper` documentation for each site you want to archive.
2. Configure your access tokens for Github / AWS

TODO:

- [ ] the shots.yml repo should probably be separate from the repo for archiving shots to avoid needing to pull those assets. (use spencer-net-shots-archive as submodule)
- [ ] move s3 stuff to r2 for cheaper storage (https://github.com/marketplace/actions/r2-upload-action)
- [ ] find some easier way to add new ones, currently requires a lot of manual code

manual steps to add a new source

- add a new source to shots.yml
- configure 1) the renaming and 2) the uploading from workflows/.shots.yml
- add folder for your new source that is named appropriately.
