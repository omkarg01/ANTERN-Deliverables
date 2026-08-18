#!/usr/bin/env python3
"""Run the CMIS Temporal background worker (M9)."""

from __future__ import annotations

from cmis.config import load_dotenv_file
from cmis.workflows.worker import main

if __name__ == "__main__":
    load_dotenv_file()
    main()
