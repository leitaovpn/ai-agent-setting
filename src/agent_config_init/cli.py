"""CLI entry point for agent-config-init."""

import argparse
import json
import os
import sys
from pathlib import Path

from agent_config_init.config import ConfigNotFoundError, load_config
from agent_config_init.merge import deep_equal, deep_merge_into_target

# Mapping from agent name to the relative target path within the project
AGENT_TARGET_PATHS = {
    "claude": ".claude/settings.json",
}

SUPPORTED_AGENTS = frozenset(AGENT_TARGET_PATHS)


def main():
    parser = argparse.ArgumentParser(
        description="Initialize and merge agent configuration files"
    )
    parser.add_argument(
        "agent_name",
        help=f"Agent name to initialize (supported: {', '.join(sorted(SUPPORTED_AGENTS))})",
    )
    args = parser.parse_args()

    if args.agent_name not in SUPPORTED_AGENTS:
        print(
            f"Error: Unsupported agent '{args.agent_name}'. "
            f"Supported: {', '.join(sorted(SUPPORTED_AGENTS))}",
            file=sys.stderr,
        )
        sys.exit(1)

    # Load the template config
    try:
        template = load_config(args.agent_name)
    except ConfigNotFoundError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

    # Determine target path
    target_rel = AGENT_TARGET_PATHS[args.agent_name]
    target_path = Path.cwd() / target_rel

    merged = deep_merge_into_target(target_path, template)

    # Ensure parent directory exists
    target_path.parent.mkdir(parents=True, exist_ok=True)

    # Check if content would actually change
    if target_path.exists():
        try:
            with open(target_path, "r", encoding="utf-8") as f:
                current = json.load(f)
            if deep_equal(current, merged):
                print(f"No changes needed for {target_path}")
                return
        except (json.JSONDecodeError, OSError):
            pass

    # Atomic write: write to temp file then rename
    tmp_path = target_path.with_suffix(".tmp")
    with open(tmp_path, "w", encoding="utf-8") as f:
        json.dump(merged, f, indent=2)
        f.write("\n")
    os.replace(tmp_path, target_path)

    print(f"Wrote {target_path}")
