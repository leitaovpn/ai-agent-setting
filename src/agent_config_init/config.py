"""Template discovery with multi-location search.

Search order (first match wins):
1. $AGENT_CONFIG_INIT_DIR/<agent>/settings.json  (env var override)
2. /etc/agent-config-init/<agent>/settings.json  (system install)
3. <sys.prefix>/etc/agent-config-init/<agent>/settings.json  (pip --prefix)
4. <package_dir>/../../config/<agent>/settings.json  (dev fallback)
"""

import json
import os
import re
import sys
from pathlib import Path


class ConfigNotFoundError(Exception):
    """Raised when no configuration template is found for the given agent."""


_SAFE_AGENT_NAME = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9_.-]*$")


def _validate_agent_name(agent_name: str) -> None:
    if not _SAFE_AGENT_NAME.match(agent_name):
        raise ValueError(
            f"Invalid agent name {agent_name!r}. "
            f"Must match {_SAFE_AGENT_NAME.pattern}"
        )


def _build_candidates(agent_name: str):
    """Yield candidate paths for the agent's settings.json template."""
    _validate_agent_name(agent_name)

    env_dir = os.environ.get("AGENT_CONFIG_INIT_DIR")
    if env_dir:
        yield Path(env_dir) / agent_name / "settings.json"

    yield Path("/etc/agent-config-init") / agent_name / "settings.json"
    yield Path(sys.prefix) / "etc" / "agent-config-init" / agent_name / "settings.json"

    # Development fallback: relative to this file
    # src/agent_config_init/config.py → up 3 levels → config/<agent>/settings.json
    pkg_dir = Path(__file__).resolve().parent.parent.parent
    yield pkg_dir / "config" / agent_name / "settings.json"


def load_config(agent_name: str) -> dict:
    """Load the template configuration for *agent_name*."""
    _validate_agent_name(agent_name)

    candidates = list(_build_candidates(agent_name))

    for path in candidates:
        if path.is_file():
            try:
                with open(path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except json.JSONDecodeError as e:
                raise ConfigNotFoundError(
                    f"Template file {path} is not valid JSON: {e}"
                ) from e

    raise ConfigNotFoundError(
        f"No configuration template found for agent '{agent_name}'.\n"
        f"Searched:\n" + "\n".join(f"  - {p}" for p in candidates)
    )
