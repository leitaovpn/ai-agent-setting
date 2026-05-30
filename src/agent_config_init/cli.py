"""CLI entry point for agent-config-init."""

import argparse
import json
import os
import sys
from pathlib import Path

from agent_config_init.config import ConfigNotFoundError, load_config
from agent_config_init.merge import MergeError, deep_equal, deep_merge_into_target

# Mapping from agent name to the relative target path within the project
AGENT_TARGET_PATHS = {
    "claude": ".claude/settings.json",
}

SUPPORTED_AGENTS = frozenset(AGENT_TARGET_PATHS)


def _atomic_write(target_path: Path, merged: dict) -> None:
    """Write *merged* to *target_path* atomically, preserving permissions."""
    tmp_path = target_path.with_suffix(".tmp")

    if tmp_path.is_dir():
        raise MergeError(
            f"{tmp_path} is a directory, cannot write temp file"
        )

    # Clean up stale tmp file from a previous crash
    tmp_path.unlink(missing_ok=True)

    try:
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(merged, f, indent=2)
            f.write("\n")
    except IsADirectoryError:
        raise MergeError(
            f"{tmp_path} is a directory, cannot write temp file"
        )

    # Preserve original file permissions if target exists
    if target_path.exists():
        try:
            st = target_path.stat()
            os.chmod(tmp_path, st.st_mode)
        except OSError:
            pass

    try:
        os.replace(tmp_path, target_path)
    except OSError:
        tmp_path.unlink(missing_ok=True)
        raise


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

    try:
        template = load_config(args.agent_name)
    except ConfigNotFoundError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

    target_rel = AGENT_TARGET_PATHS[args.agent_name]
    target_path = Path.cwd() / target_rel

    try:
        merged, original = deep_merge_into_target(target_path, template)
    except MergeError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

    target_path.parent.mkdir(parents=True, exist_ok=True)

    if original is not None and deep_equal(original, merged):
        print(f"No changes needed for {target_path}")
        return

    try:
        _atomic_write(target_path, merged)
    except MergeError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

    print(f"Wrote {target_path}")
