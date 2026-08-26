#!/usr/bin/env python3
"""CLI entrypoint: python3 run.py [--skip-fetch]"""

from fitbit_scraper.pipeline import main

if __name__ == "__main__":
    raise SystemExit(main())
