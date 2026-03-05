#!/usr/bin/env python3
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
from session_logging.sanitizer import main

if __name__ == "__main__":
    raise SystemExit(main())
