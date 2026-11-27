"""Ask Claude through the Messages API."""

import json
import os
import urllib.request


def _entry():
    """Return the answer writer module the rest of the project imports."""
    import answer_reply

    return answer_reply

def _api_key():
    return os.environ.get(_entry().KEY_ENV, "").strip()


def _model_name():
    chosen = os.environ.get(_entry().MODEL_ENV, "").strip()
    return chosen or _entry().DEFAULT_MODEL


def _message_text(body):
    """Return the text blocks from a Messages API response."""
    if not isinstance(body, dict):
        return ""
    content = body.get("content")
    if not isinstance(content, list):
        return ""
    parts = []
    for block in content:
        if not isinstance(block, dict) or block.get("type") != "text":
            continue
        text = block.get("text")
        if isinstance(text, str) and text.strip():
            parts.append(text.strip())
    return "\n".join(parts).strip()


def _post_message(payload, key, timeout):
    """POST one Messages API request. The key travels in the header only."""
    request = urllib.request.Request(
        _entry().MESSAGES_URL,
        data=json.dumps(payload).encode("utf-8"),
        method="POST",
        headers={
            "content-type": "application/json",
            "x-api-key": key,
            "anthropic-version": _entry().API_VERSION,
        },
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        raw = response.read().decode("utf-8")
    return json.loads(raw)


def _claude_reply(instructions, client=None):
    """Ask Claude with the instructions already built for this question."""
    payload = {
        "model": _model_name(),
        "max_tokens": _entry().MAX_TOKENS,
        "output_config": {"effort": "low"},
        "messages": [{"role": "user", "content": instructions}],
    }
    if client is not None:
        body = client(payload)
    else:
        key = _api_key()
        if not key:
            raise RuntimeError("missing key")
        body = _entry()._post_message(payload, key, _entry().TIMEOUT_SECONDS)
    text = _message_text(body)
    if not text:
        raise ValueError("empty reply")
    return text
