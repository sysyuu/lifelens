"""Unified LLM client via ModelGate (OpenAI-compatible API)."""

import json
import base64
import logging
from typing import Optional

from openai import AsyncOpenAI

from server.config import settings

logger = logging.getLogger(__name__)

_client: Optional[AsyncOpenAI] = None


def get_client() -> AsyncOpenAI:
    global _client
    if _client is None:
        _client = AsyncOpenAI(
            api_key=settings.modelgate.api_key,
            base_url=settings.modelgate.base_url,
        )
    return _client


def _fix_llm_json(text: str) -> str:
    """Attempt to fix common JSON issues from LLM output.

    The most common issue is unescaped double quotes inside string values.
    Strategy: walk through the text character by character, tracking whether
    we are inside a JSON string. When we encounter a quote that appears to be
    inside a string value (not a structural delimiter), escape it.
    """
    result = []
    in_string = False
    i = 0
    n = len(text)

    while i < n:
        ch = text[i]

        if ch == '\\' and in_string:
            # Escaped character — copy both chars
            result.append(ch)
            if i + 1 < n:
                i += 1
                result.append(text[i])
            i += 1
            continue

        if ch == '"':
            if not in_string:
                # Opening a string
                in_string = True
                result.append(ch)
            else:
                # We're inside a string and hit a quote.
                # Look ahead to see if this is a structural close-quote:
                # after it we expect optional whitespace then one of: , } ] :
                rest = text[i + 1:].lstrip()
                if not rest or rest[0] in (',', '}', ']', ':'):
                    # Structural close quote
                    in_string = False
                    result.append(ch)
                else:
                    # Unescaped quote inside string — escape it
                    result.append('\\"')
            i += 1
            continue

        result.append(ch)
        i += 1

    return ''.join(result)


async def chat_completion(
    model: str,
    system_prompt: str,
    user_content: str | list,
    temperature: float = 0.7,
    max_tokens: int = 8192,
    response_format: Optional[dict] = None,
) -> dict:
    """Send a chat completion request and return parsed response with usage stats.

    Args:
        model: Model ID (e.g. "Claude-Opus-4.6")
        system_prompt: System message content
        user_content: Either a string or a list of content parts (for multimodal)
        temperature: Sampling temperature
        max_tokens: Max output tokens
        response_format: Optional response format constraint

    Returns:
        {"content": str, "token_usage": dict}
    """
    client = get_client()

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_content},
    ]

    kwargs = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
    }
    if response_format:
        kwargs["response_format"] = response_format

    response = await client.chat.completions.create(**kwargs)

    content = response.choices[0].message.content or ""
    token_usage = {}
    if response.usage:
        token_usage = {
            "prompt_tokens": response.usage.prompt_tokens,
            "completion_tokens": response.usage.completion_tokens,
            "total_tokens": response.usage.total_tokens,
        }

    return {"content": content, "token_usage": token_usage}


async def chat_completion_json(
    model: str,
    system_prompt: str,
    user_content: str | list,
    temperature: float = 0.3,
    max_tokens: int = 8192,
) -> dict:
    """Send a chat completion and parse the response as JSON.

    Uses lower temperature by default for structured output.
    """
    result = await chat_completion(
        model=model,
        system_prompt=system_prompt,
        user_content=user_content,
        temperature=temperature,
        max_tokens=max_tokens,
    )

    content = result["content"].strip()

    # Strip markdown code fences if present (handles ```json ... ``` and ``` ... ```)
    import re
    fence_match = re.search(r'```(?:json)?\s*\n([\s\S]*?)\n\s*```', content)
    if fence_match:
        content = fence_match.group(1).strip()
    elif content.startswith("```"):
        lines = content.split("\n")
        lines = lines[1:]  # Remove opening fence
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        content = "\n".join(lines)

    try:
        parsed = json.loads(content)
    except json.JSONDecodeError as e:
        logger.warning(f"JSON parse attempt 1 failed: {e}")
        # Try to fix common LLM JSON issues: unescaped quotes inside strings
        try:
            parsed = json.loads(_fix_llm_json(content))
            logger.info("JSON parse succeeded after fix_llm_json")
        except json.JSONDecodeError:
            logger.error(f"Failed to parse JSON from LLM response even after fix: {content[:500]}")
            parsed = {"raw_content": content, "parse_error": True}

    return {"data": parsed, "token_usage": result["token_usage"]}


async def vision_completion(
    model: str,
    system_prompt: str,
    video_base64: str,
    mime_type: str = "video/mp4",
    additional_text: str = "",
    temperature: float = 0.3,
    max_tokens: int = 8192,
) -> dict:
    """Send a vision/video understanding request.

    For Gemini 2.5 Pro via ModelGate, we send video as base64 inline data
    using the OpenAI-compatible multimodal format.
    """
    content_parts = []

    # Video as image_url with base64 data URI
    data_uri = f"data:{mime_type};base64,{video_base64}"
    content_parts.append({
        "type": "image_url",
        "image_url": {"url": data_uri},
    })

    if additional_text:
        content_parts.append({
            "type": "text",
            "text": additional_text,
        })

    return await chat_completion_json(
        model=model,
        system_prompt=system_prompt,
        user_content=content_parts,
        temperature=temperature,
        max_tokens=max_tokens,
    )


def encode_video_base64(file_path: str) -> str:
    """Read a video file and return base64 encoded string."""
    with open(file_path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")
