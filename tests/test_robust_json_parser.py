"""Regression tests for OpenAI-compatible structured JSON repair.

Covers the idea2video storyboard/shots failure mode where models return
markdown fences, trailing commas, prose wrappers, or slightly wrong schemas
and LangChain's stock PydanticOutputParser raises OutputParserException.
"""

from __future__ import annotations

import unittest
from typing import List

from langchain_core.exceptions import OutputParserException
from langchain_core.output_parsers import PydanticOutputParser as StockParser
from pydantic import BaseModel, Field

from langchain_core.messages import AIMessage
from langchain_core.outputs import ChatGeneration

from agents.camera_image_generator import CameraTreeResponse
from agents.storyboard_artist import VisDescDecompositionResponse
from interfaces.shot_description import ShotBriefDescription
from utils.robust_json_parser import (
    RobustPydanticOutputParser,
    TrailingCommaTolerantPydanticOutputParser,
    extract_json_value,
    repair_and_parse_json,
    strip_markdown_fences,
    strip_trailing_commas,
)


class StoryboardResponse(BaseModel):
    storyboard: List[ShotBriefDescription] = Field(description="shots")


SHOT = {
    "idx": 0,
    "is_last": True,
    "cam_idx": 0,
    "visual_desc": "Wide cartoon shot of a cat and a dog meeting.",
    "audio_desc": "Soft park ambience",
}


def _storyboard_json(**overrides) -> str:
    import json

    shot = dict(SHOT, **overrides)
    return json.dumps({"storyboard": [shot]}, ensure_ascii=False)


class StripHelpersTests(unittest.TestCase):
    def test_strip_trailing_commas(self):
        self.assertEqual(strip_trailing_commas('{"a": 1,}'), '{"a": 1}')
        self.assertEqual(strip_trailing_commas('{"a": [1, 2,],}'), '{"a": [1, 2]}')

    def test_strip_markdown_fences(self):
        fenced = "```json\n{\"a\": 1}\n```"
        self.assertEqual(strip_markdown_fences(fenced), '{"a": 1}')
        self.assertEqual(strip_markdown_fences('{"a": 1}'), '{"a": 1}')

    def test_extract_json_with_prose(self):
        text = 'Sure, here you go:\n{"storyboard": [{"idx": 0}]}\nDone.'
        self.assertEqual(extract_json_value(text), {"storyboard": [{"idx": 0}]})


class RobustParserStoryboardTests(unittest.TestCase):
    def setUp(self):
        self.parser = TrailingCommaTolerantPydanticOutputParser(pydantic_object=StoryboardResponse)
        self.stock = StockParser(pydantic_object=StoryboardResponse)

    def test_clean_json_still_works(self):
        parsed = self.parser.parse(_storyboard_json())
        self.assertEqual(len(parsed.storyboard), 1)
        self.assertEqual(parsed.storyboard[0].idx, 0)

    def test_trailing_commas_repaired(self):
        dirty = '{"storyboard": [{"idx": 0, "is_last": true, "cam_idx": 0, "visual_desc": "v", "audio_desc": "a",},]}'
        with self.assertRaises(OutputParserException):
            self.stock.parse(dirty)
        parsed = self.parser.parse(dirty)
        self.assertEqual(parsed.storyboard[0].visual_desc, "v")

    def test_fenced_json_with_trailing_comma(self):
        dirty = "```json\n" + '{"storyboard": [{"idx": 0, "is_last": true, "cam_idx": 0, "visual_desc": "猫", "audio_desc": "a",},]}' + "\n```"
        with self.assertRaises(OutputParserException):
            self.stock.parse(dirty)
        parsed = self.parser.parse(dirty)
        self.assertIn("猫", parsed.storyboard[0].visual_desc)

    def test_prose_wrapped_json(self):
        dirty = "以下是分镜 JSON：\n" + _storyboard_json() + "\n请查收。"
        with self.assertRaises(OutputParserException):
            self.stock.parse(dirty)
        parsed = self.parser.parse(dirty)
        self.assertEqual(parsed.storyboard[0].cam_idx, 0)

    def test_properties_wrapper(self):
        import json

        dirty = json.dumps({"properties": {"storyboard": [SHOT]}}, ensure_ascii=False)
        parsed = self.parser.parse(dirty)
        self.assertEqual(len(parsed.storyboard), 1)

    def test_bare_array_wrapped_as_storyboard(self):
        import json

        dirty = json.dumps([SHOT], ensure_ascii=False)
        parsed = self.parser.parse(dirty)
        self.assertEqual(parsed.storyboard[0].idx, 0)

    def test_shots_key_alias(self):
        import json

        dirty = json.dumps({"shots": [SHOT]}, ensure_ascii=False)
        parsed = self.parser.parse(dirty)
        self.assertEqual(len(parsed.storyboard), 1)

    def test_null_audio_desc_coerced(self):
        import json

        shot = dict(SHOT, audio_desc=None)
        dirty = json.dumps({"storyboard": [shot]}, ensure_ascii=False)
        parsed = self.parser.parse(dirty)
        self.assertEqual(parsed.storyboard[0].audio_desc, "")

    def test_chinese_idea2video_style_prompt_payload(self):
        """Payload shaped like idea2video cartoon short planning."""
        dirty = (
            "```JSON\n"
            '{"storyboard": ['
            '{"idx": 0, "is_last": false, "cam_idx": 0, "visual_desc": "卡通宽景：猫和狗见面", "audio_desc": "bgm",},'
            '{"idx": 1, "is_last": true, "cam_idx": 1, "visual_desc": "近景打招呼", "audio_desc": null,},'
            '],}\n'
            "```"
        )
        parsed = self.parser.parse(dirty)
        self.assertEqual(len(parsed.storyboard), 2)
        self.assertEqual(parsed.storyboard[1].audio_desc, "")
        self.assertIn("猫", parsed.storyboard[0].visual_desc)

    def test_clear_error_includes_preview(self):
        with self.assertRaises(OutputParserException) as ctx:
            self.parser.parse("not json at all — totally broken")
        message = str(ctx.exception)
        self.assertIn("after JSON repair", message)
        self.assertIn("Preview:", message)
        self.assertIn("StoryboardResponse", message)


