"""Tests for bridging agent.local.yaml credentials into CLI pipeline configs."""

from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import yaml

from agent_runtime.config import load_agent_config
from utils.agent_pipeline_bridge import apply_agent_local_overrides


class AgentPipelineBridgeTests(unittest.TestCase):
    def setUp(self):
        load_agent_config.cache_clear()

    def tearDown(self):
        load_agent_config.cache_clear()

    def _write_agent_local(self, root: Path, payload: dict) -> None:
        config_dir = root / "configs"
        config_dir.mkdir(parents=True, exist_ok=True)
        (config_dir / "agent.local.yaml").write_text(yaml.safe_dump(payload), encoding="utf-8")
        load_agent_config.cache_clear()

    def test_fills_empty_chat_and_video_credentials(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._write_agent_local(root, {
                "llm": {
                    "model_provider": "openai",
                    "model": "agent-llm",
                    "base_url": "https://llm.agent.test/v1",
                    "api_key": "llm-secret",
                },
                "image": {
                    "model": "agent-image",
                    "base_url": "https://openrouter.ai/api/v1",
                    "api_key": "image-secret",
                },
                "video": {
                    "model": "agent-video",
                    "base_url": "https://openrouter.ai/api/v1",
                    "api_key": "video-secret",
                },
            })
            pipeline = {
                "chat_model": {"init_args": {"api_key": "", "model": "", "base_url": "", "model_provider": ""}},
                "image_generator": {
                    "class_path": "tools.image_generator_openrouter_api.ImageGeneratorOpenRouterAPI",
                    "init_args": {"api_key": "", "model": "", "base_url": ""},
                },
                "video_generator": {
                    "class_path": "tools.video_generator_veo_openrouter_api.VideoGeneratorOpenRouterAPI",
                    "init_args": {"api_key": "", "model": "", "base_url": ""},
                },
            }
            with patch.dict(os.environ, {}, clear=True):
                merged = apply_agent_local_overrides(pipeline, root)
            self.assertEqual(merged["chat_model"]["init_args"]["api_key"], "llm-secret")
            self.assertEqual(merged["chat_model"]["init_args"]["model"], "agent-llm")
            self.assertEqual(merged["image_generator"]["init_args"]["api_key"], "image-secret")
            self.assertEqual(merged["image_generator"]["init_args"]["model"], "agent-image")
            self.assertEqual(merged["video_generator"]["init_args"]["api_key"], "video-secret")
            self.assertEqual(merged["video_generator"]["init_args"]["model"], "agent-video")

    def test_does_not_overwrite_nonempty_pipeline_values(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._write_agent_local(root, {
                "llm": {"api_key": "from-agent", "model": "agent-model"},
            })
            pipeline = {
                "chat_model": {"init_args": {"api_key": "pipeline-key", "model": "pipeline-model"}},
            }
            with patch.dict(os.environ, {}, clear=True):
                merged = apply_agent_local_overrides(pipeline, root)
            self.assertEqual(merged["chat_model"]["init_args"]["api_key"], "pipeline-key")
            self.assertEqual(merged["chat_model"]["init_args"]["model"], "pipeline-model")


if __name__ == "__main__":
    unittest.main()
