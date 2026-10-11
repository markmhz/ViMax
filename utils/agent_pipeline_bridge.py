"""Bridge credentials from configs/agent.local.yaml into CLI pipeline YAML configs.

CLI pipelines (`idea2video.yaml`, `script2video.yaml`) use a different schema than
the Web/TUI agent config. When pipeline init_args leave api_key (or model/base_url)
empty, fill them from agent.local.yaml / VIMAX_* env so Settings keys also work
for `main_idea2video.py` / `main_script2video.py`.
"""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Any

from agent_runtime.config import (
    image_api_key,
    image_base_url,
    image_model,
    llm_api_key,
    llm_base_url,
    llm_model,
    llm_model_provider,
    load_agent_config,
    video_api_key,
    video_base_url,
    video_model,
)


def apply_agent_local_overrides(config: dict[str, Any], workspace_root: str | Path = ".") -> dict[str, Any]:
    """Return a shallow-copied pipeline config with empty credentials filled from agent.local.yaml."""
    if not isinstance(config, dict):
        return config
    root = Path(workspace_root).resolve()
    load_agent_config.cache_clear()
    merged = deepcopy(config)

    chat = merged.get("chat_model")
    if isinstance(chat, dict):
        init_args = chat.setdefault("init_args", {})
        if isinstance(init_args, dict):
            _fill(init_args, "api_key", llm_api_key(root))
            _fill(init_args, "base_url", llm_base_url(root))
            _fill(init_args, "model", llm_model(root))
            _fill(init_args, "model_provider", llm_model_provider(root))

    image = merged.get("image_generator")
    if isinstance(image, dict):
        init_args = image.setdefault("init_args", {})
        if isinstance(init_args, dict):
            _fill(init_args, "api_key", image_api_key(root))
            # Only overlay model/base_url when the class looks OpenAI-compatible / Yunwu / OpenRouter.
            class_path = str(image.get("class_path") or "")
            if "OpenRouter" in class_path or "Yunwu" in class_path or "Nanobanana" in class_path:
                _fill(init_args, "model", image_model(root))
                _fill(init_args, "base_url", image_base_url(root))

    video = merged.get("video_generator")
    if isinstance(video, dict):
        init_args = video.setdefault("init_args", {})
        if isinstance(init_args, dict):
            _fill(init_args, "api_key", video_api_key(root))
            class_path = str(video.get("class_path") or "")
            if "OpenRouter" in class_path or "Yunwu" in class_path:
                _fill(init_args, "model", video_model(root))
                _fill(init_args, "base_url", video_base_url(root))
                if "t2v_model" in init_args or "Veo" in class_path:
                    _fill(init_args, "t2v_model", video_model(root))
                    _fill(init_args, "ff2v_model", video_model(root))

    return merged


def _fill(target: dict[str, Any], key: str, value: str) -> None:
    if not value:
        return
    current = target.get(key)
    if current is None or (isinstance(current, str) and not current.strip()):
        target[key] = value
