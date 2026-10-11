"""Guardrails for the soft workflow-selection gate in prompts/workflow.md."""

from __future__ import annotations

import unittest
from pathlib import Path


class WorkflowSoftGateTests(unittest.TestCase):
    def test_soft_gate_allows_clear_intent_without_forcing_clarification(self):
        text = (Path(__file__).resolve().parents[1] / "prompts" / "workflow.md").read_text(encoding="utf-8")
        self.assertIn("Workflow selection (soft gate)", text)
        self.assertIn("only ask when ambiguous", text)
        self.assertIn("you do **not** need them to type the word `idea2video`", text)
        self.assertIn("novel_path", text)
        self.assertIn("Ask which workflow only when the request is still ambiguous", text)


if __name__ == "__main__":
    unittest.main()
