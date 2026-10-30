"""Preview or create capture material for an already approved bounded unit."""

import argparse
import json
import sys
from pathlib import Path

from bounded.prepare_unit import prepare


def main():
    parser = argparse.ArgumentParser(allow_abbrev=False)
    parser.add_argument(
        "--packet", required=True, help="workspace-relative approved schema-2 packet"
    )
    parser.add_argument(
        "--config", required=True, help="workspace-relative explicit bounded-v1 config"
    )
    parser.add_argument(
        "--capture-spec", required=True, help="workspace-relative explicit facts specification"
    )
    parser.add_argument(
        "--apply", action="store_true", help="create missing material; never overwrite"
    )
    args = parser.parse_args()
    try:
        result = prepare(Path.cwd(), args.packet, args.config, args.capture_spec, apply=args.apply)
    except (ValueError, OSError, KeyError, TypeError, RuntimeError) as exc:
        print(
            json.dumps({"status": "blocked", "model_calls": 0, "reason": str(exc)}), file=sys.stderr
        )
        return 2
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
