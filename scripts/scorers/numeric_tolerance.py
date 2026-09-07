#!/usr/bin/env python3
"""Print one numeric-equality score with a fixed absolute tolerance."""

from __future__ import annotations

import json
import math
import sys

TOLERANCE = 1e-9


def main() -> int:
    try:
        payload = json.load(sys.stdin)
        if set(payload) != {"returned_output_hash", "prediction", "expected"}:
            raise ValueError("input fields differ")
        expected = float(payload["expected"])
        if not math.isfinite(expected):
            raise ValueError("expected value must be finite")
        try:
            prediction = float(payload["prediction"])
        except (TypeError, ValueError):
            print("0")
            return 0
        if not math.isfinite(prediction):
            print("0")
            return 0
        print("1" if abs(prediction - expected) <= TOLERANCE else "0")
        return 0
    except (TypeError, ValueError, json.JSONDecodeError) as exc:
        sys.stderr.write(f"numeric_tolerance: {exc}\n")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
