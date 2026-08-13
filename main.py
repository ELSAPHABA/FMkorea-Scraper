from pathlib import Path
import sys

src_path = Path(__file__).with_name("src")
if src_path.is_dir():
    sys.path.insert(0, str(src_path))

from fmkorea_scraper.adapters.cli import main


if __name__ == "__main__":
    raise SystemExit(main())
