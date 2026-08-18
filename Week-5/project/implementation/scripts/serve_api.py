#!/usr/bin/env python3
"""Run the CMIS FastAPI server."""

from __future__ import annotations

import os

import uvicorn

from cmis.config import load_dotenv_file


def main() -> None:
    load_dotenv_file()
    host = os.environ.get("CMIS_API_HOST", "0.0.0.0")
    port = int(os.environ.get("PORT", os.environ.get("CMIS_API_PORT", "8000")))
    reload = os.environ.get("CMIS_API_RELOAD", "0") == "1"
    uvicorn.run(
        "cmis.api.server:app",
        host=host,
        port=port,
        reload=reload,
    )


if __name__ == "__main__":
    main()
