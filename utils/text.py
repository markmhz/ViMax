from __future__ import annotations

import json
import re
from typing import Any


# Lone UTF-16 surrogates (U+D800–U+DFFF) cannot be encoded as UTF-8. They show
# up on Windows when text is mis-decoded from the console, clipboard, or pipes.
_SURROGATE_RE = re.compile(r"[\ud800-\udfff]")


def scrub_surrogates(value: str, *, replacement: str = "\ufffd") -> str:
    """Replace lone UTF-16 surrogates so the string can be UTF-8 encoded / JSON-dumped."""
    if not value or not isinstance(value, str):
        return value
    if not any("\ud800" <= ch <= "\udfff" for ch in value):
        return value
    return _SURROGATE_RE.sub(replacement, value)


def scrub_unicode_tree(value: Any) -> Any:
    """Recursively scrub lone surrogates from strings in JSON-like structures."""
    if isinstance(value, str):
        return scrub_surrogates(value)
    if isinstance(value, list):
        return [scrub_unicode_tree(item) for item in value]
    if isinstance(value, tuple):
        return tuple(scrub_unicode_tree(item) for item in value)
    if isinstance(value, dict):
        return {scrub_surrogates(str(key)) if isinstance(key, str) else key: scrub_unicode_tree(item) for key, item in value.items()}
    return value


def safe_json_dumps(value: Any, **kwargs: Any) -> str:
    """json.dumps that scrubs surrogates first so UTF-8 writers never crash."""
    kwargs.setdefault("ensure_ascii", False)
    kwargs.setdefault("default", str)
    return json.dumps(scrub_unicode_tree(value), **kwargs)


def safe_path_component(name) -> str:
    """Sanitize an LLM-derived identifier for use as a filesystem path component.

    Identifiers come from model output over user-supplied story text, so they may
    contain separators or traversal sequences; keep word characters (including
    CJK), dashes, dots and spaces, replace everything else, and strip leading
    dots so the result can never escape or hide within the working directory.
    """
    cleaned = re.sub(r"[^\w\-. ]", "_", scrub_surrogates(str(name)))
    cleaned = cleaned.strip().lstrip(".")
    return cleaned or "unnamed"
