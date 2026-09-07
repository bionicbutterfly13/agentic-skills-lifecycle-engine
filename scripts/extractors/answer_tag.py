#!/usr/bin/env python3
"""Extract exactly one nonempty <answer> payload from a returned output."""

from __future__ import annotations

import json
import re
import sys


def main() -> int:
    try:
        payload = json.load(sys.stdin)
        if set(payload) != {"returned_output", "returned_output_hash"}:
            raise ValueError("input fields differ")
        output = payload["returned_output"]
        output_hash = payload["returned_output_hash"]
        if not isinstance(output, str) or not isinstance(output_hash, str):
            raise ValueError("input types differ")
        matches = re.findall(r"<answer>(.*?)</answer>", output, flags=re.DOTALL)
        if len(matches) != 1 or not matches[0].strip():
            raise ValueError("expected exactly one nonempty answer tag")
        print(
            json.dumps(
                {
                    "returned_output_hash": output_hash,
                    "prediction": matches[0].strip(),
                },
                ensure_ascii=False,
                sort_keys=True,
            )
        )
        return 0
    except (KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
        sys.stderr.write(f"answer_tag: {exc}\n")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())

