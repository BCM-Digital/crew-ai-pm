from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Dict, Optional
import requests

from ..memory import memory


@dataclass
class Tool:
    name: str
    description: str
    args_schema: Dict[str, Any]
    handler: Callable[[Dict[str, Any]], Any]


def http_get_tool(args: Dict[str, Any]) -> Dict[str, Any]:
    url = args.get("url")
    headers = args.get("headers") or {}
    timeout = int(args.get("timeout", 15))
    if not url:
        return {"error": "missing url"}
    resp = requests.get(url, headers=headers, timeout=timeout)
    text = resp.text[:20000]
    return {"status": resp.status_code, "text": text}


def memory_add_tool(args: Dict[str, Any]) -> Dict[str, Any]:
    text: str = args.get("text", "")
    meta: Dict[str, Any] = args.get("metadata", {}) or {}
    if not text:
        return {"error": "missing text"}
    mem_id = memory.add(text=text, metadata=meta)
    return {"id": mem_id}


def memory_search_tool(args: Dict[str, Any]) -> Dict[str, Any]:
    query: str = args.get("query", "")
    top_k: int = int(args.get("top_k", 5))
    if not query:
        return {"error": "missing query"}
    results = memory.query(query, top_k=top_k)
    return {"results": [{"id": r.id, "text": r.text, "metadata": r.metadata} for r in results]}


def get_default_tools() -> list[Tool]:
    return [
        Tool(
            name="http_get",
            description="Fetch a URL over HTTP GET and return status and first 20k chars of text.",
            args_schema={"url": "string", "headers": "object?", "timeout": "int?"},
            handler=http_get_tool,
        ),
        Tool(
            name="memory_add",
            description="Store an important fact or summary in long-term memory.",
            args_schema={"text": "string", "metadata": "object?"},
            handler=memory_add_tool,
        ),
        Tool(
            name="memory_search",
            description="Search long-term memory for relevant items.",
            args_schema={"query": "string", "top_k": "int?"},
            handler=memory_search_tool,
        ),
    ]


def tool_by_name(name: str) -> Optional[Tool]:
    for t in get_default_tools():
        if t.name == name:
            return t
    return None