class RobustParserDecompositionTests(unittest.TestCase):
    def setUp(self):
        self.parser = RobustPydanticOutputParser(pydantic_object=VisDescDecompositionResponse)

    def test_variation_type_case_folded(self):
        dirty = (
            '{"ff_desc":"a","ff_vis_char_idxs":[0],"lf_desc":"b","lf_vis_char_idxs":[],'
            '"motion_desc":"m","variation_type":"Small","variation_reason":"r"}'
        )
        parsed = self.parser.parse(dirty)
        self.assertEqual(parsed.variation_type, "small")

    def test_fenced_decomposition_with_trailing_comma(self):
        dirty = (
            "```json\n"
            '{"ff_desc":"首帧","ff_vis_char_idxs":[],"lf_desc":"末帧","lf_vis_char_idxs":[],'
            '"motion_desc":"静止镜头","variation_type":"small","variation_reason":"微调",}\n'
            "```"
        )
        parsed = self.parser.parse(dirty)
        self.assertEqual(parsed.ff_desc, "首帧")
        self.assertEqual(parsed.variation_type, "small")


class RepairHelpersUnitTests(unittest.TestCase):
    def test_repair_and_parse_json_returns_normalized_dict(self):
        value = repair_and_parse_json(
            'Here:\n{"shots": [{"idx": 0, "is_last": true, "cam_idx": 0, "visual_desc": "v", "audio_desc": null,}]}\n',
            StoryboardResponse,
        )
        self.assertIn("storyboard", value)
        self.assertEqual(value["storyboard"][0]["audio_desc"], "")


class DeepSeekEmptyContentReasoningFallbackTests(unittest.TestCase):
    """DeepSeek-V4.1-Flash on Thunisoft often returns content='' and JSON in reasoning."""

    def test_camera_tree_parses_json_from_reasoning_when_content_empty(self):
        payload = {
            "camera_parent_items": [
                {
                    "parent_cam_idx": None,
                    "parent_shot_idx": None,
                    "reason": "CAMERA_0 establishes the scene",
                    "is_parent_fully_covers_child": None,
                    "missing_info": None,
                },
                {
                    "parent_cam_idx": 0,
                    "parent_shot_idx": 0,
                    "reason": "Close-up covered by wide shot",
                    "is_parent_fully_covers_child": True,
                    "missing_info": None,
                },
            ]
        }
        import json

        reasoning = json.dumps(payload, ensure_ascii=False)
        message = AIMessage(content="", additional_kwargs={"reasoning": reasoning})
        generation = ChatGeneration(message=message)
        parser = TrailingCommaTolerantPydanticOutputParser(pydantic_object=CameraTreeResponse)
        parsed = parser.parse_result([generation])
        self.assertEqual(len(parsed.camera_parent_items), 2)
        self.assertIsNone(parsed.camera_parent_items[0].parent_cam_idx)
        self.assertEqual(parsed.camera_parent_items[1].parent_cam_idx, 0)

    def test_empty_content_without_reasoning_is_clear_retryable_error(self):
        parser = TrailingCommaTolerantPydanticOutputParser(pydantic_object=CameraTreeResponse)
        with self.assertRaises(OutputParserException) as ctx:
            parser.parse("   ")
        message = str(ctx.exception)
        self.assertIn("empty content", message.lower())
        self.assertIn("CameraTreeResponse", message)
        self.assertIn("thinking", message.lower())

    def test_camera_tree_uses_tolerant_parser_alias(self):
        from agents import camera_image_generator as cig
        from agents import storyboard_artist as sba

        self.assertIs(cig.PydanticOutputParser, TrailingCommaTolerantPydanticOutputParser)
        self.assertIs(sba.PydanticOutputParser, TrailingCommaTolerantPydanticOutputParser)


if __name__ == "__main__":
    unittest.main()
