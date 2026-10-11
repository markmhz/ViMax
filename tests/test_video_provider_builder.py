"""Tests for video generator provider selection and Settings-facing errors."""

from __future__ import annotations

import unittest
from unittest.mock import patch

from agent_runtime.vimax_adapters import _build_video_generator
from tools.video_generator_openrouter_api import VideoGeneratorOpenRouterAPI
from tools.video_generator_veo_google_api import VideoGeneratorVeoGoogleAPI
from tools.video_generator_veo_yunwu_api import VideoGeneratorVeoYunwuAPI


class VideoProviderBuilderTests(unittest.TestCase):
    def test_builds_openrouter_yunwu_and_google(self):
        cases = [
            ("openrouter", VideoGeneratorOpenRouterAPI),
            ("yunwu", VideoGeneratorVeoYunwuAPI),
            ("google", VideoGeneratorVeoGoogleAPI),
        ]
        for provider, expected_cls in cases:
            with self.subTest(provider=provider):
                with patch("agent_runtime.vimax_adapters.video_api_key", return_value="secret"), \
                     patch("agent_runtime.vimax_adapters.video_model", return_value="veo-test"), \
                     patch("agent_runtime.vimax_adapters.video_base_url", return_value="https://example.test/v1"), \
                     patch("agent_runtime.vimax_adapters.video_provider", return_value=provider):
                    generator = _build_video_generator()
                self.assertIsInstance(generator, expected_cls)

    def test_unsupported_provider_mentions_settings(self):
        with patch("agent_runtime.vimax_adapters.video_api_key", return_value="secret"), \
             patch("agent_runtime.vimax_adapters.video_model", return_value="veo-test"), \
             patch("agent_runtime.vimax_adapters.video_base_url", return_value="https://example.test/v1"), \
             patch("agent_runtime.vimax_adapters.video_provider", return_value=""):
            with self.assertRaisesRegex(RuntimeError, r"Settings → Video|video\.provider"):
                _build_video_generator()


if __name__ == "__main__":
    unittest.main()
