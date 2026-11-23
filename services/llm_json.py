"""
Safe handling of model replies that are meant to be JSON.

request_json asks the model, strips any code fences, parses the JSON,
checks its shape, and asks once more if any of that fails. If the second
reply is also unusable it raises ModelReplyError, which main.py turns
into a 502 response with a readable message.
"""
import json
import logging
import re
from typing import Any, Callable

from pydantic import BaseModel, TypeAdapter, ValidationError

logger = logging.getLogger(__name__)

_FENCE = re.compile(r"```[ \t]*(?:json|JSON)?[ \t]*\r?\n?(.*?)```", re.DOTALL)


class InvalidReply(ValueError):
    """A single model reply could not be used."""


class ModelReplyError(Exception):
    """The model gave no usable reply after retrying. Shown to the client."""


def strip_code_fences(raw: str) -> str:
    """Return the JSON text from a reply that may be wrapped in ``` fences."""
    text = raw.strip()
    match = _FENCE.search(text)
    if match:
        return match.group(1).strip()
    if text.startswith("```"):
        # Opening fence with no closing fence (e.g. a truncated reply)
        text = text[3:]
        if text[:4].lower() == "json":
            text = text[4:]
    return text.strip()


def parse_json_reply(raw: str, schema: TypeAdapter) -> Any:
    """Parse and validate one reply. Raises InvalidReply on any problem."""
    if raw is None or not raw.strip():
        raise InvalidReply("empty reply")

    # Try the reply as it is first, so fences inside JSON strings (for
    # example in a code example) are left alone.
    candidates = [raw.strip()]
    stripped = strip_code_fences(raw)
    if stripped != candidates[0]:
        candidates.append(stripped)

    data, parse_error = None, None
    for text in candidates:
        try:
            data = json.loads(text)
            break
        except json.JSONDecodeError as exc:
            parse_error = exc
    else:
        raise InvalidReply(f"not valid JSON: {parse_error}")

    try:
        validated = schema.validate_python(data)
    except ValidationError as exc:
        raise InvalidReply(f"unexpected shape: {exc.error_count()} error(s): "
                           f"{exc.errors()[0]['msg']}") from exc
    return _plain(validated)


def _plain(value: Any) -> Any:
    """
    Convert validated models back to dicts. exclude_unset keeps exactly the
    fields the model sent (plus extras), with values coerced to their
    declared types, e.g. "false" -> False.
    """
    if isinstance(value, BaseModel):
        return value.model_dump(exclude_unset=True)
    if isinstance(value, list):
        return [_plain(v) for v in value]
    return value


def request_json(
    call: Callable[[], str],
    schema: TypeAdapter,
    what: str,
    attempts: int = 2,
) -> Any:
    """
    Call the model and return its parsed JSON reply (as plain dicts/lists).
    Retries once (attempts=2) before raising ModelReplyError.
    """
    last_error = None
    for attempt in range(1, attempts + 1):
        raw = call()
        try:
            return parse_json_reply(raw, schema)
        except InvalidReply as exc:
            last_error = exc
            logger.warning("Unusable %s reply (attempt %d/%d): %s",
                           what, attempt, attempts, exc)

    raise ModelReplyError(
        f"The AI model returned an unusable {what}. Please try again."
    ) from last_error
