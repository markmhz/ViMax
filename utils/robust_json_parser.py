# OpenAI-compatible chat endpoints (gemini-flash-lite, DeepSeek via custom
# gateways, etc.) often emit structured JSON that is *almost* valid:
# trailing commas, markdown fences, prose around the payload, JSON-schema
# "properties" wrappers, nulls for string fields, or slightly wrong keys.
# Stock LangChain PydanticOutputParser raises OutputParserException and the
# @retry loop resamples the LLM — often failing the same way again.
#
# Repair locally before giving up so idea2video storyboard/shots planning
# (and other agents using this parser) survive noisy model output.
from __future__ import annotations

import json
import re
from typing import Any, List, get_args, get_origin

from langchain_core.exceptions import OutputParserException
from langchain_core.output_parsers import PydanticOutputParser
from langchain_core.outputs import Generation
from pydantic import BaseModel, ValidationError

_TRAILING_COMMA_RE = re.compile(r",(\s*[}\]])")
_FENCE_RE = re.compile(
    r"^\s*```(?:json|JSON|Json)?\s*\r?\n(?P<body>.*?)```\s*$",
    re.DOTALL,
)
# Common alternate list keys when the schema expects `storyboard`.
_LIST_KEY_ALIASES = {
    "storyboard": ("shots", "shot_list", "shot_brief_descriptions", "items", "data"),
}


def strip_trailing_commas(text: str) -> str:
    return _TRAILING_COMMA_RE.sub(r"\1", text)


def strip_markdown_fences(text: str) -> str:
    """Remove a surrounding ``` / ```json fence if the whole string is fenced."""
    if not text:
        return text
    match = _FENCE_RE.match(text.strip())
    if match:
        return match.group("body").strip()
    stripped = text.strip()
    if stripped.startswith("```"):
        lines = stripped.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        return "\n".join(lines).strip()
    return text


def extract_json_value(text: str) -> Any:
    """Parse the first JSON object/array in text, tolerating leading/trailing prose."""
    if text is None:
        raise json.JSONDecodeError("Expecting value", "", 0)
    cleaned = strip_markdown_fences(str(text))
    cleaned = strip_trailing_commas(cleaned.strip())
    decoder = json.JSONDecoder()
    for index, char in enumerate(cleaned):
        if char not in "{[":
            continue
        try:
            value, _end = decoder.raw_decode(cleaned[index:])
            return value
        except json.JSONDecodeError:
            continue
    # Last resort: whole string after comma strip.
    return json.loads(cleaned)


def _unwrap_properties(value: Any) -> Any:
    if isinstance(value, dict) and isinstance(value.get("properties"), dict) and len(value) <= 3:
        # JSON-schema-ish wrapper: {"properties": {...}, "type": "object"}
        inner = value["properties"]
        if isinstance(inner, dict):
            return inner
    return value


def _alias_list_keys(value: Any, model: type[BaseModel]) -> Any:
    if not isinstance(value, dict):
        return value
    fields = getattr(model, "model_fields", {})
    for field_name, aliases in _LIST_KEY_ALIASES.items():
        if field_name not in fields or field_name in value:
            continue
        for alias in aliases:
            if alias in value:
                value = dict(value)
                value[field_name] = value.pop(alias)
                break
    return value


def _wrap_root_list(value: Any, model: type[BaseModel]) -> Any:
    """If the model expects a single list field and the model returned a bare list, wrap it."""
    if not isinstance(value, list):
        return value
    fields = getattr(model, "model_fields", {})
    list_fields = [
        name
        for name, field in fields.items()
        if get_origin(field.annotation) in (list, List) or field.annotation is list
    ]
    if len(list_fields) == 1:
        return {list_fields[0]: value}
    return value


def _literal_strings(annotation: Any) -> tuple[str, ...] | None:
    origin = get_origin(annotation)
    # typing.Literal origin compares equal to Literal itself across versions.
    if origin is None:
        return None
    args = get_args(annotation)
    if args and all(isinstance(item, str) for item in args):
        # Distinguish Literal["a"] from Optional[str] / Union — Literal args are all strings
        # and origin's name is Literal.
        if getattr(origin, "__name__", str(origin)) == "Literal" or str(origin) == "typing.Literal":
            return tuple(args)
    return None


def _coerce_null_strings(value: Any, model: type[BaseModel]) -> Any:
    """Replace null with '' for required str fields (common LLM slip)."""
    if not isinstance(value, dict):
        return value
    fields = getattr(model, "model_fields", {})
    out = dict(value)
    for name, field in fields.items():
        if name not in out or out[name] is not None:
            continue
        if field.annotation is str:
            out[name] = ""
    return out


def _normalize_literal_case(value: Any, model: type[BaseModel]) -> Any:
    """Case-fold string literals when the schema uses lowercase enums (e.g. variation_type)."""
    if not isinstance(value, dict):
        return value
    fields = getattr(model, "model_fields", {})
    out = dict(value)
    for name, field in fields.items():
        if name not in out or not isinstance(out[name], str):
            continue
        allowed = _literal_strings(field.annotation)
        if not allowed:
            continue
        raw = out[name].strip()
        lowered = raw.lower()
        if lowered in allowed:
            out[name] = lowered
            continue
        for item in allowed:
            if item.lower() == raw.lower():
                out[name] = item
                break
    return out


