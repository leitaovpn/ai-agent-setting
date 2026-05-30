"""Deep-merge algorithm for JSON configuration files.

Rules:
- Keys only in template → added to result.
- Both dicts → recursive merge, preserving all existing keys.
- Both lists → append template items not already present (dedup via deep equality).
- Type mismatch or primitives → keep existing value.
"""

import copy
import json
from pathlib import Path
from typing import Dict, Optional, Tuple, cast


class MergeError(Exception):
    """Raised when the target file cannot be read or merged."""


_MISSING = object()


def deep_equal(a, b) -> bool:
    """Structural deep equality for JSON-compatible values."""
    if type(a) is not type(b):
        return False
    if isinstance(a, dict):
        return a.keys() == b.keys() and all(
            deep_equal(a[k], b[k]) for k in a
        )
    if isinstance(a, list):
        return len(a) == len(b) and all(
            deep_equal(x, y) for x, y in zip(a, b)
        )
    return a == b


def deep_merge(existing, template):
    """Deep-merge *template* into *existing*. Never removes existing data.

    Returns a new dict/list; does not mutate inputs.
    *existing* may be the _MISSING sentinel to indicate a missing key.
    """
    if existing is _MISSING:
        return copy.deepcopy(template)

    if isinstance(existing, dict) and isinstance(template, dict):
        result = dict(existing)
        for key, t_val in template.items():
            if key in result:
                result[key] = deep_merge(result[key], t_val)
            else:
                result[key] = deep_merge(_MISSING, t_val)
        return result

    if isinstance(existing, list) and isinstance(template, list):
        result = list(existing)
        for t_item in template:
            if not any(deep_equal(t_item, e_item) for e_item in result):
                result.append(copy.deepcopy(t_item))
        return result

    return existing


def deep_merge_into_target(
    target_path: Path, template: dict
) -> Tuple[Dict, Optional[Dict]]:
    """Read *target_path*, deep-merge *template* into its contents.

    Returns (merged_dict, original_dict_or_None).
    """
    try:
        with open(target_path, "r", encoding="utf-8") as f:
            existing = json.load(f)
    except FileNotFoundError:
        return template, None
    except (json.JSONDecodeError, UnicodeDecodeError) as e:
        raise MergeError(
            f"Existing file {target_path} is not valid JSON: {e}"
        ) from e
    except PermissionError as e:
        raise MergeError(
            f"Permission denied reading {target_path}: {e}"
        ) from e
    except IsADirectoryError:
        raise MergeError(
            f"{target_path} is a directory, expected a JSON file"
        )
    except OSError as e:
        raise MergeError(f"Cannot read {target_path}: {e}") from e

    if not isinstance(existing, dict):
        raise MergeError(
            f"{target_path} must contain a JSON object, "
            f"got {type(existing).__name__}"
        )

    return cast(dict, deep_merge(existing, template)), existing
