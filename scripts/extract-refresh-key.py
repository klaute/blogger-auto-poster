#!/usr/bin/env python3

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.oauth_setup import main


if __name__ == "__main__":
    args = [
        "--credentials-file",
        "credentials.json",
        "--update-config",
        "config/config.yml",
        "--manual-code",
    ]
    args.extend(sys.argv[1:])
    raise SystemExit(main(args))
