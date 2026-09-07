#!/usr/bin/env python3
"""Print one exact-match score for a prediction and expected value."""

from __future__ import annotations

import json
import sys


def main() -> int:
    try:
        payload = json.load(sys.stdin)
        if set(payload) != {"returned_output_hash", "prediction", "expected"}:
            raise ValueError("input fields differ")
        print("1" if payload["prediction"] == payload["expected"] else "0")
        return 0
    except (TypeError, ValueError, json.JSONDecodeError) as exc:
        sys.stderr.write(f"exact_match: {exc}\n")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())

