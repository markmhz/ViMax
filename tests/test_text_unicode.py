"""Regression: lone UTF-16 surrogates must not crash UTF-8 encode / JSON dumps.

Windows idea2video prompts have failed with:
  turn failed: 'utf-8' codec can't encode character '\\udcaa' in position 4: surrogates not allowed
"""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from agent_runtime.prompts import PromptBuilder, PromptPart
from agent_runtime.session_index import SessionIndex
from agent_runtime.tools import build_builtin_registry
from utils.text import safe_json_dumps, scrub_surrogates, scrub_unicode_tree


# Lone low surrogate — same family as the Windows failure (`\\udcaa`).
LONE_SURROGATE = "\udcaa"
CHINESE_PROMPT = "做一个猫咪和狗见面的卡通短片"
DIRTY_PROMPT = f"做一{LONE_SURROGATE}个猫咪和狗见面的卡通短片"


class ScrubSurrogatesTests(unittest.TestCase):
    def test_lone_surrogate_cannot_utf8_encode_without_scrub(self):
        with self.assertRaises(UnicodeEncodeError):
            LONE_SURROGATE.encode("utf-8")

    def test_scrub_replaces_lone_surrogate(self):
        cleaned = scrub_surrogates(DIRTY_PROMPT)
        self.assertNotIn(LONE_SURROGATE, cleaned)
        self.assertEqual(cleaned.encode("utf-8").decode("utf-8"), cleaned)
        self.assertIn("猫咪", cleaned)
        self.assertIn("卡通短片", cleaned)

    def test_scrub_preserves_clean_chinese(self):
        self.assertEqual(scrub_surrogates(CHINESE_PROMPT), CHINESE_PROMPT)

    def test_scrub_unicode_tree_nested(self):
        payload = {"prompt": DIRTY_PROMPT, "items": [LONE_SURROGATE, {"k": DIRTY_PROMPT}]}
        cleaned = scrub_unicode_tree(payload)
        encoded = json.dumps(cleaned, ensure_ascii=False).encode("utf-8")
        self.assertNotIn(LONE_SURROGATE, encoded.decode("utf-8"))

    def test_safe_json_dumps_encodes_to_utf8(self):
        text = safe_json_dumps({"idea": DIRTY_PROMPT, "ok": True})
        raw = text.encode("utf-8")
        loaded = json.loads(raw.decode("utf-8"))
        self.assertEqual(loaded["ok"], True)
        self.assertNotIn(LONE_SURROGATE, loaded["idea"])
        self.assertIn("猫咪", loaded["idea"])


class PromptTraceSurrogateTests(unittest.TestCase):
    def test_trace_encodes_parts_with_lone_surrogates(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "prompts").mkdir()
            (root / "prompts" / "agent.md").write_text("agent rules", encoding="utf-8")
            (root / "prompts" / "workflow.md").write_text("workflow rules", encoding="utf-8")
            index = SessionIndex(root)
            index.create(idea="cat")
            registry = build_builtin_registry(root, index)
            builder = PromptBuilder(root / "prompts", index, registry)
            parts = [
                PromptPart("dirty", "dirty", DIRTY_PROMPT, "dynamic", "user"),
            ]
            # Previously: part.body.encode("utf-8") raised UnicodeEncodeError → turn failed.
            trace = builder.trace(parts)
            self.assertGreater(trace["total_estimated_tokens"], 0)
            self.assertEqual(trace["segments"][0]["bytes"], len(scrub_surrogates(DIRTY_PROMPT).encode("utf-8")))


class SessionLogSurrogateTests(unittest.TestCase):
    def test_append_log_and_save_tolerate_surrogates(self):
        with tempfile.TemporaryDirectory() as tmp:
            index = SessionIndex(Path(tmp))
            record = index.create(idea=DIRTY_PROMPT)
            index.append_log("loop_history", {
                "session_id": record["session_id"],
                "raw_user_input": DIRTY_PROMPT,
                "final_assistant_text": f"ok{LONE_SURROGATE}",
            })
            log_text = (index.logs_dir / "loop_history.jsonl").read_text(encoding="utf-8")
            log_text.encode("utf-8")  # must already be valid UTF-8
            self.assertNotIn(LONE_SURROGATE, log_text)
            payload = index.load()
            index.save(payload)
            saved = index.sessions_path.read_text(encoding="utf-8")
            saved.encode("utf-8")


class MainAgentCliSurrogateTests(unittest.IsolatedAsyncioTestCase):
    async def test_once_scrub_surrogate_before_runtime(self):
        import contextlib
        import io
        import sys

        import main_agent

        class Runtime:
            def __init__(self):
                self.inputs = []
                self.session_index = type("SI", (), {"snapshot": staticmethod(lambda: {"session": {}})})()

            async def stream_events(self, user_input):
                self.inputs.append(user_input)
                yield {"type": "turn", "turn_id": "t1", "turn": {"id": "t1"}}
                yield {"type": "done", "turn_id": "t1", "assistant": "ok", "tool_results": []}

        runtime = Runtime()
        stdout = io.StringIO()
        with patch.object(main_agent, "load_runtime", return_value=runtime), \
             patch.object(main_agent, "load_session_index", return_value=runtime.session_index), \
             patch.object(sys, "stdin", io.StringIO("")), \
             contextlib.redirect_stdout(stdout), \
             contextlib.redirect_stderr(io.StringIO()):
            code = await main_agent.amain(["--jsonl", "--once", DIRTY_PROMPT])
        self.assertEqual(code, 0)
        self.assertEqual(len(runtime.inputs), 1)
        self.assertNotIn(LONE_SURROGATE, runtime.inputs[0])
        for line in stdout.getvalue().splitlines():
            json.loads(line)  # valid JSONL
            line.encode("utf-8")


if __name__ == "__main__":
    unittest.main()
