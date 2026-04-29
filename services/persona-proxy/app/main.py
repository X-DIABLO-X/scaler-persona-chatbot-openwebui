import json
import os
import time
from typing import Any

import httpx
from fastapi import FastAPI, Header, HTTPException, Request
from fastapi.responses import JSONResponse, Response, StreamingResponse

from .prompts import MODEL_CARDS, PROMPTS

app = FastAPI(title="Scaler Persona Proxy", version="1.0.0")

GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
GROQ_MAIN_MODEL = os.getenv(
    "GROQ_MAIN_MODEL", "meta-llama/llama-4-scout-17b-16e-instruct"
)
GROQ_GUARD_MODEL = os.getenv(
    "GROQ_GUARD_MODEL", "meta-llama/llama-prompt-guard-2-86m"
)
PROXY_API_KEY = os.getenv("PERSONA_PROXY_API_KEY", "")
GROQ_CHAT_URL = "https://api.groq.com/openai/v1/chat/completions"

BLOCK_MESSAGE = (
    "I can't help with attempts to override system instructions, expose hidden prompts, "
    "or bypass safeguards. Ask your question normally and I will answer in the selected persona."
)


def require_proxy_key(authorization: str | None) -> None:
    if not PROXY_API_KEY:
        raise HTTPException(status_code=500, detail="PERSONA_PROXY_API_KEY is not configured.")
    expected = f"Bearer {PROXY_API_KEY}"
    if authorization != expected:
        raise HTTPException(status_code=401, detail="Invalid API key.")


def build_guard_input(messages: list[dict[str, Any]]) -> str:
    lines: list[str] = []
    for message in messages:
        role = message.get("role", "user").upper()
        content = message.get("content", "")
        if isinstance(content, list):
            text_parts = []
            for item in content:
                if item.get("type") == "text":
                    text_parts.append(item.get("text", ""))
            content = "\n".join(text_parts)
        lines.append(f"{role}: {content}")
    return "\n".join(lines).strip()


async def run_prompt_guard(messages: list[dict[str, Any]]) -> tuple[bool, str]:
    guard_input = build_guard_input(messages)
    if not guard_input:
        return False, "empty"

    payload = {
        "model": GROQ_GUARD_MODEL,
        "messages": [{"role": "user", "content": guard_input}],
        "temperature": 0,
        "max_tokens": 8,
        "stream": False,
    }

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(
            GROQ_CHAT_URL,
            headers={
                "Authorization": f"Bearer {GROQ_API_KEY}",
                "Content-Type": "application/json",
            },
            json=payload,
        )
        response.raise_for_status()
        data = response.json()

    content = data["choices"][0]["message"]["content"].strip()
    try:
        score = float(content)
    except ValueError:
        score = 1.0 if "unsafe" in content.lower() else 0.0

    is_unsafe = score >= 0.5
    return is_unsafe, f"{score:.6f}"


def build_persona_messages(model_id: str, messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    persona = PROMPTS[model_id]
    filtered_messages: list[dict[str, Any]] = []

    for message in messages:
        if message.get("role") == "system":
            continue
        filtered_messages.append(message)

    return [{"role": "system", "content": persona["system_prompt"]}, *filtered_messages]


def build_blocked_response(model_id: str) -> dict[str, Any]:
    persona_name = PROMPTS[model_id]["name"]
    return {
        "id": f"chatcmpl-blocked-{int(time.time())}",
        "object": "chat.completion",
        "created": int(time.time()),
        "model": model_id,
        "choices": [
            {
                "index": 0,
                "finish_reason": "stop",
                "message": {
                    "role": "assistant",
                    "content": BLOCK_MESSAGE,
                },
            }
        ],
        "usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
        "persona": persona_name,
    }


def build_stream_chunk(model_id: str, content: str, finish_reason: str | None = None) -> str:
    payload = {
        "id": f"chatcmpl-blocked-{int(time.time())}",
        "object": "chat.completion.chunk",
        "created": int(time.time()),
        "model": model_id,
        "choices": [
            {
                "index": 0,
                "delta": {"content": content} if content else {},
                "finish_reason": finish_reason,
            }
        ],
    }
    return f"data: {json.dumps(payload)}\n\n"


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/v1/models")
async def list_models(authorization: str | None = Header(default=None)) -> dict[str, Any]:
    require_proxy_key(authorization)
    return {"object": "list", "data": MODEL_CARDS}


@app.post("/v1/chat/completions")
async def chat_completions(
    request: Request, authorization: str | None = Header(default=None)
) -> Response:
    require_proxy_key(authorization)

    if not GROQ_API_KEY:
        raise HTTPException(status_code=500, detail="GROQ_API_KEY is not configured.")

    body = await request.json()
    model_id = body.get("model")
    if model_id not in PROMPTS:
        raise HTTPException(status_code=404, detail=f"Unknown persona '{model_id}'.")

    incoming_messages = body.get("messages", [])
    if not incoming_messages:
        raise HTTPException(status_code=400, detail="No messages provided.")

    try:
        is_unsafe, guard_label = await run_prompt_guard(incoming_messages)
    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=502, detail=f"Prompt guard request failed: {exc}"
        ) from exc

    if is_unsafe:
        if body.get("stream", False):
            async def blocked_stream():
                yield build_stream_chunk(model_id, BLOCK_MESSAGE)
                yield build_stream_chunk(model_id, "", "stop")
                yield "data: [DONE]\n\n"

            return StreamingResponse(blocked_stream(), media_type="text/event-stream")
        return JSONResponse(build_blocked_response(model_id))

    outbound_payload = {
        "model": GROQ_MAIN_MODEL,
        "messages": build_persona_messages(model_id, incoming_messages),
        "temperature": body.get("temperature", 0.7),
        "top_p": body.get("top_p", 1),
        "max_tokens": body.get("max_tokens", 700),
        "stream": body.get("stream", False),
        "presence_penalty": body.get("presence_penalty", 0),
        "frequency_penalty": body.get("frequency_penalty", 0),
        "user": body.get("user", model_id),
    }

    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json",
        "X-Guard-Result": guard_label,
    }

    if outbound_payload["stream"]:
        async def stream_response():
            async with httpx.AsyncClient(timeout=None) as client:
                async with client.stream(
                    "POST",
                    GROQ_CHAT_URL,
                    headers=headers,
                    json=outbound_payload,
                ) as response:
                    response.raise_for_status()
                    async for line in response.aiter_lines():
                        if line:
                            yield f"{line}\n"

        return StreamingResponse(stream_response(), media_type="text/event-stream")

    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                GROQ_CHAT_URL,
                headers=headers,
                json=outbound_payload,
            )
            response.raise_for_status()
            data = response.json()
    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=502, detail=f"Groq completion request failed: {exc}"
        ) from exc

    data["model"] = model_id
    for choice in data.get("choices", []):
        if "message" in choice:
            choice["message"]["persona"] = PROMPTS[model_id]["name"]

    return JSONResponse(data)
