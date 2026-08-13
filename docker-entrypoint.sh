#!/bin/sh
set -eu

exec python -m fmkorea_scraper.adapters.container "$@"
