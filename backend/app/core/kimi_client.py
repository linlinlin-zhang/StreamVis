from __future__ import annotations

import json
import socket
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any, Dict, Iterable, Iterator, List, Optional


class KimiError(RuntimeError):
    pass


@dataclass(frozen=True)
class KimiStreamChunk:
    delta: str
    is_done: bool = False
    raw: Optional[Dict[str, Any]] = None


def _http_post_json(
    url: str,
    *,
    headers: Dict[str, str],
    body: Dict[str, Any],
    timeout_s: float,
) -> Dict[str, Any]:
    data = json.dumps(body).encode("utf-8")
    req = urllib.request.Request(url, data=data, method="POST")
    for k, v in headers.items():
        req.add_header(k, v)
    try:
        with urllib.request.urlopen(req, timeout=timeout_s) as resp:
            raw = resp.read().decode("utf-8")
            return json.loads(raw) if raw else {}
    except urllib.error.HTTPError as e:
        raw = e.read().decode("utf-8") if e.fp else ""
        raise KimiError(f"http_error status={e.code} body={raw}") from e
    except Exception as e:
        raise KimiError(str(e)) from e


def _iter_sse_events(fp) -> Iterator[str]:
    buf: List[str] = []
    for raw_line in fp:
        line = raw_line.decode("utf-8", errors="ignore").rstrip("\n")
        if not line:
            if buf:
                yield "\n".join(buf)
                buf = []
            continue
        if line.startswith("data:"):
            buf.append(line[5:].lstrip())
    if buf:
        yield "\n".join(buf)


class KimiClient:
    def __init__(
        self,
        *,
        api_key: str,
        base_url: str,
        model: str,
        timeout_s: float = 60.0,
    ) -> None:
        if not api_key:
            raise ValueError("api_key required")
        if not base_url:
            raise ValueError("base_url required")
        if not model:
            raise ValueError("model required")
        self._api_key = api_key
        self._base_url = base_url.rstrip("/")
        self._model = model
        self._timeout_s = timeout_s

    def _headers(self) -> Dict[str, str]:
        return {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }

    def chat(
        self,
        *,
        messages: List[Dict[str, Any]],
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        tools: Optional[List[Dict[str, Any]]] = None,
        tool_choice: Optional[Any] = None,
        stream: bool = False,
    ) -> Dict[str, Any]:
        temp = float(temperature)
        if temp < 0.0:
            temp = 0.0
        if temp > 1.0:
            temp = 1.0
        if "kimi-k2.5" in self._model:
            temp = 1.0

        payload: Dict[str, Any] = {
            "model": self._model,
            "messages": messages,
            "temperature": temp,
            "stream": bool(stream),
        }
        if max_tokens is not None:
            payload["max_tokens"] = int(max_tokens)
        if tools:
            payload["tools"] = tools
        if tool_choice is not None:
            payload["tool_choice"] = tool_choice

        return _http_post_json(
            f"{self._base_url}/chat/completions",
            headers=self._headers(),
            body=payload,
            timeout_s=self._timeout_s,
        )

    def stream_chat(
        self,
        *,
        messages: List[Dict[str, Any]],
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        tools: Optional[List[Dict[str, Any]]] = None,
    ) -> Iterable[KimiStreamChunk]:
        temp = float(temperature)
        if temp < 0.0:
            temp = 0.0
        if temp > 1.0:
            temp = 1.0
        if "kimi-k2.5" in self._model:
            temp = 1.0

        payload: Dict[str, Any] = {
            "model": self._model,
            "messages": messages,
            "temperature": temp,
            "stream": True,
        }
        if max_tokens is not None:
            payload["max_tokens"] = int(max_tokens)
        if tools:
            payload["tools"] = tools

        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(f"{self._base_url}/chat/completions", data=data, method="POST")
        for k, v in self._headers().items():
            req.add_header(k, v)

        try:
            with urllib.request.urlopen(req, timeout=self._timeout_s) as resp:
                for event in _iter_sse_events(resp):
                    if event.strip() == "[DONE]":
                        yield KimiStreamChunk(delta="", is_done=True)
                        return
                    try:
                        obj = json.loads(event)
                    except Exception:
                        continue
                    choices = obj.get("choices") or []
                    if not choices:
                        continue
                    delta_obj = (choices[0] or {}).get("delta") or {}
                    delta = delta_obj.get("content")
                    if delta:
                        yield KimiStreamChunk(delta=str(delta), raw=obj)
                yield KimiStreamChunk(delta="", is_done=True)
        except urllib.error.HTTPError as e:
            raw = e.read().decode("utf-8") if e.fp else ""
            raise KimiError(f"http_error status={e.code} body={raw}") from e
        except socket.timeout as e:
            raise KimiError("timeout") from e
        except Exception as e:
            raise KimiError(str(e)) from e
