"""List / delete studio-compliance Agent Engine deployments.

    python deploy/cleanup.py --list
    python deploy/cleanup.py --delete projects/.../reasoningEngines/... --yes
"""

from __future__ import annotations

import argparse

from _common import init_vertex
from studio_compliance.config import load_config


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--list", action="store_true")
    parser.add_argument("--delete", metavar="RESOURCE_NAME")
    parser.add_argument("--yes", action="store_true", help="Confirm deletion")
    args = parser.parse_args()

    init_vertex(load_config())
    from vertexai import agent_engines

    if args.list or not args.delete:
        print("Deployed engines:")
        for engine in agent_engines.list():
            print(f"  {engine.resource_name}  ({engine.display_name})")
        return 0

    if not args.yes:
        print(f"Refusing to delete {args.delete} without --yes")
        return 1
    agent_engines.get(args.delete).delete(force=True)
    print(f"Deleted {args.delete}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