def normalize_structured_payload(value: Any, model: type[BaseModel]) -> Any:
    """Apply light schema-friendly normalizations before pydantic validation."""
    value = _unwrap_properties(value)
    value = _wrap_root_list(value, model)
    value = _alias_list_keys(value, model)
    value = _coerce_null_strings(value, model)
    value = _normalize_literal_case(value, model)
    if isinstance(value, dict):
        fields = getattr(model, "model_fields", {})
        for name, field in fields.items():
            if name not in value or not isinstance(value[name], list):
                continue
            args = get_args(field.annotation)
            if not args:
                continue
            item_type = args[0]
            if isinstance(item_type, type) and issubclass(item_type, BaseModel):
                value = dict(value)
                value[name] = [
                    normalize_structured_payload(item, item_type) if isinstance(item, dict) else item
                    for item in value[name]
                ]
    return value


def repair_and_parse_json(text: str, model: type[BaseModel]) -> Any:
    """Extract + normalize JSON text into a value suitable for model_validate."""
    value = extract_json_value(text)
    return normalize_structured_payload(value, model)


def _preview(text: str, limit: int = 240) -> str:
    compact = " ".join(str(text or "").split())
    if len(compact) <= limit:
        return compact
    return compact[: limit - 3] + "..."


def _message_reasoning_text(message: Any) -> str:
    """Pull reasoning / thinking text DeepSeek-style gateways stash when content is empty."""
    if message is None:
        return ""
    chunks: list[str] = []
    additional = getattr(message, "additional_kwargs", None) or {}
    metadata = getattr(message, "response_metadata", None) or {}
    for source in (additional, metadata):
        if not isinstance(source, dict):
            continue
        for key in ("reasoning", "reasoning_content", "reasoning_text", "thinking", "thought"):
            value = source.get(key)
            if isinstance(value, str) and value.strip():
                chunks.append(value)
            elif isinstance(value, dict):
                nested = value.get("content") or value.get("text")
                if isinstance(nested, str) and nested.strip():
                    chunks.append(nested)
    # Some gateways put reasoning on the message itself.
    for attr in ("reasoning", "reasoning_content"):
        value = getattr(message, attr, None)
        if isinstance(value, str) and value.strip():
            chunks.append(value)
    return "\n".join(chunks)


def generation_text_candidates(generation: Generation) -> list[str]:
    """Ordered text candidates to parse: content first, then reasoning fallbacks."""
    seen: set[str] = set()
    candidates: list[str] = []

    def _add(text: Any) -> None:
        if not isinstance(text, str):
            return
        stripped = text.strip()
        if not stripped or stripped in seen:
            return
        seen.add(stripped)
        candidates.append(text)

    _add(getattr(generation, "text", None))
    message = getattr(generation, "message", None)
    if message is not None:
        content = getattr(message, "content", None)
        if isinstance(content, str):
            _add(content)
        elif isinstance(content, list):
            parts = []
            for block in content:
                if isinstance(block, str):
                    parts.append(block)
                elif isinstance(block, dict) and isinstance(block.get("text"), str):
                    parts.append(block["text"])
            _add("\n".join(parts))
        _add(_message_reasoning_text(message))
    info = getattr(generation, "generation_info", None) or {}
    if isinstance(info, dict):
        for key in ("reasoning", "reasoning_content", "thinking"):
            _add(info.get(key))
    return candidates


class TrailingCommaTolerantPydanticOutputParser(PydanticOutputParser):
    """PydanticOutputParser that repairs common OpenAI-compatible JSON glitches."""

    def parse_result(self, result: List[Generation], *, partial: bool = False):
        try:
            return super().parse_result(result, partial=partial)
        except (OutputParserException, ValidationError) as first_error:
            if not result:
                raise
            generation = result[0]
            candidates = generation_text_candidates(generation)
            if not candidates:
                model_name = getattr(self.pydantic_object, "__name__", "model")
                raise OutputParserException(
                    f"Failed to parse {model_name}: model returned empty content "
                    f"(and no reasoning text to fall back on). This is often caused by "
                    f"thinking/reasoning models exhausting max_completion_tokens before "
                    f"emitting JSON. Retryable after disabling thinking or raising max tokens. "
                    f"Preview: ''. Parser error: {first_error}"
                ) from first_error
            last_error: Exception = first_error
            for candidate in candidates:
                try:
                    return self._parse_repaired(candidate)
                except Exception as repair_error:  # noqa: PERF203 — try each candidate
                    last_error = repair_error
            model_name = getattr(self.pydantic_object, "__name__", "model")
            raise OutputParserException(
                f"Failed to parse {model_name} from model output after JSON repair. "
                f"Preview: {_preview(candidates[0])!r}. "
                f"Parser error: {first_error}. Repair error: {last_error}"
            ) from last_error

    def parse(self, text: str):
        if not isinstance(text, str) or not text.strip():
            model_name = getattr(self.pydantic_object, "__name__", "model")
            raise OutputParserException(
                f"Failed to parse {model_name}: model returned empty content. "
                f"Retryable after disabling thinking or raising max tokens. Preview: ''."
            )
        try:
            return super().parse(text)
        except (OutputParserException, ValidationError) as first_error:
            try:
                return self._parse_repaired(text)
            except Exception as repair_error:
                model_name = getattr(self.pydantic_object, "__name__", "model")
                raise OutputParserException(
                    f"Failed to parse {model_name} from model output after JSON repair. "
                    f"Preview: {_preview(text)!r}. "
                    f"Parser error: {first_error}. Repair error: {repair_error}"
                ) from repair_error

    def _parse_repaired(self, text: str):
        if not isinstance(text, str) or not text.strip():
            raise OutputParserException("Empty model output; nothing to repair")
        payload = repair_and_parse_json(text, self.pydantic_object)
        return self.pydantic_object.model_validate(payload)


# Backward-compatible / clearer alias.
RobustPydanticOutputParser = TrailingCommaTolerantPydanticOutputParser
