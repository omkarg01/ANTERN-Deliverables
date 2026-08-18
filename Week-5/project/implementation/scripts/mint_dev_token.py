#!/usr/bin/env python3
"""Mint a dev JWT for CMIS API testing."""

from __future__ import annotations

import argparse
import os
import sys

from cmis.api.auth import mint_access_token
from cmis.config import load_dotenv_file


def main() -> int:
    parser = argparse.ArgumentParser(description="Mint a CMIS dev JWT")
    parser.add_argument("tenant_id", help="Tenant scope for the token")
    parser.add_argument("user_id", help="User scope for the token")
    parser.add_argument(
        "--hours",
        type=int,
        default=24,
        help="Token lifetime in hours (default: 24)",
    )
    args = parser.parse_args()

    load_dotenv_file()
    secret = os.environ.get("CMIS_JWT_SECRET", "").strip()
    if not secret:
        print("CMIS_JWT_SECRET is not set. Add it to implementation/.env", file=sys.stderr)
        return 1

    from datetime import timedelta

    token = mint_access_token(
        tenant_id=args.tenant_id,
        user_id=args.user_id,
        expires_in=timedelta(hours=args.hours),
    )
    print(token)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
